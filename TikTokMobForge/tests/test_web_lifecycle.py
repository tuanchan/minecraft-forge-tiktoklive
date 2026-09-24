"""GUI reuse must survive Edge handing app URLs to an existing process."""
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))
import main as web


class WebLifecycleTests(unittest.TestCase):
    def test_reserved_port_falls_back(self):
        fallback = Mock()
        with patch.object(web, "existing_gui", return_value=False), \
                patch.object(web, "ThreadingHTTPServer", side_effect=[PermissionError(13, "reserved"), fallback]) as create:
            server, url = web.gui_server()
        self.assertIs(server, fallback)
        port = create.call_args_list[1].args[0][1]
        self.assertNotEqual(port, web.GUI_PORT)
        self.assertEqual(url, f"http://127.0.0.1:{port}/")

    def test_reuses_fallback_server(self):
        with patch.object(web, "existing_gui", side_effect=[False, True]), \
                patch.object(web, "ThreadingHTTPServer", side_effect=PermissionError(13, "reserved")) as create:
            server, url = web.gui_server()
        self.assertIsNone(server)
        self.assertNotEqual(url, f"http://127.0.0.1:{web.GUI_PORT}/")
        self.assertEqual(create.call_count, 1)

    def test_unexpected_socket_error_is_not_hidden(self):
        with patch.object(web, "existing_gui", return_value=False), \
                patch.object(web, "ThreadingHTTPServer", side_effect=OSError(24, "too many files")):
            with self.assertRaises(OSError):
                web.gui_server()

    def test_edge_handoff_is_not_waited_on(self):
        with patch.object(Path, "is_file", return_value=True), \
                patch.object(Path, "mkdir"), patch.object(web.subprocess, "Popen") as launch:
            web.open_window("http://127.0.0.1:12345/")
        launch.return_value.wait.assert_not_called()

    def test_health_identifies_this_project_and_reuses_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/"
        try:
            self.assertTrue(web.existing_gui(url))
            with patch.object(web, "GUI_PORT", server.server_port), \
                    patch.object(web, "open_window") as opened, \
                    patch.object(web, "ThreadingHTTPServer") as create:
                web.main()
                create.assert_not_called()
                opened.assert_called_once_with(url)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertFalse(web.existing_gui(url))

    def test_idle_server_stops_but_live_process_is_preserved(self):
        for running in (False, True):
            with self.subTest(running=running):
                server = Mock(last_activity=time.monotonic() - 200)
                stopped = Mock()
                stopped.wait.side_effect = [False, True]
                process = Mock()
                process.poll.return_value = None if running else 0
                with patch.object(web.CONTROLLER, "processes", {process}), \
                        patch.object(web.CONTROLLER.test_runner, "state", return_value={"running": False}):
                    web.stop_when_idle(server, stopped)
                self.assertEqual(server.shutdown.called, not running)


if __name__ == "__main__":
    unittest.main()
