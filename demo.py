"""Launch a disposable studio with synthetic records on the loopback interface."""

import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    with TemporaryDirectory(prefix="repertoire-studio-demo-") as demo_directory:
        os.environ["REPERTOIRE_DEMO_DATABASE"] = str(Path(demo_directory) / "demo.db")
        os.environ["FLASK_SECRET_KEY"] = secrets.token_hex(32)

        from app import app

        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
