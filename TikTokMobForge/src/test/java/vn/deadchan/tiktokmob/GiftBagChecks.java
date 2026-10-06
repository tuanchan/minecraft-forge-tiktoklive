package vn.deadchan.tiktokmob;

import com.mojang.serialization.JsonOps;
import net.minecraft.SharedConstants;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.RegistryOps;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.SimpleContainer;
import java.util.UUID;

/** Real ItemStack serialization and storage checks without a live world or TikTok. */
public final class GiftBagChecks {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        var registries = net.minecraft.data.registries.VanillaRegistries.createLookup();
        BuiltInRegistries.DATA_COMPONENT_INITIALIZERS.build(registries).forEach(pending -> pending.apply());
        PendingEnchantChecks.run(registries);
        FullArmorChecks.run(registries);
        InteractionQueueChecks.run();
        RewardMotionChecks.run();
        LightningCleanupChecks.run();
        RewardOptionChecks.run(registries);
        RuntimeSettingsChecks.run();
        BoardTextChecks.run();
        check(ServerPinnedCommentBoard.contentToken("Tuấn 😀", "Bảng 3D sắc nét").equals("18073b7521da0e5a8c561c4e16e54b62"), "WebView/Python and Java UTF-8 frame identity");
        System.out.println("WEB_BOARD_TOKEN_OK: Vietnamese and emoji match the WebView frame protocol");
        DonationLimitChecks.run();
        GolemGuardChecks.run();
        GuardBagChecks.run(registries);
        UUID owner = UUID.randomUUID(), stranger = UUID.randomUUID();
        GiftBagData bag = new GiftBagData();
        bag.deposit(owner, new ItemStack(Items.ARROW, 130));
        check(bag.count(owner) == 130, "Deposit count");
        check(bag.page(owner, 0).entries().size() == 3, "Split at max stack size");
        var entry = bag.page(owner, 0).entries().getFirst();
        SimpleContainer inventory = new SimpleContainer(36);
        bag.withdraw(stranger, entry.id(), inventory);
        check(bag.count(owner) == 130, "Other UUID cannot withdraw");
        for (int i = 0; i < 36; i++) inventory.setItem(i, new ItemStack(Items.COBBLESTONE, 64));
        bag.withdraw(owner, entry.id(), inventory);
        check(bag.count(owner) == 130, "Full inventory preserves gift");
        inventory.setItem(0, new ItemStack(Items.ARROW, 57));
        bag.withdraw(owner, entry.id(), inventory);
        check(bag.count(owner) == 123, "Partial inventory capacity");
        check(inventory.getItem(0).getCount() == 64, "Only available capacity filled");
        inventory.setItem(1, ItemStack.EMPTY);
        bag.withdraw(owner, entry.id(), inventory);
        long remaining = bag.count(owner);
        bag.withdraw(owner, entry.id(), inventory);
        check(bag.count(owner) == remaining, "Duplicate click cannot duplicate items");
        check(inventory.getItem(1).getCount() == 57, "Replayed withdrawal does not duplicate items");
        ItemStack sword = new ItemStack(Items.DIAMOND_SWORD);
        sword.setDamageValue(321);
        bag.deposit(owner, sword);
        for (int i = 0; i < 100; i++) bag.deposit(owner, new ItemStack(Items.SHIELD));
        check(bag.page(owner, 1).entries().size() == 45, "Beyond one page");
        check(bag.page(owner, Integer.MAX_VALUE).page() == 2, "Out of range page clamped");
        var ops = RegistryOps.create(JsonOps.INSTANCE, RegistryAccess.fromRegistryOfRegistries(BuiltInRegistries.REGISTRY));
        var saved = GiftBagData.TYPE.codec().encodeStart(ops, bag).getOrThrow();
        GiftBagData restored = GiftBagData.TYPE.codec().parse(ops, saved).getOrThrow();
        UUID respawnedOwner = UUID.fromString(owner.toString());
        check(restored.count(respawnedOwner) == bag.count(owner), "Saved/reloaded UUID ownership");
        var restoredSword = restored.page(owner, 0).entries().stream().filter(e -> e.stack().is(Items.DIAMOND_SWORD)).findFirst().orElseThrow();
        check(restoredSword.stack().getDamageValue() == 321, "Item components survive serialization");
        check(restored.count(stranger) == 0, "World storage isolates players");
        System.out.println("GIFT_BAG_CHECKS_OK: capacity, partial/full inventory, replay, owner isolation, pages, save/reload, components");
    }
}
