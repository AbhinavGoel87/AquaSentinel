"""HTTP API for the field page, the doctor rover, and the ESP32 boards."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.irrigation.safety import SafetyError

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _sim():
    return current_app.extensions["sim"]


def _doctor():
    return current_app.extensions["doctor"]


def _treatments():
    return current_app.extensions["treatments"]


def _bundle():
    payload = _sim().snapshot()
    payload["doctor"] = _doctor().public()
    payload["treatment"] = _treatments().public()
    return payload


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "kshetra", "hardware": "simulated"})


@api_bp.get("/field")
def field():
    return jsonify(_bundle())


@api_bp.get("/outputs")
def outputs():
    snapshot = _sim().snapshot()
    treatment = _treatments().public()
    return jsonify(
        {
            "sprinklers": [{"id": zone["id"], "on": zone["valve_open"]} for zone in snapshot["zones"]],
            "treatment": None
            if not treatment["active"]
            else {"id": treatment["treatment_id"], "seconds_remaining": treatment["seconds_remaining"]},
            "emergency_stop": snapshot["emergency_stop"],
        }
    )


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
    payload = _bundle()
    payload["treatment"] = treatment
    return jsonify(payload)


@api_bp.post("/treatments/stop")
def stop_treatment():
    treatment = _treatments().halt("farmer_stop")
    payload = _bundle()
    payload["treatment"] = treatment
    return jsonify(payload)


@api_bp.post("/zones/<zone_id>/valve")
def set_zone_valve(zone_id: str):
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("open"), bool):
        return jsonify({"error": "Expected a JSON boolean field named open."}), 400
    try:
        snapshot = _sim().set_valve(zone_id, body["open"], "dashboard")
        snapshot["doctor"] = _doctor().public()
        snapshot["treatment"] = _treatments().public()
    except KeyError:
        return jsonify({"error": f"Unknown zone '{zone_id}'."}), 404
    except SafetyError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(snapshot)


@api_bp.post("/emergency-stop")
def emergency_stop():
    _treatments().halt("emergency_stop")
    snapshot = _sim().emergency_stop()
    snapshot["doctor"] = _doctor().public()
    snapshot["treatment"] = _treatments().public()
    return jsonify(snapshot)


@api_bp.post("/emergency-stop/reset")
def reset_emergency():
    snapshot = _sim().reset_emergency()
    snapshot["doctor"] = _doctor().public()
    snapshot["treatment"] = _treatments().public()
    return jsonify(snapshot)


@api_bp.post("/simulation/sensors/<sensor_id>/fault")
def inject_fault(sensor_id: str):
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("failed"), bool):
        return jsonify({"error": "Expected a JSON boolean field named failed."}), 400
    simulator = _sim()
    if not getattr(simulator, "allows_fault_injection", False):
        return jsonify({"error": "Fault injection is available only in the simulator."}), 409
    try:
        simulator.set_sensor_failed(sensor_id, body["failed"])
    except KeyError:
        return jsonify({"error": f"Unknown sensor '{sensor_id}'."}), 404
    return jsonify(_bundle())
