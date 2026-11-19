"""Start the Kshetra plant doctor."""

from backend.app import create_app
from backend.config import load_config


def main() -> None:
    config = load_config()
    app = create_app(config)
    url = f"http://{config.host}:{config.port}"
    print("Kshetra is running at", url)
    print("This page classifies plant photos. It does not connect to the field.")
    print("Press Ctrl+C to stop.")
    app.run(host=config.host, port=config.port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
