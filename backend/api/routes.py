"""HTTP API for the plant doctor and the ESP32-CAM."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.irrigation.safety import SafetyError
from backend.utils.timeutil import utc_now

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _doctor():
    return current_app.extensions["doctor"]


def _treatments():
    return current_app.extensions["treatments"]


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "kshetra"})


@api_bp.get("/doctor")
def doctor():
    _treatments().tick(utc_now(), False)
    payload = _doctor().public()
    payload["treatment"] = _treatments().public()
    return payload


@api_bp.post("/treatments/confirm")
def confirm_treatment():
    body = request.get_json(silent=True) or {}
    current = _doctor().public().get("report")
    if current is None or current["report_id"] != body.get("report_id"):
        return jsonify({"error": "Confirm the latest doctor report."}), 409
    try:
        treatment = _treatments().confirm(current)
    except SafetyError as exc:
        return jsonify({"error": str(exc)}), 409
    payload = _doctor().public()
    payload["treatment"] = treatment
    return jsonify(payload)


@api_bp.post("/inspections")
def create_inspection():
    upload = request.files.get("image")
    if upload is not None:
        payload = upload.read()
        rover_id = request.form.get("rover_id", "rover1")
        checkpoint_id = request.form.get("checkpoint_id") or None
        source = request.form.get("source", "hardware")
    else:
        payload = request.get_data()
        rover_id = request.args.get("rover_id", "rover1")
        checkpoint_id = request.args.get("checkpoint_id") or None
        source = request.args.get("source", "hardware")
    if source not in ("simulated", "hardware"):
        return jsonify({"error": "source must be simulated or hardware."}), 400
    try:
        report = _doctor().examine(payload, rover_id, checkpoint_id, source)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(report)


@api_bp.get("/inspections/<int:inspection_id>/image")
def inspection_image(inspection_id: int):
    path = _doctor().image_path(inspection_id)
    if path is None:
        return jsonify({"error": "That photo is not in this build."}), 404
    return send_file(path)
