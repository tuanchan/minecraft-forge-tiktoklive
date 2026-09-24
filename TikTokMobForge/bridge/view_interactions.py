"""Named viewer rewards from identity-bearing LIVE events.

Presence is a lease, not an authoritative viewer list: TikTok does not expose
reliable per-viewer departures. Room counts never refresh individual leases.
"""
import time
from dataclasses import dataclass
from interaction_limits import user_key


@dataclass
class Viewer:
    name: str
    seen: float
    rewarded: float | None = None
    remaining: int = 0


class ViewInteractions:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.reset()

    def reset(self):
        self.viewers = {}
        self.signal = None
        self.round_started = None
        self.round_sent = 0

    def observe(self, count):
        self.signal = self.clock()
        if int(count) <= 0:
            self.viewers.clear()

    def observe_event(self, event):
        key = user_key(event)
        user = getattr(event, "user", None)
        name = next((str(getattr(user, field, "") or "").strip()
                     for field in ("nickname", "unique_id", "display_id")
                     if str(getattr(user, field, "") or "").strip()), "")
        if key.startswith("anonymous:") or not name:
            return False
        now = self.clock()
        self.signal = now
        if key in self.viewers:
            self.viewers[key].name = name
            self.viewers[key].seen = now
        else:
            if len(self.viewers) >= 10000:
                oldest = min(self.viewers, key=lambda item: self.viewers[item].seen)
                del self.viewers[oldest]
            self.viewers[key] = Viewer(name, now)
        return True

    def tick(self, config, send):
        now = self.clock()
        interval = max(1, float(config.get("view_interval_seconds", 60)))
        # Permit at least one repeat even for intervals longer than five minutes.
        lease = max(300, interval + 90)
        self.viewers = {key: viewer for key, viewer in self.viewers.items()
                        if now - viewer.seen <= lease}
        if not config.get("view_enabled", True):
            for viewer in self.viewers.values():
                viewer.remaining = 0
            self.round_started = None
            self.round_sent = 0
            return
        if self.signal is None or now - self.signal > 90:
            return
        cap = max(1, min(1000, int(config.get("view_max_mobs_per_round", 20))))
        if self.round_started is None or now - self.round_started >= interval:
            self.round_started, self.round_sent = now, 0
        budget = min(5, max(0, cap - self.round_sent))
        per_view = max(1, min(100, int(config.get("view_spawn_count", 1))))
        # Oldest reward first avoids starving later arrivals under the room cap.
        ordered = sorted(self.viewers.items(), key=lambda item:
                         float("-inf") if item[1].rewarded is None else item[1].rewarded)
        for key, viewer in ordered:
            if budget <= 0:
                break
            if not viewer.remaining:
                if viewer.rewarded is not None and now - viewer.rewarded < interval:
                    continue
                viewer.remaining = per_view
            viewer.remaining = min(viewer.remaining, per_view)
            while viewer.remaining and budget:
                send(config, str(config.get("view_mob_type", "zombie")),
                     viewer.name, key, "+ View" if config.get("display_view_enabled", True) else "", notification_kind="view")
                viewer.remaining -= 1
                self.round_sent += 1
                budget -= 1
                if not viewer.remaining:
                    viewer.rewarded = now
