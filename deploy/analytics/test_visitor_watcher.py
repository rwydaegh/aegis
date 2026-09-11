"""Exercise filtering, baselining, deduplication and delivery retries."""

# ruff: noqa: PT009, PT027
# Use unittest so these operational checks also run on the production host.

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import visitor_watcher as watcher


def visit(identifier, city="Paris", country="FR", site=None):
    return {"website_id": site or next(iter(watcher.SITES)), "visit_id": identifier, "city": city, "country": country}


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state.json"
        for context in (
            patch.object(watcher, "STATE_PATH", self.state),
            patch.dict(
                os.environ, {"VISITOR_EMAIL_FROM": "test", "VISITOR_EMAIL_TO": "test", "VISITOR_RESEND_API_KEY": "test"}
            ),
        ):
            context.start()
            self.addCleanup(context.stop)

    def test_filter(self):
        self.assertTrue(watcher.excluded(visit("1", " Gent ", "be")))
        self.assertTrue(watcher.excluded(visit("1", "Ghent", "BE")))
        self.assertFalse(watcher.excluded(visit("1", "Ghent", "US")))
        self.assertFalse(watcher.excluded(visit("1", None, None)))

    @patch.object(watcher, "notify")
    @patch.object(watcher, "recent_visits")
    def test_baseline_and_both_sites_deduplicate(self, recent, notify):
        recent.return_value = [visit("old")]
        watcher.run()
        notify.assert_not_called()
        recent.return_value += [visit("new"), visit("new", site=list(watcher.SITES)[1]), visit("local", "Ghent", "BE")]
        watcher.run()
        self.assertEqual(notify.call_count, 2)
        watcher.run()
        self.assertEqual(notify.call_count, 2)

    @patch.object(watcher, "notify")
    @patch.object(watcher, "recent_visits")
    def test_failed_delivery_retries_only_unsent(self, recent, notify):
        recent.return_value = []
        watcher.run()
        baseline = json.loads(self.state.read_text())["checked_at"]
        recent.return_value = [visit("first"), visit("second")]
        notify.side_effect = [None, RuntimeError("delivery failed")]
        with self.assertRaises(RuntimeError):
            watcher.run()
        self.assertEqual(json.loads(self.state.read_text())["checked_at"], baseline)
        notify.reset_mock(side_effect=True)
        watcher.run()
        self.assertEqual(notify.call_count, 1)
        self.assertEqual(notify.call_args.args[0]["visit_id"], "second")

    @patch.object(watcher, "recent_visits", side_effect=RuntimeError("database offline"))
    def test_failed_query_preserves_cursor(self, recent):
        initial = {"checked_at": 123, "initialized": True, "visits": []}
        self.state.write_text(json.dumps(initial))
        with self.assertRaises(RuntimeError):
            watcher.run()
        self.assertEqual(json.loads(self.state.read_text()), initial)
        self.assertEqual(recent.call_args.args[0], 123 - 7200)


if __name__ == "__main__":
    unittest.main()
