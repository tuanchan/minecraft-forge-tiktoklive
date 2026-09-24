"""Vietnamese Edge TTS, decoded to the shared sequential PCM playback format."""
import asyncio
import os
import subprocess

VOICES = {"vi-VN-HoaiMyNeural": "Hoài My — nữ", "vi-VN-NamMinhNeural": "Nam Minh — nam"}


async def _audio(config: dict, text: str) -> bytes:
    import edge_tts
    voice = config.get("tts_edge_voice", "vi-VN-HoaiMyNeural")
    if voice not in VOICES:
        raise ValueError("Hãy chọn giọng tiếng Việt Hoài My hoặc Nam Minh")
    chunks = []
    speech = edge_tts.Communicate(
        text, voice,
        rate=f"{int(config.get('tts_edge_rate', 5)):+d}%",
        pitch=f"{int(config.get('tts_edge_pitch', 40)):+d}Hz",
        volume="+0%",
    )
    async for chunk in speech.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    audio = b"".join(chunks)
    if not audio:
        raise ValueError("Dịch vụ giọng Việt không trả âm thanh. Kiểm tra Internet và thử lại.")
    return audio


async def _timed_audio(config: dict, text: str) -> bytes:
    return await asyncio.wait_for(_audio(config, text), timeout=45)


def synthesize(config: dict, text: str) -> bytes:
    try:
        import imageio_ffmpeg
        audio = asyncio.run(_timed_audio(config, text))
    except ImportError as error:
        raise ValueError("Thiếu thư viện giọng Việt. Mở bridge/RUN_BRIDGE.bat để tự cài thư viện.") from error
    except TimeoutError as error:
        raise ValueError("Dịch vụ giọng Việt phản hồi quá lâu. Kiểm tra Internet và thử lại.") from error
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"Không kết nối được dịch vụ giọng Việt ({type(error).__name__}). Kiểm tra Internet và thử lại.") from error
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
         "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", "pipe:1"],
        input=audio, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode or not result.stdout or len(result.stdout) % 2:
        raise ValueError("Không giải mã được âm thanh giọng Việt. Thử Test giọng lại.")
    return result.stdout
