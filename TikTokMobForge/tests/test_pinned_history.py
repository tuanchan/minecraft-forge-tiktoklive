import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_settings import web
import pinned_overlay

class PinnedHistoryTests(unittest.TestCase):
    def test_new_pins_and_empty_request_keep_previous_frames(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pinned_overlay, "STATE", Path(folder) / "state.json"):
            tokens = []
            for index in range(8):
                pinned_overlay.publish("User " + str(index), "Comment " + str(index), bytes([index]))
                tokens.append(pinned_overlay.snapshot()["token"])
            pinned_overlay.publish("", "")
            history = pinned_overlay.snapshot()["boards"]
            self.assertEqual({board["token"] for board in history}, set(tokens))
            self.assertEqual(len({board["avatar"] for board in history}), 8)
            self.assertEqual(len(list((Path(folder) / "pinned-history").glob("*.json"))), 8)
            pinned_overlay.publish("User 0", "Comment 0", b"\x00")
            self.assertEqual(len(pinned_overlay.snapshot()["boards"]), 8)

if __name__ == "__main__":
    unittest.main()
