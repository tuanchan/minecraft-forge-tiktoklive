from pathlib import Path
import hashlib
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');a='                                frame.save(os.environ["PIN_NATIVE_SCREENSHOT"])';b=a+'''
                                old_file = manifest["file"]
                                web.CONTROLLER.save({"mod": {"pinned_board_width": 1.8, "pinned_board_height": 1.2}})
                                deadline = time.monotonic() + 15
                                while time.monotonic() < deadline:
                                    manifest = json.loads((frame_root / "frame.json").read_text(encoding="utf-8-sig"))
                                    if manifest["file"] != old_file and manifest["width"] == 1800 and manifest["height"] == 360:
                                        break
                                    time.sleep(.2)
                                assert (manifest["width"], manifest["height"]) == (1800, 360), manifest
                                old_file = manifest["file"]
                                send_interaction({"live_comments_only": False, "minecraft_host": "localhost", "minecraft_port": 9876}, "pin_comment", "Tuấn 😀", "test", "", "Bảng 3D sắc nét", avatar_png=picture)
                                deadline = time.monotonic() + 15
                                while time.monotonic() < deadline:
                                    manifest = json.loads((frame_root / "frame.json").read_text(encoding="utf-8-sig"))
                                    if manifest["file"] != old_file and manifest["token"] == pinned_overlay.snapshot()["token"]:
                                        break
                                    time.sleep(.2)
                                assert manifest["token"] == pinned_overlay.snapshot()["token"]
                                assert manifest["file"] != old_file
''';assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
expected=hashlib.sha256('Tuấn 😀\nBảng 3D sắc nét'.encode()).hexdigest()[:32]
p=Path('TikTokMobForge/src/test/java/vn/deadchan/tiktokmob/GiftBagChecks.java');s=p.read_text(encoding='utf-8');a='        RuntimeSettingsChecks.run();';b=a+'\n        check(ServerPinnedCommentBoard.contentToken("Tuấn 😀", "Bảng 3D sắc nét").equals("'+expected+'"), "WebView/Python and Java UTF-8 frame identity");\n        System.out.println("WEB_BOARD_TOKEN_OK: Vietnamese and emoji match the WebView frame protocol");';assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
