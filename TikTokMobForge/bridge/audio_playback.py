"""Serialize comment and gift audio so neither cuts off an active sentence."""
import threading

PLAYBACK_LOCK = threading.Lock()
