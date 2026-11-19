"""Start the Kshetra controller and the field simulator."""

from backend.app import create_app
from backend.config import load_config

def main() -> None:
    config = load_config()
    app = create_app(config)
    simulator = app.extensions["sim"]
    simulator.start()
    url = f"http://{config.host}:{config.port}"
    print("Kshetra is running at", url)
    print("This process is a simulation. No sensors, rovers, or valves are connected.")
    print("Press Ctrl+C to stop.")
    try:
        app.run(host=config.host, port=config.port, debug=False, use_reloader=False, threaded=True)
    finally:
        simulator.stop()


if __name__ == "__main__":
    main()
