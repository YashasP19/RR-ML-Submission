"""Flask application factory for the Pressure Players site."""
import os

from flask import Flask

from .data_store import ResultsStore
from .routes import api, pages


def create_app(results_dir=None):
    app = Flask(__name__)
    default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    app.config["RESULTS_DIR"] = results_dir or os.environ.get("RESULTS_DIR", default_dir)
    app.config["STORE"] = ResultsStore(app.config["RESULTS_DIR"])
    app.register_blueprint(pages)
    app.register_blueprint(api, url_prefix="/api")

    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

    @app.context_processor
    def asset_version():
        latest = max((os.path.getmtime(os.path.join(root, f)) for root, _, files in os.walk(static_dir) for f in files), default=0)
        return {"asset_v": int(latest)}

    @app.after_request
    def add_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        if resp.mimetype == "application/json":
            resp.headers.setdefault("Cache-Control", "public, max-age=60")
        return resp

    return app
