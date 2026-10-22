'''
Created on 23 April 2026

@author: thomasgumbricht
'''

# Standard library imports
import json
import os
from time import perf_counter

# Third-party imports
import numpy as np
import pandas as pd

# Application package imports
from src.postgres import Get_schema_table
from src.postgres.pg_ai4sh import PG_manage_AI4SH
from src.utils.json_read_write import Dump_json

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


class Process_select(Get_schema_table):
    """
    Select a filtered spectral subset from the database.

    Save the selected data locally as Parquet.
    """

    def __init__(self, process_S, pg_session_C):
        self.verbose = process_S.process.verbose
        self.process_S = process_S
        self.pg_session_C = pg_session_C

        self.pg_ai4sh_C = PG_manage_AI4SH(pg_session_C)

        services().log(
            section="process",
            status="success",
            message=_format_trace_message(
                "Select process initialized",
                {
                    "process": getattr(
                        process_S.process,
                        "process",
                        None,
                    ),
                    "verbose": bool(self.verbose),
                },
            ),
        )

    def _Sub_process(self, json_file_key):
        process_name = self.process_S.process.process

        services().log(
            section="dispatcher",
            status="info",
            message=_format_trace_message(
                "Dispatching select subprocess",
                {
                    "process": process_name,
                    "json_file_key": json_file_key,
                },
            ),
        )

        try:
            if process_name == "select_spectra":
                result = self._Select_spectra()

            elif process_name == "select_indicator":
                result = self._Select_indicator()

            else:
                services().log(
                    section="dispatcher",
                    status="error",
                    message=_format_trace_message(
                        "Unknown select subprocess",
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
                    "Select subprocess completed",
                    {
                        "process": process_name,
                    },
                ),
            )

            return result

        except Exception as exc:
            services().log(
                section="dispatcher",
                status="error",
                message=_format_trace_message(
                    "Select subprocess failed",
                    {
                        "process": process_name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ),
            )

            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _Print_available_indicators(
        self,
        dataset_name,
        campaign_name,
    ):
        """Query available indicators and return the retrieved list."""
        services().log(
            section="sql",
            status="info",
            message=_format_trace_message(
                "Querying available indicators",
                {
                    "dataset": dataset_name,
                    "campaign": campaign_name or None,
                },
            ),
        )

        available = (
            self.pg_ai4sh_C
            ._Retrieve_available_indicators_for_dataset(
                {
                    "dataset_name": dataset_name,
                    "campaign_name": campaign_name,
                },
                self.pg_session_C,
            )
        )

        indicator_details = []

        if available:
            for name, alias in available:
                indicator_details.append({
                    "name": name,
                    "alias": alias or None,
                })

        services().log(
            section="sql",
            status="success",
            message=_format_trace_message(
                "Available indicators retrieved",
                {
                    "dataset": dataset_name,
                    "campaign": campaign_name or None,
                    "count": len(available) if available else 0,
                    "indicators": indicator_details,
                },
            ),
        )

        return available

    def _Build_output_paths(self):
        """
        Build paths from the process parameters.

        Return (out_dir, params_fpn, data_fpn).
        """
        p = self.process_S.process.parameters

        subset_dir = "%s_%s-%s_%s" % (
            p.dataset_name,
            p.begin_wavelength,
            p.end_wavelength,
            p.output_bandwidth,
        )

        out_dir = os.path.join(
            p.output_root_fp,
            subset_dir,
        )

        fname_base = "%s_%s-%s_%s" % (
            p.provision_name,
            p.begin_wavelength,
            p.end_wavelength,
            p.output_bandwidth,
        )

        params_fpn = os.path.join(
            out_dir,
            "params-%s.json" % fname_base,
        )

        data_fpn = os.path.join(
            out_dir,
            "data-%s.parquet" % fname_base,
        )

        services().log(
            section="process",
            status="success",
            message=_format_trace_message(
                "Select output paths built",
                {
                    "output_directory": out_dir,
                    "params_file": params_fpn,
                    "data_file": data_fpn,
                },
            ),
        )

        return out_dir, params_fpn, data_fpn

    def _Parse_indicator_array(self):
        """
        Parse indicator names from a list or PostgreSQL array string.

        structure.py may convert CSV input to "{a,b,c}".
        """
        raw = getattr(
            self.process_S.process.parameters,
            "indicator_array",
            "",
        )

        if not raw:
            return []

        if isinstance(raw, list):
            indicators = [
                x.strip()
                for x in raw
                if x.strip()
            ]

        else:
            s = str(raw).strip()

            if s.startswith("{") and s.endswith("}"):
                s = s[1:-1]

            indicators = [
                x.strip()
                for x in s.split(",")
                if x.strip()
            ]

        services().log(
            section="process",
            status="success",
            message=_format_trace_message(
                "Indicator array parsed",
                {
                    "count": len(indicators),
                    "indicators": indicators,
                },
            ),
        )

        return indicators

    def _Parse_data_range(self):
        """
        Parse {indicator: {min, max}} from the data_range parameter.

        Empty input disables range filtering.
        """
        raw = getattr(
            self.process_S.process.parameters,
            "data_range",
            "",
        )

        if not raw:
            return {}

        try:
            data_range = json.loads(raw)

            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Data range parsed",
                    {
                        "indicators": list(data_range.keys()),
                    },
                ),
            )

            return data_range

        except json.JSONDecodeError as exc:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Could not parse data range JSON",
                    {
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ),
            )

            return {}

    # ------------------------------------------------------------------
    # Main select logic
    # ------------------------------------------------------------------

    def _Select_indicator(self):
        """
        Report available provisions and indicators.

        This operation does not save data.
        """
        p = self.process_S.process.parameters

        dataset_name = p.dataset_name
        campaign_name = getattr(
            p,
            "campaign_name",
            "",
        ).strip()

        services().log(
            section="process",
            status="info",
            message=_format_trace_message(
                "Querying available dataset metadata",
                {
                    "dataset": dataset_name,
                    "campaign": campaign_name or None,
                },
            ),
        )

        # Spectral sensors (provisions).
        provisions = (
            self.pg_ai4sh_C
            ._Retrieve_available_provisions_for_dataset(
                {
                    "dataset_name": dataset_name,
                    "campaign_name": campaign_name,
                },
                self.pg_session_C,
            )
        )

        services().log(
            section="sql",
            status="success",
            message=_format_trace_message(
                "Available spectral provisions retrieved",
                {
                    "dataset": dataset_name,
                    "campaign": campaign_name or None,
                    "count": (
                        len(provisions)
                        if provisions
                        else 0
                    ),
                    "provisions": (
                        list(provisions)
                        if provisions
                        else []
                    ),
                },
            ),
        )

        available = self._Print_available_indicators(
            dataset_name,
            campaign_name,
        )

        services().log(
            section="process",
            status="success",
            message=_format_trace_message(
                "Dataset metadata query completed",
                {
                    "dataset": dataset_name,
                    "campaign": campaign_name or None,
                    "provision_count": (
                        len(provisions)
                        if provisions
                        else 0
                    ),
                    "indicator_count": (
                        len(available)
                        if available
                        else 0
                    ),
                },
            ),
        )

        return {
            "provisions": provisions or [],
            "indicators": available or [],
        }

    def _Select_spectra(self):
        """Query, filter, resample, and save Parquet and parameters."""
        started_at = perf_counter()

        p = self.process_S.process.parameters

        services().log(
            section="process",
            status="info",
            message=_format_trace_message(
                "Selecting spectral subset",
                {
                    "dataset": p.dataset_name,
                    "provision": p.provision_name,
                    "begin_wavelength": p.begin_wavelength,
                    "end_wavelength": p.end_wavelength,
                    "output_bandwidth": p.output_bandwidth,
                },
            ),
        )

        try:
            out_dir, params_fpn, data_fpn = (
                self._Build_output_paths()
            )

            if (
                os.path.exists(data_fpn)
                and not self.process_S.process.overwrite
            ):
                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Spectral subset already exists; skipping",
                        {
                            "data_file": data_fpn,
                        },
                    ),
                )

                return None

            indicators = self._Parse_indicator_array()
            data_range = self._Parse_data_range()

            as_absorbance = bool(
                getattr(p, "as_absorbance", False)
            )

            preparation_name = getattr(
                p,
                "preparation_name",
                "",
            ).strip()

            campaign_name = getattr(
                p,
                "campaign_name",
                "",
            ).strip()

            # 1. Retrieve the native spectrometer wavelength array.
            wl_query = {
                "dataset_name": p.dataset_name,
                "provision_name": p.provision_name,
            }

            services().log(
                section="sql",
                status="info",
                message=_format_trace_message(
                    "Retrieving spectrometer wavelengths",
                    {
                        "dataset": p.dataset_name,
                        "provision": p.provision_name,
                    },
                ),
            )

            input_wl = (
                self.pg_ai4sh_C
                ._Retrieve_spectrometer_wavelengths(
                    wl_query,
                    self.pg_session_C,
                )
            )

            if input_wl is None:
                services().log(
                    section="sql",
                    status="error",
                    message=_format_trace_message(
                        "No spectrometer found for provision",
                        {
                            "provision": p.provision_name,
                        },
                    ),
                )

                return None

            input_wl = np.array(
                input_wl,
                dtype=float,
            )

            services().log(
                section="sql",
                status="success",
                message=_format_trace_message(
                    "Spectrometer wavelengths retrieved",
                    {
                        "band_count": len(input_wl),
                        "min_wavelength": float(input_wl[0]),
                        "max_wavelength": float(input_wl[-1]),
                    },
                ),
            )

            if (
                p.begin_wavelength + 1 < input_wl[0]
                or p.end_wavelength - 1 > input_wl[-1]
            ):
                services().log(
                    section="process",
                    status="error",
                    message=_format_trace_message(
                        "Requested wavelength range exceeds "
                        "spectrometer range",
                        {
                            "requested_min": p.begin_wavelength,
                            "requested_max": p.end_wavelength,
                            "available_min": float(input_wl[0]),
                            "available_max": float(input_wl[-1]),
                        },
                    ),
                )

                return None

            # Build the output grid without assuming native bandwidth.
            output_wl = np.arange(
                p.begin_wavelength,
                p.end_wavelength + 1,
                p.output_bandwidth,
                dtype=int,
            )

            if self.verbose:
                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Output wavelength grid prepared",
                        {
                            "input_band_count": len(input_wl),
                            "output_band_count": len(output_wl),
                            "output_min": int(output_wl[0]),
                            "output_max": int(output_wl[-1]),
                            "output_step": int(p.output_bandwidth),
                        },
                    ),
                )

            # 2. Retrieve spectral scans.
            spectra_query = {
                "dataset_name": p.dataset_name,
                "provision_name": p.provision_name,
                "campaign_name": campaign_name,
                "preparation_name": preparation_name,
            }

            services().log(
                section="sql",
                status="info",
                message=_format_trace_message(
                    "Retrieving spectral records",
                    {
                        "dataset": p.dataset_name,
                        "provision": p.provision_name,
                        "campaign": campaign_name or None,
                        "preparation": preparation_name or None,
                    },
                ),
            )

            spectra_recs = (
                self.pg_ai4sh_C
                ._Retrieve_spectra_for_dataset(
                    spectra_query,
                    self.pg_session_C,
                )
            )

            if not spectra_recs:
                services().log(
                    section="sql",
                    status="error",
                    message=_format_trace_message(
                        "No spectral data found",
                        {
                            "dataset": p.dataset_name,
                            "provision": p.provision_name,
                        },
                    ),
                )

                return None

            services().log(
                section="sql",
                status="success",
                message=_format_trace_message(
                    "Spectral records retrieved",
                    {
                        "record_count": len(spectra_recs),
                    },
                ),
            )

            # 3. Retrieve indicator measurements.
            if indicators:
                services().log(
                    section="sql",
                    status="info",
                    message=_format_trace_message(
                        "Retrieving laboratory measurements",
                        {
                            "dataset": p.dataset_name,
                            "indicator_count": len(indicators),
                        },
                    ),
                )

                lab_recs = (
                    self.pg_ai4sh_C
                    ._Retrieve_lab_measurements_for_dataset(
                        {
                            "dataset_name": p.dataset_name,
                            "lab_indicators": indicators,
                        },
                        self.pg_session_C,
                    )
                )

                if not lab_recs:
                    services().log(
                        section="sql",
                        status="error",
                        message=_format_trace_message(
                            "No laboratory measurements found "
                            "for requested indicators",
                            {
                                "indicators": indicators,
                            },
                        ),
                    )

                    return None

                services().log(
                    section="sql",
                    status="success",
                    message=_format_trace_message(
                        "Laboratory measurements retrieved",
                        {
                            "record_count": len(lab_recs),
                        },
                    ),
                )

            else:
                lab_recs = []

            # 4. Filter and resample spectra into DataFrame rows.
            wl_col_names = [
                "w_%d" % wl
                for wl in output_wl
            ]

            rows = []
            depth_excluded = 0

            for rec in spectra_recs:
                (
                    sample_name,
                    campaign_name_rec,
                    lat,
                    lon,
                    prof_min,
                    prof_max,
                    signal_array,
                ) = rec

                # Apply depth limits only where profile data exists.
                if (
                    prof_min is not None
                    and prof_min < p.min_profile
                ):
                    depth_excluded += 1
                    continue

                if (
                    prof_max is not None
                    and prof_max > p.max_profile
                ):
                    depth_excluded += 1
                    continue

                mask = (
                    (input_wl >= p.begin_wavelength)
                    & (input_wl <= p.end_wavelength)
                )

                clipped_wl = input_wl[mask]

                clipped_signal = np.array(
                    signal_array,
                    dtype=float,
                )[mask]

                if len(clipped_wl) < 2:
                    continue

                resampled = np.interp(
                    output_wl,
                    clipped_wl,
                    clipped_signal,
                )

                if as_absorbance:
                    # Apparent absorbance: log10(1/R).
                    resampled = -np.log10(
                        np.maximum(resampled, 1e-6)
                    )

                resampled = np.round(resampled, 6)

                row = {
                    "sample_name": sample_name,
                    "campaign_name": campaign_name_rec,
                    "latitude_dd": lat,
                    "longitude_dd": lon,
                    "profile_min": prof_min,
                    "profile_max": prof_max,
                }

                for col, val in zip(wl_col_names, resampled):
                    row[col] = float(val)

                rows.append(row)

            if self.verbose or depth_excluded:
                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Depth filtering completed",
                        {
                            "input_records": len(spectra_recs),
                            "excluded_records": depth_excluded,
                            "remaining_records": len(rows),
                        },
                    ),
                )

            if not rows:
                services().log(
                    section="process",
                    status="error",
                    message=_format_trace_message(
                        "No samples passed depth filter",
                        {
                            "excluded_records": depth_excluded,
                        },
                    ),
                )

                return None

            spectra_df = pd.DataFrame(rows)

            # 5. Pivot indicator measurements and merge with spectra.
            if lab_recs:
                lab_df = pd.DataFrame(
                    lab_recs,
                    columns=[
                        "sample_name",
                        "indicator_name",
                        "value",
                    ],
                )

                lab_pivot = lab_df.pivot_table(
                    index="sample_name",
                    columns="indicator_name",
                    values="value",
                    aggfunc="first",
                )

                lab_pivot.columns.name = None

                missing_indicators = [
                    ind
                    for ind in indicators
                    if ind not in lab_pivot.columns
                ]

                if missing_indicators:
                    services().log(
                        section="process",
                        status="error",
                        message=_format_trace_message(
                            "Requested indicators missing "
                            "from query results",
                            {
                                "missing_indicators": (
                                    missing_indicators
                                ),
                            },
                        ),
                    )

                    self._Print_available_indicators(
                        p.dataset_name,
                        campaign_name,
                    )

                    # Preserve the existing terminal confirmation.
                    confirm = input(
                        "Continue without %s? Enter y to continue "
                        "or n to stop: "
                        % missing_indicators
                    )

                    if confirm.lower() != "y":
                        services().log(
                            section="process",
                            status="error",
                            message=_format_trace_message(
                                "Spectral selection cancelled by user",
                                {
                                    "missing_indicators": (
                                        missing_indicators
                                    ),
                                },
                            ),
                        )

                        return None

                    services().log(
                        section="process",
                        status="success",
                        message=_format_trace_message(
                            "Continuing without missing indicators",
                            {
                                "missing_indicators": (
                                    missing_indicators
                                ),
                            },
                        ),
                    )

                df = spectra_df.merge(
                    lab_pivot.reset_index(),
                    on="sample_name",
                    how="inner",
                )

            else:
                df = spectra_df

            # 6. Apply indicator value ranges.
            range_excluded = 0

            for indicator, rng in data_range.items():
                if indicator not in df.columns:
                    services().log(
                        section="process",
                        status="error",
                        message=_format_trace_message(
                            "Data range indicator not present "
                            "in results",
                            {
                                "indicator": indicator,
                            },
                        ),
                    )

                    continue

                before = len(df)

                if "min" in rng:
                    df = df[df[indicator] >= rng["min"]]

                if "max" in rng:
                    df = df[df[indicator] <= rng["max"]]

                range_excluded += before - len(df)

            if self.verbose or range_excluded:
                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Data range filtering completed",
                        {
                            "excluded_records": range_excluded,
                            "remaining_records": len(df),
                        },
                    ),
                )

            if df.empty:
                services().log(
                    section="process",
                    status="error",
                    message=_format_trace_message(
                        "No samples remain after all filters",
                        {
                            "depth_excluded": depth_excluded,
                            "range_excluded": range_excluded,
                        },
                    ),
                )

                return None

            # 7. Save selected data and its parameters.
            os.makedirs(out_dir, exist_ok=True)

            services().log(
                section="process",
                status="info",
                message=_format_trace_message(
                    "Saving spectral subset",
                    {
                        "sample_count": len(df),
                        "data_file": data_fpn,
                        "params_file": params_fpn,
                    },
                ),
            )

            df.to_parquet(data_fpn, index=False)

            params_D = {
                "dataset_name": p.dataset_name,
                "campaign_name": getattr(p, "campaign_name", ""),
                "provision_name": p.provision_name,
                "preparation_name": preparation_name,
                "begin_wavelength": int(p.begin_wavelength),
                "end_wavelength": int(p.end_wavelength),
                "output_bandwidth": int(p.output_bandwidth),
                "min_profile": int(p.min_profile),
                "max_profile": int(p.max_profile),
                "indicator_array": indicators,
                "data_range": data_range,
                "as_absorbance": as_absorbance,
                "output_wavelengths": [
                    int(w)
                    for w in output_wl
                ],
                "n_samples": len(df),
            }

            Dump_json(
                params_fpn,
                params_D,
                verbose=self.verbose,
            )

            duration_ms = round(
                (perf_counter() - started_at) * 1000,
                2,
            )

            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Spectral subset saved",
                    {
                        "sample_count": len(df),
                        "column_count": len(df.columns),
                        "data_file": data_fpn,
                        "params_file": params_fpn,
                        "duration_ms": duration_ms,
                    },
                ),
            )

            return data_fpn

        except Exception as exc:
            duration_ms = round(
                (perf_counter() - started_at) * 1000,
                2,
            )

            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Spectral subset selection failed",
                    {
                        "dataset": getattr(p, "dataset_name", None),
                        "provision": getattr(p, "provision_name", None),
                        "duration_ms": duration_ms,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                ),
            )

            raise