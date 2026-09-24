import asyncio
import argparse
from view_interactions import ViewInteractions
import base64
import json
import socket
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from interaction_limits import InteractionLimits, user_key
from follow_history import FollowHistory
from runtime_settings import LiveSettings

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
DISCOVERED_GIFTS_PATH = ROOT / "discovered_gifts.json"
SINGLE_INSTANCE_PORT = 39876
LIVE_RECONNECT_DELAYS_SECONDS = (5, 10, 20, 30, 60)
DEFAULT_GIFT_ACTIONS = [
    {"gift_name": "Rose", "gift_id": "", "vietnamese_name": "Hoa Hồng", "coin_value": 1, "action": "special", "target": "absorption", "amount": 1},
    {"gift_name": "TikTok", "gift_id": "", "vietnamese_name": "TikTok", "coin_value": 1, "action": "item", "target": "minecraft:iron_sword", "amount": 1},
    {"gift_name": "Heart Me", "gift_id": "", "vietnamese_name": "Thả Tim", "coin_value": 1, "action": "item", "target": "minecraft:iron_pickaxe", "amount": 1},
    {"gift_name": "GG", "gift_id": "", "vietnamese_name": "GG", "coin_value": 1, "action": "special", "target": "iron_armor", "amount": 1},
    {"gift_name": "Ice Cream Cone", "gift_id": "", "vietnamese_name": "Kem Ốc Quế", "coin_value": 1, "action": "item", "target": "minecraft:arrow", "amount": 16},
    {"gift_name": "Confetti", "gift_id": "", "vietnamese_name": "Pháo Giấy", "coin_value": 100, "action": "item", "target": "minecraft:golden_apple", "amount": 64},
    {"gift_name": "Galaxy", "gift_id": "", "vietnamese_name": "Dải Ngân Hà", "coin_value": 1000, "action": "special", "target": "netherite_armor", "amount": 1},
]
for _common_gift in json.loads((ROOT / "common_gifts.json").read_text(encoding="utf-8")):
    if not any(rule["gift_name"].casefold() == _common_gift["gift_name"].casefold() for rule in DEFAULT_GIFT_ACTIONS):
        DEFAULT_GIFT_ACTIONS.append(_common_gift)

INTERACTION_LABELS = {
    "skeleton": "+ Like",
    "zombie": "Comment",
    "enderman": "+ Share",
    "creeper": "+ Follow",
    "absorption": "Gift: Rose",
    "golden_apple": "Gift: Donut",
    "regeneration": "Gift: Perfume",
    "shield": "Gift: Cap",
    "money_gun": "Gift: Money Gun",
    "diamond_sword": "Gift: Galaxy",
    "diamond_armor": "Gift: Lion",
    "iron_armor": "Gift: Full Iron Armor",
    "netherite_armor": "Gift: Full Netherite Armor",
    "netherite_power": "Gift: Universe",
}


class OutputTee:
    """Ghi đồng thời ra cửa sổ chạy và các file log UTF-8."""

    def __init__(self, *streams) -> None:
        self._streams = streams

    def write(self, value: str) -> int:
        for stream in self._streams:
            stream.write(value)
            stream.flush()
        return len(value)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()

    def isatty(self) -> bool:
        return False


def enable_file_logging() -> list:
    log_directory = ROOT / "logs"
    log_directory.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = (log_directory / f"bridge_{timestamp}.log").open(
        "a", encoding="utf-8", buffering=1
    )
    latest = (log_directory / "bridge_latest.log").open(
        "w", encoding="utf-8", buffering=1
    )
    sys.stdout = OutputTee(sys.stdout, archive, latest)
    sys.stderr = OutputTee(sys.stderr, archive, latest)
    print(f"=== TikTok Mob Bridge | {datetime.now().isoformat(timespec='seconds')} ===")
    return [archive, latest]


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)
    if config.get("tts_provider") == "voicevox":
        config["tts_provider"] = "elevenlabs"
    return config


def load_gift_actions(config: dict) -> list[dict]:
    configured = config.get("gift_actions")
    if isinstance(configured, list):
        return [rule for rule in configured if isinstance(rule, dict)]
    return [dict(rule) for rule in DEFAULT_GIFT_ACTIONS]


def save_discovered_gifts(gifts: list[dict]) -> None:
    existing: dict[str, dict] = {}
    if DISCOVERED_GIFTS_PATH.is_file():
        try:
            loaded = json.loads(DISCOVERED_GIFTS_PATH.read_text(encoding="utf-8"))
            for gift in loaded if isinstance(loaded, list) else []:
                if isinstance(gift, dict):
                    key = str(gift.get("gift_id") or normalize_gift_name(str(gift.get("name", ""))))
                    if key:
                        existing[key] = gift
        except (OSError, ValueError):
            pass
    for gift in gifts:
        key = str(gift.get("gift_id") or normalize_gift_name(str(gift.get("name", ""))))
        if key:
            previous = existing.get(key, {})
            existing[key] = {
                **previous,
                **{field: value for field, value in gift.items() if value not in (None, "", [])},
            }
    ordered = sorted(
        existing.values(),
        key=lambda gift: (int(gift.get("diamond_count", 0) or 0), str(gift.get("name", "")).casefold()),
    )
    temporary_path = DISCOVERED_GIFTS_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(DISCOVERED_GIFTS_PATH)


def extract_image_url(value, depth: int = 0) -> str:
    if depth > 5 or value is None:
        return ""
    if isinstance(value, str):
        return value if value.startswith(("https://", "http://")) else ""
    if isinstance(value, (list, tuple)):
        for child in value:
            found = extract_image_url(child, depth + 1)
            if found:
                return found
        return ""
    keys = ("url_list", "urls", "url", "uri", "icon", "image", "picture", "thumbnail")
    if isinstance(value, dict):
        for key in keys:
            if key in value:
                found = extract_image_url(value[key], depth + 1)
                if found:
                    return found
        return ""
    for key in keys:
        found = extract_image_url(getattr(value, key, None), depth + 1)
        if found:
            return found
    return ""


def extract_gift_catalog(payload) -> list[dict]:
    found: dict[str, dict] = {}

    def walk(value) -> None:
        if isinstance(value, dict):
            name = value.get("name") or value.get("gift_name")
            gift_id = value.get("id") or value.get("gift_id")
            is_gift_record = any(
                key in value for key in ("diamond_count", "gift_type", "type")
            )
            if name and gift_id and is_gift_record:
                key = str(gift_id)
                found[key] = {
                    "gift_id": key,
                    "name": str(name),
                    "diamond_count": int(value.get("diamond_count", 0) or 0),
                    "image_url": extract_image_url(value),
                }
            for child in value.values():
                walk(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child)

    walk(payload)
    return list(found.values())


def observed_gift(event) -> dict | None:
    gift = getattr(event, "gift", None)
    if gift is None:
        return None
    gift_id = getattr(event, "gift_id", None) or getattr(gift, "id", None)
    name = str(getattr(gift, "name", "") or "").strip()
    if not name:
        return None
    return {
        "gift_id": str(gift_id or ""),
        "name": name,
        "diamond_count": int(getattr(gift, "diamond_count", 0) or 0),
        "image_url": extract_image_url(gift),
    }


def find_gift_action(
    actions: list[dict], gift_id: str, gift_name: str, diamond_count: int = 0
) -> dict | None:
    normalized_name = normalize_gift_name(gift_name)
    for action in actions:
        configured_id = str(action.get("gift_id", "")).strip()
        if configured_id and configured_id == gift_id:
            return action
    for action in actions:
        if (not str(action.get("gift_id", "")).strip() or not gift_id) and normalized_name and normalize_gift_name(str(action.get("gift_name", ""))) == normalized_name:
            return action
    return None


def unmapped_gift_action(config: dict) -> dict | None:
    if config.get("unmapped_gift_mode", "thanks") != "reward":
        return None
    action = str(config.get("unmapped_gift_action", "item"))
    target = str(config.get("unmapped_gift_target", "minecraft:bread"))
    if action not in {"item", "mob", "special"} or not target:
        return None
    return {"action": action, "target": target,
            "amount": max(1, min(100, int(config.get("unmapped_gift_amount", 1)))),
            "level": max(0 if target.startswith("enchant_") else 1,
                         min(255, int(config.get("unmapped_gift_level", 1))))}


def acquire_single_instance_socket() -> socket.socket:
    instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        instance_socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        instance_socket.listen(1)
        return instance_socket
    except OSError as error:
        instance_socket.close()
        raise RuntimeError(
            "START_TIKTOK.bat đang chạy ở cửa sổ khác. "
            "Hãy chỉ mở một cửa sổ để tránh đọc comment chồng tiếng."
        ) from error


def normalize_gift_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFD", name.casefold().strip())
    without_accents = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_accents.replace("đ", "d").split())


def send_interaction(
    config: dict,
    interaction: str,
    display_name: str,
    user_key: str = "test-user",
    notification: str | None = None,
    payload: str = "",
    donation: bool = False,
    notification_kind: str = "",
) -> None:
    if config.get("live_comments_only", False):
        return
    safe_name = (display_name or "TikTok").strip()[:64]
    safe_user_key = (user_key or safe_name).strip()[:128]
    safe_notification = (
        INTERACTION_LABELS.get(interaction, "") if notification is None else notification
    ).strip()[:96]
    encoded_user_key = base64.b64encode(safe_user_key.encode("utf-8")).decode("ascii")
    encoded_name = base64.b64encode(safe_name.encode("utf-8")).decode("ascii")
    encoded_notification = base64.b64encode(
        safe_notification.encode("utf-8")
    ).decode("ascii")
    encoded_payload = base64.b64encode(str(payload).encode("utf-8")).decode("ascii")
    priority = "donation" if donation else "normal"
    payload = (
        f"{interaction}\t{encoded_user_key}\t{encoded_name}\t{encoded_notification}"
        f"\t{encoded_payload}\t{priority}\t{notification_kind}\n"
    ).encode("utf-8")
    with socket.create_connection(
        (config["minecraft_host"], int(config["minecraft_port"])), timeout=3
    ) as connection:
        connection.sendall(payload)


def send_mob_interaction(
    config: dict,
    mob_id: str,
    display_name: str,
    user_key: str,
    notification: str,
    donation: bool = False,
    notification_kind: str = "",
) -> None:
    normalized_id = str(mob_id).strip().lower()
    if ":" not in normalized_id:
        normalized_id = f"minecraft:{normalized_id}"
    send_interaction(
        config,
        "mob",
        display_name,
        user_key,
        notification,
        normalized_id,
        donation,
        notification_kind,
    )


def dispatch_gift_action(
    config: dict,
    action: dict,
    display_name: str,
    user_key: str,
    notification: str,
    repeat_count: int = 1,
) -> str:
    action_kind = str(action.get("action", "special")).strip().lower()
    target = str(action.get("target", "")).strip().lower()
    amount = max(1, min(100, int(action.get("amount", 1) or 1)))
    for repeat_index in range(max(1, repeat_count)):
        for amount_index in range(amount):
            current_notification = (
                notification if repeat_index == 0 and amount_index == 0 else ""
            )
            if action_kind == "mob":
                send_mob_interaction(
                    config, target, display_name, user_key, current_notification, True
                )
            elif action_kind == "item":
                send_interaction(
                    config,
                    "item",
                    display_name,
                    user_key,
                    current_notification,
                    target,
                    True,
                )
            else:
                send_interaction(
                    config,
                    target,
                    display_name,
                    user_key,
                    current_notification,
                    payload=str(max(0, min(255, int(action.get("level", 0 if target.startswith("enchant_") else 1))))),
                    donation=True,
                    notification_kind="gift",
                )
    return f"{action_kind}:{target} x{amount}"


def test_mobs(config: dict) -> None:
    configured_mobs = (
        ("like_mob_type", "skeleton", "Like Tester", "+ Like"),
        ("comment_mob_type", "zombie", "Comment Tester", "Comment"),
        ("share_mob_type", "enderman", "Share Tester", "+ Share"),
        ("follow_mob_type", "creeper", "Follow Tester", "+ Follow"),
    )
    for key, default_mob, tester_name, notification in configured_mobs:
        mob_id = str(config.get(key, default_mob))
        send_mob_interaction(config, mob_id, tester_name, f"test-{key}", notification)
        print(f"TEST MOB {key} -> {mob_id}")
    print("Đã gửi thử toàn bộ mob đang chọn cho Like, Comment, Share và Follow.")


def test_mob_limit(config: dict) -> None:
    test_user_key = "test-limit-same-user"
    for number, mob in enumerate(
        ("skeleton", "zombie", "enderman", "creeper", "skeleton"), start=1
    ):
        send_interaction(config, mob, f"Limit User mob {number}", test_user_key)
    print("Đã gửi 5 mob từ cùng một user. Mob số 1 phải bị xóa, chỉ còn mob 2-5.")


def test_spam_mobs(config: dict, user_count: int) -> None:
    mobs = ("skeleton", "zombie", "enderman", "creeper")
    mobs_per_user = 10
    log_directory = ROOT / "logs"
    log_directory.mkdir(exist_ok=True)
    log_path = log_directory / datetime.now().strftime("spam_mobs_%Y%m%d_%H%M%S.log")
    log_lines = [
        f"TEST_SPAM_MOBS started_at={datetime.now().isoformat(timespec='seconds')}",
        f"users={user_count} mobs_per_user={mobs_per_user}",
    ]
    for mob_number in range(1, mobs_per_user + 1):
        mob = mobs[(mob_number - 1) % len(mobs)]
        for user_number in range(1, user_count + 1):
            user_key = f"test-spam-user-{user_number}"
            display_name = f"Spam User {user_number} mob {mob_number}"
            send_interaction(
                config,
                mob,
                display_name,
                user_key,
            )
            log_line = (
                f"SEND user={user_key} number={mob_number}/{mobs_per_user} "
                f"type={mob} name={display_name}"
            )
            log_lines.append(log_line)
            print(log_line)
    log_lines.append(
        f"EXPECTED users={user_count} active_per_user=4 total_active={4 * user_count}"
    )
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(
        f"Đã spam {mobs_per_user} mob/user cho {user_count} user "
        f"({mobs_per_user * user_count} mob)."
    )
    print(
        f"Kết quả đúng: mỗi user chỉ còn 4 mob cuối; "
        f"tổng cộng còn {4 * user_count} mob."
    )
    print(f"Log gửi test: {log_path}")
    print("Log spawn/despawn thực tế: xem [TikTokMobLimit] trong logs/latest.log của Minecraft.")


def test_timer(config: dict) -> None:
    send_interaction(config, "skeleton", "Timer Tester", "test-timer-user")
    print("Đã gửi 1 Skeleton. Name tag phải đếm từ [03:00] và mob biến mất sau 3 phút.")


def test_gifts(config: dict) -> None:
    from gift_alerts import GiftAlerts
    alerts = GiftAlerts(config)
    actions = load_gift_actions(config)
    for index, action in enumerate(actions, start=1):
        gift_name = str(action.get("vietnamese_name") or action.get("gift_name") or index)
        def deliver(action=action, gift_name=gift_name, index=index):
            description = dispatch_gift_action(config, action, f"Test {gift_name}",
                                               f"test-gift-{index}", f"Test quà: {gift_name}")
            print(f"TEST GIFT {gift_name} -> {description}")
        alerts.enqueue(f"Test {gift_name}", gift_name, 1, on_ready=deliver)
    alerts.close()
    alerts.pending.join()
    print(f"Đã gửi thử {len(actions)} ánh xạ quà tặng đang cấu hình.")


def test_rose(config: dict) -> None:
    send_interaction(config, "absorption", "Test Rose", "test-rose-user")
    print("Đã gửi 1 Hoa Hồng: người chơi phải được cộng thêm 1 tim vàng.")


def run_test(config: dict, test_name: str) -> None:
    tests = {
        "mobs": test_mobs,
        "limit": test_mob_limit,
        "timer": test_timer,
        "gifts": test_gifts,
        "rose": test_rose,
    }
    if test_name == "all":
        for test in tests.values():
            test(config)
        return
    tests[test_name](config)


def run_live(config: dict) -> None:
    from TikTokLive import TikTokLiveClient
    from live_connection import install_websocket_url_fix, run_client_with_cleanup

    install_websocket_url_fix()
    from TikTokLive.events import (
        CommentEvent,
        ConnectEvent,
        DisconnectEvent,
        FollowEvent,
        GiftEvent,
        LikeEvent,
        ShareEvent,
        RoomUserSeqEvent,
        JoinEvent,
    )

    if config.get("live_comments_only", False):
        config["gift_voicevox_enabled"] = False
        config["gift_overlay_enabled"] = False
    username = str(config["tiktok_username"]).lstrip("@")
    live_settings = LiveSettings(config)
    live_settings.refresh()
    gift_actions = load_gift_actions(config)
    limits = InteractionLimits()
    follow_history = FollowHistory(ROOT / "follow_history.sqlite3", username)
    views = ViewInteractions()
    view_task = None

    async def view_loop():
        while True:
            live_settings.refresh()
            try:
                views.tick(config, send_mob_interaction)
            except OSError as error:
                print(f"[TikTokView] Chưa gửi được mob, sẽ thử lại: {error}")
            await asyncio.sleep(1)

    client = TikTokLiveClient(unique_id=f"@{username}")
    from gift_alerts import GiftAlerts, avatar_url
    gift_alerts = GiftAlerts(config)
    try:
        from comment_tts import create_comment_speaker

        comment_speaker = create_comment_speaker(config)
    except ModuleNotFoundError as error:
        comment_speaker = None
        print(
            f"TTS comment đã tắt vì thiếu thư viện {error.name}. "
            "Hãy chạy START_TIKTOK.bat để tự cài dependencies."
        )

    def nickname(event) -> str:
        user = getattr(event, "user", None)
        return getattr(user, "nickname", None) or getattr(user, "unique_id", None) or "TikTok"

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent) -> None:
        nonlocal failed_attempts, view_task
        failed_attempts = 0
        if view_task is not None:
            view_task.cancel()
        views.reset()
        view_task = asyncio.create_task(view_loop())
        print(f"Đã kết nối TikTok LIVE @{username}; đọc bình luận đã sẵn sàng, Minecraft là tùy chọn.")
        try:
            catalog = extract_gift_catalog(await client.web.fetch_gift_list())
            save_discovered_gifts(catalog)
            print(f"Đã tải {len(catalog)} quà đang khả dụng từ phòng LIVE.")
        except Exception as error:
            print(f"Không tải được toàn bộ danh mục quà, vẫn tiếp tục nhận sự kiện: {error}")

    @client.on(DisconnectEvent)
    async def on_disconnect(event: DisconnectEvent) -> None:
        nonlocal view_task
        if view_task is not None:
            view_task.cancel()
            view_task = None
        views.reset()
        print("TikTok LIVE đã ngắt kết nối.")

    @client.on(JoinEvent)
    async def on_join(event: JoinEvent) -> None:
        views.observe_event(event)
        follow_history.observe(event, user_key(event))

    @client.on(RoomUserSeqEvent)
    async def on_viewers(event: RoomUserSeqEvent) -> None:
        views.observe(event.total)

    @client.on(FollowEvent)
    async def on_follow(event: FollowEvent) -> None:
        views.observe_event(event)
        live_settings.refresh()
        follow_mob = str(config.get("follow_mob_type", "creeper"))
        follow_spawn_count = max(1, min(100, int(config.get("follow_spawn_count", 1))))
        name = nickname(event)
        key = user_key(event)
        if not follow_history.claim(key):
            print(f"FOLLOW bỏ qua: tài khoản đã follow/nhận thưởng trước đó user={key}")
            return
        notification = "+ Follow" if config.get("display_follow_enabled", True) else ""
        for index in range(follow_spawn_count):
            send_mob_interaction(config, follow_mob, name, key, notification if index == 0 else "", notification_kind="follow")
        print(f"FOLLOW {name} user={key} -> {follow_spawn_count} x {follow_mob}")

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent) -> None:
        views.observe_event(event)
        live_settings.refresh()
        comment_mob = str(config.get("comment_mob_type", "zombie"))
        comment_spawn_count = max(1, min(100, int(config.get("comment_spawn_count", 1))))
        comment_limit = max(1, int(config.get("comment_limit", 1)))
        comment_cooldown_seconds = max(1.0, float(config.get("comment_cooldown_seconds", 10)))
        name = nickname(event)
        key = user_key(event)
        follow_history.observe(event, key)
        allowed, remaining = limits.allow("comment", key, comment_limit, comment_cooldown_seconds)
        if comment_speaker is not None and (allowed or config.get("tts_read_limited_comments", True)):
            comment_speaker.enqueue(name, event.comment)
        notification = ""
        if config.get("display_comment_enabled", True):
            notification = "Comment"
            if config.get("display_comment_text", False):
                limit = max(1, min(96, int(config.get("display_comment_max_characters", 80))))
                notification = " ".join(str(event.comment or "").split())[:limit] or "Comment"
        if not allowed:
            if notification and config.get("display_limited_comments", False):
                send_interaction(config, "notification", name, key, notification, notification_kind="comment")
            print(f"COMMENT {name} user={key} bị giới hạn riêng, chờ thêm {remaining:.1f} giây")
            return
        for index in range(comment_spawn_count):
            send_mob_interaction(config, comment_mob, name, key, notification if index == 0 else "", notification_kind="comment")
        print(f"COMMENT {name} user={key} -> {comment_spawn_count} x {comment_mob}")

    @client.on(ShareEvent)
    async def on_share(event: ShareEvent) -> None:
        views.observe_event(event)
        live_settings.refresh()
        share_mob = str(config.get("share_mob_type", "enderman"))
        share_spawn_count = max(1, min(100, int(config.get("share_spawn_count", 1))))
        share_limit = max(1, int(config.get("share_limit", 1)))
        share_cooldown_seconds = max(1.0, float(config.get("share_cooldown_seconds", 10)))
        name = nickname(event)
        key = user_key(event)
        allowed, remaining = limits.allow("share", key, share_limit, share_cooldown_seconds)
        notification = "+ Share" if config.get("display_share_enabled", True) else ""
        if not allowed:
            if notification and config.get("display_limited_shares", False):
                send_interaction(config, "notification", name, key, notification, notification_kind="share")
            print(f"SHARE {name} user={key} bị giới hạn riêng, chờ thêm {remaining:.1f} giây")
            return
        for index in range(share_spawn_count):
            send_mob_interaction(config, share_mob, name, key, notification if index == 0 else "", notification_kind="share")
        print(f"SHARE {name} user={key} -> {share_spawn_count} x {share_mob}")

    @client.on(LikeEvent)
    async def on_like(event: LikeEvent) -> None:
        views.observe_event(event)
        live_settings.refresh()
        like_mob = str(config.get("like_mob_type", "skeleton"))
        like_spawn_count = max(1, min(100, int(config.get("like_spawn_count", 1))))
        likes_needed = max(1, int(config.get("likes_per_skeleton", 50)))
        name = nickname(event)
        key = user_key(event)
        count = max(1, int(getattr(event, "count", 1) or 1))
        if config.get("display_like_enabled", True):
            send_interaction(config, "notification", name, key, "+ Like", notification_kind="like")
        skeletons = limits.add_likes(key, count, likes_needed)
        total_spawn = skeletons * like_spawn_count
        for _ in range(total_spawn):
            send_mob_interaction(config, like_mob, name, key, "", notification_kind="like")
        if skeletons:
            print(f"LIKE {name} user={key} -> {total_spawn} x {like_mob}")

    @client.on(GiftEvent)
    async def on_gift(event: GiftEvent) -> None:
        views.observe_event(event)
        gift = getattr(event, "gift", None)
        gift_name = str(getattr(gift, "name", "") or "").strip()
        gift_metadata = observed_gift(event)
        if gift_metadata is not None:
            try:
                save_discovered_gifts([gift_metadata])
            except OSError as error:
                print(f"Không lưu được quà vừa phát hiện: {error}")
        gift_id = str(getattr(event, "gift_id", None) or getattr(gift, "id", None) or "")
        diamond_count = int(getattr(gift, "diamond_count", 0) or 0)
        action = find_gift_action(gift_actions, gift_id, gift_name, diamond_count)
        if action is None:
            action = unmapped_gift_action(config)
            print(f"GIFT UNMAPPED id={gift_id} name={gift_name} mode={config.get('unmapped_gift_mode', 'thanks')}")
        if bool(getattr(event, "streaking", False)):
            return

        name = nickname(event)
        gift_count = max(1, int(getattr(event, "repeat_count", 1) or 1))
        vietnamese_name = str((action or {}).get("vietnamese_name", "")).strip() or gift_name
        gift_notification = f"Quà: {vietnamese_name}"
        if gift_count > 1:
            gift_notification += f" x{gift_count}"
        if not config.get("display_gift_enabled", True):
            gift_notification = ""
        key = user_key(event)
        def deliver_reward():
            if action is None:
                if gift_notification and config.get("display_unmapped_gifts", True):
                    send_interaction(config, "notification", name, key, gift_notification, donation=True)
                print(f"GIFT chưa gán phần thưởng: {gift_name} (ID {gift_id or '?'})")
                return
            description = dispatch_gift_action(
                config,
                action,
                name,
                key,
                gift_notification,
                gift_count,
            )
            print(
                f"GIFT {name} -> {gift_count} x {gift_name} -> "
                f"{description}"
            )
        gift_alerts.enqueue(name, vietnamese_name, gift_count,
                            avatar_url(getattr(event, "user", None)), on_ready=deliver_reward)

    event_handlers = (
        (ConnectEvent, on_connect),
        (DisconnectEvent, on_disconnect),
        (FollowEvent, on_follow),
        (RoomUserSeqEvent, on_viewers),
        (JoinEvent, on_join),
        (CommentEvent, on_comment),
        (ShareEvent, on_share),
        (LikeEvent, on_like),
        (GiftEvent, on_gift),
    )

    def replace_failed_client() -> None:
        """Use a fresh signer and cookie jar after a rejected handshake."""
        nonlocal client, view_task
        if view_task is not None:
            view_task.cancel()
            view_task = None
        views.reset()
        client = TikTokLiveClient(unique_id=f"@{username}")
        for event_type, handler in event_handlers:
            client.on(event_type)(handler)

    print(f"Đang chờ @{username} bắt đầu LIVE...")
    from websockets.exceptions import ConnectionClosed
    from websockets.legacy.exceptions import InvalidStatusCode

    failed_attempts = 0
    while True:
        try:
            run_client_with_cleanup(client)
            return
        except (ConnectionClosed, InvalidStatusCode, OSError) as error:
            delay = LIVE_RECONNECT_DELAYS_SECONDS[
                min(failed_attempts, len(LIVE_RECONNECT_DELAYS_SECONDS) - 1)
            ]
            failed_attempts += 1
            status_code = getattr(error, "status_code", None)
            reason = f"HTTP {status_code}" if status_code else str(error)
            print(
                f"Kết nối TikTok LIVE bị từ chối ({reason}). "
                f"Tự thử lại sau {delay} giây; không cần bấm Chạy LIVE lại."
            )
            replace_failed_client()
            time.sleep(delay)


def main() -> None:
    log_files = enable_file_logging()
    parser = argparse.ArgumentParser()
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--test",
        choices=("all", "mobs", "limit", "timer", "gifts", "rose"),
        nargs="?",
        const="all",
    )
    test_group.add_argument("--test-tts", action="store_true")
    test_group.add_argument("--test-gift-alert", action="store_true")
    test_group.add_argument(
        "--test-spam-users",
        type=int,
        choices=(1, 2, 3),
        metavar="SO_USER",
    )
    args = parser.parse_args()
    try:
        config = load_config()
        if args.test_gift_alert:
            from gift_alerts import GiftAlerts
            alerts = GiftAlerts(config)
            if not alerts.play({"name": "Người tặng mẫu", "gift": "Hoa Hồng", "count": 3, "avatar": ""}):
                raise SystemExit(1)
        elif args.test_tts:
            from comment_tts import create_comment_speaker

            speaker = create_comment_speaker({**config, "tts_enabled": True})
            if speaker is None or not speaker.play_test():
                raise SystemExit(1)
            print("Test TTS thành công. Nếu bạn nghe được câu mẫu thì audio đã hoạt động.")
        elif args.test_spam_users:
            test_spam_mobs(config, args.test_spam_users)
        elif args.test:
            run_test(config, args.test)
        else:
            instance_socket = acquire_single_instance_socket()
            try:
                try:
                    run_live(config)
                except Exception as error:
                    if error.__class__.__name__ == "UserOfflineError":
                        username = str(config.get("tiktok_username", "")).lstrip("@")
                        print(
                            f"Tài khoản @{username} chưa LIVE hoặc phòng LIVE chưa công khai. "
                            "Hãy bật LIVE, đợi vài giây rồi chạy lại."
                        )
                        raise SystemExit(2) from None
                    raise
            finally:
                instance_socket.close()
    finally:
        for log_file in log_files:
            log_file.flush()


if __name__ == "__main__":
    main()
