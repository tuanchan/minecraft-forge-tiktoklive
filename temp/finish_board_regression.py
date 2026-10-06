from pathlib import Path
p=Path('TikTokMobForge/tests/browser_reward_options_smoke.py');s=p.read_text(encoding='utf-8').replace("                time.sleep(2)\n", "                deadline = time.monotonic() + 20\n                while time.monotonic() < deadline:\n                    if browser.evaluate(\"typeof state !== 'undefined' && !!state && !document.querySelector('#loading')\"): break\n                    time.sleep(.1)\n");p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/src/main/java/vn/deadchan/tiktokmob/ServerPinnedCommentBoard.java');s=p.read_text(encoding='utf-8').replace('            if (player == null || existing.level != player.level()) continue;', '''            if (player == null || existing.level != player.level()) {
                if (existing.setting.grabbing()) {
                    var old = existing.setting;
                    existing.setting = new GiftNetwork.BoardPosition(old.side(), old.height(), old.distance(), old.scale(), false, old.pinned(), true);
                    persist(existing);
                }
                continue;
            }''');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/web/index.html');s=p.read_text(encoding='utf-8').replace('Bình luận mới giữ nguyên các bảng cũ.', 'Bình luận mới giữ nguyên trạng thái quay/ghim của từng bảng. Ngắm bảng cần chỉnh rồi giữ G để kéo hoặc nhấn F để ghim/bỏ ghim.');p.write_text(s,encoding='utf-8')
