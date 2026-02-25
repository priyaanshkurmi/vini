import os
import json
import subprocess
from pathlib import Path

ALLOWED_APPS = {
    "safari", "finder", "notes", "calendar",
    "terminal", "calculator", "music", "photos"
}

ALLOWED_DIRS = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
]


def open_app(app_name: str) -> str:
    if app_name.lower() not in ALLOWED_APPS:
        return f"App '{app_name}' is not in the allowed list."
    subprocess.Popen(["open", "-a", app_name])
    return f"Opened {app_name}."


def create_file(path: str, content: str) -> str:
    p = Path(path).expanduser().resolve()
    if not any(str(p).startswith(str(d)) for d in ALLOWED_DIRS):
        return "Path is outside allowed directories."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Created file at {p}."


def read_file(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return "File not found."
    return p.read_text()[:2000]


def list_directory(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        return "Not a directory."
    items = [f.name for f in p.iterdir()][:30]
    return json.dumps(items)