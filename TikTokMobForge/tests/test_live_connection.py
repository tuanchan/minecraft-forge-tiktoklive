import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from live_connection import install_websocket_url_fix
from TikTokLive.client.ws import ws_connect


class WebSocketUrlTests(unittest.TestCase):
    def test_fallback_user_agent_is_safe_without_changing_signed_values(self):
        install_websocket_url_fix()
        agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        response = SimpleNamespace(cursor="cursor", push_server="wss://example.test/", route_params={
            "user_agent": agent, "token": "signed%2Bvalue%3D", "client": "ttlive-python",
        })
        uri = ws_connect.build_webcast_uri(response, {"version_code": "180800", "room_id": 123}, "&version_code=270000")
        self.assertFalse(any(c.isspace() for c in uri))
        self.assertIn("signed%2Bvalue%3D", uri)
        parsed = parse_qs(urlsplit(uri).query)
        self.assertEqual(parsed["user_agent"], [agent])
        self.assertEqual(parsed["version_code"], ["180800", "270000"])
        self.assertEqual(parsed["token"], ["signed+value="])

    def test_repeated_install_does_not_wrap_again(self):
        install_websocket_url_fix()
        builder = ws_connect.build_webcast_uri
        install_websocket_url_fix()
        self.assertIs(ws_connect.build_webcast_uri, builder)

    def test_fallback_bootstrap_starts_connect_event_and_heartbeat(self):
        install_websocket_url_fix()
        for host, expected in (("ws-fallback.eulerstream.com", True), ("example.test", False)):
            with self.subTest(host=host):
                response = SimpleNamespace(cursor="cursor", push_server=f"wss://{host}/",
                    route_params={"user_agent": "Mozilla/5.0 (Windows NT 10.0)"}, is_first=False)
                ws_connect.build_webcast_uri(response, {}, "")
                self.assertEqual(response.is_first, expected)


if __name__ == "__main__":
    unittest.main()
