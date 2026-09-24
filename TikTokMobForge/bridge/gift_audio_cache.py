"""Persistent, voice-specific MP4 audio cache for gift acknowledgements."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

import voicevox_tts

CACHE_DIR = Path(__file__).resolve().parents[1] / "runtime/gift-audio"


def synthesize(config, text):
    settings = {key: config.get(key, default) for key, default in (
        ("tts_voicevox_url", "http://127.0.0.1:50021"),
        ("tts_voicevox_speaker_id", 3), ("tts_voicevox_speed", 1.0),
        ("tts_voicevox_pitch", 0.0), ("tts_voicevox_intonation", 1.0))}
    key = hashlib.sha256(json.dumps([1, text, settings], sort_keys=True).encode()).hexdigest()
    path = CACHE_DIR / (key + ".mp4")
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def convert(args, data=None):
        result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", *args],
            input=data, capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode:
            raise ValueError("Không xử lý được cache âm thanh cảm ơn")
        return result.stdout

    if path.is_file():
        try:
            pcm = convert(["-i", str(path), "-f", "s16le", "-ar", "24000", "-ac", "1", "pipe:1"])
            if pcm and len(pcm) % 2 == 0:
                return pcm
        except (ValueError, OSError, subprocess.TimeoutExpired):
            pass  # Regenerate a damaged cache entry.
    pcm = voicevox_tts.synthesize(config, text)
    temporary = path.with_name(key + "." + uuid.uuid4().hex + ".mp4")
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        convert(["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0",
                 "-c:a", "alac", "-y", str(temporary)], pcm)
        os.replace(temporary, path)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"GIFT không lưu được cache; vẫn phát âm thanh: {error}")
    finally:
        temporary.unlink(missing_ok=True)
    return pcm
