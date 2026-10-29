"""PythonAnywhere WSGI entry point (copied to the Web tab's WSGI file).

The setup script creates a persistent key outside Git. Never paste it here.
"""

import os
import sys
from pathlib import Path

project_path = Path.home() / "flask_site"
secret_path = Path.home() / ".config" / "flask_site" / "secret_key"

if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = secret_path.read_text().strip()
if len(os.environ["SECRET_KEY"]) < 32:
    raise RuntimeError("Set a persistent SECRET_KEY with at least 32 characters.")

os.environ["FLASK_SITE_ENV"] = "production"
if str(project_path) not in sys.path:
    sys.path.insert(0, str(project_path))

from flask_site import app as application  # noqa: E402
