"""Server-owned action mapping. Paths are relative to run.py; never supplied by HTTP."""
NOTEBOOK_JOBS = {
    "create_database": "xspatula/setup/setup_db.ipynb",
    "setup_processes": "xspatula/setup/setup_processes.ipynb",
    "delete_database": "xspatula/setup/delete_db.ipynb",
    "utility_data": "xspatula/import_ai4sh_data/import_data/load_ai4sh_utility_data_xspatula.ipynb",
    "dataset_metadata": "xspatula/import_ai4sh_data/import_data/load_ai4sh_dataset_meta_xspatula.ipynb",
    "sample_data": "xspatula/import_ai4sh_data/import_data/load_ai4sh_sample_data_xspatula.ipynb",
    "wetlab_data": "xspatula/import_ai4sh_data/import_data/load_ai4sh_wetlab_data_xspatula.ipynb",
    "spectral_data": "xspatula/import_ai4sh_data/import_data/load_ai4sh_spectral_data_xspatula.ipynb",
    "all_data": "xspatula/import_ai4sh_data/import_data/load_ai4sh_data.ipynb",
}
CELL_TIMEOUT_SECONDS = 3600
