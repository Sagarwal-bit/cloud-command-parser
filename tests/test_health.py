import os
import unittest

os.environ["SKIP_MODEL_LOAD"] = "1"
os.environ["MODEL_VERSION"] = "vtest"
os.environ["HOSTNAME"] = "pod-test"

try:
    from fastapi.testclient import TestClient
    from service.app import app, state
    HAVE_FASTAPI = True
except ImportError:  # fastapi/httpx not installed in this environment
    HAVE_FASTAPI = False

GOOD = '{"intent": "alarm_set", "date": "tomorrow", "time": "seven am", "place": null}'


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx not installed")
class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        state.update(ready=False, generator=None)
        os.environ.pop("FAULT_INJECT", None)

    def test_healthz_always_200_readyz_503_until_loaded(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        self.assertEqual(self.client.get("/readyz").status_code, 503)
        state.update(ready=True, generator=lambda t: GOOD)
        self.assertEqual(self.client.get("/readyz").status_code, 200)

    def test_parse_success_headers_and_body(self):
        state.update(ready=True, generator=lambda t: GOOD)
        r = self.client.post("/parse", json={"text": "set an alarm"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.json()), ["intent", "date", "time", "place"])
        self.assertEqual(r.headers["X-Model-Version"], "vtest")
        self.assertEqual(r.headers["X-Served-By"], "pod-test")

    def test_invalid_output_gives_500_exact_body(self):
        state.update(ready=True, generator=lambda t: '{"intent": "alarm_set", "date": "tomor')
        r = self.client.post("/parse", json={"text": "x"})
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json(), {"error": "invalid_model_output"})

    def test_fault_inject(self):
        state.update(ready=True, generator=lambda t: GOOD)
        os.environ["FAULT_INJECT"] = "1"
        r = self.client.post("/parse", json={"text": "x"})
        self.assertEqual((r.status_code, r.json()), (500, {"error": "invalid_model_output"}))


if __name__ == "__main__":
    unittest.main()
