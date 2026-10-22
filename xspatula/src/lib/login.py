"""
@file login.py

@brief User authentication module for process database access.

@details Validates project login input, authenticates the active user against
PostgreSQL, and returns user status information required by later processing
steps.

Version History:
- Created: 2025-01-05
- Updated: 2025-09-03 (Documentation added)
- Updated: 2026-07-30 (Structured tracing added)

@author Thomas Gumbricht
@date Created: 2025-01-05
@date Updated: 2026-07-30
"""

# Standard library imports
import json
from base64 import b64encode

# Package application imports
from src.postgres import PG_user_status, PG_session

from app.services.workspace_context import services


LOGIN_EVALUATION = "login_evaluation"


def _format_trace_message(message, details):
    """Preserve legacy details inside the current trace message."""
    return (
        f"{message} | "
        f"{json.dumps(details, ensure_ascii=False, default=str)}"
    )


def Get_set_database_session(scheme_params_D):
    """
    Authenticate the user and initialize a PostgreSQL session.

    Update scheme_params_D with the authenticated user status.

    Returns
    -------
    tuple
        (user_status_D, pg_session_C) on success.
        (None, None) when authentication or session creation fails.
    """
    services().log(
        section="scheme",
        status="info",
        message="Resolving database user session",
    )

    user_status_D = Project_login(scheme_params_D)

    if not user_status_D:
        services().log(
            section="scheme",
            status="error",
            message="Database user authentication failed",
        )
        return None, None

    if "stratum_code" not in user_status_D:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "Authenticated user has no stratum code",
                {
                    "user_name": user_status_D.get("user_name"),
                },
            ),
        )
        return None, None

    dot_env_var = "user_cat_%s" % user_status_D["stratum_code"]

    scheme_params_D["user_status"] = user_status_D

    services().log(
        section="scheme",
        status="success",
        message=_format_trace_message(
            "Database user authenticated",
            {
                "user_name": user_status_D.get("user_name"),
                "stratum_code": user_status_D.get("stratum_code"),
                "status_code": user_status_D.get("status_code"),
            },
        ),
    )

    services().log(
        section="sql",
        status="info",
        message=_format_trace_message(
            "Opening PostgreSQL session",
            {
                "environment": dot_env_var,
                "database": scheme_params_D.get(
                    "postgresdb", {}
                ).get("db"),
            },
        ),
    )

    try:
        pg_session_C = PG_session(
            dot_env_var,
            scheme_params_D["process"][0]["verbose"],
        )

    except Exception as error:
        services().log(
            section="sql",
            status="error",
            message=_format_trace_message(
                "Could not connect to PostgreSQL server",
                {
                    "database": scheme_params_D.get(
                        "postgresdb", {}
                    ).get("db"),
                    "environment": dot_env_var,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            ),
        )
        return None, None

    services().log(
        section="sql",
        status="success",
        message=_format_trace_message(
            "PostgreSQL session opened",
            {
                "environment": dot_env_var,
            },
        ),
    )

    return user_status_D, pg_session_C


def Project_login(default_parameter_D):
    """
    Authenticate using a netrc identifier or username and password.

    Return the user status dictionary, or None when authentication fails.
    """
    services().log(
        section="scheme",
        status="info",
        message="Authenticating project user",
    )

    if "user_project" not in default_parameter_D:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "User project configuration is missing",
                {
                    "missing_object": "user_project",
                },
            ),
        )
        return None

    user_project_D = default_parameter_D["user_project"]

    if (
        "user_netrc_id" in user_project_D
        and len(user_project_D["user_netrc_id"]) > 0
    ):
        authentication_method = "netrc"

        services().log(
            section="scheme",
            status="info",
            message=_format_trace_message(
                "Authenticating user with netrc identifier",
                {
                    "user_netrc_id": user_project_D["user_netrc_id"],
                },
            ),
        )

        rec = PG_user_status(
            LOGIN_EVALUATION,
            user_project_D["user_netrc_id"],
        )

    elif "user_name" in user_project_D and "password" in user_project_D:
        authentication_method = "credentials"

        services().log(
            section="scheme",
            status="info",
            message=_format_trace_message(
                "Authenticating user with credentials",
                {
                    "user_name": user_project_D["user_name"],
                },
            ),
        )

        # Preserve the encoding expected by the existing authentication API.
        rec = PG_user_status(
            LOGIN_EVALUATION,
            None,
            user_project_D["user_name"],
            b64encode(user_project_D["password"].encode()),
        )

    else:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "No supported user authentication information found",
                {
                    "required": (
                        "user_netrc_id or user_name and password "
                        "under user_project"
                    ),
                },
            ),
        )
        return None

    if not rec:
        services().log(
            section="scheme",
            status="error",
            message=_format_trace_message(
                "User was not recognized",
                {
                    "user_name": user_project_D.get("user_name"),
                    "authentication_method": authentication_method,
                },
            ),
        )
        return None

    params = [
        "id",
        "email",
        "first_name",
        "middle_name",
        "last_name",
        "user_name",
        "stratum_code",
        "status_code",
    ]

    user_status_D = dict(zip(params, rec))

    services().log(
        section="scheme",
        status="success",
        message=_format_trace_message(
            "Project user authenticated",
            {
                "user_name": user_status_D.get("user_name"),
                "stratum_code": user_status_D.get("stratum_code"),
                "authentication_method": authentication_method,
            },
        ),
    )

    return user_status_D