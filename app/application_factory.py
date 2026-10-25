# Flask application factory and shared activity routes. Public services are context-bound
# while configuring the workspace and loading activity data; execution binds in Runtime.
from pathlib import Path
from .repositories.key_value_repository import KeyValueRepository
from flask import Flask, jsonify, render_template, request
from .task_runtime import Runtime
from .services.workspace_context import bind, unbind
from .workspace_configuration import configure

# Create the runtime and encrypted repository; configure menus with context binding.
def create_app(database_path=None):
    app = Flask(__name__)
    runtime = Runtime()
    runtime.store = KeyValueRepository(database_path or Path(app.instance_path) / "workspace.sqlite3")
    token = bind(runtime)
    try:
        from .services.import_data_controls import recover_interrupted_actions
        recover_interrupted_actions()
        configure()
    finally: unbind(token)
    app.extensions["runtime"] = runtime

    @app.before_request
    # Require the shell header for POSTs and reject new actions while a job or loading is active.
    def guard():
        if request.method == "POST":
            if request.headers.get("X-Shell-Request") != "1":
                return jsonify(error="Missing application request header"), 403
            with runtime.lock:
                if runtime.progress_state["active"] or (runtime.job and runtime.job["status"] == "running"):
                    return jsonify(error="An activity is running"), 409

    @app.get("/")
    # Return the shared shell HTML, not an activity-specific page.
    def index(): return render_template("workspace_shell.html")

    @app.get("/api/state")
    # Serialize runtime state and registered activity metadata under the shared lock.
    def state():
        with runtime.lock:
            return jsonify(**runtime.snapshot(), activities=[a.metadata() for a in runtime.registry.values()])

    @app.get("/api/activities/<activity_id>/ui")
    # Return markup only for a registered, enabled activity.
    def ui(activity_id):
        with runtime.lock:
            activity = runtime.registry.get(activity_id)
            if not activity or not activity.enabled:
                return jsonify(error="Activity unavailable"), 404
            return render_template(activity.template)

    @app.get("/api/activities/<activity_id>/data")
    # Call the read-only load() method with runtime binding; disable response caching for form secrets.
    def activity_data(activity_id):
        activity = runtime.registry.get(activity_id)
        if not activity or not activity.enabled:
            return jsonify(error="Activity unavailable"), 404
        token = bind(runtime)
        try:
            response = jsonify(activity.load())
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            unbind(token)

    @app.post("/api/activities/<activity_id>/run")
    # Validate an enabled activity and JSON object, then acknowledge background execution with HTTP 202.
    def run(activity_id):
        with runtime.lock:
            activity = runtime.registry.get(activity_id)
            if not activity or not activity.enabled:
                return jsonify(error="Activity unavailable"), 404
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                return jsonify(error="Expected JSON object"), 400
            try: return jsonify(job_id=runtime.start(activity, payload)), 202
            except RuntimeError as exc: return jsonify(error=str(exc)), 409
    return app
