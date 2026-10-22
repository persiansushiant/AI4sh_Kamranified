'''
Created on 29 May 2025

@author: thomasgumbricht
'''

# Standard library imports
import json
from os import path
from time import perf_counter

# Application package imports
from src.ai4sh.import_data import Process_import_JSON
from src.ai4sh.plot import Process_plot
from src.ai4sh.select import Process_select
from src.ai4sh.machine_learning_preprocess import Process_ml_preprocess
from src.ai4sh.machine_learning_model import Process_regression_model

from src.lib.login import Get_set_database_session
from src.utils import Today_as_str_YYYYMMDD

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


def Run_process(strcutured_process_D, scheme_params_D):
    """Execute all structured processes in sequence."""
    started_at = perf_counter()
    result_print_L = []
    pg_session_C = None

    process_file_count = (
        len(strcutured_process_D)
        if strcutured_process_D
        else 0
    )

    process_count = (
        sum(
            len(processes_D)
            for processes_D in strcutured_process_D.values()
        )
        if strcutured_process_D
        else 0
    )

    services().log(
        section="process",
        status="info",
        message=_format_trace_message(
            "Starting process execution",
            {
                "process_files": process_file_count,
                "processes": process_count,
            },
        ),
    )

    try:
        services().log(
            section="sql",
            status="info",
            message="Opening database session for process execution",
        )

        # Retrieve user access information and the PostgreSQL session.
        user_status_D, pg_session_C = Get_set_database_session(
            scheme_params_D
        )

        if not user_status_D:
            services().log(
                section="sql",
                status="error",
                message=(
                    "Database authentication did not return a user status"
                ),
            )
            return None

        services().log(
            section="sql",
            status="success",
            message=_format_trace_message(
                "Database session ready for process execution",
                {
                    "user_stratum": user_status_D.get("stratum_code"),
                },
            ),
        )

        for key, processes_D in strcutured_process_D.items():
            json_file_name = path.split(key)[1]

            services().log(
                section="process",
                status="info",
                message=_format_trace_message(
                    "Processing command file",
                    {
                        "file": key,
                        "ready_processes": len(processes_D),
                    },
                ),
            )

            for p_nr, process_S in processes_D.items():
                process_started_at = perf_counter()
                process_name = process_S.process.process
                root_process = process_S.process.root_process

                services().log(
                    section="process",
                    status="info",
                    message=_format_trace_message(
                        "Checking process access requirements",
                        {
                            "process_number": p_nr,
                            "process": process_name,
                            "root_process": root_process,
                            "file": json_file_name,
                        },
                    ),
                )

                # Compare the required stratum with the user's stratum.
                rec = pg_session_C._Single_search(
                    {"process": process_name},
                    ["min_user_stratum"],
                    "process",
                    "process",
                )

                process_stratum = rec[0] if rec else 0
                user_stratum = user_status_D["stratum_code"]

                if process_stratum > user_stratum:
                    services().log(
                        section="process",
                        status="error",
                        message=_format_trace_message(
                            "Skipping process because user stratum "
                            "is insufficient",
                            {
                                "process_number": p_nr,
                                "process": process_name,
                                "required_stratum": process_stratum,
                                "user_stratum": user_stratum,
                                "file": json_file_name,
                            },
                        ),
                    )
                    continue

                mode = "run"

                if process_S.process.overwrite:
                    mode = "overwrite"
                elif process_S.process.delete:
                    mode = "delete"

                services().log(
                    section="process",
                    status="info",
                    message=_format_trace_message(
                        "Running process",
                        {
                            "process_number": p_nr,
                            "process": process_name,
                            "root_process": root_process,
                            "mode": mode,
                            "file": json_file_name,
                        },
                    ),
                )

                if root_process == "translate_data":
                    services().log(
                        section="dispatcher",
                        status="info",
                        message=_format_trace_message(
                            "Dispatching process to JSON import handler",
                            {
                                "process": process_name,
                            },
                        ),
                    )

                    import_C = Process_import_JSON(
                        process_S,
                        pg_session_C,
                    )
                    result = import_C._Sub_process(key)

                    if result:
                        result_print_L.append(result)

                elif root_process == "manage_table_data":
                    services().log(
                        section="dispatcher",
                        status="info",
                        message=_format_trace_message(
                            "Dispatching process to table-data handler",
                            {
                                "process": process_name,
                            },
                        ),
                    )

                    import_C = Process_import_JSON(
                        process_S,
                        pg_session_C,
                    )
                    result = import_C._Sub_process(key)

                    if result:
                        result_print_L.append(result)

                elif root_process == "select_data":
                    services().log(
                        section="dispatcher",
                        status="info",
                        message=_format_trace_message(
                            "Dispatching process to selection handler",
                            {
                                "process": process_name,
                            },
                        ),
                    )

                    select_C = Process_select(
                        process_S,
                        pg_session_C,
                    )
                    select_C._Sub_process(key)

                elif root_process == "plot":
                    services().log(
                        section="dispatcher",
                        status="info",
                        message=_format_trace_message(
                            "Dispatching process to plotting handler",
                            {
                                "process": process_name,
                            },
                        ),
                    )

                    plot_C = Process_plot(
                        process_S,
                        pg_session_C,
                    )
                    plot_C._Sub_process(key)

                elif root_process == "machine_learning":
                    if process_name == "regression_modeling":
                        services().log(
                            section="dispatcher",
                            status="info",
                            message=_format_trace_message(
                                "Dispatching process to "
                                "regression-model handler",
                                {
                                    "process": process_name,
                                },
                            ),
                        )

                        model_C = Process_regression_model(
                            process_S,
                            pg_session_C,
                        )
                        model_C._Sub_process(key)

                    else:
                        services().log(
                            section="dispatcher",
                            status="info",
                            message=_format_trace_message(
                                "Dispatching process to "
                                "machine-learning preprocess handler",
                                {
                                    "process": process_name,
                                },
                            ),
                        )

                        ml_C = Process_ml_preprocess(
                            process_S,
                            pg_session_C,
                        )
                        ml_C._Sub_process(key)

                else:
                    services().log(
                        section="dispatcher",
                        status="error",
                        message=_format_trace_message(
                            "Root process handler is not available",
                            {
                                "root_process": root_process,
                                "process": process_name,
                                "process_number": p_nr,
                                "file": json_file_name,
                            },
                        ),
                    )
                    return None

                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Process completed",
                        {
                            "process_number": p_nr,
                            "process": process_name,
                            "root_process": root_process,
                            "duration_ms": round(
                                (
                                    perf_counter()
                                    - process_started_at
                                ) * 1000,
                                2,
                            ),
                        },
                    ),
                )

            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Command file completed",
                    {
                        "file": key,
                        "processes": len(processes_D),
                    },
                ),
            )

        if result_print_L:
            services().log(
                section="process",
                status="success",
                message=_format_trace_message(
                    "Translated process definitions were created",
                    {
                        "created_processes": len(result_print_L),
                        "creation_date": Today_as_str_YYYYMMDD(),
                    },
                ),
            )

            for row_number, row in enumerate(
                result_print_L,
                start=1,
            ):
                services().log(
                    section="process",
                    status="success",
                    message=_format_trace_message(
                        "Generated process definition",
                        {
                            "number": row_number,
                            "definition": row,
                        },
                    ),
                )

        services().log(
            section="process",
            status="success",
            message=_format_trace_message(
                "All processes finished",
                {
                    "process_files": process_file_count,
                    "processes": process_count,
                    "generated_processes": len(result_print_L),
                    "duration_ms": round(
                        (perf_counter() - started_at) * 1000,
                        2,
                    ),
                },
            ),
        )

        return result_print_L if result_print_L else None

    except Exception as error:
        services().log(
            section="process",
            status="error",
            message=_format_trace_message(
                "Process execution failed",
                {
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "duration_ms": round(
                        (perf_counter() - started_at) * 1000,
                        2,
                    ),
                },
            ),
        )
        raise

    finally:
        # Preserve cleanup on success, early return, or execution failure.
        if pg_session_C is not None:
            services().log(
                section="sql",
                status="info",
                message=(
                    "Closing database session after process execution"
                ),
            )

            try:
                pg_session_C._Close()

                services().log(
                    section="sql",
                    status="success",
                    message=(
                        "Database session closed after process execution"
                    ),
                )

            except Exception as error:
                services().log(
                    section="sql",
                    status="error",
                    message=_format_trace_message(
                        "Could not close database session",
                        {
                            "error_type": type(error).__name__,
                            "error": str(error),
                        },
                    ),
                )