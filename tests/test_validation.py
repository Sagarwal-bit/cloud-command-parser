import unittest

from service.validator import InvalidModelOutput, validate_output


class ValidationTests(unittest.TestCase):
    def test_accepts_valid_frame(self):
        out = validate_output('{"intent": "weather_query", "date": null, "time": null, "place": "london"}')
        self.assertEqual(out["place"], "london")
        self.assertEqual(list(out), ["intent", "date", "time", "place"])

    def test_rejects_non_json(self):
        with self.assertRaises(InvalidModelOutput):
            validate_output("not json")

    def test_rejects_wrong_keys(self):
        with self.assertRaises(InvalidModelOutput):
            validate_output('{"intent": "alarm_set", "date": null, "time": null}')
        with self.assertRaises(InvalidModelOutput):
            validate_output('{"intent": "alarm_set", "date": null, "time": null, "place": null, "x": 1}')

    def test_rejects_unknown_intent_and_bad_slot_type(self):
        with self.assertRaises(InvalidModelOutput):
            validate_output('{"intent": "play_music", "date": null, "time": null, "place": null}')
        with self.assertRaises(InvalidModelOutput):
            validate_output('{"intent": "alarm_set", "date": 5, "time": null, "place": null}')

    def test_rejects_truncated_json(self):
        with self.assertRaises(InvalidModelOutput):
            validate_output('{"intent": "alarm_set", "date": "tomor')


if __name__ == "__main__":
    unittest.main()
