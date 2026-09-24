import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from test_settings import isolated_settings, web, config, comment_tts
import vietnamese_tts
import edge_tts
import imageio_ffmpeg


class VietnameseTests(unittest.TestCase):
    def test_roundtrip_and_validation(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            controller.save({"gui": gui, "bridge": {"tts_provider": "edge",
                "tts_edge_voice": "vi-VN-HoaiMyNeural", "tts_edge_pitch": 60, "tts_edge_rate": -5}})
            saved = controller.state()["bridge"]
            self.assertEqual(saved["tts_provider"], "edge")
            self.assertEqual(saved["tts_edge_pitch"], 60)
            self.assertEqual(saved["tts_edge_rate"], -5)
            for key, value in (("tts_edge_voice", "ja-JP-NanamiNeural"), ("tts_edge_rate", -51),
                               ("tts_edge_pitch", 101), ("tts_edge_pitch", 2.5), ("tts_edge_rate", True)):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    controller.save({"bridge": {key: value}})

    def test_vietnamese_text_and_tuning_reach_service_and_pcm_decoder(self):
        async def stream():
            yield {"type": "WordBoundary"}
            yield {"type": "audio", "data": b"mp3-part-1"}
            yield {"type": "audio", "data": b"mp3-part-2"}
        with patch.object(edge_tts, "Communicate", return_value=SimpleNamespace(stream=stream)) as speak, \
                patch.object(imageio_ffmpeg, "get_ffmpeg_exe", return_value="ffmpeg.exe"), \
                patch.object(vietnamese_tts.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"\0\0" * 10)) as decode:
            pcm = vietnamese_tts.synthesize({"tts_edge_pitch": 60, "tts_edge_rate": -5}, "Xin chào mọi người!")
            speak.assert_called_once_with("Xin chào mọi người!", "vi-VN-HoaiMyNeural", rate="-5%", pitch="+60Hz", volume="+0%")
            self.assertEqual(decode.call_args.kwargs["input"], b"mp3-part-1mp3-part-2")
            self.assertIn("24000", decode.call_args.args[0])
            self.assertEqual(pcm, b"\0\0" * 10)

    def test_no_audio_is_an_error(self):
        async def stream():
            yield {"type": "WordBoundary"}
        with patch.object(edge_tts, "Communicate", return_value=SimpleNamespace(stream=stream)):
            with self.assertRaisesRegex(ValueError, "không trả âm thanh"):
                asyncio.run(vietnamese_tts._audio({}, "Xin chào"))

    def test_shared_speaker_uses_vietnamese_without_elevenlabs_or_voicevox(self):
        with patch.object(comment_tts.threading.Thread, "start"), \
                patch.object(comment_tts, "ElevenLabs") as eleven, \
                patch.object(vietnamese_tts, "synthesize", return_value=b"\0\0" * 10) as synth, \
                patch.object(comment_tts.voicevox_tts, "synthesize") as japanese, \
                patch.object(comment_tts.winsound, "PlaySound") as play:
            speaker = comment_tts.create_comment_speaker({**config.DEFAULT_BRIDGE_CONFIG, "tts_provider": "edge"})
            self.assertTrue(speaker.play_test())
            self.assertTrue(synth.call_args.args[1].startswith("Xin chào"))
            self.assertTrue(speaker._synthesize_and_play("Bé Mây", "Thích quá!"))
            self.assertEqual(synth.call_args.args[1], "Bé Mây bình luận: Thích quá!")
            eleven.assert_not_called(); japanese.assert_not_called()
            self.assertEqual(play.call_count, 2)
