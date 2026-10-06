from pathlib import Path
r=Path('TikTokMobForge')
p=r/'src/test/java/vn/deadchan/tiktokmob/BoardTextChecks.java';s=p.read_text(encoding='utf-8').replace('    static void run() {','''    static void run() {
        var origin = net.minecraft.world.phys.Vec3.ZERO;
        var forward = new net.minecraft.world.phys.Vec3(0, 0, -1);
        if (BoardRaycast.distance(new net.minecraft.world.phys.Vec3(0, 1, 4), forward, origin, 0, 0, 4, 2) != 4)
            throw new AssertionError("Crosshair inside front face must hit");
        if (BoardRaycast.distance(new net.minecraft.world.phys.Vec3(0, 1, -4), forward.scale(-1), origin, 0, 0, 4, 2) != 4)
            throw new AssertionError("Back face must be selectable");
        for (var eye : new net.minecraft.world.phys.Vec3[]{new net.minecraft.world.phys.Vec3(2.1, 1, 4),
                new net.minecraft.world.phys.Vec3(0, 2.1, 4), new net.minecraft.world.phys.Vec3(0, -.1, 4)})
            if (BoardRaycast.distance(eye, forward, origin, 0, 0, 4, 2) >= 0)
                throw new AssertionError("Looking outside the rectangle must not delete");
        if (BoardRaycast.distance(new net.minecraft.world.phys.Vec3(0, 1, 4), forward.scale(-1), origin, 0, 0, 4, 2) >= 0)
            throw new AssertionError("Board behind the viewer must not hit");
        for (float yaw : new float[]{0, 45, 90, 180, 270}) for (float pitch : new float[]{-70, 0, 60}) {
            var rotation = new org.joml.Quaternionf().rotationYXZ((float)Math.toRadians(-yaw), (float)Math.toRadians(pitch), 0);
            var eye = rotation.transform(new org.joml.Vector3f(0, 1, 7));
            var ray = rotation.transform(new org.joml.Vector3f(0, 0, -1));
            double hit = BoardRaycast.distance(new net.minecraft.world.phys.Vec3(eye.x,eye.y,eye.z),
                new net.minecraft.world.phys.Vec3(ray.x,ray.y,ray.z), origin, yaw, pitch, 4, 2);
            if (Math.abs(hit - 7) > .001) throw new AssertionError("Rotated board ray missed: " + yaw + "/" + pitch);
        }
        System.out.println("BOARD_RAYCAST_OK: front/back, rotated, outside, behind");''');p.write_text(s,encoding='utf-8')
p=r/'tests/browser_pin_smoke.py';s=p.read_text(encoding='utf-8');a='''                    deadline = time.monotonic() + 10
                    while len(calls) < 2 and time.monotonic() < deadline:
                        time.sleep(0.1)
                    assert calls[1]["mode"] == "pin_clear"''';b='''                    time.sleep(.2)
                    assert len(calls) == 1, "Delete help must not send a global-clear command"
                    assert browser.evaluate("document.querySelector('#toastHost').textContent.includes('nhấn X')")''';assert a in s;s=s.replace(a,b)
anchor='''                                assert manifest["file"] != old_file

                            finally:'''
assert anchor in s
s=s.replace(anchor,'''                                assert manifest["file"] != old_file
                                # Rapid updates used to overwrite one frame and remove every older PNG after three captures.
                                tokens = [manifest["token"]]
                                for index in range(5):
                                    send_interaction({"live_comments_only": False, "minecraft_host": "localhost", "minecraft_port": 9876},
                                        "pin_comment", "Board " + str(index), "test", "", "Retained comment " + str(index), avatar_png=picture)
                                    tokens.append(pinned_overlay.snapshot()["token"])
                                deadline = time.monotonic() + 25
                                while time.monotonic() < deadline and not all((frame_root / (token + '.json')).exists() for token in tokens):
                                    time.sleep(.2)
                                files = []
                                for token in tokens:
                                    saved = json.loads((frame_root / (token + '.json')).read_text(encoding='utf-8-sig'))
                                    assert saved['token'] == token
                                    assert (frame_root / saved['file']).is_file(), "Old board PNG was evicted"
                                    files.append(saved['file'])
                                assert len(set(files)) == len(tokens), "Boards share a mutable texture file"
                                print('MULTI_BOARD_FRAMES_OK: rapid pins, six retained token manifests and independent PNGs')

                            finally:''');p.write_text(s,encoding='utf-8')
(r/'tests/test_pinned_history.py').write_text('''import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_settings import web
import pinned_overlay

class PinnedHistoryTests(unittest.TestCase):
    def test_new_pins_and_empty_request_keep_previous_frames(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pinned_overlay, "STATE", Path(folder) / "state.json"):
            tokens = []
            for index in range(8):
                pinned_overlay.publish("User " + str(index), "Comment " + str(index), bytes([index]))
                tokens.append(pinned_overlay.snapshot()["token"])
            pinned_overlay.publish("", "")
            history = pinned_overlay.snapshot()["boards"]
            self.assertEqual({board["token"] for board in history}, set(tokens))
            self.assertEqual(len({board["avatar"] for board in history}), 8)
            self.assertEqual(len(list((Path(folder) / "pinned-history").glob("*.json"))), 8)
            pinned_overlay.publish("User 0", "Comment 0", b"\\x00")
            self.assertEqual(len(pinned_overlay.snapshot()["boards"]), 8)

if __name__ == "__main__":
    unittest.main()
''',encoding='utf-8')
print('MULTI_BOARD_TESTS_UPDATED')
