package vn.deadchan.tiktokmob;

import net.minecraft.core.HolderLookup;
import net.minecraft.resources.RegistryOps;
import net.minecraft.nbt.NbtOps;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;

final class RewardOptionChecks {
    static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    static void run(HolderLookup.Provider registries) {
        check(RewardOptions.ticks("1", "fuse_seconds", 4) == 80, "Old rules keep default fuse");
        check(RewardOptions.ticks("{\"fuse_seconds\":1.25}", "fuse_seconds", 4) == 25, "Fractional fuse in ticks");
        check(RewardOptions.ticks("{\"duration_seconds\":-1}", "duration_seconds", 5) == 2, "Bound unsafe negative timer");
        check(RewardOptions.number("{\"radius\":999}", "radius", 0, 0, 16) == 16, "Bound web workload");
        check(RewardOptions.number("broken", "height", 96, 1, 2048) == 96, "Malformed payload defaults");
        check(RewardOptions.blockOverride("1") == null, "Legacy gifts inherit global explosion settings");
        check(RewardOptions.booleanOption("{}", "damage_players") == null, "Old TNT keeps damage enabled");
        check(Boolean.FALSE.equals(RewardOptions.booleanOption("{\"damage_players\":false}", "damage_players")), "TNT disables player damage");
        check(Boolean.TRUE.equals(RewardOptions.booleanOption("{\"damage_players\":true}", "damage_players")), "TNT enables player damage");
        check(RewardOptions.booleanOption("{\"damage_players\":\"false\"}", "damage_players") == null, "Invalid damage flag rejected");
        check(Boolean.TRUE.equals(RewardOptions.blockOverride("{\"break_blocks\":true}")), "Gift enables terrain damage");
        check(Boolean.FALSE.equals(RewardOptions.blockOverride("{\"break_blocks\":false}")), "Gift disables terrain damage");
        check(RewardOptions.blockOverride("{\"break_blocks\":\"false\"}") == null, "Reject string boolean override");
        check(RewardOptions.mobId("{\"mob\":\"minecraft:creeper\",\"break_blocks\":true}").equals("minecraft:creeper"), "Creeper ID survives options payload");
        check(RewardOptions.ticks("{\"fuse_seconds\":0}", "fuse_seconds", 4) == 0, "Zero fuse means immediate explosion");
        double height = 64;
        for (int i = 0; i < 10; i++) height = SkyLaunch.stackHeight(height, 20);
        check(height == 264, "Ten simultaneous gifts add all ten heights");
        var data = new TemporaryPumpkins();
        ItemStack helmet = SpecialRewards.enchantedArmorSet(registries, true).getFirst();
        helmet.setDamageValue(117);
        helmet.set(DataComponents.CUSTOM_NAME, Component.literal("Original helmet"));
        data.hats.put("owner", new TemporaryPumpkins.Hat(helmet, 12345, "token"));
        data.hats.put("no-helmet", new TemporaryPumpkins.Hat(ItemStack.EMPTY, 30, "other"));
        var ops = registries.createSerializationContext(NbtOps.INSTANCE);
        var encoded = TemporaryPumpkins.TYPE.codec().encodeStart(ops, data).getOrThrow();
        var decoded = TemporaryPumpkins.TYPE.codec().parse(ops, encoded).getOrThrow();
        check(ItemStack.isSameItemSameComponents(helmet, decoded.hats.get("owner").helmet()), "Helmet damage/name/enchant survive save/reload");
        check(decoded.hats.get("owner").expires() == 12345, "Expiration survives reload");
        check(decoded.hats.get("no-helmet").helmet().isEmpty(), "Empty head survives reload");
        check(TemporaryPumpkins.token(new ItemStack(Items.CARVED_PUMPKIN)).isEmpty(), "Normal pumpkins unmarked");
        System.out.println("REWARD_OPTIONS_OK: payloads, bounds, stacked height, helmet escrow save/reload");
    }
}
