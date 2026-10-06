package vn.deadchan.tiktokmob;

import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** Intersect the actual two-sided board rectangle, not TextDisplay's empty collision box. */
final class BoardRaycast {
    static double distance(Vec3 eye, Vec3 direction, Vec3 bottomCenter, float yaw, float pitch,
                           double width, double height) {
        if (!Double.isFinite(width) || !Double.isFinite(height) || width <= 0 || height <= 0) return -1;
        Quaternionf inverse = new Quaternionf().rotationYXZ((float)Math.toRadians(-yaw),
            (float)Math.toRadians(pitch), 0).conjugate();
        Vec3 offset = eye.subtract(bottomCenter);
        Vector3f localEye = inverse.transform(new Vector3f((float)offset.x, (float)offset.y, (float)offset.z));
        Vector3f localRay = inverse.transform(new Vector3f((float)direction.x, (float)direction.y, (float)direction.z));
        if (Math.abs(localRay.z) < 1e-6) return -1;
        double t = -localEye.z / localRay.z;
        double x = localEye.x + t * localRay.x, y = localEye.y + t * localRay.y;
        return t >= 0 && Math.abs(x) <= width / 2 && y >= 0 && y <= height ? t : -1;
    }
}
