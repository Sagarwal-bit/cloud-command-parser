"""Score command-parser predictions against labelled data.

Usage
  python score.py PREDICTIONS GOLD [--schema data/schema.json] [--out report.json] [--min-validity 95]

PREDICTIONS  JSON Lines, one object per line: {"id": "V001", "prediction": "<raw model output text>"}
             "prediction" is the raw text your model produced (a string). It is parsed here.
GOLD         JSON Lines in the format of validation.jsonl.

Measures (all in percent, over every id in GOLD; a missing prediction counts as wrong)
  json_validity      output parses as a JSON object with exactly the keys intent, date, time, place
  intent_accuracy    intent equals the gold intent
  date_accuracy      date equals the gold date (null must match null)
  time_accuracy      time equals the gold time
  place_accuracy     place equals the gold place
  full_frame         intent and all three slots are correct together

Slot strings are compared after lower-casing and removing leading and trailing spaces.
With --min-validity, the script exits with status 1 if json_validity is below the given value.
Only the Python standard library is used.
"""
import argparse
import json
import sys

KEYS = ('intent', 'date', 'time', 'place')


def read_jsonl(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                sys.exit(f'{path}: line {n} is not valid JSON')
    return rows


def parse_prediction(raw):
    """Return the parsed object, or None if it is not a valid 4-key JSON object."""
    if isinstance(raw, dict):
        obj = raw
    else:
        try:
            obj = json.loads(str(raw).strip())
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(obj, dict) or set(obj.keys()) != set(KEYS):
        return None
    for k in ('date', 'time', 'place'):
        if obj[k] is not None and not isinstance(obj[k], str):
            return None
    if not isinstance(obj['intent'], str):
        return None
    return obj


def norm(v):
    return None if v is None else ' '.join(str(v).strip().lower().split())


def score(preds, gold):
    by_id = {}
    for p in preds:
        if 'id' not in p or 'prediction' not in p:
            sys.exit('every prediction line needs "id" and "prediction"')
        by_id[p['id']] = p['prediction']
    n = len(gold)
    c = {'json_validity': 0, 'intent_accuracy': 0, 'date_accuracy': 0,
         'time_accuracy': 0, 'place_accuracy': 0, 'full_frame': 0}
    for g in gold:
        obj = parse_prediction(by_id.get(g['id'])) if g['id'] in by_id else None
        if obj is None:
            continue
        c['json_validity'] += 1
        ok = {k: (obj[k] == g[k]) if k == 'intent' else (norm(obj[k]) == norm(g[k])) for k in KEYS}
        c['intent_accuracy'] += ok['intent']
        c['date_accuracy'] += ok['date']
        c['time_accuracy'] += ok['time']
        c['place_accuracy'] += ok['place']
        c['full_frame'] += all(ok.values())
    report = {k: round(100.0 * v / n, 2) for k, v in c.items()}
    report['examples'] = n
    report['missing_predictions'] = sum(1 for g in gold if g['id'] not in by_id)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('predictions')
    ap.add_argument('gold')
    ap.add_argument('--out', help='write the report as JSON to this file')
    ap.add_argument('--min-validity', type=float, help='exit with status 1 if json_validity is below this percent')
    a = ap.parse_args()
    report = score(read_jsonl(a.predictions), read_jsonl(a.gold))
    text = json.dumps(report, indent=2)
    print(text)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    if a.min_validity is not None and report['json_validity'] < a.min_validity:
        print(f'QUALITY GATE FAILED: json_validity {report["json_validity"]} < {a.min_validity}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
