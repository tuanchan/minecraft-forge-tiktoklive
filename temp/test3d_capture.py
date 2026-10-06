from pathlib import Path
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');s=s.replace('with patch.object(pinned_overlay, "STATE", Path(profile) / "overlay.json"):', 'with patch.object(pinned_overlay, "STATE", Path(profile) / "overlay.json"), patch("bridge.socket.create_connection"):\n')
s=s.replace('{"live_comments_only": False}, "pin_comment"','{"live_comments_only": False, "minecraft_host": "localhost", "minecraft_port": 9876}, "pin_comment"')
a='''                            native = subprocess.Popen([os.environ["PIN_NATIVE_EXE"], "--pin-overlay", f"http://127.0.0.1:{server.server_port}"], creationflags=subprocess.CREATE_NO_WINDOW)
                            try:
                                time.sleep(5)
                                assert native.poll() is None, "Native WebView exited"
                                from PIL import ImageGrab
                                ImageGrab.grab().save(os.environ["PIN_NATIVE_SCREENSHOT"])
                            finally:'''
b='''                            frame_root = Path(profile) / "frames"
                            native_env = {**os.environ, "PIN_BOARD_FRAME_ROOT": str(frame_root)}
                            native = subprocess.Popen([os.environ["PIN_NATIVE_EXE"], "--pin-overlay", f"http://127.0.0.1:{server.server_port}"], env=native_env, creationflags=subprocess.CREATE_NO_WINDOW)
                            try:
                                deadline = time.monotonic() + 20
                                while not (frame_root / "frame.json").exists() and time.monotonic() < deadline:
                                    assert native.poll() is None, "Native WebView exited"
                                    time.sleep(.2)
                                manifest = json.loads((frame_root / "frame.json").read_text(encoding="utf-8-sig"))
                                assert manifest["token"] == pinned_overlay.snapshot()["token"]
                                frame = Image.open(frame_root / manifest["file"])
                                assert frame.size == (1400, 480), frame.size
                                assert frame.mode == "RGBA", frame.mode
                                assert frame.getpixel((0,0))[3] == 0, "Rounded corner lost transparency"
                                assert frame.getpixel((700,240))[3] > 200, "Frame is blank"
                                frame.save(os.environ["PIN_NATIVE_SCREENSHOT"])
                            finally:'''
assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
