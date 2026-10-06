package vn.deadchan.tiktokmob;

import java.util.ArrayList;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.Mob;

/** Kills only loaded tool summons in all dimensions; no radius or natural-mob sweep. */
final class ClearToolMobs {
    static boolean eligible(EntityType<?> type, boolean summoned) {
        return summoned && type != EntityTypes.PLAYER && type != EntityTypes.IRON_GOLEM
            && type != EntityTypes.SNOW_GOLEM && type != EntityTypes.WOLF;
    }

    static Component killMessage(String killer, Component mobName, Component species) {
        return Component.literal("[TikTok] ").withStyle(ChatFormatting.GOLD)
            .append(Component.literal(killer).withStyle(ChatFormatting.YELLOW))
            .append(Component.literal(" đã giết ").withStyle(ChatFormatting.WHITE))
            .append(mobName.copy().withStyle(ChatFormatting.RED))
            .append(Component.literal(" (").withStyle(ChatFormatting.GRAY))
            .append(species.copy().withStyle(ChatFormatting.GRAY))
            .append(Component.literal(")").withStyle(ChatFormatting.GRAY));
    }

    static int kill(MinecraftServer server, String killer) {
        int count = 0;
        for (var level : server.getAllLevels()) {
            var victims = new ArrayList<Mob>();
            for (var entity : level.getAllEntities()) {
                if (entity instanceof Mob mob && mob.isAlive()
                    && eligible(mob.getType(), mob.entityTags().contains("tiktokmob:summoned")
                        || mob.entityTags().contains("tiktokmob:donation"))) victims.add(mob);
            }
            // Collect first: death callbacks may mutate the world's entity collections.
            for (Mob mob : victims) {
                Component name = mob.getDisplayName().copy();
                mob.kill(level);
                if (!mob.isAlive()) {
                    count++;
                    server.getPlayerList().broadcastSystemMessage(killMessage(killer, name, mob.getType().getDescription()), false);
                }
            }
        }
        if (count == 0) server.getPlayerList().broadcastSystemMessage(
            Component.literal("[TikTok] " + killer + " dùng Dọn quái tool: không có mob phù hợp.")
                .withStyle(ChatFormatting.GRAY), false);
        return count;
    }
}
