package vn.deadchan.tiktokmob;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.network.ChannelBuilder;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.SimpleChannel;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

public final class GiftNetwork {
    public static final SimpleChannel CHANNEL = ChannelBuilder.named("tiktokmob:ui")
        .networkProtocolVersion(4).simpleChannel();
    public record SkyRide(int carrierId) {}
    static Consumer<SkyRide> onSkyRide = message -> {};
    public record Notification(String title, String username, String kind, boolean donation) {}
    public record GiftAlert(String token) {}
    static Consumer<GiftAlert> onGiftAlert = message -> {};
    public record UiState(String settings, long giftCount) {}
    public record SettingsPatch(String requestId, String json) {}
    public record SettingsReply(String requestId, String json, String message, boolean success) {}
    static java.util.function.BiConsumer<ServerPlayer, SettingsPatch> onSettingsPatch = (player, patch) -> {};
    static Consumer<SettingsReply> onSettingsReply = message -> {};
    public record BagRequest(int page, String withdrawId) {}
    public record BagPage(int page, int pages, long total, List<GiftBagData.Entry> entries) {}
    static Consumer<Notification> onNotification = message -> {};
    static Consumer<UiState> onState = message -> {};
    static Consumer<BagPage> onPage = message -> {};

    public static void register() {
        CHANNEL.messageBuilder(SkyRide.class, NetworkDirection.PLAY_TO_CLIENT)
            .encoder((m, b) -> b.writeInt(m.carrierId()))
            .decoder(b -> new SkyRide(b.readInt()))
            .consumerMainThread((m, c) -> onSkyRide.accept(m)).add();
        CHANNEL.messageBuilder(SettingsPatch.class, NetworkDirection.PLAY_TO_SERVER)
            .encoder((m, b) -> { b.writeUtf(m.requestId); b.writeUtf(m.json); })
            .decoder(b -> new SettingsPatch(b.readUtf(36), b.readUtf(8192)))
            .consumerMainThread((m, c) -> {
                ServerPlayer player = c.getSender();
                if (player == null) return;
                if (!RuntimeSettings.canEdit(player)) {
                    send(player, new SettingsReply(m.requestId, "{}", "Chỉ chủ world hoặc OP được đổi cài đặt", false));
                    return;
                }
                onSettingsPatch.accept(player, m);
            }).add();
        CHANNEL.messageBuilder(SettingsReply.class, NetworkDirection.PLAY_TO_CLIENT)
            .encoder((m, b) -> { b.writeUtf(m.requestId); b.writeUtf(m.json); b.writeUtf(m.message); b.writeBoolean(m.success); })
            .decoder(b -> new SettingsReply(b.readUtf(36), b.readUtf(), b.readUtf(1024), b.readBoolean()))
            .consumerMainThread((m, c) -> onSettingsReply.accept(m)).add();
        CHANNEL.messageBuilder(GiftAlert.class, NetworkDirection.PLAY_TO_CLIENT)
            .encoder((m, b) -> b.writeUtf(m.token))
            .decoder(b -> new GiftAlert(b.readUtf(32)))
            .consumerMainThread((m, c) -> onGiftAlert.accept(m)).add();
        CHANNEL.messageBuilder(Notification.class, NetworkDirection.PLAY_TO_CLIENT)
            .encoder((m, b) -> { b.writeUtf(m.title); b.writeUtf(m.username); b.writeUtf(m.kind); b.writeBoolean(m.donation); })
            .decoder(b -> new Notification(b.readUtf(96), b.readUtf(64), b.readUtf(20), b.readBoolean()))
            .consumerMainThread((m, c) -> onNotification.accept(m)).add();
        CHANNEL.messageBuilder(UiState.class, NetworkDirection.PLAY_TO_CLIENT)
            .encoder((m, b) -> { b.writeUtf(m.settings); b.writeLong(m.giftCount); })
            .decoder(b -> new UiState(b.readUtf(), b.readLong()))
            .consumerMainThread((m, c) -> onState.accept(m)).add();
        CHANNEL.messageBuilder(BagRequest.class, NetworkDirection.PLAY_TO_SERVER)
            .encoder((m, b) -> { b.writeVarInt(m.page); b.writeUtf(m.withdrawId); })
            .decoder(b -> new BagRequest(b.readVarInt(), b.readUtf(36)))
            .consumerMainThread((m, c) -> {
                ServerPlayer player = c.getSender();
                if (player == null || !player.isAlive() || player.isSpectator()) return;
                GiftBagData bag = GiftBagData.get(player);
                if (!m.withdrawId.isEmpty()) bag.withdraw(player, m.withdrawId);
                send(player, bag.page(player, m.page));
            }).add();
        CHANNEL.messageBuilder(BagPage.class, NetworkDirection.PLAY_TO_CLIENT)
            .encoder((m, b) -> {
                b.writeVarInt(m.page); b.writeVarInt(m.pages); b.writeLong(m.total);
                b.writeVarInt(m.entries.size());
                for (var entry : m.entries) { b.writeUtf(entry.id()); ItemStack.STREAM_CODEC.encode(b, entry.stack()); }
            })
            .decoder(b -> {
                int page = b.readVarInt(), pages = b.readVarInt(); long total = b.readLong();
                int size = b.readVarInt();
                if (size < 0 || size > 45) throw new IllegalArgumentException("Invalid gift page");
                List<GiftBagData.Entry> entries = new ArrayList<>();
                for (int i = 0; i < size; i++) entries.add(new GiftBagData.Entry(b.readUtf(36), ItemStack.STREAM_CODEC.decode(b)));
                return new BagPage(page, pages, total, entries);
            }).consumerMainThread((m, c) -> onPage.accept(m)).add();
    }
    static void send(ServerPlayer player, Object message) { CHANNEL.send(message, PacketDistributor.PLAYER.with(player)); }
    static void request(int page, String id) { CHANNEL.send(new BagRequest(page, id), PacketDistributor.SERVER.noArg()); }
}
