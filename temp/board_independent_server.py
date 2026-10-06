from pathlib import Path
j=Path('TikTokMobForge/src/main/java/vn/deadchan/tiktokmob')
p=j/'GiftNetwork.java';s=p.read_text(encoding='utf-8').replace('.networkProtocolVersion(10)','.networkProtocolVersion(11)').replace('record PinnedComment(String author, String text, long revision)', 'record PinnedComment(String author, String text, long revision, BoardPosition position, boolean selectionReply)')
s=s.replace('    public record BoardDelete() {}','    public record BoardDelete() {}\n    public record BoardSelect() {}\n    public record BoardMove(long revision, BoardPosition position) {}\n    static Consumer<ServerPlayer> onBoardSelect = player -> {};')
s=s.replace('BiConsumer<ServerPlayer, BoardPosition> onBoardPosition', 'BiConsumer<ServerPlayer, BoardMove> onBoardPosition')
a=s.index('        CHANNEL.messageBuilder(BoardPosition.class');b=s.index('        CHANNEL.messageBuilder(BoardDelete.class',a)
s=s[:a]+'''        CHANNEL.messageBuilder(BoardMove.class, NetworkDirection.PLAY_TO_SERVER)
            .encoder((m, b) -> { b.writeLong(m.revision()); encodePosition(m.position(), b); })
            .decoder(b -> new BoardMove(b.readLong(), decodePosition(b)))
            .consumerMainThread((m, c) -> { if (c.getSender() != null) onBoardPosition.accept(c.getSender(), m); }).add();
        CHANNEL.messageBuilder(BoardSelect.class, NetworkDirection.PLAY_TO_SERVER)
            .encoder((m, b) -> {}).decoder(b -> new BoardSelect())
            .consumerMainThread((m, c) -> { if (c.getSender() != null) onBoardSelect.accept(c.getSender()); }).add();
'''+s[b:]
s=s.replace('b.writeLong(m.revision); })','b.writeLong(m.revision); encodePosition(m.position(), b); b.writeBoolean(m.selectionReply()); })')
s=s.replace('new PinnedComment(b.readUtf(64), b.readUtf(400), b.readLong())','new PinnedComment(b.readUtf(64), b.readUtf(400), b.readLong(), decodePosition(b), b.readBoolean())')
s=s.replace('static void sendBoardPosition(BoardPosition position) { CHANNEL.send(position, PacketDistributor.SERVER.noArg()); }','''static void sendBoardPosition(long revision, BoardPosition position) { CHANNEL.send(new BoardMove(revision, position), PacketDistributor.SERVER.noArg()); }
    static void selectBoard() { CHANNEL.send(new BoardSelect(), PacketDistributor.SERVER.noArg()); }
    private static void encodePosition(BoardPosition m, net.minecraft.network.FriendlyByteBuf b) {
        b.writeDouble(m.side()); b.writeDouble(m.height()); b.writeDouble(m.distance()); b.writeDouble(m.scale());
        b.writeBoolean(m.grabbing()); b.writeBoolean(m.pinned()); b.writeBoolean(m.paused());
    }
    private static BoardPosition decodePosition(net.minecraft.network.FriendlyByteBuf b) {
        return new BoardPosition(b.readDouble(), b.readDouble(), b.readDouble(), b.readDouble(), b.readBoolean(), b.readBoolean(), b.readBoolean());
    }''');p.write_text(s,encoding='utf-8')
p=j/'ServerPinnedCommentBoard.java';s=p.read_text(encoding='utf-8').replace('/** The newest board is movable; older boards remain saved world displays until aimed deletion. */','/** Each board has its own owner, movement state, and stable control revision. */')
s=s.replace('Map<UUID, Board> BOARDS', 'Map<Long, Board> BOARDS').replace('private static final Map<UUID, GiftNetwork.BoardPosition> POSITIONS = new HashMap<>();','private static final Map<UUID, Long> SELECTED = new HashMap<>();\n    private static TikTokMobMod.ModSettings currentSettings = new TikTokMobMod.ModSettings();\n    private static final String STATE_TAG = "tiktokmob:board_state:";\n    private record SavedBoard(UUID owner, GiftNetwork.BoardPosition position) {}')
s=s.replace('        long revision;', '        long revision;\n        UUID owner;\n        GiftNetwork.BoardPosition setting = DEFAULT;')
s=s.replace('static void position(ServerPlayer player, GiftNetwork.BoardPosition packet) {','''static void position(ServerPlayer player, GiftNetwork.BoardMove message) {
        Board board = BOARDS.get(message.revision());
        if (board == null || !player.getUUID().equals(board.owner) || board.level != player.level()) return;
        GiftNetwork.BoardPosition packet = message.position();''')
s=s.replace('        UUID id = player.getUUID();\n        GiftNetwork.BoardPosition previous = POSITIONS.getOrDefault(id, DEFAULT);', '        GiftNetwork.BoardPosition previous = board.setting;')
s=s.replace('        POSITIONS.put(id, current);\n        Board board = BOARDS.get(id);', '        board.setting = current;\n        persist(board);')
a=s.index('    static void add(');b=s.index('    static void tick(',a)
s=s[:a]+'''    static void add(MinecraftServer server, String author, String text, byte[] avatarPng,
                    TikTokMobMod.ModSettings settings) {
        if (text.isBlank()) return;
        currentSettings = settings;
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            Board selected = BOARDS.get(SELECTED.get(player.getUUID()));
            GiftNetwork.BoardPosition previous = selected == null ? DEFAULT : selected.setting;
            GiftNetwork.BoardPosition position = new GiftNetwork.BoardPosition(previous.side(), previous.height(),
                previous.distance(), previous.scale(), false, false, false);
            Board board = create(player, author, text, avatarPng, position, Style.from(settings, position.scale()));
            board.owner = player.getUUID(); board.setting = position; board.revision = ++nextRevision;
            BOARDS.put(board.revision, board);
            SELECTED.put(player.getUUID(), board.revision);
            persist(board);
            sendState(player);
        }
    }

    static void sendState(ServerPlayer player) { sendState(player, false); }
    private static void sendState(ServerPlayer player, boolean selectionReply) {
        Board board = BOARDS.get(SELECTED.get(player.getUUID()));
        GiftNetwork.send(player, board == null ? new GiftNetwork.PinnedComment("", "", 0, DEFAULT, selectionReply)
            : new GiftNetwork.PinnedComment(board.author, board.text, board.revision, board.setting, selectionReply));
    }

    static void selectAimed(ServerPlayer player) {
        Display.TextDisplay display = aimed(player);
        if (display != null) {
            Board board = BOARDS.values().stream().filter(item -> item.display == display).findFirst().orElse(null);
            if (board == null) board = restore(player, display);
            if (board != null && player.getUUID().equals(board.owner)) SELECTED.put(player.getUUID(), board.revision);
        }
        sendState(player, true);
    }

    private static void persist(Board board) {
        board.display.entityTags().removeIf(tag -> tag.startsWith(STATE_TAG));
        String json = new com.google.gson.Gson().toJson(new SavedBoard(board.owner, board.setting));
        board.display.addTag(STATE_TAG + java.util.Base64.getEncoder().encodeToString(json.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    }

    private static Board restore(ServerPlayer player, Display.TextDisplay display) {
        String[] fields = display.getEntityData().get(textDataAccessor()).getString().split(":", 6);
        if (fields.length != 6) return null;
        BoardCaption caption = BoardCaption.decode(fields[5]);
        if (caption == null) return null;
        try {
            SavedBoard saved = null;
            for (String tag : display.entityTags()) if (tag.startsWith(STATE_TAG)) {
                saved = new com.google.gson.Gson().fromJson(new String(java.util.Base64.getDecoder().decode(tag.substring(STATE_TAG.length())),
                    java.nio.charset.StandardCharsets.UTF_8), SavedBoard.class);
            }
            if (saved != null && !player.getUUID().equals(saved.owner())) return null;
            double scale = caption.boardScale();
            Style style = new Style(currentSettings.pinned_board_background, currentSettings.pinned_board_border,
                caption.authorColor(), caption.commentColor(), scale, caption.scale() / scale, caption.avatarScale(),
                currentSettings.pinned_board_corner_radius, caption.avatarX(), caption.avatarY(), caption.x(), caption.y(),
                Double.parseDouble(fields[3]) / (5.4 * scale), Double.parseDouble(fields[4]) / (1.62 * scale), caption.authorX(), caption.authorY());
            GiftNetwork.BoardPosition position = saved == null ? new GiftNetwork.BoardPosition(0, .15,
                clamp(display.position().distanceTo(player.getEyePosition()), 2, 20), clamp(scale / currentSettings.pinned_board_scale, .05, 2.5), false, true, false) : saved.position();
            if (position == null) return null;
            // Never resume a stale mouse drag after reconnecting.
            position = new GiftNetwork.BoardPosition(position.side(), position.height(), position.distance(), position.scale(), false, position.pinned(), position.paused());
            var header = createHeader(player.level(), display.position(), display.getYRot() - 180, caption.text(), style, position.pinned());
            header.addTag(PART + display.getUUID());
            Board board = new Board(player.level(), display, header, List.of(), caption.author(), caption.text(), display.getYRot() - 180, new byte[0], style);
            board.owner = player.getUUID(); board.setting = position; board.revision = ++nextRevision;
            board.orientationPitch = display.getXRot(); board.pinned = position.pinned();
            board.anchor = position.pinned() ? display.position() : null;
            board.relativeOffset = display.position().subtract(player.position());
            board.orbitAngle = Math.atan2(-board.relativeOffset.x, board.relativeOffset.z);
            BOARDS.put(board.revision, board); persist(board);
            return board;
        } catch (RuntimeException invalid) { return null; }
    }

'''+s[b:]
a=s.index('        var active = new HashSet<UUID>();',s.index('    static void tick'));b=s.index('            Style style =',a)
s=s[:a]+'''        currentSettings = settings;
        if (server.getTickCount() % 20 == 0) for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            for (Display.TextDisplay display : player.level().getEntitiesOfClass(Display.TextDisplay.class, player.getBoundingBox().inflate(105))) {
                if (!display.getEntityData().get(textDataAccessor()).getString().startsWith("tiktokmob:web-board:")) continue;
                if (BOARDS.values().stream().noneMatch(board -> board.display == display)) restore(player, display);
            }
        }
        for (Board existing : new ArrayList<>(BOARDS.values())) {
            long id = existing.revision;
            if (existing.display.isRemoved()) { existing.header.discard(); BOARDS.remove(id); continue; }
            ServerPlayer player = server.getPlayerList().getPlayer(existing.owner);
            if (player == null || existing.level != player.level()) continue;
            String author = existing.author, text = existing.text;
            byte[] avatarPng = existing.avatarPng;
            GiftNetwork.BoardPosition setting = existing.setting;
'''+s[b:]
s=s.replace('                board.revision = existing.revision;','                board.revision = existing.revision;\n                board.owner = existing.owner; board.setting = existing.setting;\n                persist(board);')
a=s.index('        for (UUID id : new HashSet<>(BOARDS.keySet()))');b=s.index('    static void deleteAimed',a)
s=s[:a]+'''    }

    static void clear() {
        for (Board board : BOARDS.values()) { persist(board); board.header.discard(); }
        BOARDS.clear(); SELECTED.clear();
    }

'''+s[b:]
s=s.replace('    static void deleteAimed(ServerPlayer player) {\n        Vec3 eye', '    private static Display.TextDisplay aimed(ServerPlayer player) {\n        Vec3 eye')
s=s.replace('        if (selected == null) return;\n        final Display.TextDisplay target = selected;', '''        return selected;
    }

    static void deleteAimed(ServerPlayer player) {
        final Display.TextDisplay target = aimed(player);
        if (target == null) return;''')
s=s.replace('getPlayer(entry.getKey())', 'getPlayer(entry.getValue().owner)')
s=s.replace('            if (owner != null) GiftNetwork.send(owner, new GiftNetwork.PinnedComment("", "", 0));', '''            if (owner != null && java.util.Objects.equals(SELECTED.get(owner.getUUID()), entry.getKey())) {
                SELECTED.remove(owner.getUUID());
                GiftNetwork.send(owner, new GiftNetwork.PinnedComment("", "", 0, DEFAULT, false));
            }''')
p.write_text(s,encoding='utf-8')
p=j/'TikTokMobMod.java';s=p.read_text(encoding='utf-8').replace('GiftNetwork.onBoardPosition = ServerPinnedCommentBoard::position;', 'GiftNetwork.onBoardPosition = ServerPinnedCommentBoard::position;\n        GiftNetwork.onBoardSelect = ServerPinnedCommentBoard::selectAimed;');p.write_text(s,encoding='utf-8')
print('INDEPENDENT_BOARD_STATES_ADDED')
