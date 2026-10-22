"""
@file initiate.py

@brief Process initialization module for loading and structuring process configurations.

@details Loads scheme and project configuration files, resolves their paths, and
returns structured process objects ready for downstream execution.

Version History:
- Created: December 2025
- Trace instrumentation added: July 2026

@author Thomas Gumbricht
"""

import json

# Package application imports
from src.lib import (
    Full_path_locate,
    Get_scheme_project_path_setup,
    Structure_processes,
)

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


def Initiate_process(notebook_FP, scheme_file, proj_proc_file):
    """
    Initialize a workflow by loading scheme and process configurations.

    Parameters
    ----------
    notebook_FP : str
        Notebook directory used as the base for relative paths.
    scheme_file : str
        Absolute or relative path to the scheme configuration.
    proj_proc_file : str
        Absolute or relative path to the project/process configuration.

    Returns
    -------
    tuple
        (structured_processes, scheme_params) on success.
        (None, None) when configuration loading fails or no executable
        processes are available.

    Notes
    -----
    Trace registration requires a bound workspace runtime.
    """
    services().log(
        section="job",
        status="info",
        message=_format_trace_message(
            "Starting workflow initialization",
            {
                "scheme_file": scheme_file,
                "workflow_file": proj_proc_file,
                "notebook_path": notebook_FP,
            },
        ),
    )

    try:
        services().log(
            section="scheme",
            status="info",
            message=_format_trace_message(
                "Resolving scheme path",
                {
                    "scheme_file": scheme_file,
                },
            ),
        )

        # The scheme path may be absolute or relative to the notebook.
        resolved_scheme_file = Full_path_locate(
            None,
            scheme_file,
            False,
            notebook_FP,
        )

        services().log(
            section="scheme",
            status="success",
            message=_format_trace_message(
                "Scheme path resolved",
                {
                    "resolved_scheme_file": resolved_scheme_file,
                },
            ),
        )

        services().log(
            section="scheme",
            status="info",
            message=_format_trace_message(
                "Loading scheme and workflow configuration",
                {
                    "workflow_file": proj_proc_file,
                },
            ),
        )

        setup_result = Get_scheme_project_path_setup(
            resolved_scheme_file,
            proj_proc_file,
        )

        if not setup_result:
            services().log(
                section="scheme",
                status="error",
                message=_format_trace_message(
                    "Scheme or workflow configuration could not be loaded",
                    {
                        "resolved_scheme_file": resolved_scheme_file,
                        "workflow_file": proj_proc_file,
                    },
                ),
            )

            return None, None

        scheme_params_D, json_process_file_FPN_L = setup_result

        services().log(
            section="scheme",
            status="success",
            message=_format_trace_message(
                "Scheme and workflow configuration loaded",
                {
                    "process_file_count": (
                        len(json_process_file_FPN_L)
                        if json_process_file_FPN_L
                        else 0
                    ),
                },
            ),
        )

        if not json_process_file_FPN_L:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "No process configuration found to run",
                    {
                        "workflow_file": proj_proc_file,
                    },
                ),
            )

            return None, None

        services().log(
            section="process",
            status="info",
            message=_format_trace_message(
                "Structuring processes",
                {
                    "process_file_count": len(json_process_file_FPN_L),
                },
            ),
        )

        structured_process_D = Structure_processes(
            scheme_params_D,
            json_process_file_FPN_L,
        )

        if not structured_process_D:
            services().log(
                section="process",
                status="error",
                message=_format_trace_message(
                    "Process structuring returned no executable processes",
                    {
                        "process_file_count": len(json_process_file_FPN_L),
                    },
                ),
            )

            return None, None

        services().log(
            section="process",
            status="success",
            message=_format_trace_message(
                "Processes structured successfully",
                {
                    "structured_process_count": len(structured_process_D),
                },
            ),
        )

        services().log(
            section="job",
            status="success",
            message=_format_trace_message(
                "Workflow initialization completed",
                {
                    "workflow_file": proj_proc_file,
                },
            ),
        )

        return structured_process_D, scheme_params_D

    except Exception as error:
        services().log(
            section="job",
            status="error",
            message=_format_trace_message(
                "Workflow initialization failed",
                {
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "scheme_file": scheme_file,
                    "workflow_file": proj_proc_file,
                },
            ),
        )

        # Preserve the original exception and traceback.
        raise