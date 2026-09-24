"""Durable follow reward deduplication, scoped to the broadcaster."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class FollowHistory:
    def __init__(self, path, broadcaster):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.broadcaster = broadcaster.strip().lstrip("@").casefold()
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS follows (channel TEXT, identity TEXT, PRIMARY KEY(channel, identity))")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def claim(self, key):
        # No stable identity: fail closed, otherwise repeated anonymous packets evade dedup.
        if key.startswith("anonymous:"):
            return False
        with self._connect() as db:
            return db.execute("INSERT OR IGNORE INTO follows VALUES (?, ?)", (self.broadcaster, key)).rowcount == 1

    def observe(self, event, key):
        user = getattr(event, "user", None)
        info = getattr(user, "follow_info", None)
        # TikTok follow_status: 1 following broadcaster, 2 mutual follows.
        if getattr(info, "follow_status", 0) in (1, 2):
            self.claim(key)
