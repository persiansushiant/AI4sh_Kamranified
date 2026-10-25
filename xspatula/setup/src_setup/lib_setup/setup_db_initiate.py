"""Database setup orchestration, with optional UI-managed confirmation.

interactive=True means execution is managed by the UI and yes/no confirmation
is skipped. The default False preserves prompts for standalone notebooks.
"""
from os import path, makedirs
from shutil import rmtree
import traceback

from setup.src_setup.lib_setup.setup_db import Setup_prod_roles
from src.lib import Full_path_locate, Get_scheme_project_path_setup
from src_setup.lib_setup import Setup_prod_DB, Setup_schemas_tables


def Get_user_response_boolean(prompt_text, *, interactive=False):
    """Return y for UI-managed execution, otherwise request console input."""
    if type(interactive) is not bool:
        raise TypeError("interactive must be a boolean")
    if interactive:
        return "y"
    print("\n⚠️    ✅  %s?: y\n      ❌ To skip/quit: n\n" % prompt_text)
    return input("⚠️ %s (y); stop(n): " % prompt_text)


def Delete_db_environments(notebook_FP):
    """Remove the generated PostgreSQL environment directory when present."""
    environment_path = path.join(path.split(notebook_FP)[0], 'src', 'postgres', 'environment')
    if path.exists(environment_path):
        rmtree(environment_path)


def Create_db_environment_dot(notebook_FP, postgresDB_D):
    """Create per-user database environment files from the scheme settings."""
    environment_path = path.join(path.split(notebook_FP)[0], 'src', 'postgres', 'environment')
    Delete_db_environments(notebook_FP)
    makedirs(environment_path)
    for item in postgresDB_D['db_users']:
        user_id = item['user_id']
        password = item['password']
        dot_env_file = path.join(environment_path, f'.{user_id}.env')
        with open(dot_env_file, 'w') as f:
            f.write(f"DB_NAME={postgresDB_D['db']}\n")
            f.write(f"DB_USER={user_id}\n")
            f.write(f"DB_PASSWORD={password}\n")
            f.write(f"DB_HOST={postgresDB_D['host']}\n")
            f.write(f"DB_PORT={postgresDB_D['port']}\n")
    print(f'\n. Database environment files created in: {environment_path}')


def Initiate_database(notebook_FP, scheme_file, proj_proc_file, *, interactive=False):
    """Load scheme/job files and run the existing database setup workflow."""
    if type(interactive) is not bool:
        raise TypeError("interactive must be a boolean")
    print('Scheme file:', scheme_file)
    scheme_file = Full_path_locate(None, scheme_file, False, notebook_FP)
    success = Get_scheme_project_path_setup(scheme_file, proj_proc_file)
    if not success:
        return None
    scheme_params_D, json_process_file_FPN_L = success

    if scheme_params_D['process'][0]['delete']:
        print("\n.   ⚠️  Confirm that you want to delete parts of or the whole the database.\n")
        confirm = Get_user_response_boolean(
            "Delete database %s?" % scheme_params_D['postgresdb']['db'],
            interactive=interactive,
        )
        if confirm.lower() != 'y':
            return None
    else:
        if scheme_params_D['process'][0]['verbose'] > 0:
            print("\n.   ⚠️  Confirm that you want to set up the database.\n")
            confirm = Get_user_response_boolean(
                "Set up database %s?" % scheme_params_D['postgresdb']['db'],
                interactive=interactive,
            )
            if confirm.lower() != 'y':
                return None
        print('\n. Setting up system production database: %s' % scheme_params_D['postgresdb']['db'])
        Create_db_environment_dot(notebook_FP, scheme_params_D['postgresdb'])
        success = Setup_prod_DB(scheme_params_D)
        if not success:
            Delete_db_environments(notebook_FP)
            return None

    if json_process_file_FPN_L:
        Setup_schemas_tables(scheme_params_D, json_process_file_FPN_L)
        if not scheme_params_D['process'][0]['delete']:
            try:
                Setup_prod_roles(scheme_params_D)
            except Exception:
                traceback.print_exc()
    else:
        print('⚠️ No process to run')
