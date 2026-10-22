'''
Created on 22 April 2026

@author: thomasgumbricht
'''

# Standard library imports
import os
import json
import glob
import time
from math import ceil

# Third-party imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Application package imports
from src.postgres import Get_schema_table
from src.postgres.pg_ai4sh import PG_manage_AI4SH

from src.ai4sh.chemometrics import (
    apply_transformations,
    apply_standardisation,
    apply_chemometrics,
    apply_scatter_correction,
    apply_scaling,
)

from src.ai4sh.filter import (
    apply_filter,
    apply_multi_filter,
    _load_filter_config,
)

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


# Repository root relative to src/ai4sh/plot.py.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))
)

_DEFAULT_SYMBOLS_FPN = os.path.join(
    _REPO_ROOT,
    'ai4sh',
    'default',
    'plot',
    'targetfeaturesymbols.json',
)


def _spectra_x_axis(columns):
    """Return appropriate x-axis values and a label."""
    if not columns:
        return [], 'x'

    first = str(columns[0])

    if first.startswith('pc'):
        return list(range(1, len(columns) + 1)), 'Component'

    try:
        vals = [
            int(str(c).lstrip('d'))
            for c in columns
        ]
        return vals, 'Wavelength (nm)'

    except (ValueError, TypeError):
        return list(range(len(columns))), 'Band'


def _step_to_abbrev(step_label):
    """
    Return a short abbreviation for a chemometric step.

    See ai4sh/default/chemometric/chemometric_abbreviations.md.
    """
    if step_label == 'raw':
        return 'raw'

    if step_label.startswith('derivative:'):
        if 'order ' in step_label:
            n = (
                step_label.split('order ')[-1]
                .rstrip(')')
                .strip()
            )
            return 'd%s' % n

        return 'd1'

    if step_label.startswith('scatter_correction:'):
        scaler = step_label.split(':', 1)[-1].strip()
        return scaler.replace('+', '')

    if step_label.startswith('scaling:'):
        method = step_label.split(':', 1)[-1].strip()
        return {
            'meancentring': 'mc',
            'autoscaling': 'as',
            'paretoscaling': 'ps',
            'poissonscaling': 'poi',
        }.get(method, method[:4])

    if step_label.startswith('decomposition:'):
        if 'pca' in step_label:
            parts = step_label.split('(')
            n = (
                parts[1].split(' ')[0]
                if len(parts) > 1
                else '?'
            )
            return 'pca%s' % n

        return 'decomp'

    if step_label.startswith('filter:'):
        method = step_label.split(':', 1)[-1]
        return {
            'moving_average': 'ma',
            'gauss': 'gf',
            'savitzky-golay': 'sg',
            'lowess': 'lw',
            'multi_filter': 'mf',
        }.get(method, method[:4])

    return ''.join(
        c if c.isalnum() else ''
        for c in step_label.lower()
    )[:6]


class Process_plot(Get_schema_table):
    """Plot indicators and spectra from saved Parquet datasets."""

    def __init__(self, process_S, pg_session_C):
        self.verbose = process_S.process.verbose
        self.process_S = process_S
        self.pg_session_C = pg_session_C

        self.pg_ai4sh_C = PG_manage_AI4SH(pg_session_C)

        services().log(
            section="process",
            status="success",
            message=_format_trace_message(
                "Plot process initialized",
                {
                    "process": self.process_S.process.process,
                },
            ),
        )

    def _Sub_process(self, _json_file_key):
        process_name = self.process_S.process.process
        started = time.perf_counter()

        services().log(
            section="dispatcher",
            status="info",
            message=_format_trace_message(
                "Dispatching plot process",
                {
                    "process": process_name,
                },
            ),
        )

        try:
            if process_name == 'plot_indicators':
                result = self._Plot_indicators()

            elif process_name == 'plot_spectra':
                result = self._Plot_spectra()

            elif process_name == 'plot_spectra_scattercorrection_scalers':
                result = self._Plot_spectra_scattercorrection_scalers()

            elif process_name == 'plot_spectra_scaling_methods':
                result = self._Plot_spectra_scaling_methods()

            else:
                services().log(
                    section="dispatcher",
                    status="error",
                    message=_format_trace_message(
                        "Unknown plot process",
                        {
                            "process": process_name,
                        },
                    ),
                )
                return None

            services().log(
                section="dispatcher",
                status="success",
                message=_format_trace_message(
                    "Plot process completed",
                    {
                        "process": process_name,
                        "duration_ms": round(
                            (time.perf_counter() - started) * 1000,
                            2,
                        ),
                    },
                ),
            )

            return result

        except Exception as exc:
            services().log(
                section="dispatcher",
                status="error",
                message=_format_trace_message(
                    "Plot process failed",
                    {
                        "process": process_name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "duration_ms": round(
                            (time.perf_counter() - started) * 1000,
                            2,
                        ),
                    },
                ),
            )
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _Parse_indicator_array(self):
        """Parse a JSON list, CSV string, or PostgreSQL array string."""
        raw = getattr(
            self.process_S.process.parameters,
            'indicator_array',
            '',
        )

        if not raw:
            return []

        if isinstance(raw, list):
            return [
                x.strip()
                for x in raw
                if x.strip()
            ]

        s = str(raw).strip()

        if s.startswith('{') and s.endswith('}'):
            s = s[1:-1]

        return [
            x.strip()
            for x in s.split(',')
            if x.strip()
        ]

    def _Load_parquet_data(self, project_root_fp):
        """
        Load data-*.parquet and optional params-*.json.

        Return (DataFrame, params_dict).
        """
        parquet_matches = glob.glob(
            os.path.join(project_root_fp, 'data-*.parquet')
        )
        params_matches = glob.glob(
            os.path.join(project_root_fp, 'params-*.json')
        )

        if not parquet_matches:
            raise FileNotFoundError(
                'No data-*.parquet file found in: %s'
                % project_root_fp
            )

        df = pd.read_parquet(parquet_matches[0])

        params_D = {}

        if params_matches:
            with open(params_matches[0]) as f:
                params_D = json.load(f)

        if self.verbose >= 1:
            n_samples = params_D.get('n_samples', len(df))

            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Plot dataset loaded",
                    {
                        "rows": len(df),
                        "expected_rows": n_samples,
                        "file": os.path.basename(parquet_matches[0]),
                    },
                ),
            )

        return df, params_D

    def _Load_feature_symbols(self):
        """Load default or explicitly configured indicator symbols."""
        raw = getattr(
            self.process_S.process.parameters,
            'targetfeaturesymbols',
            'default',
        )

        if not raw or str(raw).strip().lower() == 'default':
            fpn = _DEFAULT_SYMBOLS_FPN
        else:
            fpn = str(raw).strip()

        if not os.path.exists(fpn):
            if self.verbose >= 1:
                services().log(
                    section="process",
                    status="error",
                    message=_format_trace_message(
                        "Plot symbol file not found; using fallback labels",
                        {
                            "path": fpn,
                        },
                    ),
                )

            return {}

        with open(fpn) as f:
            data = json.load(f)

        return data.get('targetFeatureSymbols', {})

    def _Build_plot_output_path(self, project_root_fp):
        """Create and return project_root_fp/plot/."""
        plot_dir = os.path.join(project_root_fp, 'plot')
        os.makedirs(plot_dir, exist_ok=True)
        return plot_dir

    def _Get_symbol(self, symbols, indicator):
        """Return (color, label, unit), using fallback values."""
        sym = symbols.get(indicator, {})

        color = sym.get('color', 'steelblue')
        label = sym.get('label', indicator)
        unit = sym.get('unit', '')

        return color, label, unit

    def _build_transform_info(
        self,
        indicator,
        transform_dict,
        standard_dict,
    ):
        """Return annotation text and filename suffix for an indicator."""
        transform = transform_dict.get(indicator, 'linear')
        standardised = (
            standard_dict.get(indicator, 'none') != 'none'
        )

        transform_label = (
            'none'
            if transform == 'linear'
            else transform
        )

        ann = 'standard: %s  transform: %s' % (
            str(standardised).lower(),
            transform_label,
        )

        parts = []

        if standardised:
            parts.append('z')

        if transform != 'linear':
            parts.append(transform)

        suffix = (
            '_' + '_'.join(parts)
            if parts
            else ''
        )

        return ann, suffix

    def _build_combined_suffix(
        self,
        indicators,
        transform_dict,
        standard_dict,
    ):
        """Combine applied operations into a plot filename suffix."""
        has_z = any(
            standard_dict.get(i, 'none') != 'none'
            for i in indicators
        )

        transforms = sorted(set(
            transform_dict.get(i, 'linear')
            for i in indicators
            if transform_dict.get(i, 'linear') != 'linear'
        ))

        parts = []

        if has_z:
            parts.append('z')

        parts.extend(transforms)

        return (
            '_' + '_'.join(parts)
            if parts
            else ''
        )

    def _Parse_chemometrics_array(self, raw):
        """Parse chemometric step names from an array parameter."""
        if not raw:
            return []

        if isinstance(raw, list):
            return [
                x.strip()
                for x in raw
                if x.strip()
            ]

        s = str(raw).strip()

        if s.startswith('{') and s.endswith('}'):
            s = s[1:-1]

        return [
            x.strip()
            for x in s.split(',')
            if x.strip()
        ]

    def _Plot_spectra_panel(
        self,
        df_step,
        step_cols,
        colors,
        step_label,
        ann,
        chain_ann,
        file_suffix,
        show,
        save,
        plot_dir,
    ):
        """Render one spectral panel with its preprocessing history."""
        x_vals, x_label = _spectra_x_axis(step_cols)

        y_label = (
            'Score'
            if step_cols and str(step_cols[0]).startswith('pc')
            else 'Reflectance'
        )

        fig, ax = plt.subplots(figsize=(10, 5))

        for i, (_, row) in enumerate(df_step.iterrows()):
            ax.plot(
                x_vals,
                row[step_cols].values,
                color=colors[i],
                linewidth=0.8,
            )

        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(step_label)

        ax.text(
            0.02, 0.04, ann,
            transform=ax.transAxes,
            fontsize=8,
            verticalalignment='bottom',
        )
        ax.text(
            0.98, 0.98, chain_ann,
            transform=ax.transAxes,
            fontsize=8,
            ha='right',
            va='top',
            color='gray',
        )

        fig.tight_layout()

        if save:
            fpn = os.path.join(
                plot_dir,
                'spectra_%s.png' % file_suffix,
            )
            fig.savefig(fpn, bbox_inches='tight')

            if self.verbose >= 1:
                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Plot saved",
                        {"path": fpn},
                    ),
                )

        if show:
            plt.show()

        plt.close(fig)

    def _Histogram_plot(
        self,
        df,
        indicators,
        symbols,
        bins,
        show,
        save,
        plot_dir,
        transform_dict=None,
        standard_dict=None,
    ):
        """Plot individual histograms followed by a combined grid."""
        n_cols = 3

        transform_dict = transform_dict or {}
        standard_dict = standard_dict or {}

        # Close individual figures before creating the combined grid.
        for indicator in indicators:
            if indicator not in df.columns:
                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="error",
                        message=_format_trace_message(
                            "Indicator missing from plot dataset; skipping",
                            {"indicator": indicator},
                        ),
                    )
                continue

            series = df[indicator].dropna()
            color, label, unit = self._Get_symbol(symbols, indicator)

            ann, suffix = self._build_transform_info(
                indicator,
                transform_dict,
                standard_dict,
            )

            fig, ax = plt.subplots(figsize=(6, 4))

            series.plot.hist(
                bins=bins,
                color=color,
                ax=ax,
            )

            ax.set_title(label)
            ax.set_xlabel(unit)
            ax.text(
                0.98, 0.98, ann,
                transform=ax.transAxes,
                fontsize=7,
                ha='right',
                va='top',
                color='gray',
            )

            if save:
                fpn = os.path.join(
                    plot_dir,
                    'histogram_%s%s.png' % (indicator, suffix),
                )
                fig.savefig(fpn, bbox_inches='tight')

                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="success",
                        message=_format_trace_message(
                            "Plot saved",
                            {"path": fpn},
                        ),
                    )

            if show:
                plt.show()

            plt.close(fig)

        if len(indicators) > 1:
            n_rows = ceil(len(indicators) / n_cols)

            multi_fig, multi_axs = plt.subplots(
                n_rows,
                n_cols,
                figsize=(n_cols * 4, n_rows * 3),
            )

            axs_flat = np.array(multi_axs).flatten()

            f = 0

            for indicator in indicators:
                if indicator not in df.columns:
                    continue

                series = df[indicator].dropna()
                color, label, unit = self._Get_symbol(
                    symbols,
                    indicator,
                )
                ann, _ = self._build_transform_info(
                    indicator,
                    transform_dict,
                    standard_dict,
                )

                ax = axs_flat[f]
                series.plot.hist(
                    bins=bins,
                    color=color,
                    ax=ax,
                )

                ax.set_title(label)
                ax.set_xlabel(unit)
                ax.text(
                    0.98, 0.98, ann,
                    transform=ax.transAxes,
                    fontsize=6,
                    ha='right',
                    va='top',
                    color='gray',
                )

                if f % n_cols != 0:
                    ax.set_ylabel('')

                f += 1

            for idx in range(f, len(axs_flat)):
                axs_flat[idx].set_visible(False)

            multi_fig.tight_layout()

            if save:
                combined_suffix = self._build_combined_suffix(
                    indicators,
                    transform_dict,
                    standard_dict,
                )

                fpn = os.path.join(
                    plot_dir,
                    'histogram_all-indicators%s.png'
                    % combined_suffix,
                )
                multi_fig.savefig(fpn, bbox_inches='tight')

                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="success",
                        message=_format_trace_message(
                            "Plot saved",
                            {"path": fpn},
                        ),
                    )

            if show:
                plt.show()

            plt.close(multi_fig)

    def _Boxplot_plot(
        self,
        df,
        indicators,
        symbols,
        show,
        save,
        plot_dir,
        transform_dict=None,
        standard_dict=None,
    ):
        """Plot individual boxplots followed by a combined grid."""
        n_cols = 3

        transform_dict = transform_dict or {}
        standard_dict = standard_dict or {}

        for indicator in indicators:
            if indicator not in df.columns:
                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="error",
                        message=_format_trace_message(
                            "Indicator missing from plot dataset; skipping",
                            {"indicator": indicator},
                        ),
                    )
                continue

            color, label, unit = self._Get_symbol(
                symbols,
                indicator,
            )

            ann, suffix = self._build_transform_info(
                indicator,
                transform_dict,
                standard_dict,
            )

            fig, ax = plt.subplots(figsize=(4, 5))

            df.boxplot(
                column=[indicator],
                patch_artist=True,
                boxprops=dict(facecolor=color),
                ax=ax,
            )

            ax.set_title(label)
            ax.set_xlabel(unit)
            ax.text(
                0.98, 0.98, ann,
                transform=ax.transAxes,
                fontsize=7,
                ha='right',
                va='top',
                color='gray',
            )

            if save:
                fpn = os.path.join(
                    plot_dir,
                    'boxplot_%s%s.png' % (indicator, suffix),
                )
                fig.savefig(fpn, bbox_inches='tight')

                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="success",
                        message=_format_trace_message(
                            "Plot saved",
                            {"path": fpn},
                        ),
                    )

            if show:
                plt.show()

            plt.close(fig)

        if len(indicators) > 1:
            n_rows = ceil(len(indicators) / n_cols)

            multi_fig, multi_axs = plt.subplots(
                n_rows,
                n_cols,
                figsize=(n_cols * 3, n_rows * 4),
            )

            axs_flat = np.array(multi_axs).flatten()

            f = 0

            for indicator in indicators:
                if indicator not in df.columns:
                    continue

                color, label, unit = self._Get_symbol(
                    symbols,
                    indicator,
                )
                ann, _ = self._build_transform_info(
                    indicator,
                    transform_dict,
                    standard_dict,
                )

                ax = axs_flat[f]

                df.boxplot(
                    column=[indicator],
                    patch_artist=True,
                    boxprops=dict(facecolor=color),
                    ax=ax,
                )

                ax.set_title(label)
                ax.set_xlabel(unit)
                ax.text(
                    0.98, 0.98, ann,
                    transform=ax.transAxes,
                    fontsize=6,
                    ha='right',
                    va='top',
                    color='gray',
                )

                if f % n_cols != 0:
                    ax.set_ylabel('')

                f += 1

            for idx in range(f, len(axs_flat)):
                axs_flat[idx].set_visible(False)

            multi_fig.tight_layout()

            if save:
                combined_suffix = self._build_combined_suffix(
                    indicators,
                    transform_dict,
                    standard_dict,
                )

                fpn = os.path.join(
                    plot_dir,
                    'boxplot_all-indicators%s.png'
                    % combined_suffix,
                )
                multi_fig.savefig(fpn, bbox_inches='tight')

                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="success",
                        message=_format_trace_message(
                            "Plot saved",
                            {"path": fpn},
                        ),
                    )

            if show:
                plt.show()

            plt.close(multi_fig)

    # ------------------------------------------------------------------
    # Main process
    # ------------------------------------------------------------------

    def _Plot_indicators(self):
        """Read saved Parquet data and plot indicator distributions."""
        p = self.process_S.process.parameters

        project_root_fp = str(p.project_root_fp).strip()

        if not os.path.isabs(project_root_fp):
            project_root_fp = os.path.join(
                _REPO_ROOT,
                'ai4sh',
                project_root_fp.lstrip('./'),
            )

        if not os.path.exists(project_root_fp):
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Plot project root not found",
                    {"path": project_root_fp},
                ),
            )
            return

        try:
            df, params_D = self._Load_parquet_data(project_root_fp)

        except FileNotFoundError as e:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Plot dataset file not found",
                    {
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                ),
            )
            return

        if self.verbose >= 2 and params_D:
            provision = params_D.get('provision_name', '')
            bw = params_D.get('output_bandwidth', '')
            beg = params_D.get('begin_wavelength', '')
            end = params_D.get('end_wavelength', '')

            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Plot dataset metadata resolved",
                    {
                        "dataset": params_D.get('dataset_name', ''),
                        "provision": provision,
                        "begin_wavelength": beg,
                        "end_wavelength": end,
                        "bandwidth": bw,
                    },
                ),
            )

        indicators = self._Parse_indicator_array()

        if not indicators:
            skip_prefixes = ('w_',)
            skip_cols = {
                'sample_name',
                'campaign_name',
                'latitude_dd',
                'longitude_dd',
                'profile_min',
                'profile_max',
            }

            indicators = [
                c
                for c in df.columns
                if c not in skip_cols
                and not any(
                    c.startswith(px)
                    for px in skip_prefixes
                )
            ]

        indicators = [
            i
            for i in indicators
            if i in df.columns
        ]

        if not indicators:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "No indicators found in plot dataset",
                    {"available_columns": list(df.columns)},
                ),
            )
            return

        if self.verbose >= 1:
            services().log(
                section="process",
                status="info",
                message=_format_trace_message(
                    "Plotting indicators",
                    {
                        "indicator_count": len(indicators),
                        "indicators": indicators,
                    },
                ),
            )

        transformation_param = getattr(
            p,
            'transformation',
            'default',
        )
        standardisation_param = getattr(
            p,
            'standardisation',
            'default',
        )

        df, transform_dict = apply_transformations(
            df,
            indicators,
            transformation_param,
            self.verbose,
        )

        df, standard_dict = apply_standardisation(
            df,
            indicators,
            standardisation_param,
            self.verbose,
        )

        symbols = self._Load_feature_symbols()

        do_histogram = getattr(p, 'histogram', True)
        do_boxplot = getattr(p, 'boxplot', True)
        show = getattr(p, 'show', True)
        save = getattr(p, 'save', False)
        bins = getattr(p, 'bins', 10)

        plot_dir = (
            self._Build_plot_output_path(project_root_fp)
            if save
            else None
        )

        if do_histogram:
            self._Histogram_plot(
                df,
                indicators,
                symbols,
                bins,
                show,
                save,
                plot_dir,
                transform_dict,
                standard_dict,
            )

        if do_boxplot:
            self._Boxplot_plot(
                df,
                indicators,
                symbols,
                show,
                save,
                plot_dir,
                transform_dict,
                standard_dict,
            )

    def _Plot_spectra(self):
        """Plot spectra through each configured chemometric step."""
        p = self.process_S.process.parameters

        project_root_fp = str(p.project_root_fp).strip()

        if not os.path.isabs(project_root_fp):
            project_root_fp = os.path.join(
                _REPO_ROOT,
                'ai4sh',
                project_root_fp.lstrip('./'),
            )

        if not os.path.exists(project_root_fp):
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Plot project root not found",
                    {"path": project_root_fp},
                ),
            )
            return

        try:
            df, params_D = self._Load_parquet_data(project_root_fp)

        except FileNotFoundError as e:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Plot dataset file not found",
                    {
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                ),
            )
            return

        spectral_cols = [
            c
            for c in df.columns
            if c.startswith('w_')
        ]

        if not spectral_cols:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "No spectral columns found in plot dataset",
                    {"required_prefix": "w_"},
                ),
            )
            return

        n_total = len(df)
        max_spectra = int(getattr(p, 'max_spectra', 0))

        skip = (
            max(1, ceil(n_total / max_spectra))
            if max_spectra > 0
            else 1
        )

        df_sub = df.iloc[::skip].reset_index(drop=True)
        n_plot = len(df_sub)

        if self.verbose >= 1:
            services().log(
                section="process",
                status="info",
                message=_format_trace_message(
                    "Plotting spectra",
                    {
                        "spectra_shown": n_plot,
                        "spectra_total": n_total,
                        "bands": len(spectral_cols),
                        "skip": skip,
                    },
                ),
            )

        colormap = (
            str(getattr(p, 'colormap', 'jet')).strip()
            or 'jet'
        )
        colors = plt.get_cmap(colormap)(
            np.linspace(0, 1, n_plot)
        )

        show = getattr(p, 'show', True)
        save = getattr(p, 'save', False)

        plot_dir = (
            self._Build_plot_output_path(project_root_fp)
            if save
            else None
        )

        wavelengths = [
            int(c[2:])
            for c in spectral_cols
        ]

        spec_df = df_sub[spectral_cols].copy()
        spec_df.columns = wavelengths

        filter_param = (
            str(getattr(p, 'filter', 'none')).strip()
            or 'none'
        )
        multi_filter_param = (
            str(getattr(p, 'multi_filter', 'none')).strip()
            or 'none'
        )

        chemometrics_param = (
            str(getattr(p, 'chemometrics', 'default')).strip()
            or 'default'
        )
        chemometrics_array = self._Parse_chemometrics_array(
            getattr(p, 'chemometrics_array', [])
        )

        panels = [('raw', spec_df, wavelengths)]
        base_df = spec_df
        base_cols = wavelengths

        # Multi-filter takes precedence over the single-filter option.
        if multi_filter_param.lower() not in ('none', 'no', ''):
            multi_cfg = _load_filter_config(multi_filter_param)

            if multi_cfg is not None:
                df_f, cols_f, flabel = apply_multi_filter(
                    base_df,
                    base_cols,
                    multi_cfg,
                )

                panels.append((flabel, df_f, cols_f))
                base_df, base_cols = df_f, cols_f

        elif filter_param.lower() not in ('none', 'no', ''):
            filter_cfg = _load_filter_config(filter_param)

            if filter_cfg is not None:
                df_f, cols_f, flabel = apply_filter(
                    base_df,
                    base_cols,
                    filter_cfg,
                )

                panels.append((flabel, df_f, cols_f))
                base_df, base_cols = df_f, cols_f

        # The chemometric result starts with raw; avoid duplicating it.
        chem_steps = apply_chemometrics(
            base_df,
            base_cols,
            chemometrics_array,
            chemometrics_param,
            self.verbose,
        )
        panels.extend(chem_steps[1:])

        bw = params_D.get('output_bandwidth', '')
        ann = 'n=%d  shown=%d' % (n_total, n_plot)

        if bw:
            ann += '  bw=%s nm' % bw

        chain_abbrevs = []

        for step_label, df_step, step_cols in panels:
            abbrev = _step_to_abbrev(step_label)

            if step_label != 'raw':
                chain_abbrevs.append(abbrev)

            chain_ann = (
                '→'.join(chain_abbrevs)
                if chain_abbrevs
                else 'raw'
            )
            file_suffix = (
                '_'.join(chain_abbrevs)
                if chain_abbrevs
                else 'raw'
            )

            self._Plot_spectra_panel(
                df_step,
                step_cols,
                colors,
                step_label,
                ann,
                chain_ann,
                file_suffix,
                show,
                save,
                plot_dir,
            )

    def _Load_spec_df(self, p):
        """
        Load and subsample spectral data.

        Return spec_df, wavelengths, colors, ann, params_D,
        show, save, plot_dir. Return eight None values on handled errors.
        """
        project_root_fp = str(p.project_root_fp).strip()

        if not os.path.isabs(project_root_fp):
            project_root_fp = os.path.join(
                _REPO_ROOT,
                'ai4sh',
                project_root_fp.lstrip('./'),
            )

        if not os.path.exists(project_root_fp):
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Plot project root not found",
                    {"path": project_root_fp},
                ),
            )
            return None, None, None, None, None, None, None, None

        try:
            df, params_D = self._Load_parquet_data(project_root_fp)

        except FileNotFoundError as e:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Plot dataset file not found",
                    {
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                ),
            )
            return None, None, None, None, None, None, None, None

        spectral_cols = [
            c
            for c in df.columns
            if c.startswith('w_')
        ]

        if not spectral_cols:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "No spectral columns found in plot dataset",
                    {"required_prefix": "w_"},
                ),
            )
            return None, None, None, None, None, None, None, None

        n_total = len(df)
        max_spectra = int(getattr(p, 'max_spectra', 0))

        skip = (
            max(1, ceil(n_total / max_spectra))
            if max_spectra > 0
            else 1
        )

        df_sub = df.iloc[::skip].reset_index(drop=True)
        n_plot = len(df_sub)

        if self.verbose >= 1:
            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Spectral plot data prepared",
                    {
                        "spectra_total": n_total,
                        "spectra_shown": n_plot,
                        "skip": skip,
                    },
                ),
            )

        colormap = (
            str(getattr(p, 'colormap', 'jet')).strip()
            or 'jet'
        )
        colors = plt.get_cmap(colormap)(
            np.linspace(0, 1, n_plot)
        )

        bw = params_D.get('output_bandwidth', '')
        ann = 'n=%d  shown=%d' % (n_total, n_plot)

        if bw:
            ann += '  bw=%s nm' % bw

        wavelengths = [
            int(c[2:])
            for c in spectral_cols
        ]

        spec_df = df_sub[spectral_cols].copy()
        spec_df.columns = wavelengths

        show = getattr(p, 'show', True)
        save = getattr(p, 'save', False)

        plot_dir = (
            self._Build_plot_output_path(project_root_fp)
            if save
            else None
        )

        return (
            spec_df,
            wavelengths,
            colors,
            ann,
            params_D,
            show,
            save,
            plot_dir,
        )

    def _Plot_spectra_comparison(
        self,
        panels,
        colors,
        ann,
        title,
        filename_stem,
        show,
        save,
        plot_dir,
    ):
        """Render a vertically stacked spectral comparison."""
        n = len(panels)
        panel_h = 2.0

        fig, axs = plt.subplots(
            nrows=n,
            ncols=1,
            figsize=(10, panel_h * n),
            sharex=True,
            sharey=False,
        )

        if n == 1:
            axs = [axs]

        for ax, (abbrev, label, df_step, step_cols) in zip(
            axs,
            panels,
        ):
            x_vals, _ = _spectra_x_axis(step_cols)

            y_label = (
                'Score'
                if step_cols and str(step_cols[0]).startswith('pc')
                else 'Reflectance'
            )

            for i, (_, row) in enumerate(df_step.iterrows()):
                ax.plot(
                    x_vals,
                    row[step_cols].values,
                    color=colors[i],
                    linewidth=0.5,
                )

            ax.set_ylabel(y_label, fontsize=7)
            ax.tick_params(labelsize=7)

            ax.text(
                0.98, 0.95, abbrev,
                transform=ax.transAxes,
                fontsize=8,
                ha='right',
                va='top',
                color='gray',
            )

        axs[-1].set_xlabel('Wavelength (nm)', fontsize=8)
        axs[0].text(
            0.02, 0.95, ann,
            transform=axs[0].transAxes,
            fontsize=7,
            va='top',
            color='gray',
        )

        fig.suptitle(title, fontsize=9, y=1.0)
        fig.tight_layout()

        if save:
            fpn = os.path.join(
                plot_dir,
                'spectra_%s.png' % filename_stem,
            )
            fig.savefig(fpn, bbox_inches='tight')

            if self.verbose >= 1:
                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Plot saved",
                        {"path": fpn},
                    ),
                )

        if show:
            plt.show()

        plt.close(fig)

    def _Plot_spectra_scattercorrection_scalers(self):
        """Compare scatter correction methods in a stacked plot."""
        p = self.process_S.process.parameters

        (
            spec_df,
            wavelengths,
            colors,
            ann,
            _,
            show,
            save,
            plot_dir,
        ) = self._Load_spec_df(p)

        if spec_df is None:
            return

        scalers = ['l1', 'l2', 'max', 'snv', 'msc']
        panels = [('raw', 'raw', spec_df, wavelengths)]

        for sc in scalers:
            try:
                df_out, cols_out, _ = apply_scatter_correction(
                    spec_df,
                    wavelengths,
                    {'scaler': [sc]},
                )

                panels.append((
                    sc,
                    'scatter_correction: %s' % sc,
                    df_out,
                    cols_out,
                ))

            except Exception as exc:
                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="error",
                        message=_format_trace_message(
                            "Scatter correction comparison step failed",
                            {
                                "scaler": sc,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            },
                        ),
                    )

        self._Plot_spectra_comparison(
            panels,
            colors,
            ann,
            title='Scatter correction comparison',
            filename_stem='compare_scattercorrection',
            show=show,
            save=save,
            plot_dir=plot_dir,
        )

    def _Plot_spectra_scaling_methods(self):
        """Compare scaling methods in a stacked plot."""
        p = self.process_S.process.parameters

        (
            spec_df,
            wavelengths,
            colors,
            ann,
            _,
            show,
            save,
            plot_dir,
        ) = self._Load_spec_df(p)

        if spec_df is None:
            return

        methods = [
            'meancentring',
            'autoscaling',
            'paretoscaling',
            'poissonscaling',
        ]
        panels = [('raw', 'raw', spec_df, wavelengths)]

        for method in methods:
            abbrev = {
                'meancentring': 'mc',
                'autoscaling': 'as',
                'paretoscaling': 'ps',
                'poissonscaling': 'poi',
            }[method]

            try:
                df_out, cols_out, _ = apply_scaling(
                    spec_df,
                    wavelengths,
                    {'method': method},
                )

                panels.append((
                    abbrev,
                    'scaling: %s' % method,
                    df_out,
                    cols_out,
                ))

            except Exception as exc:
                if self.verbose >= 1:
                    services().log(
                        section="process",
                        status="error",
                        message=_format_trace_message(
                            "Scaling comparison step failed",
                            {
                                "method": method,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            },
                        ),
                    )

        self._Plot_spectra_comparison(
            panels,
            colors,
            ann,
            title='Scaling method comparison',
            filename_stem='compare_scaling',
            show=show,
            save=save,
            plot_dir=plot_dir,
        )