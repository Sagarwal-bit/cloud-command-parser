"""Output validation against data/schema.json (standard library only)."""
import json
import os
from pathlib import Path

SCHEMA_PATH = Path(os.environ.get(
    "SCHEMA_PATH", Path(__file__).resolve().parents[1] / "data" / "schema.json"))


class InvalidModelOutput(ValueError):
    """Raised when model text is not a schema-conformant command frame."""


def load_schema(path=SCHEMA_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_SCHEMA = load_schema()
KEYS = tuple(_SCHEMA["keys"])
INTENTS = frozenset(_SCHEMA["intents"])


def validate_output(text):
    """Parse `text` and return the dict if it satisfies the schema, else raise."""
    try:
        obj = json.loads(str(text).strip())
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidModelOutput("not json") from exc
    if not isinstance(obj, dict) or set(obj) != set(KEYS):
        raise InvalidModelOutput("keys")
    if obj["intent"] not in INTENTS:
        raise InvalidModelOutput("intent")
    for slot in ("date", "time", "place"):
        if obj[slot] is not None and not isinstance(obj[slot], str):
            raise InvalidModelOutput(f"slot {slot}")
    return {k: obj[k] for k in KEYS}
