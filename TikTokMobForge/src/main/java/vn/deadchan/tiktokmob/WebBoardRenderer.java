package vn.deadchan.tiktokmob;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.DisplayRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.state.TextDisplayEntityRenderState;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.util.FormattedCharSequence;
import org.joml.Quaternionf;

/** Two world-space faces: WebView frame/avatar with Minecraft hologram text. */
final class WebBoardRenderer extends DisplayRenderer.TextDisplayRenderer {
    private String lastCaption = "";
    private BoardCaption caption;
    WebBoardRenderer(EntityRendererProvider.Context context) { super(context); }

    @Override public void submitInner(TextDisplayEntityRenderState state, PoseStack poses,
                                      SubmitNodeCollector collector, int light, float partial) {
        String marker = state.textRenderState.text().getString();
        if (!marker.startsWith("tiktokmob:web-board:")) {
            super.submitInner(state, poses, collector, light, partial);
            return;
        }
        String[] fields = marker.split(":", 6);
        if (fields.length < 5) return;
        try {
            float width = Float.parseFloat(fields[3]), height = Float.parseFloat(fields[4]);
            if (!Float.isFinite(width) || !Float.isFinite(height) || width <= 0 || height <= 0) return;
            String encoded = fields.length == 6 ? fields[5] : "";
            if (!encoded.equals(lastCaption)) { lastCaption = encoded; caption = BoardCaption.decode(encoded); }
            if (caption != null && caption.text().startsWith("mission:")) {
                MissionHud.submit(poses, collector, width, height, caption, fields[2]);
                return;
            }
            var texture = WebBoardTexture.texture(fields[2]);
            if (texture == null) return;
            for (int side = 0; side < 2; side++) {
                poses.pushPose();
                if (side == 1) poses.mulPose(new Quaternionf().rotationY((float) Math.PI));
                // Separate front/back surfaces slightly; each side has readable, unmirrored content.
                poses.translate(0, 0, Math.max(.0002f, width * .0002f));
                surface(poses, collector, texture, width, height);
                if (caption != null) hologram(poses, collector, width, height, caption);
                poses.popPose();
            }
        } catch (NumberFormatException ignored) { }
    }

    private static void surface(PoseStack poses, SubmitNodeCollector collector, Identifier texture, float width, float height) {
        collector.submitCustomGeometry(poses, RenderTypes.text(texture), (pose, vertices) -> {
            vertices.addVertex(pose, -width / 2, 0, 0).setColor(-1).setUv(0, 1).setLight(0xF000F0);
            vertices.addVertex(pose, width / 2, 0, 0).setColor(-1).setUv(1, 1).setLight(0xF000F0);
            vertices.addVertex(pose, width / 2, height, 0).setColor(-1).setUv(1, 0).setLight(0xF000F0);
            vertices.addVertex(pose, -width / 2, height, 0).setColor(-1).setUv(0, 0).setLight(0xF000F0);
        });
    }

    private static void hologram(PoseStack poses, SubmitNodeCollector collector, float width, float height, BoardCaption data) {
        Font font = Minecraft.getInstance().font;
        float pixel = (float) (.018 * data.scale());
        Component title = rainbowTitle();
        float titlePixel = Math.min(pixel * 1.15f, width * .76f / Math.max(1, font.width(title)));
        draw(poses, collector, title.getVisualOrderText(), 0, height - height * .08f, titlePixel, -1);
        float avatarSize = Math.min((float)(.6048 * data.boardScale() * data.avatarScale()), Math.min(width * .26f, height * .40f));
        float avatarX = bound((float)data.avatarX() / 100, .04f + avatarSize / width / 2, .30f - avatarSize / width / 2);
        float avatarY = bound((float)data.avatarY() / 100, .28f + avatarSize / height / 2, .76f - avatarSize / height / 2);
        float nameY = bound((float)data.authorY() / 100, avatarY + avatarSize / height / 2 + .075f, .89f);
        float nameWidth = 2 * Math.min(avatarX - .025f, .315f - avatarX) * width;
        float bodyX = bound((float)data.x() / 100, .65f, .68f);
        float bodyY = bound((float)data.y() / 100, .38f, .80f);
        float bodyWidth = width * .56f;
        float bodyHeight = 2 * Math.min(bodyY - .26f, .94f - bodyY) * height;
        int wrapWidth = Math.max(1, (int)(bodyWidth / pixel));
        var lines = font.split(Component.literal(data.text()), wrapWidth);
        int widest = lines.stream().mapToInt(font::width).max().orElse(1);
        float bodyPixel = Math.min(pixel, Math.min(bodyWidth / Math.max(1, widest), bodyHeight / Math.max(11, lines.size() * 11)));
        float x = width * (bodyX - .5f);
        float top = height * (1 - bodyY) + lines.size() * 11 * bodyPixel / 2;
        int nameColor = 0xff000000 | Integer.parseInt(data.authorColor().substring(1), 16);
        int commentColor = 0xff000000 | Integer.parseInt(data.commentColor().substring(1), 16);
        var author = Component.literal("@" + data.author()).withStyle(style -> style.withBold(true));
        float namePixel = Math.min(pixel, Math.min(nameWidth / Math.max(1, font.width(author)), height * .10f / 9));
        draw(poses, collector, author.getVisualOrderText(), width * (avatarX - .5f),
            height * (1 - nameY) + namePixel * 4.5f, namePixel, nameColor);
        for (var line : lines) {
            draw(poses, collector, line, x, top, bodyPixel, commentColor);
            top -= bodyPixel * 11;
        }
    }

    private static float bound(float value, float low, float high) {
        return Math.max(low, Math.min(high, value));
    }

    private static Component rainbowTitle() {
        String text = "BÌNH LUẬN GHIM";
        int[] colors = {0xff4268, 0xffa442, 0xffe85a, 0x58ef79, 0x39dbf7, 0x8586ff, 0xec62ff};
        var result = Component.empty();
        long time = Minecraft.getInstance().level == null ? 0 : Minecraft.getInstance().level.getGameTime();
        for (int i = 0; i < text.length(); i++) {
            int color = colors[(i + (int)(time / 8 % colors.length)) % colors.length];
            result.append(Component.literal(text.substring(i, i + 1)).withStyle(style -> style.withColor(color).withBold(true)));
        }
        return result;
    }

    static void draw(PoseStack poses, SubmitNodeCollector collector, FormattedCharSequence text,
                             float centerX, float topY, float pixel, int color) {
        poses.pushPose();
        poses.translate(centerX, topY, .001f);
        poses.scale(pixel, -pixel, pixel);
        collector.submitText(poses, -Minecraft.getInstance().font.width(text) / 2f, 0, text, true,
            Font.DisplayMode.POLYGON_OFFSET, 0xF000F0, color, 0, 0);
        poses.popPose();
    }
}
