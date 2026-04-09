import os
import json
import subprocess
from pathlib import Path

# No whitelist — open any installed app
ALLOWED_DIRS = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
]


def open_app(app_name: str) -> str:
    """Open any installed Mac application by name."""
    if not app_name.strip():
        return "No app name provided."
    try:
        # Try exact name first
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Opened {app_name}."

        # Try title case (e.g. "apple tv" → "Apple TV")
        result = subprocess.run(
            ["open", "-a", app_name.title()],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Opened {app_name.title()}."

        # Try with spaces normalized
        name_clean = " ".join(w.capitalize() for w in app_name.split())
        result = subprocess.run(
            ["open", "-a", name_clean],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Opened {name_clean}."

        return f"Couldn't find '{app_name}'. Make sure it's installed."

    except Exception as e:
        return f"Failed to open app: {e}"


def create_file(path: str, content: str) -> str:
    p = Path(path).expanduser().resolve()
    # Allow Desktop, Documents, Downloads
    if not any(str(p).startswith(str(d)) for d in ALLOWED_DIRS):
        return "Path is outside allowed directories."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Created {p.name} on {p.parent.name}."


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


def open_file(path: str) -> str:
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        return f"File not found: {path}"
    try:
        subprocess.Popen(["open", expanded])
        return f"Opened {os.path.basename(expanded)}."
    except Exception as e:
        return f"Failed to open file: {e}"


def run_shortcut(name: str) -> str:
    """Run a macOS Shortcut by name."""
    try:
        subprocess.Popen(["shortcuts", "run", name])
        return f"Running shortcut: {name}"
    except Exception as e:
        return f"Failed to run shortcut: {e}"


def set_volume(level: int) -> str:
    """Set system volume 0-100."""
    level = max(0, min(100, level))
    os.system(f"osascript -e 'set volume output volume {level}'")
    return f"Volume set to {level}%."


def get_clipboard() -> str:
    """Get current clipboard text."""
    result = subprocess.run(["pbpaste"], capture_output=True, text=True)
    return result.stdout[:500] if result.stdout else "Clipboard is empty."