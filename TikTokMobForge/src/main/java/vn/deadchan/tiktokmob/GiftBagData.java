package vn.deadchan.tiktokmob;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import java.util.*;

/** World-owned storage: never attached to a player entity that can die. */
public final class GiftBagData extends SavedData {
    public record Entry(String id, ItemStack stack) {
        static final Codec<Entry> CODEC = RecordCodecBuilder.create(i -> i.group(
            Codec.STRING.fieldOf("id").forGetter(Entry::id),
            ItemStack.CODEC.fieldOf("stack").forGetter(Entry::stack)
        ).apply(i, Entry::new));
    }
    private static final Codec<GiftBagData> CODEC = Codec.unboundedMap(Codec.STRING, Entry.CODEC.listOf())
        .xmap(GiftBagData::new, data -> data.bags);
    public static final SavedDataType<GiftBagData> TYPE = new SavedDataType<>(
        Identifier.fromNamespaceAndPath("tiktokmob", "gift_bags"), GiftBagData::new, CODEC, null);
    private final Map<String, List<Entry>> bags = new HashMap<>();

    public GiftBagData() {}
    private GiftBagData(Map<String, List<Entry>> saved) {
        saved.forEach((key, entries) -> bags.put(key, new ArrayList<>(entries)));
    }
    public static GiftBagData get(ServerPlayer player) {
        return player.level().getServer().overworld().getDataStorage().computeIfAbsent(TYPE);
    }
    private List<Entry> entries(UUID owner) {
        return bags.computeIfAbsent(owner.toString(), key -> new ArrayList<>());
    }
    List<Entry> controlEntries(ServerPlayer player) {
        return entries(player.getUUID()).stream().filter(e -> !GuardSummons.kind(e.stack()).isEmpty()).toList();
    }
    public long count(ServerPlayer player) {
        return count(player.getUUID());
    }
    long count(UUID owner) {
        return entries(owner).stream().mapToLong(e -> e.stack().getCount()).sum();
    }
    public void deposit(ServerPlayer player, ItemStack incoming) {
        deposit(player.getUUID(), incoming);
    }
    void deposit(UUID owner, ItemStack incoming) {
        ItemStack remaining = incoming.copy();
        List<Entry> entries = entries(owner);
        for (Entry entry : entries) {
            ItemStack stored = entry.stack();
            if (ItemStack.isSameItemSameComponents(stored, remaining)) {
                int moved = Math.min(remaining.getCount(), stored.getMaxStackSize() - stored.getCount());
                stored.grow(moved);
                remaining.shrink(moved);
                if (remaining.isEmpty()) break;
            }
        }
        while (!remaining.isEmpty()) {
            entries.add(new Entry(UUID.randomUUID().toString(), remaining.split(remaining.getMaxStackSize())));
        }
        setDirty();
    }
    public void withdraw(ServerPlayer player, String id) {
        if (!player.isAlive() || player.isSpectator()) return;
        withdraw(player.getUUID(), id, player.getInventory());
        player.inventoryMenu.broadcastChanges();
        player.containerMenu.broadcastChanges();
    }
    void withdraw(UUID owner, String id, Container inventory) {
        List<Entry> entries = entries(owner);
        for (Iterator<Entry> it = entries.iterator(); it.hasNext();) {
            Entry entry = it.next();
            if (!entry.id().equals(id)) continue;
            // Explicit capacity checks also preserve overflow in Creative, where Inventory.add discards it.
            ItemStack remainder = entry.stack().copy();
            insert(inventory, remainder);
            int moved = entry.stack().getCount() - remainder.getCount();
            if (moved > 0) {
                entry.stack().shrink(moved);
                if (entry.stack().isEmpty()) it.remove();
                setDirty();
            }
            break;
        }
    }
    private static void insert(Container inventory, ItemStack remainder) {
        int slots = Math.min(36, inventory.getContainerSize());
        for (int pass = 0; pass < 2 && !remainder.isEmpty(); pass++) {
            for (int i = 0; i < slots && !remainder.isEmpty(); i++) {
                ItemStack current = inventory.getItem(i);
                if (pass == 0 && !current.isEmpty() && ItemStack.isSameItemSameComponents(current, remainder)) {
                    int amount = Math.min(remainder.getCount(), Math.max(0, current.getMaxStackSize() - current.getCount()));
                    current.grow(amount); remainder.shrink(amount);
                } else if (pass == 1 && current.isEmpty()) {
                    inventory.setItem(i, remainder.split(remainder.getMaxStackSize()));
                }
            }
        }
        inventory.setChanged();
    }
    public GiftNetwork.BagPage page(ServerPlayer player, int requestedPage) {
        return page(player.getUUID(), requestedPage);
    }
    GiftNetwork.BagPage page(UUID owner, int requestedPage) {
        List<Entry> entries = entries(owner);
        int pages = Math.max(1, (entries.size() + 44) / 45);
        int page = Math.max(0, Math.min(pages - 1, requestedPage));
        return new GiftNetwork.BagPage(page, pages, count(owner), entries.subList(page * 45,
            Math.min(entries.size(), (page + 1) * 45)).stream()
            .map(e -> new Entry(e.id(), e.stack().copy())).toList());
    }
}
