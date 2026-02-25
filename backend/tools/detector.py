import re
import json


TOOL_PATTERN = re.compile(r"<tool>(.*?)</tool>", re.DOTALL)


def extract_tool_call(text: str) -> dict | None:
    match = TOOL_PATTERN.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None