import re
import logging
from datetime import datetime
from tools.registry import open_app, create_file, read_file, list_directory
from tools.detector import extract_tool_call

logging.basicConfig(
    filename="tool_audit.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)


def execute_if_tool(response_text: str) -> tuple[str, str | None]:
    call = extract_tool_call(response_text)
    if not call:
        return response_text, None

    action = call.get("action", "")
    logging.info(f"TOOL_CALL: {call}")

    dispatch = {
        "open_app":       lambda: open_app(call.get("app", "")),
        "create_file":    lambda: create_file(call.get("path", ""), call.get("content", "")),
        "read_file":      lambda: read_file(call.get("path", "")),
        "list_directory": lambda: list_directory(call.get("path", "")),
    }

    result = dispatch.get(action, lambda: f"Unknown tool: {action}")()

    # Strip the tool tag from the visible response
    clean = re.sub(r"<tool>.*?</tool>", "", response_text, flags=re.DOTALL).strip()
    return clean, result