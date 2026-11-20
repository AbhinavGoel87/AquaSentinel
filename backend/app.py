"""Flask application factory."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, render_template

from backend.api.routes import api_bp
from backend.config import Config, load_config
from backend.database.db import Database
from backend.irrigation.treatments import TreatmentController
from backend.vision.catalog import load_catalog
from backend.vision.doctor import DoctorService

ROOT = Path(__file__).resolve().parents[1]


def create_app(config: Config | None = None) -> Flask:
    cfg = config or load_config()
    app = Flask(
        __name__,
        template_folder=str(ROOT / "frontend" / "templates"),
        static_folder=str(ROOT / "frontend" / "static"),
    )
    database = Database(cfg.db_path)
    database.ensure_schema()
    doctor = DoctorService(database, load_catalog(cfg.plant_database_path), cfg.inspection_path)
    treatments = TreatmentController(database, doctor.catalog)
    app.extensions["config"] = cfg
    app.extensions["db"] = database
    app.extensions["doctor"] = doctor
    app.extensions["treatments"] = treatments
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def missing(_err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "That address is not part of this build."}), 404
        return ("Page not found.", 404)

    return app
