from pathlib import Path
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');a='                        if os.environ.get("PIN_OVERLAY_SCREENSHOT"):';b='''                        if os.environ.get("PIN_NATIVE_EXE"):
                            native = subprocess.Popen([os.environ["PIN_NATIVE_EXE"], "--pin-overlay", f"http://127.0.0.1:{server.server_port}"], creationflags=subprocess.CREATE_NO_WINDOW)
                            try:
                                time.sleep(5)
                                assert native.poll() is None, "Native WebView exited"
                                from PIL import ImageGrab
                                ImageGrab.grab().save(os.environ["PIN_NATIVE_SCREENSHOT"])
                            finally:
                                native.terminate()
                                native.wait(timeout=5)
'''+a
assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
