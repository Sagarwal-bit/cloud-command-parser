"""Load test for the command parser, for use with Locust (https://locust.io).

Install:  pip install locust
Run (the settings used for marking):
  locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m \
         --host http://localhost:8080 --csv results/loadtest

Locust prints the usual statistics and writes results/loadtest_stats.csv, which contains
the request count, failure count, median (50%) and 95% latency, and requests per second.

This file adds one thing Locust does not do by itself: it counts the response headers
X-Served-By (which replica answered) and X-Model-Version (which model version answered),
and prints both counts at the end of the run. It also saves them to results/loadtest_headers.json.

A request counts as a failure if it does not return HTTP 200 within 30 seconds.
Commands are taken in turn from data/validation.jsonl.
"""
import itertools
import json
import os
import threading
from collections import Counter

from locust import HttpUser, constant, events, task

TEXTS_FILE = os.environ.get('LOADTEST_TEXTS', 'data/validation.jsonl')
HEADERS_OUT = os.environ.get('LOADTEST_HEADERS_OUT', 'results/loadtest_headers.json')

_texts = [json.loads(line)['text'] for line in open(TEXTS_FILE, encoding='utf-8') if line.strip()]
_next_text = itertools.cycle(_texts)
_lock = threading.Lock()
_replicas = Counter()
_versions = Counter()


class ParserUser(HttpUser):
    wait_time = constant(0)  # send the next request as soon as the previous one returns

    @task
    def parse(self):
        with _lock:
            text = next(_next_text)
        with self.client.post('/parse', json={'text': text}, timeout=30,
                              name='/parse', catch_response=True) as resp:
            if resp.status_code == 200:
                with _lock:
                    _replicas[resp.headers.get('X-Served-By')] += 1
                    _versions[resp.headers.get('X-Model-Version')] += 1
                resp.success()
            else:
                resp.failure(f'HTTP {resp.status_code}')


@events.test_stop.add_listener
def _report(environment, **kwargs):
    result = {'per_replica': dict(_replicas), 'per_model_version': dict(_versions)}
    print('\nSuccessful requests by header:')
    print(json.dumps(result, indent=2))
    os.makedirs(os.path.dirname(HEADERS_OUT) or '.', exist_ok=True)
    with open(HEADERS_OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
