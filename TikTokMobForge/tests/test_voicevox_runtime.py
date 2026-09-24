import contextlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from test_settings import comment_tts
import voicevox_runtime as runtime


class RuntimeTests(unittest.TestCase):
    def test_existing_listener_is_reused(self):
        with patch.object(runtime, "is_listening", return_value=True), patch.object(runtime.subprocess, "Popen") as start:
            runtime.ensure_running("http://127.0.0.1:50021")
            start.assert_not_called()

    def test_missing_install_has_actionable_error(self):
        with patch.object(runtime, "is_listening", return_value=False), patch.object(runtime, "engine_path", return_value=None):
            with self.assertRaisesRegex(ValueError, "CAI_VOICEVOX.bat"):
                runtime.ensure_running("http://127.0.0.1:50021")

    def test_engine_starts_hidden_on_configured_port(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(runtime, "RUNTIME", Path(directory)), \
                patch.object(runtime, "engine_path", return_value=Path(directory) / "run.exe"), \
                patch.object(runtime, "startup_lock", return_value=contextlib.nullcontext()), \
                patch.object(runtime, "is_listening", side_effect=[False, False, True]), \
                patch.object(runtime.subprocess, "Popen") as start:
            start.return_value.poll.return_value = None
            runtime.ensure_running("http://127.0.0.1:50025")
            self.assertEqual(start.call_args.args[0][-4:], ["--host", "127.0.0.1", "--port", "50025"])
            self.assertEqual(start.call_args.kwargs["creationflags"], runtime.subprocess.CREATE_NO_WINDOW)
            self.assertTrue((Path(directory) / "voicevox-engine.log").exists())

    def test_second_caller_rechecks_after_lock(self):
        with patch.object(runtime, "is_listening", side_effect=[False, True]), \
                patch.object(runtime, "engine_path", return_value=Path("run.exe")), \
                patch.object(runtime, "startup_lock", return_value=contextlib.nullcontext()), \
                patch.object(runtime.subprocess, "Popen") as start:
            runtime.ensure_running("http://127.0.0.1:50021")
            start.assert_not_called()
