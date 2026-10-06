package vn.deadchan.tiktokmob;

import com.google.gson.Gson;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/** Native hologram content travels with the server-owned world display. */
record BoardCaption(String author, String text, String authorColor, String commentColor,
                    double scale, double x, double y, double authorX, double authorY,
                    double avatarX, double avatarY, double avatarScale, double boardScale) {
    private static final Gson GSON = new Gson();
    static String encode(BoardCaption caption) {
        return Base64.getEncoder().encodeToString(GSON.toJson(caption).getBytes(StandardCharsets.UTF_8));
    }
    static BoardCaption decode(String encoded) {
        if (encoded.length() > 8192) return null;
        try {
            var value = GSON.fromJson(new String(Base64.getDecoder().decode(encoded), StandardCharsets.UTF_8), BoardCaption.class);
            if (value == null || value.author == null || value.text == null || value.authorColor == null
                || value.commentColor == null || !value.authorColor.matches("#[a-fA-F0-9]{6}")
                || !value.commentColor.matches("#[a-fA-F0-9]{6}") || !Double.isFinite(value.scale)
                || value.scale <= 0 || !Double.isFinite(value.x) || !Double.isFinite(value.y)
                || !Double.isFinite(value.authorX) || !Double.isFinite(value.authorY)
                || !Double.isFinite(value.avatarX) || !Double.isFinite(value.avatarY)
                || !Double.isFinite(value.avatarScale) || value.avatarScale <= 0
                || !Double.isFinite(value.boardScale) || value.boardScale <= 0
                || value.authorX < 0 || value.authorX > 100 || value.authorY < 0 || value.authorY > 100
                || value.x < 0 || value.x > 100 || value.y < 0 || value.y > 100) return null;
            return value;
        } catch (RuntimeException invalid) { return null; }
    }
}
