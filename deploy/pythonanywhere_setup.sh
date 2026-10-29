#!/usr/bin/env bash
# Run inside ~/flask_site on PythonAnywhere, NOT on your laptop.
# The Python version must match the existing web app's Web-tab Python version.
set -eo pipefail

PROJECT_DIR="$HOME/flask_site"
ACCOUNT="${HOME##*/}"
DOMAIN="${PA_DOMAIN:-${ACCOUNT,,}.pythonanywhere.com}"
WSGI_FILE="/var/www/${DOMAIN//./_}_wsgi.py"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
PYTHON="$(command -v "python${PYTHON_VERSION}" || true)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$SCRIPT_DIR" != "$PROJECT_DIR/deploy" || ! -f "$WSGI_FILE" ]]; then
    echo "Run this from ~/flask_site on PythonAnywhere, after creating the Web app."
    echo "Expected WSGI file: $WSGI_FILE"
    exit 1
fi
if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
    echo "Python $PYTHON_VERSION is unavailable. Set PYTHON_VERSION to the version shown on your Web tab."
    exit 1
fi

export WORKON_HOME="${WORKON_HOME:-$HOME/.virtualenvs}"
if ! type mkvirtualenv >/dev/null 2>&1; then
    WRAPPER="$(command -v virtualenvwrapper.sh || true)"
    if [[ -z "$WRAPPER" ]]; then WRAPPER="/usr/local/bin/virtualenvwrapper.sh"; fi
    if [[ ! -f "$WRAPPER" ]]; then
        echo "virtualenvwrapper is missing. Run this in a PythonAnywhere Bash console."
        exit 1
    fi
    source "$WRAPPER"
fi

if [[ -d "$WORKON_HOME/flaskENV" ]]; then
    workon flaskENV
else
    mkvirtualenv --python="$PYTHON" flaskENV
fi
ACTUAL_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$ACTUAL_VERSION" != "$PYTHON_VERSION" ]]; then
    echo "Existing flaskENV uses Python $ACTUAL_VERSION, not $PYTHON_VERSION."
    echo "Do not reuse an environment with the wrong Web-tab Python version."
    exit 1
fi

cd "$PROJECT_DIR"
python -m pip install -r requirements.txt
python -m pip check
python -m unittest discover -s tests -v

# Keep the same key across reloads; keep it private and outside the repository.
python - <<'PY'
import os
import secrets
from pathlib import Path

directory = Path.home() / ".config" / "flask_site"
directory.mkdir(parents=True, exist_ok=True)
directory.chmod(0o700)
path = directory / "secret_key"
try:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    if len(path.read_text().strip()) < 32:
        raise SystemExit("Existing secret key is invalid; stopping without replacing it.")
else:
    with os.fdopen(descriptor, "w") as stream:
        stream.write(secrets.token_hex(32) + "\n")
path.chmod(0o600)
print("Persistent secret key is configured outside Git (value not displayed).")
PY

# Prove that the production entry point imports before touching the live WSGI file.
python - <<'PY'
import runpy

application = runpy.run_path("deploy/pythonanywhere_wsgi.py")["application"]
assert not application.debug
assert application.config["SESSION_COOKIE_SECURE"]
assert application.test_client().get("/").status_code == 200
print("Production WSGI import check passed.")
PY

# Preserve the old Django/Flask entry point; do not delete its source or database.
WSGI_FILE="$WSGI_FILE" python - <<'PY'
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

target = Path(os.environ["WSGI_FILE"])
backups = Path.home() / ".config" / "flask_site" / "backups"
backups.mkdir(parents=True, exist_ok=True)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
backup = backups / (target.name + "." + stamp + ".bak")
shutil.copy2(target, backup)
shutil.copyfile("deploy/pythonanywhere_wsgi.py", target)
print(f"Previous WSGI configuration backed up to: {backup}")
print(f"Flask WSGI configuration written to: {target}")
PY

echo
echo "ONE MANUAL STEP REMAINS: update the PythonAnywhere Web tab, then Reload."
echo "Python version:       $PYTHON_VERSION"
echo "Source / working dir: $PROJECT_DIR"
echo "Virtualenv:           $WORKON_HOME/flaskENV"
echo "Static URL /static/ → $PROJECT_DIR/static"
echo "Enable Force HTTPS, then click Reload."
echo "Verify: https://$DOMAIN/ and https://$DOMAIN/hello/Ezekiel"
echo "Setup does not change Web-tab settings or reload the live app automatically."
