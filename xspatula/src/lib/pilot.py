"""
@file pilot.py

@brief Project path resolution and JSON configuration management utilities for
in-situ data management workflows.

@details Resolves project, scheme, and process file paths across relative,
absolute, and home-based notations, then loads configuration inputs for package
workflows.
"""

from __future__ import annotations

import json
from os import makedirs, path
from pathlib import Path
from typing import Any

from src.utils import Read_json
from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


def Get_project_path(parent_FP: str, project_path: str) -> str:
    """Resolve a path string using parent_FP as its anchor."""
    parent_FP = (
        str(Path(parent_FP).parent)
        if Path(parent_FP).is_file()
        else parent_FP
    )

    if project_path.startswith("../"):
        project_path = str(
            (Path(parent_FP) / project_path).resolve()
        )

    elif project_path.startswith("./"):
        project_path = str(
            Path(parent_FP) / project_path[2:]
        )

    elif project_path == ".":
        project_path = parent_FP

    elif project_path.startswith("~/"):
        project_path = str(
            Path.home() / project_path[2:]
        )

    elif project_path.startswith("/"):
        pass

    else:
        project_path = str(
            Path(parent_FP) / project_path
        )

    return project_path


def Full_path_locate(
    parent_path: str | None,
    path_string: str,
    dir_make: bool = False,
    notebook_FP: str | None = None,
) -> str | None:
    """Resolve a two-level path and validate or optionally create it."""
    services().log(
        section="pilot",
        status="info",
        message=_format_trace_message(
            "Resolving path",
            {
                "parent_path": parent_path,
                "path_string": path_string,
                "notebook_path": notebook_FP,
                "create_directory": dir_make,
            },
        ),
    )

    if parent_path:
        if notebook_FP:
            fp = Get_project_path(notebook_FP, parent_path)
        else:
            fp = parent_path

    elif notebook_FP:
        fp = notebook_FP

    else:
        services().log(
            section="pilot",
            status="error",
            message=_format_trace_message(
                "Path resolution requires parent_path or notebook_FP",
                {
                    "path_string": path_string,
                },
            ),
        )
        return None

    full_path = Get_project_path(fp, path_string)

    if dir_make and not path.exists(full_path):
        try:
            makedirs(full_path, exist_ok=True)

        except OSError as error:
            services().log(
                section="pilot",
                status="error",
                message=_format_trace_message(
                    "Directory creation failed",
                    {
                        "path": full_path,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    },
                ),
            )
            return None

        services().log(
            section="pilot",
            status="success",
            message=_format_trace_message(
                "Directory created",
                {
                    "path": full_path,
                },
            ),
        )

    if not path.exists(full_path):
        services().log(
            section="pilot",
            status="error",
            message=_format_trace_message(
                "Resolved path does not exist",
                {
                    "path": full_path,
                },
            ),
        )
        return None

    services().log(
        section="pilot",
        status="success",
        message=_format_trace_message(
            "Path resolved",
            {
                "path": full_path,
            },
        ),
    )

    return full_path


def Clean_pilot_list(
    user_json_process_file_FPN_L: list[str],
    project_root_FP: str,
    project_D: dict[str, Any],
) -> list[str] | None:
    """Clean a process-file list and resolve entries under its directory."""
    json_path = path.join(
        project_root_FP,
        project_D["process"]["job_folder"],
        project_D["process"]["process_sub_folder"],
    )

    services().log(
        section="pilot",
        status="info",
        message=_format_trace_message(
            "Cleaning pilot process list",
            {
                "process_directory": json_path,
                "input_count": len(user_json_process_file_FPN_L),
            },
        ),
    )

    if not path.exists(json_path):
        services().log(
            section="pilot",
            status="error",
            message=_format_trace_message(
                "Process JSON directory does not exist",
                {
                    "path": json_path,
                },
            ),
        )
        return None

    cleaned_list = [
        path.join(json_path, item.strip())
        for item in user_json_process_file_FPN_L
        if isinstance(item, str)
        and len(item.strip()) > 5
        and not item.lstrip().startswith("#")
    ]

    services().log(
        section="pilot",
        status="success",
        message=_format_trace_message(
            "Pilot process list cleaned",
            {
                "input_count": len(user_json_process_file_FPN_L),
                "output_count": len(cleaned_list),
            },
        ),
    )

    return cleaned_list


def Get_scheme_project_path_setup(
    scheme_file: str,
    project_file: str,
) -> tuple[dict[str, Any], list[str]] | None:
    """Load scheme/project configuration and select process files."""
    services().log(
        section="scheme",
        status="info",
        message=_format_trace_message(
            "Loading scheme and project configuration",
            {
                "scheme_file": scheme_file,
                "project_file": project_file,
            },
        ),
    )

    if not scheme_file or not path.exists(scheme_file):
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "Scheme file does not exist",
                {
                    "scheme_file": scheme_file,
                },
            ),
        )
        return None

    try:
        scheme_params_D = Read_json(scheme_file)

    except Exception as error:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "Scheme file could not be read",
                {
                    "scheme_file": scheme_file,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            ),
        )
        return None

    if not scheme_params_D:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "Scheme file is empty or invalid JSON",
                {
                    "scheme_file": scheme_file,
                },
            ),
        )
        return None

    try:
        verbose = scheme_params_D["process"][0]["verbose"]

    except (KeyError, IndexError, TypeError) as error:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "Scheme does not contain a valid verbose setting",
                {
                    "scheme_file": scheme_file,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            ),
        )
        return None

    if verbose > 2:
        services().log(
            section="scheme",
            status="success",
            message=_format_trace_message(
                "Scheme parameters loaded",
                {
                    "parameters": scheme_params_D,
                },
            ),
        )
    else:
        services().log(
            section="scheme",
            status="success",
            message=_format_trace_message(
                "Scheme file loaded",
                {
                    "scheme_file": scheme_file,
                },
            ),
        )

    try:
        project_root_FP = Get_project_path(
            path.split(scheme_file)[0],
            scheme_params_D["project_path"],
        )

    except (KeyError, TypeError) as error:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "Scheme does not contain a valid project_path",
                {
                    "scheme_file": scheme_file,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            ),
        )
        return None

    if not project_root_FP:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "Project root path could not be resolved",
                {
                    "configured_project_path": scheme_params_D.get(
                        "project_path"
                    ),
                    "scheme_file": scheme_file,
                },
            ),
        )
        return None

    project_file_FPN = path.join(project_root_FP, project_file)

    if not path.exists(project_file_FPN):
        services().log(
            section="job",
            status="error",
            message=_format_trace_message(
                "Project or process file does not exist",
                {
                    "project_file": project_file_FPN,
                },
            ),
        )
        return None

    if verbose > 0:
        services().log(
            section="job",
            status="info",
            message=_format_trace_message(
                "Reading project or process file",
                {
                    "project_file": project_file_FPN,
                },
            ),
        )

    try:
        proj_proc_D = Read_json(project_file_FPN)

    except Exception as error:
        services().log(
            section="job",
            status="error",
            message=_format_trace_message(
                "Project or process file could not be read",
                {
                    "project_file": project_file_FPN,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            ),
        )
        return None

    if not proj_proc_D:
        services().log(
            section="job",
            status="error",
            message=_format_trace_message(
                "Project or process file is empty or invalid JSON",
                {
                    "project_file": project_file_FPN,
                },
            ),
        )
        return None

    if verbose > 2:
        services().log(
            section="job",
            status="success",
            message=_format_trace_message(
                "Project or process parameters loaded",
                {
                    "parameters": proj_proc_D,
                },
            ),
        )

    try:
        process_config = proj_proc_D["process"]

    except (KeyError, TypeError) as error:
        services().log(
            section="job",
            status="error",
            message=_format_trace_message(
                "Project file does not contain a valid process object",
                {
                    "project_file": project_file_FPN,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            ),
        )
        return None

    json_process_file_FPN_L: list[str] | None

    if isinstance(process_config, dict) and "pilot_list" in process_config:
        if verbose > 0:
            services().log(
                section="pilot",
                status="info",
                message=_format_trace_message(
                    "Reading process files from pilot_list",
                    {
                        "project_file": project_file_FPN,
                    },
                ),
            )

        pilot_list = process_config["pilot_list"]

        if not isinstance(pilot_list, list):
            services().log(
                section="pilot",
                status="error",
                message=_format_trace_message(
                    "pilot_list must be a list of JSON files",
                    {
                        "scheme_file": scheme_file,
                        "actual_type": type(pilot_list).__name__,
                    },
                ),
            )
            return None

        json_process_file_FPN_L = Clean_pilot_list(
            pilot_list,
            project_root_FP,
            proj_proc_D,
        )

    elif isinstance(process_config, dict) and "pilot_file" in process_config:
        pilot_FPN = path.join(
            project_root_FP,
            process_config["job_folder"],
            process_config["pilot_file"],
        )

        if verbose > 0:
            services().log(
                section="pilot",
                status="info",
                message=_format_trace_message(
                    "Reading process files from pilot file",
                    {
                        "pilot_file": pilot_FPN,
                    },
                ),
            )

        if not path.exists(pilot_FPN):
            services().log(
                section="pilot",
                status="error",
                message=_format_trace_message(
                    "Pilot file does not exist",
                    {
                        "pilot_file": pilot_FPN,
                        "scheme_file": scheme_file,
                    },
                ),
            )
            return None

        try:
            with open(pilot_FPN, encoding="utf-8") as file:
                process_L = file.readlines()

        except OSError as error:
            services().log(
                section="pilot",
                status="error",
                message=_format_trace_message(
                    "Pilot file could not be read",
                    {
                        "pilot_file": pilot_FPN,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    },
                ),
            )
            return None

        json_process_file_FPN_L = Clean_pilot_list(
            process_L,
            project_root_FP,
            proj_proc_D,
        )

    elif (
        isinstance(process_config, list)
        and process_config
        and isinstance(process_config[0], dict)
        and "process" in process_config[0]
    ):
        if verbose:
            services().log(
                section="process",
                status="info",
                message=_format_trace_message(
                    "Treating project file as a single process file",
                    {
                        "process_file": project_file_FPN,
                    },
                ),
            )

        json_process_file_FPN_L = [project_file_FPN]

    else:
        services().log(
            section="job",
            status="error",
            message=_format_trace_message(
                (
                    "Project file must contain pilot_list, pilot_file, "
                    "or at least one process"
                ),
                {
                    "project_file": project_file_FPN,
                },
            ),
        )
        return None

    if json_process_file_FPN_L is None:
        return None

    if verbose > 1:
        services().log(
            section="pilot",
            status="success",
            message=_format_trace_message(
                "Process files selected",
                {
                    "count": len(json_process_file_FPN_L),
                    "files": json_process_file_FPN_L,
                },
            ),
        )
    else:
        services().log(
            section="pilot",
            status="success",
            message=_format_trace_message(
                "Process files selected",
                {
                    "count": len(json_process_file_FPN_L),
                },
            ),
        )

    return scheme_params_D, json_process_file_FPN_L