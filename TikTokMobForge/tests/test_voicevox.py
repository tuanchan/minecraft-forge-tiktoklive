"""Provider switching and local HTTP contract; no external service or real playback."""
import io
import json
import threading
import unittest
import urllib.parse
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from test_settings import isolated_settings, web, config, comment_tts
import voicevox_tts


class VoicevoxTests(unittest.TestCase):
    def setUp(self):
        runtime = patch.object(voicevox_tts.voicevox_runtime, "ensure_running")
        runtime.start()
        self.addCleanup(runtime.stop)

    def test_settings_roundtrip_and_reject_invalid(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            settings = {"tts_provider": "elevenlabs", "gift_voicevox_enabled": True, "tts_voicevox_speaker_id": 0,
                        "tts_voicevox_speed": 1.15, "tts_voicevox_pitch": 0.06,
                        "tts_voicevox_intonation": 1.4, "tts_test_text": "こんにちは！"}
            controller.save({"gui": gui, "bridge": settings})
            saved = controller.state()["bridge"]
            for key, value in settings.items():
                self.assertEqual(saved[key], value)
            controller.save({"bridge": {"tts_provider": "elevenlabs"}})
            self.assertEqual(controller.state()["bridge"]["tts_voicevox_pitch"], 0.06)
            for key, value in (("tts_provider", "unknown"), ("tts_voicevox_speed", 0),
                               ("tts_voicevox_pitch", 0.16), ("tts_voicevox_intonation", float("nan")),
                               ("tts_voicevox_speaker_id", 1.5), ("tts_voicevox_speaker_id", True),
                               ("tts_voicevox_url", "https://example.com"), ("tts_test_text", "a" * 1001)):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    controller.save({"bridge": {key: value}})

    def test_http_synthesis_tuning_and_shared_playback(self):
        requests = []
        pcm = b"\x10\x00" * 240
        class Engine(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                payload = [{"name": "ずんだもん", "styles": [
                    {"id": 3, "name": "ノーマル", "type": "talk"},
                    {"id": 6000, "name": "歌", "type": "sing"}]}]
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def do_POST(self):
                url = urllib.parse.urlsplit(self.path)
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                requests.append((url.path, urllib.parse.parse_qs(url.query), body))
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"accent_phrases": []}' if url.path == "/audio_query"
                                 else comment_tts.CommentSpeaker._to_wav(pcm))

        with HTTPServer(("127.0.0.1", 0), Engine) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                self.assertEqual(len(voicevox_tts.list_voices(base)["voices"]), 1)
                settings = {**config.DEFAULT_BRIDGE_CONFIG, "tts_provider": "voicevox",
                            "tts_voicevox_url": base, "tts_voicevox_pitch": 0.06,
                            "tts_voicevox_speed": 1.15, "tts_voicevox_intonation": 1.4,
                            "tts_test_text": "こんにちは！", "tts_volume": 0.5,
                            "tts_trailing_silence_seconds": 0.1}
                with patch.object(comment_tts.threading.Thread, "start"), \
                        patch.object(comment_tts, "ElevenLabs") as eleven, \
                        patch.object(comment_tts.winsound, "PlaySound") as play:
                    speaker = comment_tts.create_comment_speaker(settings)
                    self.assertTrue(speaker.play_test())
                    eleven.assert_not_called()
                    self.assertEqual(requests[0][1]["text"], ["こんにちは！"])
                    query = json.loads(requests[1][2])
                    self.assertEqual((query["pitchScale"], query["speedScale"], query["intonationScale"]), (0.06, 1.15, 1.4))
                    self.assertEqual(requests[1][1]["speaker"], ["3"])
                    self.assertFalse(query["outputStereo"])
                    self.assertEqual(query["volumeScale"], 1.0)
                    with wave.open(io.BytesIO(play.call_args.args[0])) as wav:
                        self.assertEqual(wav.getframerate(), 24000)
                        self.assertEqual(wav.getnframes(), 2640)
                        self.assertEqual(wav.readframes(1), b"\x08\x00")
                    self.assertTrue(speaker._synthesize_and_play("Alice", "ありがとう"))
                    self.assertEqual(requests[2][1]["text"], ["Aliceさんのコメント、ありがとう"])
            finally:
                server.shutdown(); thread.join(timeout=5)

    def test_elevenlabs_still_receives_voice_settings(self):
        from unittest.mock import Mock
        client = Mock()
        client.text_to_speech.convert.return_value = [b"\0\0" * 10]
        with patch.object(comment_tts.threading.Thread, "start"), patch.object(comment_tts.winsound, "PlaySound"):
            speaker = comment_tts.CommentSpeaker(client, "voice-id", config.DEFAULT_BRIDGE_CONFIG)
            self.assertTrue(speaker.play_test())
        args = client.text_to_speech.convert.call_args.kwargs
        self.assertEqual(args["voice_id"], "voice-id")
        self.assertEqual(args["language_code"], "vi")
        self.assertEqual(args["voice_settings"].speed, 1)

    def test_unavailable_engine_and_invalid_audio_are_reported(self):
        with patch.object(voicevox_tts.urllib.request, "urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(ValueError, "Hãy mở VOICEVOX"):
                voicevox_tts.list_voices("http://127.0.0.1:50021")
        with patch.object(voicevox_tts, "request", side_effect=[b"{}", b"invalid audio"]):
            with self.assertRaises((wave.Error, EOFError)):
                voicevox_tts.synthesize({}, "こんにちは")


if __name__ == "__main__":
    unittest.main()
