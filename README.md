# AI4SH Backbone

A local Flask workspace with Python activities, plain JavaScript modules, shared UI controls, encrypted SQLite configuration, and structured traces.

## Documentation

Read the [documentation home](docs/index.md). Published documentation uses Jekyll and GitHub Pages. Follow [the publishing guide](docs/github-publishing.md) to enable it.

## Run locally

Keep your existing `run.py` and dependency manifest. From the repository root on Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

If the previously supplied Windows launcher is included in your project, users can double-click `Start-AI4SH.bat` instead. Python must already be installed. The launcher is not included in this documentation overlay.

## Scope

This is a single-user, single-process local backbone. Database-copy and ML action handlers are placeholders in the supplied source snapshot. GitHub Pages serves documentation, not the Flask application.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep all code comments and UI text English. Keep the bundled Lucide license. Do not upload local state, encryption keys, credentials, or datasets containing private information.

This documentation package adds no runtime application source and does not change existing application behavior. Merge it into the complete project, not into `app/`.
