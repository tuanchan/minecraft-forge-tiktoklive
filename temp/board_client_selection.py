from pathlib import Path
j=Path('TikTokMobForge/src/main/java/vn/deadchan/tiktokmob')
p=j/'PinnedCommentBoard.java';s=p.read_text(encoding='utf-8').replace('    private static int syncTicks;', '''    private static int syncTicks;
    private static boolean selecting, selectionReady, keyHeld, pendingPin;
    private static double pendingScroll;
    private static boolean pendingDistance;''')
a=s.index('        if (message.revision() == revision');b=s.index('\n    static void reset()',a)
s=s[:a]+'''        boolean changed = message.revision() != revision;
        if (selecting && !message.selectionReply()) return;
        if (!changed && !message.selectionReply()) return;
        if (changed) {
            grabbing = false; wasGrabDown = false; resetHeld = false; lastTapAt = 0;
        }
        revision = message.revision(); currentAuthor = nextAuthor; currentText = nextText;
        var saved = message.position();
        position.side = saved.side(); position.height = saved.height(); position.distance = saved.distance(); position.scale = saved.scale();
        pinned = saved.pinned(); orbitPaused = saved.paused();
        if (message.selectionReply()) { selecting = false; selectionReady = true; }
        syncTicks = 0;
    }

    private static void select() {
        selecting = true; selectionReady = false;
        GiftNetwork.selectBoard();
    }
''' + s[b:]
s=s.replace('        revision = -1;', '        selecting = false; selectionReady = false; keyHeld = false; pendingPin = false; pendingScroll = 0;\n        revision = -1;')
s=s.replace('        if (!visible() || steps == 0 || !Double.isFinite(steps)) return false;', '''        if (steps == 0 || !Double.isFinite(steps)) return false;
        if (!keyHeld && !selecting) { keyHeld = true; select(); }
        if (selecting) { pendingScroll += steps; pendingDistance = distanceMode; return true; }
        if (!visible()) return false;''')
s=s.replace('        if (mc.level == null || mc.player == null || currentText.isEmpty()) {', '''        if (mc.level == null || mc.player == null) { reset(); return; }
        if (mc.gui.screen() == null && ((grabDown && !keyHeld) || pinClicked)) {
            keyHeld = grabDown; pendingPin |= pinClicked;
            if (!selecting) select();
        }
        if (!grabDown) keyHeld = false;
        if (selecting) return;
        pinClicked = pendingPin; pendingPin = false;
        if (selectionReady) {
            selectionReady = false;
            if (pendingScroll != 0) { double steps = pendingScroll; pendingScroll = 0; scroll(steps, pendingDistance); }
        }
        if (currentText.isEmpty()) {''')
s=s.replace('GiftNetwork.sendBoardPosition(new GiftNetwork.BoardPosition(', 'GiftNetwork.sendBoardPosition(revision, new GiftNetwork.BoardPosition(')
p.write_text(s,encoding='utf-8')
# Scroll replay must not request another selection when the key was released while waiting.
s=p.read_text(encoding='utf-8').replace('if (!keyHeld && !selecting) { keyHeld = true; select(); }','if (!keyHeld && !selecting && pendingScroll == 0) { keyHeld = true; select(); }').replace('double steps = pendingScroll; pendingScroll = 0; scroll(steps, pendingDistance);','double steps = pendingScroll; keyHeld = true; pendingScroll = 0; scroll(steps, pendingDistance);');p.write_text(s,encoding='utf-8')
