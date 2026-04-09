import re
import json

# Match both correct <tool>{...}</tool> and malformed <tool={...}> or <tool ={...}>
TOOL_PATTERN = re.compile(
    r'<tool[=\s]*>?\s*(\{.*?\})\s*</tool>|<tool[=\s]*(\{.*?\})\s*>',
    re.DOTALL
)

def extract_tool_call(text: str) -> dict | None:
    match = TOOL_PATTERN.search(text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try fixing common issues: single quotes, trailing commas
        try:
            fixed = raw.replace("'", '"').strip().rstrip(',')
            return json.loads(fixed)
        except Exception:
            return None