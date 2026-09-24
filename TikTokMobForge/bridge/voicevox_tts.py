"""Local VOICEVOX HTTP adapter; no API key or additional dependencies."""
import io
import json
import urllib.error
import urllib.parse
import urllib.request
import wave
import voicevox_runtime


def validate_url(value: str) -> str:
    value = str(value).strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError("VOICEVOX dùng địa chỉ HTTP trên máy này, ví dụ http://127.0.0.1:50021")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Cổng VOICEVOX không hợp lệ")
    return value


def request(base_url: str, path: str, *, params=None, body=None, post=False) -> bytes:
    url = validate_url(base_url) + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else (b"" if post else None)
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60 if post else 5) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        error.close()
        raise ValueError(f"VOICEVOX trả HTTP {error.code}. Kiểm tra giọng đã cài và nội dung tiếng Nhật.") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ValueError("Không kết nối được VOICEVOX. Hãy mở VOICEVOX và kiểm tra địa chỉ/cổng trong Cài đặt.") from error


def list_voices(base_url: str) -> dict:
    voicevox_runtime.ensure_running(validate_url(base_url))
    speakers = json.loads(request(base_url, "/speakers"))
    return {"voices": [
        {"id": style["id"], "name": f"{speaker['name']} — {style['name']}",
         "character": speaker["name"]}
        for speaker in speakers for style in speaker.get("styles", [])
        if style.get("type", "talk") == "talk"
    ]}


def synthesize(config: dict, text: str) -> bytes:
    base_url = config.get("tts_voicevox_url", "http://127.0.0.1:50021")
    voicevox_runtime.ensure_running(validate_url(base_url))
    speaker = int(config.get("tts_voicevox_speaker_id", 3))
    query = json.loads(request(base_url, "/audio_query", params={"text": text, "speaker": speaker}, post=True))
    query.update(speedScale=float(config.get("tts_voicevox_speed", 1.0)),
                 pitchScale=float(config.get("tts_voicevox_pitch", 0.0)),
                 intonationScale=float(config.get("tts_voicevox_intonation", 1.0)),
                 volumeScale=1.0, outputSamplingRate=24000, outputStereo=False)
    audio = request(base_url, "/synthesis", params={"speaker": speaker}, body=query, post=True)
    with wave.open(io.BytesIO(audio), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 24000, "NONE"):
            raise ValueError("VOICEVOX trả định dạng WAV không đúng PCM mono 24 kHz / 16 bit")
        pcm = wav.readframes(wav.getnframes())
    if not pcm:
        raise ValueError("VOICEVOX không trả dữ liệu âm thanh")
    return pcm
