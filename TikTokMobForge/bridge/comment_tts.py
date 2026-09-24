import io
from array import array
import json
import os
import queue
import threading
import time
import wave
import winsound
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types import VoiceSettings
import voicevox_tts
import vietnamese_tts
from audio_playback import PLAYBACK_LOCK


ROOT = Path(__file__).resolve().parent
PCM_SAMPLE_RATE = 24_000
ADAM_VOICE_ID = "pNInz6obpgDQGcFmaJgB"


class CommentSpeaker:
    def __init__(self, client: ElevenLabs | None, voice_id: str, config: dict) -> None:
        self._config = dict(config)
        self._provider = config.get("tts_provider", "elevenlabs")
        self._client = client
        self._voice_id = voice_id
        self._model_id = str(config.get("tts_model_id", "eleven_flash_v2_5"))
        self._max_characters = max(1, int(config.get("tts_max_characters", 180)))
        self._read_username = bool(config.get("tts_read_username", True))
        self._volume = min(1.0, max(0.0, float(config.get("tts_volume", 1.0))))
        self._keep_latest_comment = bool(
            config.get("tts_keep_latest_comment", True)
        )
        self._pause_seconds = max(
            0.0, float(config.get("tts_pause_between_comments_seconds", 1.0))
        )
        self._trailing_silence_seconds = max(
            0.0, float(config.get("tts_trailing_silence_seconds", 0.3))
        )
        self._language_code = str(config.get("tts_language_code", "")).strip() or None
        self._voice_settings = VoiceSettings(
            stability=min(1.0, max(0.0, float(config.get("tts_stability", 0.5)))),
            similarity_boost=min(
                1.0, max(0.0, float(config.get("tts_similarity_boost", 0.75)))
            ),
            style=min(1.0, max(0.0, float(config.get("tts_style", 0.0)))),
            use_speaker_boost=bool(config.get("tts_use_speaker_boost", True)),
            speed=min(1.2, max(0.7, float(config.get("tts_speed", 1.0)))),
        )
        self._playback_lock = PLAYBACK_LOCK
        self._quota_exhausted = False
        queue_size = max(1, int(config.get("tts_queue_size", 20)))
        self._comments: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=queue_size)
        self._worker = threading.Thread(
            target=self._run,
            name="tiktok-comment-tts",
            daemon=True,
        )
        self._worker.start()

    def enqueue(self, display_name: str, comment: str) -> None:
        if self._quota_exhausted:
            return
        clean_comment = " ".join(str(comment or "").split())[: self._max_characters]
        if not clean_comment:
            return
        try:
            self._comments.put_nowait((display_name, clean_comment))
        except queue.Full:
            if not self._keep_latest_comment:
                print(f"TTS bỏ qua comment của {display_name}: hàng đợi đã đầy")
                return

            try:
                old_display_name, _ = self._comments.get_nowait()
                self._comments.task_done()
            except queue.Empty:
                old_display_name = ""
            try:
                self._comments.put_nowait((display_name, clean_comment))
                print(
                    f"TTS thay comment đang chờ của {old_display_name or 'người trước'} "
                    f"bằng comment mới nhất của {display_name}"
                )
            except queue.Full:
                print(f"TTS chưa thể xếp comment mới nhất của {display_name}")

    def _run(self) -> None:
        while True:
            display_name, comment = self._comments.get()
            if self._keep_latest_comment and self._pause_seconds:
                deadline = time.monotonic() + self._pause_seconds
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        latest_name, latest_comment = self._comments.get(
                            timeout=remaining
                        )
                    except queue.Empty:
                        break
                    self._comments.task_done()
                    display_name, comment = latest_name, latest_comment
                print(
                    f"TTS đã chờ {self._pause_seconds:g} giây và chọn "
                    f"comment mới nhất của {display_name}"
                )
            try:
                self._synthesize_and_play(display_name, comment)
            finally:
                self._comments.task_done()

    def play_test(self) -> bool:
        text = str(self._config.get("tts_test_text", "")).strip()
        if not text:
            text = ("こんにちは！遊びに来てくれてありがとう。今日も一緒に楽しもうね！"
                    if self._provider == "voicevox" else
                    "Xin chào, đây là âm thanh kiểm tra đọc bình luận TikTok.")
        return self._synthesize_and_play(
            "TikTok Mob",
            text, test=True,
        )

    def _synthesize_and_play(self, display_name: str, comment: str, *, test=False) -> bool:
        try:
            prefix = f"{display_name}さんのコメント、" if self._provider == "voicevox" else f"{display_name} bình luận: "
            text = prefix + comment if self._read_username and not test else comment
            pcm_audio = self._synthesize(text)
        except Exception as error:
            message, exhausted = self._describe_error(error)
            if exhausted:
                self._quota_exhausted = True
                self._discard_pending_comments()
            print(f"TTS không đọc được comment của {display_name}: {message}")
            return False
        with self._playback_lock:
            try:
                pcm_audio = self._scale_volume(pcm_audio, self._volume)

                trailing_silence = b"\x00\x00" * int(
                    PCM_SAMPLE_RATE * self._trailing_silence_seconds
                )
                print(f"TTS đang đọc comment của {display_name}...")
                winsound.PlaySound(
                    self._to_wav(pcm_audio + trailing_silence),
                    winsound.SND_MEMORY | winsound.SND_NODEFAULT | winsound.SND_SYNC,
                )
                print(f"TTS đã đọc xong comment của {display_name}.")
                if self._pause_seconds and not self._keep_latest_comment and not test:
                    time.sleep(self._pause_seconds)
                return True
            except Exception as error:
                error, quota_exhausted = self._describe_error(error)
                if quota_exhausted:
                    self._quota_exhausted = True
                    self._discard_pending_comments()
                print(f"TTS không đọc được comment của {display_name}: {error}")
                return False

    def _synthesize(self, text: str) -> bytes:
        if self._provider == "edge":
            return vietnamese_tts.synthesize(self._config, text)
        if self._provider == "voicevox":
            return voicevox_tts.synthesize(self._config, text)
        audio_chunks = self._client.text_to_speech.convert(
            text=text,
            voice_id=self._voice_id,
            model_id=self._model_id,
            language_code=self._language_code,
            voice_settings=self._voice_settings,
            output_format="pcm_24000",
        )
        pcm_audio = b"".join(
            bytes(chunk)
            for chunk in audio_chunks
            if isinstance(chunk, (bytes, bytearray))
        )
        if not pcm_audio:
            raise RuntimeError("ElevenLabs không trả về dữ liệu âm thanh")
        return pcm_audio

    def _discard_pending_comments(self) -> None:
        while True:
            try:
                self._comments.get_nowait()
            except queue.Empty:
                return
            self._comments.task_done()

    @staticmethod
    def _describe_error(error: Exception) -> tuple[str, bool]:
        raw_message = str(error)
        quota_exhausted = "quota_exceeded" in raw_message.casefold()
        body = getattr(error, "body", None)
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (TypeError, ValueError):
                body = None
        if isinstance(body, dict):
            detail = body.get("detail", body)
            if isinstance(detail, dict):
                code = str(detail.get("code", ""))
                message = str(detail.get("message", "")).strip()
                quota_exhausted = quota_exhausted or code.casefold() == "quota_exceeded"
                if message:
                    return message, quota_exhausted
        if quota_exhausted:
            return "ElevenLabs quota exceeded; TTS paused until restart", True
        return raw_message, False

    @staticmethod
    def _scale_volume(pcm_audio: bytes, volume: float) -> bytes:
        if volume == 1.0:
            return pcm_audio
        samples = array("h")
        samples.frombytes(pcm_audio)
        return array("h", (round(sample * volume) for sample in samples)).tobytes()

    @staticmethod
    def _to_wav(pcm_audio: bytes) -> bytes:
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(PCM_SAMPLE_RATE)
            wav_file.writeframes(pcm_audio)
        return wav_buffer.getvalue()


def create_comment_speaker(config: dict) -> CommentSpeaker | None:
    if not bool(config.get("tts_enabled", True)):
        print("TTS comment đang tắt trong config.json.")
        return None

    provider = config.get("tts_provider", "elevenlabs")
    if provider == "edge":
        voice = config.get("tts_edge_voice", "vi-VN-HoaiMyNeural")
        if voice not in vietnamese_tts.VOICES:
            print("Giọng tiếng Việt không hợp lệ. Chọn Hoài My hoặc Nam Minh trong Cài đặt.")
            return None
        print(f"TTS tiếng Việt đã chọn {vietnamese_tts.VOICES[voice]}, cao độ {config.get('tts_edge_pitch', 40):+} Hz.")
        return CommentSpeaker(None, "", config)
    if provider == "voicevox":
        try:
            voicevox_tts.validate_url(config.get("tts_voicevox_url", "http://127.0.0.1:50021"))
            print(f"Đã chọn TTS VOICEVOX, giọng ID {config.get('tts_voicevox_speaker_id', 3)}. Engine sẽ tự mở khi đọc.")
            return CommentSpeaker(None, "", config)
        except ValueError as error:
            print(f"TTS VOICEVOX không khởi tạo được: {error}")
            return None
    if provider != "elevenlabs":
        print(f"Dịch vụ TTS không hợp lệ: {provider}")
        return None
    load_dotenv(ROOT / ".env", override=True, encoding="utf-8-sig")
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print("Chưa có khóa ElevenLabs: tự dùng giọng tiếng Việt miễn phí. Muốn dùng ElevenLabs, lưu API key trong Cài đặt.")
        return create_comment_speaker({**config, "tts_provider": "edge"})

    try:
        client = ElevenLabs(api_key=api_key)
        configured_voice_id = str(config.get("tts_voice_id", "")).strip()
        if configured_voice_id:
            voice_id = configured_voice_id
            voice_name = str(config.get("tts_voice_name", "Adam")).strip() or "Adam"
        else:
            preferred_name = str(config.get("tts_voice_name", "Adam")).strip() or "Adam"
            if preferred_name.casefold() == "adam":
                voice_id = ADAM_VOICE_ID
                voice_name = "Adam"
            else:
                response = client.voices.search(search=preferred_name, page_size=20)
                voice = next(
                    (
                        candidate
                        for candidate in response.voices
                        if str(candidate.name).casefold() == preferred_name.casefold()
                    ),
                    None,
                )
                if voice is None:
                    raise RuntimeError(
                        f"không tìm thấy giọng {preferred_name}; hãy điền tts_voice_id"
                    )
                voice_id = voice.voice_id
                voice_name = str(voice.name)

        print(f"TTS comment đã bật với giọng {voice_name} ({voice_id}).")
        return CommentSpeaker(client, voice_id, config)
    except Exception as error:
        print(f"TTS comment không khởi tạo được: {error}")
        return None
