'''
Created on 25 April 2026

@author: thomasgumbricht
'''

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import convolve1d, gaussian_filter1d
from scipy.signal import savgol_filter

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Keep legacy details in the message because TraceEntry has no details field."""
    return f"{message} | {json.dumps(details, ensure_ascii=False, default=str)}"


_DEFAULT_FILTER_DIR = Path(__file__).resolve().parents[2] / 'ai4sh' / 'default' / 'filter'

_FILTER_DEFAULT_FILES = {
    'moving-average': 'moving-average_default.json',
    'gauss':          'gauss_default.json',
    'savitzky-golay': 'savitzky-golay_default.json',
    'lowess':         'lowess_default.json',
}


def _load_filter_config(param):
    '''Load filter config dict from param.

    param=None / "none" / "no" → None (no filtering).
    param=filter-name           → load ai4sh/default/filter/<name>_default.json.
    param=path string           → load from that path.
    '''
    if param is None or str(param).lower() in ('none', 'no', ''):
        services().log(
            section='process',
            status='success',
            message=_format_trace_message('Filtering disabled', {'filter': 'none'}),
        )
        return None

    name = str(param).lower()
    if name in _FILTER_DEFAULT_FILES:
        fp = _DEFAULT_FILTER_DIR / _FILTER_DEFAULT_FILES[name]
        source = 'default'
    else:
        fp = Path(param)
        source = 'custom'

    services().log(
        section='process',
        status='info',
        message=_format_trace_message('Loading filter configuration', {'filter': name, 'source': source, 'path': str(fp)}),
    )

    started_at = time.perf_counter()
    try:
        with open(fp, encoding='utf-8') as fh:
            config = json.load(fh)

        services().log(
            section='process',
            status='success',
            message=_format_trace_message('Filter configuration loaded', {'filter': name, 'source': source, 'duration_ms': round((time.perf_counter() - started_at) * 1000, 2)}),
        )
        return config

    except Exception as exc:
        services().log(
            section='process',
            status='error',
            message=_format_trace_message('Failed to load filter configuration', {'filter': name, 'source': source, 'path': str(fp), 'error_type': type(exc).__name__, 'error': str(exc)}),
        )
        raise


def _lowess_1d(y, n_points):
    '''Tricube-weighted local linear regression along 1-D array y.

    n_points: number of neighbouring points (including the focal point) used in
    each local regression. Larger values give more smoothing.
    '''
    n = len(y)
    n_pts = min(int(n_points), n)
    x = np.arange(n, dtype=float)
    y_out = np.empty(n)

    for i in range(n):
        d = np.abs(x - i)
        idx = np.argpartition(d, n_pts - 1)[:n_pts]
        d_i = d[idx]
        max_d = d_i.max()
        if max_d == 0.0:
            w = np.ones(n_pts)
        else:
            u = d_i / max_d
            w = (1.0 - u ** 3) ** 3
        xi = x[idx]
        yi = y[idx]
        sw = w.sum()
        swx = (w * xi).sum()
        swx2 = (w * xi ** 2).sum()
        swy = (w * yi).sum()
        swxy = (w * xi * yi).sum()
        denom = sw * swx2 - swx ** 2
        if abs(denom) < 1e-10:
            y_out[i] = swy / sw if sw > 0 else np.mean(yi)
        else:
            a = (swy * swx2 - swxy * swx) / denom
            b = (sw * swxy - swx * swy) / denom
            y_out[i] = a + b * i

    return y_out


def apply_filter(df, columns, cfg):
    '''Apply a single smoothing filter to every row of df[columns].

    cfg is a dict whose top-level key identifies the filter type.

    Returns (df_out, columns_out, label).
    columns_out == columns (no resampling in single-filter mode).
    label format: "filter:<method>".
    '''
    started_at = time.perf_counter()
    rows = len(df.index)
    feature_count = len(columns)
    method = next(iter(cfg), 'none') if cfg else 'none'

    services().log(
        section='process',
        status='info',
        message=_format_trace_message('Applying spectral filter', {'method': method, 'rows': rows, 'features': feature_count}),
    )

    try:
        X = df[columns].values.astype(float)

        if 'moving_average' in cfg:
            mc = cfg['moving_average']
            kernel = np.asarray(mc['kernel'], dtype=float)
            kernel /= kernel.sum()
            mode = mc.get('mode', 'nearest')
            X1 = convolve1d(X, kernel, axis=-1, mode=mode)
            label = 'filter:moving_average'

        elif 'gauss' in cfg:
            gc = cfg['gauss']
            sigma = float(gc['sigma'])
            mode = gc.get('mode', 'nearest')
            X1 = gaussian_filter1d(X, sigma, axis=-1, mode=mode)
            label = 'filter:gauss'

        elif 'savitzky-golay' in cfg:
            sgc = cfg['savitzky-golay']
            wl = int(sgc['window_length'])
            po = int(sgc.get('polyorder', 2))
            deriv = int(sgc.get('deriv', 0))
            mode = sgc.get('mode', 'nearest')
            X1 = savgol_filter(
                X,
                window_length=wl,
                polyorder=po,
                deriv=deriv,
                axis=-1,
                mode=mode,
            )
            label = 'filter:savitzky-golay'

        elif 'lowess' in cfg:
            lc = cfg['lowess']
            n_pts = int(lc['n_points'])
            X1 = np.apply_along_axis(_lowess_1d, 1, X, n_pts)
            label = 'filter:lowess'

        else:
            services().log(
                section='process',
                status='success',
                message=_format_trace_message('No supported filter found; data left unchanged', {'method': method, 'rows': rows, 'features': feature_count, 'duration_ms': round((time.perf_counter() - started_at) * 1000, 2)}),
            )
            return df, list(columns), 'filter:none'

        df_out = pd.DataFrame(X1, index=df.index, columns=columns)

        services().log(
            section='process',
            status='success',
            message=_format_trace_message('Spectral filter applied', {'method': label.removeprefix('filter:'), 'rows': len(df_out.index), 'features': len(columns), 'duration_ms': round((time.perf_counter() - started_at) * 1000, 2)}),
        )
        return df_out, list(columns), label

    except Exception as exc:
        services().log(
            section='process',
            status='error',
            message=_format_trace_message('Failed to apply spectral filter', {'method': method, 'rows': rows, 'features': feature_count, 'error_type': type(exc).__name__, 'error': str(exc)}),
        )
        raise


def apply_multi_filter(df, columns, cfg):
    '''Apply per-region filters; wavelength gaps between regions are dropped.

    cfg must contain a "multi_filter" dict with parallel lists:
      begin_wavelength, end_wavelength, and at least one of:
      moving_average.kernel[], savitzky-golay.window_length[], gauss.sigma[],
      lowess.n_points[].

    Each region slice is filtered independently; results are concatenated in
    wavelength order. Columns are integer wavelengths.

    Returns (df_out, cols_out, "filter:multi_filter").
    '''
    started_at = time.perf_counter()

    try:
        mf = cfg['multi_filter']
        begins = mf['begin_wavelength']
        ends = mf['end_wavelength']
        mode = mf.get('mode', 'nearest')

        services().log(
            section='process',
            status='info',
            message=_format_trace_message('Applying multi-region spectral filter', {'regions': len(begins), 'rows': len(df.index), 'input_features': len(columns)}),
        )

        col_vals = np.array([int(c) for c in columns])

        region_dfs = []
        region_cols = []

        for r in range(len(begins)):
            bwl = begins[r]
            ewl = ends[r]
            mask = (col_vals >= bwl) & (col_vals < ewl)
            r_cols = [c for c, m in zip(columns, mask) if m]

            if not r_cols:
                services().log(
                    section='process',
                    status='success',
                    message=_format_trace_message('Skipping empty filter region', {'region_index': r, 'begin_wavelength': bwl, 'end_wavelength': ewl}),
                )
                continue

            region_cfg = {}

            ma_kernels = mf.get('moving_average', {}).get('kernel', [])
            sg_windows = mf.get('savitzky-golay', {}).get('window_length', [])
            sg_polys = mf.get('savitzky-golay', {}).get('polyorder', [])
            ga_sigmas = mf.get('gauss', {}).get('sigma', [])
            lw_npts = mf.get('lowess', {}).get('n_points', [])

            if r < len(ma_kernels) and ma_kernels[r]:
                region_cfg['moving_average'] = {
                    'kernel': ma_kernels[r],
                    'mode': mode,
                }
            elif r < len(sg_windows) and sg_windows[r]:
                po = sg_polys[r] if r < len(sg_polys) else 2
                region_cfg['savitzky-golay'] = {
                    'window_length': sg_windows[r],
                    'polyorder': po,
                    'mode': mode,
                }
            elif r < len(ga_sigmas) and ga_sigmas[r]:
                region_cfg['gauss'] = {
                    'sigma': ga_sigmas[r],
                    'mode': mode,
                }
            elif r < len(lw_npts) and lw_npts[r]:
                region_cfg['lowess'] = {'n_points': lw_npts[r]}

            region_method = next(iter(region_cfg), 'none')
            services().log(
                section='process',
                status='info',
                message=_format_trace_message('Processing filter region', {'region_index': r, 'begin_wavelength': bwl, 'end_wavelength': ewl, 'features': len(r_cols), 'method': region_method}),
            )

            if region_cfg:
                df_r, cols_r, _ = apply_filter(df, r_cols, region_cfg)
            else:
                df_r = df[r_cols].copy()
                cols_r = r_cols

            region_dfs.append(df_r)
            region_cols.extend(cols_r)

            services().log(
                section='process',
                status='success',
                message=_format_trace_message('Filter region processed', {'region_index': r, 'features': len(cols_r), 'method': region_method}),
            )

        if not region_dfs:
            services().log(
                section='process',
                status='success',
                message=_format_trace_message('No multi-filter regions produced output; data left unchanged', {'regions': len(begins), 'rows': len(df.index), 'features': len(columns), 'duration_ms': round((time.perf_counter() - started_at) * 1000, 2)}),
            )
            return df, list(columns), 'filter:multi_filter'

        df_out = pd.concat(region_dfs, axis=1)

        services().log(
            section='process',
            status='success',
            message=_format_trace_message('Multi-region spectral filter applied', {'regions_processed': len(region_dfs), 'rows': len(df_out.index), 'output_features': len(region_cols), 'duration_ms': round((time.perf_counter() - started_at) * 1000, 2)}),
        )
        return df_out, region_cols, 'filter:multi_filter'

    except Exception as exc:
        services().log(
            section='process',
            status='error',
            message=_format_trace_message('Failed to apply multi-region spectral filter', {'rows': len(df.index), 'input_features': len(columns), 'error_type': type(exc).__name__, 'error': str(exc)}),
        )
        raise

