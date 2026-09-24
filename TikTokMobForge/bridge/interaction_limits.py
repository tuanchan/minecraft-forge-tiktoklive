"""Identity and event limits shared by every configured mob type."""

import time
import uuid


def user_key(event) -> str:
    user = getattr(event, "user", None)
    # Numeric ID survives handle changes and missing display_id in LIVE packets.
    for field in ("id", "id_str", "user_id"):
        value = str(getattr(user, field, "") or "").strip()
        if value.isdigit() and int(value) > 0:
            return f"id:{int(value)}"
    for field in ("unique_id", "display_id"):
        value = str(getattr(user, field, "") or "").strip().lstrip("@").lower()
        if value and value != "0":
            return f"handle:{value}"
    value = str(getattr(user, "sec_uid", "") or "").strip()
    if value:
        return f"sec:{value}"
    # Nicknames are not unique. Unidentified events must never share one cooldown.
    key = f"anonymous:{uuid.uuid4().hex}"
    print(f"[TikTokIdentity] MISSING_ID user={key}; không gộp theo tên hiển thị")
    return key


class InteractionLimits:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.states: dict[tuple[str, str], tuple[int, float]] = {}
        self.likes: dict[str, int] = {}

    def allow(self, kind: str, key: str, limit: int, seconds: float) -> tuple[bool, float]:
        now = self.clock()
        state_key = (kind, key)
        count, until = self.states.get(state_key, (0, 0.0))
        if until > now:
            return False, until - now
        if until:
            count = 0
        count += 1
        self.states[state_key] = (count, now + seconds if count >= limit else 0.0)
        return True, 0.0

    def add_likes(self, key: str, count: int, threshold: int) -> int:
        batches, remainder = divmod(self.likes.get(key, 0) + count, threshold)
        self.likes[key] = remainder
        return batches
