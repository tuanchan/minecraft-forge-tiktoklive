package vn.deadchan.tiktokmob;

import net.minecraft.core.registries.Registries;
import net.minecraft.core.HolderLookup;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.EnchantmentTags;
import net.minecraft.tags.ItemTags;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.world.item.enchantment.Enchantments;
import java.util.List;
import java.util.Set;

final class SpecialRewards {
    static List<ItemStack> enchantedArmorSet(HolderLookup.Provider registries, boolean netherite) {
        var items = netherite
            ? List.of(net.minecraft.world.item.Items.NETHERITE_HELMET, net.minecraft.world.item.Items.NETHERITE_CHESTPLATE,
                net.minecraft.world.item.Items.NETHERITE_LEGGINGS, net.minecraft.world.item.Items.NETHERITE_BOOTS)
            : List.of(net.minecraft.world.item.Items.DIAMOND_HELMET, net.minecraft.world.item.Items.DIAMOND_CHESTPLATE,
                net.minecraft.world.item.Items.DIAMOND_LEGGINGS, net.minecraft.world.item.Items.DIAMOND_BOOTS);
        return items.stream().map(item -> {
            ItemStack stack = new ItemStack(item);
            var keys = new java.util.ArrayList<>(List.of(Enchantments.PROTECTION, Enchantments.FIRE_PROTECTION,
                Enchantments.BLAST_PROTECTION, Enchantments.PROJECTILE_PROTECTION,
                Enchantments.THORNS, Enchantments.UNBREAKING, Enchantments.MENDING));
            if (item == items.get(0)) keys.addAll(List.of(Enchantments.RESPIRATION, Enchantments.AQUA_AFFINITY));
            if (item == items.get(2)) keys.add(Enchantments.SWIFT_SNEAK);
            if (item == items.get(3)) keys.addAll(List.of(Enchantments.FEATHER_FALLING, Enchantments.DEPTH_STRIDER,
                Enchantments.FROST_WALKER, Enchantments.SOUL_SPEED));
            // Fixed FULL IV kits include incompatible vanilla armor enchantments and Mending IV.
            var enchantments = registries.lookupOrThrow(Registries.ENCHANTMENT);
            EnchantmentHelper.updateEnchantments(stack, mutable ->
                keys.forEach(key -> mutable.upgrade(enchantments.getOrThrow(key), 4)));
            return stack;
        }).toList();
    }
    static void keepInventory(ServerPlayer player, boolean enabled) {
        player.level().getGameRules().set(net.minecraft.world.level.gamerules.GameRules.KEEP_INVENTORY,
            enabled, player.level().getServer());
        player.sendSystemMessage(Component.literal("Quà donate: " + (enabled ? "Bật" : "Tắt")
            + " giữ đồ và kinh nghiệm khi chết cho thế giới."));
    }

    static void setRespawn(ServerPlayer player) {
        var data = net.minecraft.world.level.storage.LevelData.RespawnData.of(
            player.level().dimension(), player.blockPosition(), player.getYRot(), player.getXRot());
        player.setRespawnPosition(new ServerPlayer.RespawnConfig(data, true), true);
    }

    private record ChasingTnt(net.minecraft.world.entity.item.PrimedTnt tnt, ServerPlayer target) {}
    private static final java.util.List<ChasingTnt> CHASING_TNT = new java.util.ArrayList<>();

    static net.minecraft.world.phys.Vec3 chaseVelocity(net.minecraft.world.phys.Vec3 delta,
            net.minecraft.world.phys.Vec3 current, boolean grounded) {
        double distance = Math.sqrt(delta.x * delta.x + delta.z * delta.z);
        double speed = Math.min(0.32, distance * 0.18);
        double x = distance > 0.001 ? delta.x / distance * speed : 0;
        double z = distance > 0.001 ? delta.z / distance * speed : 0;
        // Smooth turns and keep gravity; hop up steps instead of teleporting onto the target.
        double y = grounded && distance > 0.8 ? 0.3 : current.y;
        return new net.minecraft.world.phys.Vec3(current.x * 0.55 + x * 0.45, y,
            current.z * 0.55 + z * 0.45);
    }

    static void tickTnt(net.minecraft.server.MinecraftServer server) {
        CHASING_TNT.removeIf(chase -> {
            var tnt = chase.tnt();
            var target = chase.target();
            if (tnt.level().getServer() != server) return false;
            if (tnt.isRemoved() || !target.isAlive() || target.isRemoved() || target.isSpectator()
                    || target.level() != tnt.level()
                    || server.getPlayerList().getPlayer(target.getUUID()) != target) return true;
            tnt.setDeltaMovement(chaseVelocity(target.position().subtract(tnt.position()),
                tnt.getDeltaMovement(), tnt.onGround()));
            return false;
        });
    }

    static void clearTnt(net.minecraft.server.MinecraftServer server) {
        CHASING_TNT.removeIf(chase -> chase.tnt().level().getServer() == server);
    }

    static void spawnTnt(ServerPlayer player) {
        var tnt = new net.minecraft.world.entity.item.PrimedTnt(player.level(),
            player.getX(), player.getY(), player.getZ(), player);
        tnt.setFuse(80);
        if (player.level().addFreshEntity(tnt)) CHASING_TNT.add(new ChasingTnt(tnt, player));
    }

    static void clearInventory(ServerPlayer player) {
        // Clear carried stacks before closing so the menu cannot return them to inventory.
        player.containerMenu.setCarried(ItemStack.EMPTY);
        player.inventoryMenu.setCarried(ItemStack.EMPTY);
        // Make room for personal crafting inputs returned when the menu closes.
        player.getInventory().clearContent();
        player.closeContainer();
        player.getInventory().clearContent();
        for (EquipmentSlot slot : ARMOR) player.setItemSlot(slot, ItemStack.EMPTY);
        player.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
        player.setItemSlot(EquipmentSlot.OFFHAND, ItemStack.EMPTY);
        player.getInventory().setChanged();
        player.inventoryMenu.broadcastChanges();
        player.containerMenu.broadcastChanges();
        player.sendSystemMessage(Component.literal("Quà donate: Đã clear sạch túi đồ, giáp và hai tay!"));
        System.out.println("[TikTokMobReward] CLEAR_INVENTORY player=" + player.getUUID());
    }

    static int nextEnchantLevel(int current, int requested) {
        return Math.min(255, Math.max(requested, current + 1));
    }
    static final List<EquipmentSlot> ARMOR = List.of(EquipmentSlot.HEAD, EquipmentSlot.CHEST,
        EquipmentSlot.LEGS, EquipmentSlot.FEET);

    static void enchant(ServerPlayer player, boolean armor, String payload) {
        int requested;
        try { requested = Math.max(0, Math.min(255, Integer.parseInt(payload))); }
        catch (NumberFormatException ignored) { requested = 0; }
        PendingEnchantData data = PendingEnchantData.get(player);
        data.add(player.getUUID(), armor, requested);
        if (applyPending(player) == 0) {
            player.sendSystemMessage(Component.literal("Đã giữ quà enchant · " + waitingMessage(data.waitingSlots(player.getUUID()))));
        }
    }

    static int applyPending(ServerPlayer player) {
        if (!player.isAlive() || player.isSpectator()) return 0;
        PendingEnchantData data = PendingEnchantData.get(player);
        Set<EquipmentSlot> applied = data.applyReady(player.getUUID(), (slot, level) ->
            enchantStack(player.registryAccess(), player.getItemBySlot(slot), slot != EquipmentSlot.MAINHAND, level));
        if (applied.isEmpty()) return 0;
        player.inventoryMenu.broadcastChanges();
        player.containerMenu.broadcastChanges();
        Set<EquipmentSlot> waiting = data.waitingSlots(player.getUUID());
        player.sendSystemMessage(Component.literal("Đã enchant đầy đủ " + applied.size() + " món"
            + (waiting.isEmpty() ? " · Đã nhận hết quà enchant." : " · " + waitingMessage(waiting))));
        return applied.size();
    }

    private static String waitingMessage(Set<EquipmentSlot> waiting) {
        long armor = ARMOR.stream().filter(waiting::contains).count();
        return (armor > 0 ? "Còn chờ " + armor + " ô giáp" : "")
            + (waiting.contains(EquipmentSlot.MAINHAND) ? (armor > 0 ? " và " : "Chờ ") + "vũ khí tay chính" : "");
    }

    static boolean enchantStack(HolderLookup.Provider registries, ItemStack stack, boolean armor, int selected) {
        if (stack.isEmpty()) return false;
        if (armor && !stack.is(ItemTags.ARMOR_ENCHANTABLE)) return false;
        if (!armor && !stack.is(ItemTags.WEAPON_ENCHANTABLE)
            && !stack.is(ItemTags.BOW_ENCHANTABLE) && !stack.is(ItemTags.CROSSBOW_ENCHANTABLE)
            && !stack.is(ItemTags.TRIDENT_ENCHANTABLE)) return false;
        int[] applied = {0};
        EnchantmentHelper.updateEnchantments(stack, mutable ->
            registries.lookupOrThrow(Registries.ENCHANTMENT).listElements().forEach(holder -> {
                // FULL includes mutually exclusive enchantments supported by the item, except curses.
                if (!holder.is(EnchantmentTags.CURSE) && holder.value().isSupportedItem(stack)) {
                    int level = selected == 0 ? holder.value().getMaxLevel() : selected;
                    // Each gift reaches its requested floor or adds one level to an existing stronger enchant.
                    mutable.upgrade(holder, nextEnchantLevel(mutable.getLevel(holder), level));
                    applied[0]++;
                }
            }));
        return applied[0] > 0;
    }

    static void repair(ServerPlayer player, boolean armor) {
        List<ItemStack> stacks = armor ? ARMOR.stream().map(player::getItemBySlot).toList()
            : List.of(player.getMainHandItem());
        stacks.stream().filter(ItemStack::isDamageableItem).forEach(stack -> stack.setDamageValue(0));
        player.inventoryMenu.broadcastChanges();
    }
}
