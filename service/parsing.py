"""Prompt format shared by training, evaluation and the service (standard library only)."""
import json

PROMPT_TEMPLATE = "Command: {text}\nJSON:"


def build_prompt(text):
    return PROMPT_TEMPLATE.format(text=text)


def build_training_text(text, target_json):
    """Training example: 'Command: <cmd>\\nJSON: <teacher json>'."""
    return build_prompt(text) + " " + target_json


def canonical_target(teacher_raw):
    """Compact, single-line form of the teacher's JSON (same content, no whitespace/newlines)."""
    return json.dumps(json.loads(teacher_raw), ensure_ascii=False)


def extract_output(generated):
    """Turn the text generated after the prompt into the candidate JSON string."""
    return generated.strip()
