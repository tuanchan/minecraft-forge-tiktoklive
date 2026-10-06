from pathlib import Path
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');a='                    assert not browser.errors, browser.errors';b='''                    import pinned_overlay
                    from bridge import send_interaction, pin_avatar_png
                    from PIL import Image
                    import io
                    with patch.object(pinned_overlay, "STATE", Path(profile) / "overlay.json"):
                        picture = pin_avatar_png("", "Admin")
                        assert Image.open(io.BytesIO(picture)).size == (256, 256)
                        send_interaction({"live_comments_only": False}, "pin_comment", "Admin", "test", "", "<b>Xin chào</b>", avatar_png=picture)
                        browser.command("Page.navigate", url=f"http://127.0.0.1:{server.server_port}/pinned-overlay.html")
                        deadline = time.monotonic() + 10
                        while time.monotonic() < deadline:
                            if browser.evaluate("document.querySelector('#board') && !document.querySelector('#board').hidden && document.querySelector('#avatar').naturalWidth === 256"):
                                break
                            time.sleep(.1)
                        assert browser.evaluate("document.querySelector('#avatar').naturalWidth") == 256
                        assert browser.evaluate("document.querySelector('#comment').textContent") == "<b>Xin chào</b>"
                        assert browser.evaluate("document.querySelector('#comment b') === null")
                        assert browser.evaluate("document.querySelector('#board').style.height") == "300px"
                        if os.environ.get("PIN_OVERLAY_SCREENSHOT"):
                            shot = browser.command("Page.captureScreenshot", format="png")
                            Path(os.environ["PIN_OVERLAY_SCREENSHOT"]).write_bytes(base64.b64decode(shot["data"]))
                        send_interaction({"live_comments_only": False}, "pin_comment", "Admin", "test", "", "")
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline and not browser.evaluate("document.querySelector('#board').hidden"):
                            time.sleep(.1)
                        assert browser.evaluate("document.querySelector('#board').hidden")
                    assert not browser.errors, browser.errors''';assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
