"""Configurable offline interaction tests using the production bridge protocol."""
import math
from reward_options import reward_payload, mob_payload
import re
import threading
import time
import uuid

from bridge import send_interaction, send_mob_interaction

EVENTS = ("like", "comment", "share", "follow", "view")
LABELS = {"view": "+ View", "like": "+ Like", "comment": "Comment", "share": "+ Share", "follow": "+ Follow"}


def number(value, label, minimum, maximum, integer=True):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} phải là số") from None
    if isinstance(value, bool) or not math.isfinite(parsed) or not minimum <= parsed <= maximum or (integer and not parsed.is_integer()):
        raise ValueError(f"{label} phải từ {minimum} đến {maximum}" + (" và là số nguyên" if integer else ""))
    return int(parsed) if integer else parsed


def build_plan(config, request):
    mode = request.get("mode")
    if mode in ("pin", "pin_clear"):
        if config.get("live_comments_only", False):
            raise ValueError("Hãy tắt chế độ chỉ đọc bình luận để thử bảng trong Minecraft")
        author = " ".join(str(request.get("pin_author") or "Admin thử bảng").split())[:64]
        content = " ".join(str(request.get("pin_text") or "").split())
        if mode == "pin" and not content:
            raise ValueError("Hãy nhập nội dung bình luận ghim")
        if len(content) > 200:
            raise ValueError("Nội dung ghim tối đa 200 ký tự")
        return [("pin_comment", content if mode == "pin" else "", author, "test-pin", "", False)], 0
    if mode not in ("mob", "event", "all_mobs", "spam", "gift", "all_gifts"):
        raise ValueError("Bài kiểm thử không hợp lệ")
    users = number(request.get("users", 1), "Số người", 1, 50)
    count = number(request.get("count", 1), "Số lượt mỗi người", 1, 100)
    interval = number(request.get("interval", 0.2), "Nghỉ giữa lượt", 0, 10, False)
    name = str(request.get("name") or "Test User").strip()[:40] or "Test User"
    actions = config.get("gift_actions", [])
    if mode == "gift":
        index = number(request.get("gift_index", -1), "Quà đã chọn", 0, len(actions) - 1)
        selected_gifts = [actions[index]]
    elif mode == "all_gifts":
        selected_gifts = actions
        if not actions:
            raise ValueError("Chưa có quà được gán phần thưởng")
    else:
        selected_gifts = []
    selected_event = request.get("event", "comment")
    if mode in ("event", "spam") and selected_event not in (*EVENTS, "all"):
        raise ValueError("Loại tương tác không hợp lệ")
    target = str(request.get("mob") or "minecraft:zombie").strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", target):
        raise ValueError("Mob phải có ID dạng minecraft:zombie")
    run_id = uuid.uuid4().hex[:8]
    plan = []

    def add(kind, payload, amount, user, label, donation=False):
        amount = number(amount, "Số lượng trong cấu hình", 1, 100)
        for index in range(amount):
            plan.append((kind, payload, f"{name} {user}", f"test-{run_id}-user-{user}",
                label if index == 0 else "", donation))
        if len(plan) > 10_000:
            raise ValueError("Bài test vượt 10.000 lệnh; hãy giảm số lượt hoặc số người")

    for round_index in range(count):
        for user in range(1, users + 1):
            if selected_gifts:
                for gift in selected_gifts:
                    kind = gift.get("action", "special")
                    reward = gift.get("target", "")
                    level = number(gift.get("level", 0 if reward.startswith("enchant_") else 1), "Cấp quà", 0, 255)
                    add(reward if kind == "special" else kind, reward_payload(gift) if kind == "special" else mob_payload(gift) if kind == "mob" else reward,
                        gift.get("amount", 1), user, f"Test quà: {gift.get('vietnamese_name') or gift.get('gift_name')}", True)
            elif mode == "mob":
                add("mob", target, 1, user, "Test triệu hồi")
            else:
                events = EVENTS if mode == "all_mobs" or selected_event == "all" else (selected_event,)
                for event in events:
                    mob = str(config.get(f"{event}_mob_type", "zombie"))
                    if ":" not in mob:
                        mob = f"minecraft:{mob}"
                    add("mob", mob, config.get(f"{event}_spawn_count", 1), user, LABELS[event])
    return plan, interval


class TestRunner:
    def __init__(self, log):
        self.log = log
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.thread = None
        self.status = {"running": False, "sent": 0, "total": 0, "message": "Chưa chạy bài test"}

    def state(self):
        with self.lock:
            return dict(self.status)

    def start(self, config, request):
        plan, interval = build_plan(config, request)
        with self.lock:
            if self.status["running"]:
                raise ValueError("Một bài test đang chạy; hãy dừng hoặc chờ hoàn tất")
            self.cancel.clear()
            self.status = {"running": True, "sent": 0, "total": len(plan), "message": "Đang gửi lệnh test"}
            self.thread = threading.Thread(target=self._run, args=(dict(config), plan, interval), daemon=True)
            self.thread.start()
        return self.state()

    def stop(self):
        self.cancel.set()
        return self.state()

    def _run(self, config, plan, interval):
        self.log("TEST", f"Bắt đầu: {len(plan)} lệnh, cách nhau {interval:g}s")
        sent = 0
        alerts = None
        try:
            batches = []
            for packet in plan:
                if packet[5] and not packet[4] and batches:
                    batches[-1].append(packet)
                else:
                    batches.append([packet])
            def send_batch(batch):
                nonlocal sent
                for kind, payload, name, key, label, donation in batch:
                    if self.cancel.is_set():
                        break
                    if kind == "mob":
                        send_mob_interaction(config, payload, name, key, label, donation)
                    else:
                        send_interaction(config, kind, name, key, label, payload, donation)
                    sent += 1
                    with self.lock:
                        self.status["sent"] = sent
                    self.log("TEST", f"SEND {sent}/{len(plan)} user={key} {kind}:{payload}")
            for batch in batches:
                if self.cancel.is_set():
                    break
                kind, payload, name, key, label, donation = batch[0]
                if donation:
                    if alerts is None:
                        from gift_alerts import GiftAlerts
                        alerts = GiftAlerts(config, log=lambda text: self.log("GIFT", text))
                    alerts.enqueue(name, label.removeprefix("Test quà: "), 1,
                                   on_ready=lambda batch=batch: send_batch(batch))
                else:
                    send_batch(batch)
                if self.cancel.wait(interval):
                    break
            if alerts is not None:
                with self.lock:
                    self.status["message"] = "Đang phát quà, GIF và lời cảm ơn trong Minecraft"
                while alerts.pending.unfinished_tasks and not self.cancel.is_set():
                    time.sleep(0.1)
            message = f"Đã dừng: gửi {sent}/{len(plan)} lệnh" if self.cancel.is_set() else f"Đã gửi {sent}/{len(plan)} lệnh; xem kết quả trong Minecraft"
        except Exception as error:
            message = f"Lỗi gửi sau {sent}/{len(plan)} lệnh: {error}"
            self.log("ERROR", message)
        else:
            self.log("TEST", message)
        finally:
            if alerts is not None:
                with self.lock:
                    self.status["message"] = "Đang phát GIF và lời cảm ơn trong Minecraft"
                while alerts.pending.unfinished_tasks and not self.cancel.is_set():
                    time.sleep(0.1)
                alerts.close(discard_pending=self.cancel.is_set())
            with self.lock:
                self.status.update(running=False, message=message)
