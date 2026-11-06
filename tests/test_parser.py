import json
import unittest

from scripts.cost import cost_per_1000, error_budget
from service.parsing import build_prompt, build_training_text, canonical_target
from worker.clean import check_record, clean
from worker.worker import select_shard


def rec(i, text, raw):
    return {"id": f"C{i:04d}", "text": text, "teacher_raw": raw}


GOOD = '{"intent": "weather_query", "date": null, "time": null, "place": "london"}'


class ParserTests(unittest.TestCase):
    def test_prompt_and_training_text(self):
        self.assertEqual(build_prompt("hi"), "Command: hi\nJSON:")
        self.assertTrue(build_training_text("hi", "{}").startswith("Command: hi\nJSON: "))

    def test_canonical_target_is_single_line(self):
        pretty = '{\n  "intent": "alarm_set",\n  "date": null,\n  "time": null,\n  "place": null\n}'
        self.assertEqual(canonical_target(pretty),
                         '{"intent": "alarm_set", "date": null, "time": null, "place": null}')

    def test_sharding_partitions_every_line_once(self):
        lines = [str(n) for n in range(10)]
        shards = [select_shard(lines, i, 3) for i in range(3)]
        self.assertEqual(shards[1], ["1", "4", "7"])
        self.assertEqual(sorted(sum(shards, [])), sorted(lines))
        with self.assertRaises(ValueError):
            select_shard(lines, 3, 3)

    def test_clean_reasons_and_accounting(self):
        records = [
            rec(1, "what is the weather in london", GOOD),                                    # kept
            rec(2, "what is the weather in london", GOOD),                                    # duplicate
            rec(3, "x", "oops"),                                                              # (a)
            rec(4, "x", '{"intent": "alarm_set"}'),                                           # (b)
            rec(5, "x", '{"intent": "nope", "date": null, "time": null, "place": null}'),     # (c)
            rec(6, "set alarm",
                '{"intent": "alarm_set", "date": "monday", "time": null, "place": null}'),         # (d)
            rec(7, "set alarm", '[1]'),                                                       # (b)
        ]
        kept, s = clean(records)
        self.assertEqual([r["id"] for r in kept], ["C0001"])
        self.assertEqual((s["a_invalid_json"], s["b_bad_keys"], s["c_bad_intent"], s["d_bad_slot"],
                          s["duplicates"], s["kept"]), (1, 2, 1, 1, 1, 1))
        self.assertEqual(s["input"], 7)
        self.assertEqual(check_record(records[0]), None)

    def test_clean_output_is_id_ordered_and_deterministic(self):
        a = [rec(2, "b in london", GOOD.replace("london", "london")), rec(1, "a in london", GOOD)]
        k1, _ = clean(a)
        k2, _ = clean(list(reversed(a)))
        self.assertEqual([r["id"] for r in k1], ["C0001", "C0002"])
        self.assertEqual(json.dumps(k1), json.dumps(k2))

    def test_cost_and_error_budget_arithmetic(self):
        # synthetic inputs, only to test the formulas (NOT measured results)
        per, hourly, rph, c = cost_per_1000(2, 1, 1, 1.0, 3.5, 0.45)
        self.assertAlmostEqual(per, 3.95)
        self.assertAlmostEqual(hourly, 7.9)
        self.assertAlmostEqual(rph, 3600)
        self.assertAlmostEqual(c, 7.9 / 3600 * 1000)
        allowed, used, pct = error_budget(1000, 5, 99.0)
        self.assertAlmostEqual(allowed, 10.0)
        self.assertAlmostEqual(pct, 50.0)


if __name__ == "__main__":
    unittest.main()
