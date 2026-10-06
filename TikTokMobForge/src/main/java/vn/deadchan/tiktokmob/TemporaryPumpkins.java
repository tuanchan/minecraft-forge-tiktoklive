package vn.deadchan.tiktokmob;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.*;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;

/** The original helmet is escrowed in world saved data until the temporary hat ends. */
final class TemporaryPumpkins extends SavedData {
    record Hat(ItemStack helmet, long expires, String token) {
        static final Codec<Hat> CODEC = RecordCodecBuilder.create(i -> i.group(
            ItemStack.OPTIONAL_CODEC.fieldOf("helmet").forGetter(Hat::helmet),
            Codec.LONG.fieldOf("expires").forGetter(Hat::expires),
            Codec.STRING.fieldOf("token").forGetter(Hat::token)
        ).apply(i, Hat::new));
    }
    private static final String KEY = "tiktokmob_temporary_pumpkin";
    final Map<String, Hat> hats = new HashMap<>();
    private static final Set<MinecraftServer> SERVERS = new HashSet<>();
    private static final Codec<TemporaryPumpkins> CODEC = Codec.unboundedMap(Codec.STRING, Hat.CODEC)
        .xmap(TemporaryPumpkins::new, data -> data.hats);
    static final SavedDataType<TemporaryPumpkins> TYPE = new SavedDataType<>(
        Identifier.fromNamespaceAndPath("tiktokmob", "temporary_pumpkins"), TemporaryPumpkins::new, CODEC, null);
    TemporaryPumpkins() {}
    private TemporaryPumpkins(Map<String, Hat> saved) { hats.putAll(saved); }
    private static TemporaryPumpkins get(ServerPlayer player) {
        var server = player.level().getServer();
        SERVERS.add(server);
        return server.overworld().getDataStorage().computeIfAbsent(TYPE);
    }
    static void register() {
        net.minecraftforge.event.entity.EntityJoinLevelEvent.BUS.addListener(event ->
            event.getEntity() instanceof net.minecraft.world.entity.item.ItemEntity item
                && !token(item.getItem()).isEmpty());
        PlayerEvent.PlayerLoggedInEvent.BUS.addListener(event -> {
            if (event.getEntity() instanceof ServerPlayer player) get(player);
        });
        PlayerEvent.PlayerLoggedOutEvent.BUS.addListener(event -> {
            if (event.getEntity() instanceof ServerPlayer player) restore(player);
        });
        LivingDeathEvent.BUS.addListener(event -> {
            if (event.getEntity() instanceof ServerPlayer player) restore(player);
            return false;
        });
        ServerStoppingEvent.BUS.addListener(event -> {
            for (var player : event.getServer().getPlayerList().getPlayers()) restore(player);
            SERVERS.remove(event.getServer());
        });
    }
    static String token(ItemStack stack) {
        return stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY).copyTag().getStringOr(KEY, "");
    }
    static void start(ServerPlayer player, int duration) {
        var data = get(player);
        String owner = player.getUUID().toString();
        Hat previous = data.hats.get(owner);
        long expires = player.level().getServer().overworld().getGameTime() + duration;
        if (previous != null && previous.token().equals(token(player.getItemBySlot(EquipmentSlot.HEAD)))) {
            data.hats.put(owner, new Hat(previous.helmet(), expires, previous.token()));
            data.setDirty(); return;
        }
        if (previous != null) restore(player);
        String id = UUID.randomUUID().toString();
        data.hats.put(owner, new Hat(player.getItemBySlot(EquipmentSlot.HEAD).copy(), expires, id));
        data.setDirty();
        ItemStack pumpkin = new ItemStack(Items.CARVED_PUMPKIN);
        CompoundTag tag = new CompoundTag(); tag.putString(KEY, id);
        pumpkin.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
        player.setItemSlot(EquipmentSlot.HEAD, pumpkin);
        player.inventoryMenu.broadcastChanges();
    }
    static void forget(ServerPlayer player) {
        var data = get(player);
        if (data.hats.remove(player.getUUID().toString()) != null) data.setDirty();
    }
    static void restore(ServerPlayer player) {
        var data = get(player);
        Hat hat = data.hats.remove(player.getUUID().toString());
        if (hat == null) return;
        // Remove only our temporary hat, never a regular pumpkin or a replacement helmet.
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            if (hat.token().equals(token(player.getInventory().getItem(i))))
                player.getInventory().setItem(i, ItemStack.EMPTY);
        }
        if (hat.token().equals(token(player.containerMenu.getCarried()))) player.containerMenu.setCarried(ItemStack.EMPTY);
        if (hat.token().equals(token(player.getItemBySlot(EquipmentSlot.HEAD)))) player.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
        if (player.getItemBySlot(EquipmentSlot.HEAD).isEmpty()) player.setItemSlot(EquipmentSlot.HEAD, hat.helmet());
        else if (!hat.helmet().isEmpty()) GiftBagData.get(player).deposit(player, hat.helmet());
        data.setDirty();
        player.inventoryMenu.broadcastChanges();
        player.containerMenu.broadcastChanges();
    }
    static void tick() {
        for (var server : List.copyOf(SERVERS)) {
            var data = server.overworld().getDataStorage().computeIfAbsent(TYPE);
            for (var player : server.getPlayerList().getPlayers()) {
                Hat hat = data.hats.get(player.getUUID().toString());
                if (hat != null && (server.overworld().getGameTime() >= hat.expires()
                    || !hat.token().equals(token(player.getItemBySlot(EquipmentSlot.HEAD))))) restore(player);
            }
        }
    }
}
