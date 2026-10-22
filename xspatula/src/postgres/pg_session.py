"""
 @file pg_session.py

 @brief PostgreSQL session and credential management module.

 @details Handles credential lookup, psycopg2 connections, session logging, and
 user status retrieval for package workflows that interact with PostgreSQL.

 *Version History*:
 - Created: 2018-02-21
 - Updated: 2025-09-09 (Separated common and logging helpers, added documentation)
 - Updated: 2026-03-11 (Parameterized queries and password handling fixes)
 - Updated: 2026-03-15 (Updated PG_user_status)
 - Updated: 2026-07-30 (Added structured tracing and removed direct console output)

 @author Thomas Gumbricht

 @date Created: 2018-02-21
 @date Updated: 2026-07-30 (Added structured tracing and removed direct console output)
"""

# Standard library imports
import json
from os import getenv, path

import netrc

from base64 import b64decode, b64encode

from dotenv import load_dotenv

# Third party imports
import psycopg2

from psycopg2 import sql as pgsql

# Package application imports
from src.postgres.pg_common import PG_common

from src.utils import Log

from app.services.workspace_context import services


def _format_trace_message(message, details):
    """Keep legacy details in the message because TraceEntry has no details field."""
    return f"{message} | {json.dumps(details, ensure_ascii=False, default=str)}"


class PG_session(PG_common):
    """
    @brief PostgreSQL session wrapper with connection and logging support.

    @details Combines shared SQL helpers with connection state, cursor handling,
    and lightweight logging used throughout PostgreSQL workflows.
    """

    def __init__(self, environment_dot_file, verbose=0, session_id='unknown'):
        """
        @brief Connect to PostgreSQL and initialize session parameters.

        @param environment_dot_file Name of the environment file containing connection settings.
        @param verbose Verbosity level for logging and output (default: 0).
        @param session_id Identifier for the session (default: 'unknown').

        @details
            - Loads environment variables for the specified database.
            - Establishes a connection and cursor to the PostgreSQL database using psycopg2.
            - Initializes session ID and verbosity.
            - Calls initializers for PG_common and Log classes.
        """

        services().log(
            section='sql',
            status='info',
            message=_format_trace_message('Opening PostgreSQL session', {'environment': environment_dot_file, 'session_id': session_id}),
        )

        try:
            env_query_D = Get_env_var(environment_dot_file)

            if env_query_D is None:
                raise RuntimeError(
                    'Could not load environment <%s>' % environment_dot_file
                )

            self.conn, self.cursor = PG_psycopg2_connect(env_query_D)

            self.session_id = session_id
            self.verbose = verbose

            PG_common.__init__(self)

            self.log = Log

            services().log(
                section='sql',
                status='success',
                message=_format_trace_message('PostgreSQL session opened', {'database': env_query_D.get('db'), 'host': env_query_D.get('host'), 'port': env_query_D.get('port'), 'session_id': session_id}),
            )

        except Exception as error:
            services().log(
                section='sql',
                status='error',
                message=_format_trace_message('Could not open PostgreSQL session', {'environment': environment_dot_file, 'session_id': session_id, 'error_type': type(error).__name__, 'error': str(error)}),
            )
            raise

    def _Close(self):
        """
        @brief Close the active cursor and database connection.

        @return None
        """

        services().log(
            section='sql',
            status='info',
            message=_format_trace_message('Closing PostgreSQL session', {'session_id': self.session_id}),
        )

        close_errors = []

        try:
            if getattr(self, 'cursor', None) is not None and not self.cursor.closed:
                self.cursor.close()
        except Exception as error:
            close_errors.append(
                {
                    'resource': 'cursor',
                    'error_type': type(error).__name__,
                    'error': str(error),
                }
            )

        try:
            if getattr(self, 'conn', None) is not None and not self.conn.closed:
                self.conn.close()
        except Exception as error:
            close_errors.append(
                {
                    'resource': 'connection',
                    'error_type': type(error).__name__,
                    'error': str(error),
                }
            )

        if close_errors:
            services().log(
                section='sql',
                status='error',
                message=_format_trace_message('PostgreSQL session closed with errors', {'session_id': self.session_id, 'errors': close_errors}),
            )
            return

        services().log(
            section='sql',
            status='success',
            message=_format_trace_message('PostgreSQL session closed', {'session_id': self.session_id}),
        )


def User_netrc_credentials(user_netrc_id):
    """
    @brief Retrieves user credentials from the .netrc file.

    @param user_netrc_id coded host login and password found in user .netrc file

    @note The user_netrc_id must exist in the .netrc file in the users home directory.

    @return Dictionary containing connection user credentials.
    """

    services().log(
        section='sql',
        status='info',
        message=_format_trace_message('Loading user credentials from .netrc', {'netrc_id': user_netrc_id}),
    )

    try:
        secrets = netrc.netrc()
        credentials = secrets.authenticators(user_netrc_id)

        if credentials is None:
            raise LookupError(
                'No .netrc credentials found for <%s>' % user_netrc_id
            )

        username, account, password = credentials

    except Exception as error:
        services().log(
            section='sql',
            status='error',
            message=_format_trace_message('Could not load user credentials from .netrc', {'netrc_id': user_netrc_id, 'error_type': type(error).__name__, 'error': str(error)}),
        )
        return None

    password = b64encode(password.encode())

    query_D = {'user_name': username, 'pswd': password}

    services().log(
        section='sql',
        status='success',
        message=_format_trace_message('User credentials loaded from .netrc', {'netrc_id': user_netrc_id, 'user_name': username}),
    )

    return query_D


def User_login_pswd(username, password):
    """
    @brief Build encoded login credentials from an explicit username and password.

    @param username Username to authenticate.
    @param password Plain-text password to encode for transport.

    @note The password is base64-encoded before it is returned in the credential dictionary.

    @return Dictionary containing connection user credentials.
    """

    services().log(
        section='sql',
        status='info',
        message=_format_trace_message('Preparing explicit user credentials', {'user_name': username}),
    )

    try:
        password = b64encode(password.encode())
        query_D = {'user_name': username, 'pswd': password}

    except Exception as error:
        services().log(
            section='sql',
            status='error',
            message=_format_trace_message('Could not prepare explicit user credentials', {'user_name': username, 'error_type': type(error).__name__, 'error': str(error)}),
        )
        raise

    services().log(
        section='sql',
        status='success',
        message=_format_trace_message('Explicit user credentials prepared', {'user_name': username}),
    )

    return query_D


def PG_psycopg2_connect(env_query_D):
    """
    @brief Establishes a connection to a PostgreSQL database using psycopg2.

    @param env_query_D Dictionary containing connection parameters:
        - db: Database name
        - user: Username
        - pswd: Base64-encoded password
        - port: Port number
        - host: Host address

    @details
        - Decodes the base64-encoded password.
        - Creates a connection and cursor to the PostgreSQL database using psycopg2.

    @return Tuple (conn, cursor):
        - conn: psycopg2 connection object
        - cursor: psycopg2 cursor object
    """

    safe_connection_details = {
        'database': env_query_D.get('db'),
        'user_name': env_query_D.get('user_name'),
        'host': env_query_D.get('host'),
        'port': env_query_D.get('port'),
    }

    services().log(
        section='sql',
        status='info',
        message=_format_trace_message('Connecting to PostgreSQL', safe_connection_details),
    )

    try:
        pg_connection_D = {
            'dbname': env_query_D['db'],
            'user': env_query_D['user_name'],
            'password': b64decode(env_query_D['pswd']).decode('ascii'),
            'port': env_query_D['port'],
            'host': env_query_D['host'],
        }

        conn = psycopg2.connect(**pg_connection_D)

        # Enable autocommit mode - makes each statement commit automatically
        conn.autocommit = True

        cursor = conn.cursor()

    except Exception as error:
        services().log(
            section='sql',
            status='error',
            message=_format_trace_message('PostgreSQL connection failed', {**safe_connection_details, 'error_type': type(error).__name__, 'error': str(error)}),
        )
        raise

    services().log(
        section='sql',
        status='success',
        message=_format_trace_message('Connected to PostgreSQL', {**safe_connection_details, 'autocommit': conn.autocommit}),
    )

    return conn, cursor


def PG_user_status(environment_dot_file, user_netrc_id, user_name=None, user_pswd=None):
    """
    @brief Retrieves the user status information from the PostgreSQL database.

    @param environment_dot_file Name of the environment file used to connect to PostgreSQL.
    @param user_netrc_id Identifier for user credentials in the .netrc file (optional).
    @param user_name Username for login (optional, used if netrc ID is not provided).
    @param user_pswd Password for login (optional, used if netrc ID is not provided).

    @details
        - Connects to the PostgreSQL server using the provided database name.
        - Retrieves user credentials either from the .netrc file or from explicit parameters.
        - Executes a parameterized SQL query to fetch user details from the community.user
          table using either email or username. The password is NEVER embedded in the SQL
          string — it is always passed as a query parameter to prevent injection and avoid
          appearing in query logs or pg_stat_activity.
        - Closes the database session after the query.

    @return Tuple containing user information (id, email, first_name, middle_name, last_name, user_name, stratum_code, status_code), or None if connection or credentials fail.
    """

    services().log(
        section='sql',
        status='info',
        message=_format_trace_message('Retrieving PostgreSQL user status', {'environment': environment_dot_file, 'credential_source': 'netrc' if user_netrc_id else 'explicit'}),
    )

    session = None

    try:
        session = PG_session(environment_dot_file)

    except Exception as error:
        services().log(
            section='sql',
            status='error',
            message=_format_trace_message('Could not connect while retrieving user status', {'environment': environment_dot_file, 'error_type': type(error).__name__, 'error': str(error)}),
        )
        return None

    try:
        if user_netrc_id:
            user_login_query_D = User_netrc_credentials(user_netrc_id)

        elif user_name and user_pswd:
            # Preserve the existing behavior: user_pswd is expected to be encoded here.
            user_login_query_D = {'user_name': user_name, 'pswd': user_pswd}

        else:
            services().log(
                section='sql',
                status='error',
                message=_format_trace_message('No user credentials were provided', {'environment': environment_dot_file}),
            )
            return None

        if not user_login_query_D or not user_login_query_D['user_name']:
            services().log(
                section='sql',
                status='error',
                message=_format_trace_message('User credentials could not be resolved', {'environment': environment_dot_file}),
            )
            return None

        plaintext_password = b64decode(user_login_query_D['pswd']).decode('ascii')

        select_cols = (
            'id, email, first_name, middle_name, last_name, '
            'user_name, stratum_code, status_code'
        )

        lookup_field = 'email' if '@' in user_login_query_D['user_name'] else 'user_name'

        if lookup_field == 'email':
            sql = pgsql.SQL(
                'SELECT {} FROM community.user WHERE email = %s AND password = %s;'
            ).format(pgsql.SQL(select_cols))

        else:
            sql = pgsql.SQL(
                'SELECT {} FROM community.user WHERE user_name = %s AND password = %s;'
            ).format(pgsql.SQL(select_cols))

        services().log(
            section='sql',
            status='info',
            message=_format_trace_message('Executing user status query', {'schema': 'community', 'table': 'user', 'operation': 'select', 'lookup_field': lookup_field}),
        )

        session.cursor.execute(
            sql,
            (user_login_query_D['user_name'], plaintext_password),
        )

        rec = session.cursor.fetchone()

        services().log(
            section='sql',
            status='success',
            message=_format_trace_message('User status query completed', {'schema': 'community', 'table': 'user', 'record_found': rec is not None}),
        )

        return rec

    except Exception as error:
        services().log(
            section='sql',
            status='error',
            message=_format_trace_message('Could not retrieve PostgreSQL user status', {'environment': environment_dot_file, 'error_type': type(error).__name__, 'error': str(error)}),
        )
        return None

    finally:
        if session is not None:
            session._Close()


def Get_env_var(db):
    """
    @brief Loads environment variables for a PostgreSQL database connection.

    @param db Name of the database. Used to locate the environment file.

    @details
        - Sets the current path to the directory of this file.
        - Constructs the environment filename as .<db>.
        - Checks if the environment file exists in the 'environment' directory.
        - Loads environment variables from the file using dotenv.
        - Retrieves DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD from environment.
        - Encodes the password using base64.

    @return Dictionary with keys 'host', 'port', 'db', 'user', and 'pswd' (base64 encoded password), or None if the environment file does not exist.
    """

    BASEDIR = path.abspath(path.dirname(__file__))
    env_FN = '.%s.env' % db
    env_path = path.join(BASEDIR, 'environment', env_FN)

    services().log(
        section='sql',
        status='info',
        message=_format_trace_message('Loading PostgreSQL environment', {'environment': db, 'environment_file': env_FN}),
    )

    if not path.exists(env_path):
        services().log(
            section='sql',
            status='error',
            message=_format_trace_message('PostgreSQL environment file does not exist', {'environment': db, 'environment_file': env_FN}),
        )
        return None

    try:
        load_dotenv(env_path, override=True)

        DB_HOST = getenv('DB_HOST')
        DB_PORT = getenv('DB_PORT')
        DB_NAME = getenv('DB_NAME')
        DB_USER = getenv('DB_USER')
        DB_PASSWORD = getenv('DB_PASSWORD')

        missing = [
            key
            for key, value in (
                ('DB_HOST', DB_HOST),
                ('DB_PORT', DB_PORT),
                ('DB_NAME', DB_NAME),
                ('DB_USER', DB_USER),
                ('DB_PASSWORD', DB_PASSWORD),
            )
            if value is None
        ]

        if missing:
            services().log(
                section='sql',
                status='error',
                message=_format_trace_message('PostgreSQL environment is incomplete', {'environment': db, 'environment_file': env_FN, 'missing_variables': missing}),
            )
            return None

        env_query_D = {
            'host': DB_HOST,
            'port': DB_PORT,
            'db': DB_NAME,
            'user_name': DB_USER,
            'pswd': b64encode(DB_PASSWORD.encode()),
        }

    except Exception as error:
        services().log(
            section='sql',
            status='error',
            message=_format_trace_message('Could not load PostgreSQL environment', {'environment': db, 'environment_file': env_FN, 'error_type': type(error).__name__, 'error': str(error)}),
        )
        return None

    services().log(
        section='sql',
        status='success',
        message=_format_trace_message('PostgreSQL environment loaded', {'environment': db, 'database': DB_NAME, 'host': DB_HOST, 'port': DB_PORT, 'user_name': DB_USER}),
    )

    return env_query_D

