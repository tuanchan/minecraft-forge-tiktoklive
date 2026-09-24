from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from config_service import (
    BRIDGE_CONFIG_PATH,
    BRIDGE_DIR,
    DEFAULT_BRIDGE_CONFIG,
    DEFAULT_GIFT_ACTIONS,
    DEFAULT_MOD_CONFIG,
    DISCOVERED_GIFTS_PATH,
    GUI_DIR,
    GUI_STATE_PATH,
    PROJECT_DIR,
    load_api_key,
    load_gui_state,
    load_json,
    load_json_list,
    mod_config_path,
    save_api_key,
    save_json,
    set_pause_on_lost_focus,
)
from catalog_service import CatalogEntry, SPECIAL_REWARDS, load_minecraft_catalog


RUN_BRIDGE = BRIDGE_DIR / "RUN_BRIDGE.bat"


class TikTokMobGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TikTok Mob Forge - Bảng điều khiển")
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.bridge_vars = {
            key: self._make_var(value) for key, value in DEFAULT_BRIDGE_CONFIG.items()
        }
        self.mod_vars = {
            key: self._make_var(value) for key, value in DEFAULT_MOD_CONFIG.items() if not isinstance(value, dict)
        }
        self.minecraft_directory = tk.StringVar()
        initial_state = load_gui_state()
        self.minecraft_directory.set(str(initial_state.get("minecraft_directory") or ""))
        self.keep_minecraft_running = tk.BooleanVar(
            value=bool(initial_state.get("keep_minecraft_running_in_background", True))
        )
        self.api_key = tk.StringVar()
        self.mob_catalog, self.item_catalog = load_minecraft_catalog(self.minecraft_directory.get())
        self.reward_catalog: list[CatalogEntry] = [*SPECIAL_REWARDS, *self.item_catalog, *self.mob_catalog]
        self.gift_actions: list[dict] = []
        self.gift_search = tk.StringVar()
        self.reward_search = tk.StringVar()
        self.rule_gift_name = tk.StringVar()
        self.rule_gift_id = tk.StringVar()
        self.rule_vietnamese_name = tk.StringVar()
        self.rule_action = tk.StringVar(value="special")
        self.rule_target = tk.StringVar(value="absorption")
        self.rule_amount = tk.StringVar(value="1")
        self.rule_level = tk.StringVar(value="0")
        self.reward_choice = tk.StringVar()
        self.reward_choice_box: ttk.Combobox | None = None
        self.gift_source_tree: ttk.Treeview | None = None
        self.reward_tree: ttk.Treeview | None = None
        self.mapping_tree: ttk.Treeview | None = None
        self._drag_data: tuple[str, object] | None = None
        self._mapping_drag_index: int | None = None
        self.event_mob_boxes: list[ttk.Combobox] = []
        self.discovered_gifts_modified = 0
        self.log_text: scrolledtext.ScrolledText | None = None
        self.status = tk.StringVar(value="Đang khởi tạo...")
        self.live_process: subprocess.Popen | None = None
        self.output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.tab_canvases: dict[str, tk.Canvas] = {}

        log_directory = GUI_DIR / "logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        self.gui_log_path = log_directory / "gui_latest.log"
        self.gui_log_file = self.gui_log_path.open("a", encoding="utf-8", buffering=1)

        self._configure_style()
        self._build_layout()
        self._load_all()
        self._log("INFO", "GUI đã sẵn sàng.")
        self.root.after(100, self._drain_output_queue)
        self.root.after(2_000, self._poll_gift_catalog)

    @staticmethod
    def _make_var(value):
        if isinstance(value, bool):
            return tk.BooleanVar(value=value)
        return tk.StringVar(value=str(value))

    def _configure_style(self) -> None:
        self.root.configure(bg="#10151f")
        self.root.option_add("*TCombobox*Listbox.background", "#0d131d")
        self.root.option_add("*TCombobox*Listbox.foreground", "#eaf0f7")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#168b68")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#10151f")
        style.configure("Card.TFrame", background="#182130")
        style.configure("TLabel", background="#10151f", foreground="#eaf0f7")
        style.configure("Card.TLabel", background="#182130", foreground="#eaf0f7")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 20), foreground="#ffffff")
        style.configure("Subtitle.TLabel", foreground="#94a5bb")
        style.configure("Section.TLabel", background="#182130", foreground="#53d6a4", font=("Segoe UI Semibold", 12))
        style.configure("TButton", padding=(12, 7), background="#253246", foreground="#ffffff")
        style.map("TButton", background=[("active", "#344661")])
        style.configure("Primary.TButton", background="#15a875", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#1ac28a")])
        style.configure("Danger.TButton", background="#b84152", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#d24e61")])
        style.configure("TNotebook", background="#10151f", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 9), background="#182130", foreground="#aebbd0")
        style.map("TNotebook.Tab", background=[("selected", "#26364c")], foreground=[("selected", "#ffffff")])
        style.configure("TEntry", fieldbackground="#0d131d", foreground="#ffffff", insertcolor="#ffffff")
        style.configure(
            "TCombobox",
            fieldbackground="#0d131d",
            background="#253246",
            foreground="#ffffff",
            arrowcolor="#ffffff",
            insertcolor="#ffffff",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#0d131d"), ("focus", "#111b29")],
            foreground=[("readonly", "#ffffff"), ("disabled", "#7f8da3")],
            selectbackground=[("focus", "#168b68")],
            selectforeground=[("focus", "#ffffff")],
        )
        style.configure(
            "Dark.Treeview",
            background="#0d131d",
            fieldbackground="#0d131d",
            foreground="#eaf0f7",
            rowheight=27,
            borderwidth=0,
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", "#168b68")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Dark.Treeview.Heading",
            background="#253246",
            foreground="#ffffff",
            relief="flat",
        )
        style.map("Dark.Treeview.Heading", background=[("active", "#344661")])
        style.configure("TCheckbutton", background="#182130", foreground="#eaf0f7")
        style.map("TCheckbutton", background=[("active", "#182130")])

    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, padding=(22, 16, 22, 10))
        header.pack(fill="x")
        ttk.Label(header, text="TikTok Mob Forge", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            textvariable=self.status,
            style="Subtitle.TLabel",
        ).pack(side="right", padx=(12, 0))

        actions = ttk.Frame(self.root, padding=(22, 0, 22, 12))
        actions.pack(fill="x")
        ttk.Button(actions, text="Lưu toàn bộ", style="Primary.TButton", command=self._save_all).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Chạy TikTok LIVE", command=self._start_live).pack(side="left", padx=4)
        ttk.Button(actions, text="Dừng", style="Danger.TButton", command=self._stop_live).pack(side="left", padx=4)
        ttk.Button(actions, text="Test giọng nói", command=self._test_tts).pack(side="left", padx=(18, 4))
        ttk.Button(actions, text="Test triệu hồi", command=self._test_mobs).pack(side="left", padx=4)
        ttk.Button(actions, text="Cài/Cập nhật mod", command=self._install_mod).pack(side="left", padx=(14, 4))
        ttk.Button(actions, text="Khôi phục mặc định", command=self._reset_defaults).pack(side="right")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=22, pady=(0, 18))
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<ButtonRelease-1>", self._finish_catalog_drag, add="+")

        general = self._new_scroll_tab("Kết nối")
        voice = self._new_scroll_tab("Giọng nói")
        summon = self._new_scroll_tab("Triệu hồi")
        gifts = self._new_scroll_tab("Quà tặng")
        logs = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(logs, text="Nhật ký")

        self._build_general_tab(general)
        self._build_voice_tab(voice)
        self._build_summon_tab(summon)
        self._build_gifts_tab(gifts)
        self._build_logs_tab(logs)

    def _new_scroll_tab(self, title: str) -> ttk.Frame:
        host = ttk.Frame(self.notebook)
        self.notebook.add(host, text=title)
        canvas = tk.Canvas(host, bg="#10151f", highlightthickness=0)
        scrollbar = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, padding=(8, 10, 18, 18))
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tab_canvases[str(host)] = canvas
        return inner

    def _on_mousewheel(self, event) -> None:
        selected_tab = self.notebook.select()
        canvas = self.tab_canvases.get(selected_tab)
        if canvas is not None:
            canvas.yview_scroll(int(-event.delta / 120), "units")

    def _card(self, parent: ttk.Frame, title: str, description: str = "") -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill="x", pady=7)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text=title, style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        if description:
            ttk.Label(card, text=description, style="Card.TLabel", foreground="#94a5bb", wraplength=850).grid(
                row=1, column=0, columnspan=3, sticky="w", pady=(3, 10)
            )
            card._next_row = 2
        else:
            card._next_row = 1
        return card

    def _field(self, card: ttk.Frame, label: str, variable, values=None, secret: bool = False, button=None):
        row = card._next_row
        card._next_row += 1
        ttk.Label(card, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 14), pady=5)
        if values:
            widget = ttk.Combobox(card, textvariable=variable, values=values, state="normal")
            widget._all_values = tuple(values)
            widget.bind("<KeyRelease>", lambda event, box=widget: self._filter_combobox(box, event))
        else:
            widget = ttk.Entry(card, textvariable=variable, show="●" if secret else "")
        widget.grid(row=row, column=1, sticky="ew", pady=5)
        if button:
            ttk.Button(card, text=button[0], command=button[1]).grid(row=row, column=2, padx=(8, 0), pady=5)
        return widget

    @staticmethod
    def _filter_combobox(widget: ttk.Combobox, event) -> None:
        if event.keysym in {"Up", "Down", "Left", "Right", "Return", "Escape", "Tab"}:
            return
        query = widget.get().casefold().strip()
        values = widget._all_values
        filtered = [value for value in values if query in value.casefold()]
        widget.configure(values=filtered or values)
        if query and filtered:
            widget.event_generate("<Down>")

    def _check(self, card: ttk.Frame, label: str, variable) -> None:
        row = card._next_row
        card._next_row += 1
        ttk.Checkbutton(card, text=label, variable=variable, style="TCheckbutton").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=5
        )

    def _build_general_tab(self, parent: ttk.Frame) -> None:
        account = self._card(parent, "TikTok và ElevenLabs", "Dữ liệu được lưu cục bộ trong bridge/config.json và bridge/.env.")
        self._field(account, "Tên tài khoản TikTok LIVE", self.bridge_vars["tiktok_username"])
        self._field(account, "ElevenLabs API key", self.api_key, secret=True)

        minecraft = self._card(parent, "Kết nối Minecraft", "Mod chỉ nghe trên máy cục bộ. Cổng bridge trong game và GUI luôn được đồng bộ.")
        self._field(
            minecraft,
            "Thư mục Minecraft",
            self.minecraft_directory,
            button=("Chọn...", self._choose_minecraft_directory),
        )
        self._field(minecraft, "Máy chủ Minecraft", self.bridge_vars["minecraft_host"])
        self._field(minecraft, "Cổng kết nối", self.bridge_vars["minecraft_port"])
        self._check(
            minecraft,
            "Tiếp tục chạy Minecraft khi chuyển sang cửa sổ GUI (không đứng đồng hồ)",
            self.keep_minecraft_running,
        )

        paths = self._card(parent, "Tệp và thư mục nhanh")
        row = paths._next_row
        ttk.Button(paths, text="Mở config bridge", command=lambda: self._open_path(BRIDGE_CONFIG_PATH)).grid(row=row, column=0, pady=5, sticky="w")
        ttk.Button(paths, text="Mở thư mục dự án", command=lambda: self._open_path(PROJECT_DIR)).grid(row=row, column=1, pady=5, sticky="w")

    def _build_voice_tab(self, parent: ttk.Frame) -> None:
        basic = self._card(parent, "Bật/tắt và chọn giọng", "Đổi các mục này cần dừng rồi chạy lại TikTok LIVE.")
        self._check(basic, "Bật đọc bình luận bằng giọng nói", self.bridge_vars["tts_enabled"])
        self._check(basic, "Đọc cả tên người bình luận", self.bridge_vars["tts_read_username"])
        self._field(basic, "Tên giọng", self.bridge_vars["tts_voice_name"])
        self._field(basic, "Voice ID", self.bridge_vars["tts_voice_id"])
        self._field(basic, "Model ElevenLabs", self.bridge_vars["tts_model_id"])
        self._field(basic, "Mã ngôn ngữ (vi/en/...)", self.bridge_vars["tts_language_code"])

        tuning = self._card(parent, "Tinh chỉnh chất giọng", "Các giá trị độ ổn định, độ giống và phong cách nằm trong khoảng 0 đến 1; tốc độ từ 0.7 đến 1.2.")
        self._field(tuning, "Độ ổn định", self.bridge_vars["tts_stability"])
        self._field(tuning, "Độ giống giọng gốc", self.bridge_vars["tts_similarity_boost"])
        self._field(tuning, "Mức phong cách", self.bridge_vars["tts_style"])
        self._field(tuning, "Tốc độ đọc", self.bridge_vars["tts_speed"])
        self._check(tuning, "Tăng cường độ rõ của người nói", self.bridge_vars["tts_use_speaker_boost"])

        queue_card = self._card(parent, "Khoảng nghỉ và hàng đợi")
        self._field(queue_card, "Nghỉ giữa hai bình luận (giây)", self.bridge_vars["tts_pause_between_comments_seconds"])
        self._field(queue_card, "Khoảng lặng cuối mỗi câu (giây)", self.bridge_vars["tts_trailing_silence_seconds"])
        self._field(queue_card, "Số ký tự tối đa mỗi bình luận", self.bridge_vars["tts_max_characters"])
        self._field(queue_card, "Số bình luận tối đa trong hàng đợi", self.bridge_vars["tts_queue_size"])
        self._check(queue_card, "Chờ đủ thời gian rồi chỉ đọc bình luận mới nhất", self.bridge_vars["tts_keep_latest_comment"])

    def _build_summon_tab(self, parent: ttk.Frame) -> None:
        mob_values = [self._mob_choice(entry) for entry in sorted(self.mob_catalog, key=lambda entry: (entry.group, entry.vietnamese_name.casefold()))]
        event_cards = (
            ("like", "LIKE", "Đủ mốc like sẽ triệu hồi mob đã chọn."),
            ("comment", "BÌNH LUẬN", "Mỗi bình luận hợp lệ sẽ triệu hồi mob đã chọn."),
            ("share", "CHIA SẺ", "Mỗi lượt chia sẻ sẽ triệu hồi mob đã chọn."),
            ("follow", "THEO DÕI", "Mỗi người theo dõi mới sẽ triệu hồi mob đã chọn."),
        )
        for prefix, title, description in event_cards:
            card = self._card(
                parent,
                f"Khối {title}",
                f"{description} Gõ tên tiếng Việt, nhóm hoặc Minecraft ID vào ô tìm kiếm.",
            )
            if prefix == "like":
                self._field(card, "Số like cho mỗi lần kích hoạt", self.bridge_vars["likes_per_skeleton"])
            box = self._field(
                card,
                f"Tìm/chọn mob cho {title}",
                self.bridge_vars[f"{prefix}_mob_type"],
                mob_values,
            )
            self.event_mob_boxes.append(box)
            self._field(card, "Số mob mỗi lần kích hoạt", self.bridge_vars[f"{prefix}_spawn_count"])
            if prefix == "comment":
                self._field(card, "Số bình luận được phép mỗi người", self.bridge_vars["comment_limit"])
                self._field(card, "Thời gian khóa bình luận (giây)", self.bridge_vars["comment_cooldown_seconds"])

        mobs = self._card(parent, "Giới hạn và vị trí triệu hồi", "Các mục này được mod nạp lại khoảng mỗi giây. Đổi cổng cần khởi động lại Minecraft.")
        self._field(mobs, "Số mob tối đa mỗi người dùng", self.mod_vars["max_mobs_per_user"])
        self._field(mobs, "Thời gian mob tồn tại (giây)", self.mod_vars["mob_lifetime_seconds"])
        self._field(mobs, "Khoảng cách sinh tối thiểu", self.mod_vars["spawn_min_distance"])
        self._field(mobs, "Khoảng cách sinh tối đa", self.mod_vars["spawn_max_distance"])
        self._field(mobs, "Độ lệch chiều cao sinh mob", self.mod_vars["spawn_height_offset"])
        self._check(mobs, "Enderman chủ động nhắm vào người chơi", self.mod_vars["enderman_targets_player"])
        self._check(mobs, "Giữ mob không tự biến mất theo luật Minecraft", self.mod_vars["mobs_persistent"])
        self._check(mobs, "Hiện đồng hồ đếm ngược trên tên mob", self.mod_vars["show_countdown_in_name"])

        performance = self._card(parent, "Hàng đợi và tốc độ xử lý")
        self._field(performance, "Số sự kiện chờ tối đa", self.mod_vars["max_pending_events"])
        self._field(performance, "Số sự kiện xử lý mỗi tick", self.mod_vars["max_interactions_per_tick"])

    def _build_gifts_tab(self, parent: ttk.Frame) -> None:
        catalogs = self._card(
            parent,
            "Bước 1 — Chọn quà TikTok",
            "Chạy LIVE một lần để danh sách quà tự xuất hiện. Tìm quà, chọn dòng phần thưởng bên dưới rồi nhấp đúp hoặc kéo quà vào đúng dòng.",
        )
        gift_tools = ttk.Frame(catalogs, style="Card.TFrame")
        gift_tools.grid(row=catalogs._next_row, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ttk.Label(gift_tools, text="Tìm theo tên, số xu hoặc Gift ID:", style="Card.TLabel").pack(side="left", padx=(0, 8))
        ttk.Entry(gift_tools, textvariable=self.gift_search).pack(side="left", fill="x", expand=True)
        ttk.Button(gift_tools, text="Làm mới", command=self._refresh_gift_catalog).pack(side="left", padx=(6, 0))
        catalogs._next_row += 1
        self.gift_source_tree = ttk.Treeview(
            catalogs,
            columns=("name", "coins", "id"),
            show="headings",
            height=7,
            style="Dark.Treeview",
        )
        self.gift_source_tree.heading("name", text="Tên quà")
        self.gift_source_tree.heading("coins", text="Xu")
        self.gift_source_tree.heading("id", text="Gift ID")
        self.gift_source_tree.column("name", width=360, anchor="w")
        self.gift_source_tree.column("coins", width=80, anchor="center")
        self.gift_source_tree.column("id", width=180, anchor="center")
        self.gift_source_tree.grid(row=catalogs._next_row, column=0, columnspan=3, sticky="nsew")
        self.gift_source_tree.bind("<ButtonPress-1>", lambda event: self._begin_catalog_drag("gift", event))
        self.gift_source_tree.bind("<ButtonRelease-1>", self._finish_catalog_drag)
        self.gift_source_tree.bind("<Double-1>", lambda _event: self._add_selected_gift())

        mappings = self._card(
            parent,
            "Bước 2 — Gán vào 7 phần thưởng dễ hiểu",
            "Năm dòng 1 xu phải dùng năm quà khác nhau. Dòng 100 xu tặng 64 táo vàng; dòng 1000 xu tặng trọn bộ giáp Netherite.",
        )
        toolbar = ttk.Frame(mappings, style="Card.TFrame")
        toolbar.grid(row=mappings._next_row, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ttk.Button(toolbar, text="Gán quà đang chọn", style="Primary.TButton", command=self._add_selected_gift).pack(side="left")
        ttk.Button(toolbar, text="Khôi phục 7 mốc mặc định", command=self._reset_default_gifts).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Test toàn bộ ánh xạ", command=self._test_gift_mappings).pack(side="right")
        mappings._next_row += 1
        self.mapping_tree = ttk.Treeview(
            mappings,
            columns=("coins", "gift", "reward", "amount", "gift_id"),
            show="headings",
            height=8,
            style="Dark.Treeview",
        )
        for column, title, width in (
            ("coins", "Giá xu", 70),
            ("gift", "Quà TikTok", 185),
            ("reward", "Phần thưởng trong Minecraft", 385),
            ("amount", "Số lượng", 75),
            ("gift_id", "Gift ID", 130),
        ):
            self.mapping_tree.heading(column, text=title)
            self.mapping_tree.column(column, width=width, anchor="center" if column in {"coins", "amount", "gift_id"} else "w")
        self.mapping_tree.grid(row=mappings._next_row, column=0, columnspan=3, sticky="nsew")
        self.mapping_tree.bind("<<TreeviewSelect>>", self._load_selected_rule_editor)

        advanced = self._card(
            parent,
            "Tùy chỉnh nâng cao (không bắt buộc)",
            "Chọn một dòng ở bảng trên rồi tìm vật phẩm, bộ giáp, hiệu ứng hoặc mob khác. Mặc định đã đúng theo yêu cầu của bạn.",
        )
        reward_values = [f"[{entry.group}] {entry.display}" for entry in self.reward_catalog]
        self.reward_choice_box = self._field(advanced, "Tìm/chọn phần thưởng", self.reward_choice, reward_values)
        self._field(advanced, "Số lượng mỗi quà", self.rule_amount)
        self._field(advanced, "Cấp enchant / XP (0 = enchant tối đa, 1–255)", self.rule_level)
        row = advanced._next_row
        ttk.Button(advanced, text="Áp dụng cho dòng đang chọn", command=self._apply_reward_choice).grid(
            row=row, column=1, sticky="e", pady=(8, 0)
        )
        self.gift_search.trace_add("write", lambda *_args: self._refresh_gift_catalog())

        effects = self._card(parent, "Hiệu ứng phần thưởng")
        self._field(effects, "Thời gian hiện thông báo (giây)", self.mod_vars["notification_duration_seconds"])
        self._field(effects, "Số tim vàng cho quà 1 xu", self.mod_vars["absorption_hearts_per_rose"])

    def _build_logs_tab(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="Xem log Minecraft", command=self._show_minecraft_log).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Mở log bridge", command=lambda: self._open_path(BRIDGE_DIR / "logs")).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Mở log GUI", command=lambda: self._open_path(GUI_DIR / "logs")).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Xóa màn hình", command=self._clear_log_display).pack(side="right")
        self.log_text = scrolledtext.ScrolledText(
            parent,
            bg="#080d14",
            fg="#dce6f3",
            insertbackground="#ffffff",
            font=("Consolas", 10),
            relief="flat",
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("INFO", foreground="#80d8b3")
        self.log_text.tag_configure("ERROR", foreground="#ff7888")
        self.log_text.tag_configure("WARN", foreground="#ffd479")
        self.log_text.tag_configure("PROCESS", foreground="#bdc9da")

    def _load_all(self) -> None:
        try:
            state = load_gui_state()
            minecraft_directory = str(state.get("minecraft_directory") or "").strip()
            self.minecraft_directory.set(minecraft_directory)
            self.keep_minecraft_running.set(
                bool(state.get("keep_minecraft_running_in_background", True))
            )
            bridge = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
            mod = load_json(mod_config_path(minecraft_directory), DEFAULT_MOD_CONFIG)
            for key, variable in self.bridge_vars.items():
                variable.set(bridge.get(key, DEFAULT_BRIDGE_CONFIG[key]))
            for prefix in ("like", "comment", "share", "follow"):
                key = f"{prefix}_mob_type"
                self.bridge_vars[key].set(self._mob_display(str(bridge.get(key, DEFAULT_BRIDGE_CONFIG[key]))))
            for key, variable in self.mod_vars.items():
                variable.set(mod.get(key, DEFAULT_MOD_CONFIG[key]))
            self.api_key.set(load_api_key())
            configured_actions = bridge.get("gift_actions")
            self.gift_actions = [dict(rule) for rule in configured_actions] if isinstance(configured_actions, list) else [dict(rule) for rule in DEFAULT_GIFT_ACTIONS]
            self._refresh_mapping_tree()
            self._refresh_gift_catalog()
            self.status.set("Sẵn sàng")
        except Exception as error:
            self.status.set("Lỗi đọc cấu hình")
            self._log("ERROR", f"Không đọc được cấu hình: {error}")
            messagebox.showerror("Không đọc được cấu hình", str(error), parent=self.root)

    def _mob_display(self, configured_value: str) -> str:
        target = configured_value.strip().lower()
        if ":" not in target:
            target = f"minecraft:{target}"
        entry = next((item for item in self.mob_catalog if item.target == target), None)
        return self._mob_choice(entry) if entry else target

    @staticmethod
    def _mob_choice(entry: CatalogEntry) -> str:
        return f"[{entry.group}] {entry.display}"

    @staticmethod
    def _target_from_display(value: str) -> str:
        target = value.rsplit(" — ", 1)[-1].strip().lower()
        if ":" not in target:
            target = f"minecraft:{target}"
        return target

    def _load_discovered_gifts(self) -> list[dict]:
        discovered: list[dict] = []
        if DISCOVERED_GIFTS_PATH.is_file():
            try:
                loaded = load_json_list(DISCOVERED_GIFTS_PATH)
                discovered.extend(item for item in loaded if isinstance(item, dict))
            except (OSError, ValueError):
                pass
        known = {
            str(item.get("gift_id") or str(item.get("name", "")).casefold()): item
            for item in discovered
        }
        for rule in self.gift_actions:
            key = str(rule.get("gift_id") or str(rule.get("gift_name", "")).casefold())
            known.setdefault(
                key,
                {
                    "gift_id": str(rule.get("gift_id", "")),
                    "name": str(rule.get("gift_name", "")),
                    "diamond_count": int(rule.get("coin_value", 0) or 0),
                },
            )
        return sorted(known.values(), key=lambda item: (int(item.get("diamond_count", 0) or 0), str(item.get("name", "")).casefold()))

    def _refresh_gift_catalog(self) -> None:
        if self.gift_source_tree is None:
            return
        query = self.gift_search.get().casefold().strip()
        self.gift_source_tree.delete(*self.gift_source_tree.get_children())
        for index, gift in enumerate(self._load_discovered_gifts()):
            searchable = f"{gift.get('name', '')} {gift.get('gift_id', '')} {gift.get('diamond_count', '')}".casefold()
            if query and query not in searchable:
                continue
            self.gift_source_tree.insert(
                "",
                "end",
                iid=f"gift-{index}",
                values=(gift.get("name", ""), gift.get("diamond_count", 0), gift.get("gift_id", "")),
            )

    def _poll_gift_catalog(self) -> None:
        try:
            modified = DISCOVERED_GIFTS_PATH.stat().st_mtime_ns if DISCOVERED_GIFTS_PATH.is_file() else 0
            if modified != self.discovered_gifts_modified:
                self.discovered_gifts_modified = modified
                self._refresh_gift_catalog()
        finally:
            self.root.after(2_000, self._poll_gift_catalog)

    def _refresh_reward_catalog(self) -> None:
        if self.reward_tree is None:
            return
        query = self.reward_search.get().casefold().strip()
        self.reward_tree.delete(*self.reward_tree.get_children())
        for index, entry in enumerate(self.reward_catalog):
            searchable = f"{entry.group} {entry.vietnamese_name} {entry.target} {entry.kind}".casefold()
            if query and query not in searchable:
                continue
            self.reward_tree.insert(
                "",
                "end",
                iid=f"reward-{index}",
                values=(entry.group, entry.vietnamese_name, entry.target),
                tags=(entry.kind,),
            )

    def _reward_label(self, action: str, target: str) -> str:
        entry = next(
            (item for item in self.reward_catalog if item.kind == action and item.target == target),
            None,
        )
        return f"{entry.vietnamese_name} — {target}" if entry else f"{action}: {target}"

    def _refresh_mapping_tree(self, select_index: int | None = None) -> None:
        if self.mapping_tree is None:
            return
        self.mapping_tree.delete(*self.mapping_tree.get_children())
        for index, rule in enumerate(self.gift_actions):
            action = str(rule.get("action", "special"))
            target = str(rule.get("target", "absorption"))
            self.mapping_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    rule.get("coin_value", 0),
                    rule.get("gift_name", ""),
                    self._reward_label(action, target),
                    rule.get("amount", 1),
                    rule.get("gift_id", ""),
                ),
            )
        if select_index is not None and 0 <= select_index < len(self.gift_actions):
            self.mapping_tree.selection_set(str(select_index))
            self.mapping_tree.focus(str(select_index))
            self.mapping_tree.see(str(select_index))

    def _selected_rule_index(self) -> int | None:
        if self.mapping_tree is None or not self.mapping_tree.selection():
            return None
        try:
            return int(self.mapping_tree.selection()[0])
        except (ValueError, IndexError):
            return None

    def _add_selected_gift(self) -> None:
        if self.gift_source_tree is None or not self.gift_source_tree.selection():
            messagebox.showwarning("Chưa chọn quà", "Hãy chọn một quà TikTok ở bảng phía trên.", parent=self.root)
            return
        index = self._selected_rule_index()
        if index is None:
            messagebox.showwarning("Chưa chọn phần thưởng", "Hãy chọn một trong 7 dòng phần thưởng trước.", parent=self.root)
            return
        values = self.gift_source_tree.item(self.gift_source_tree.selection()[0], "values")
        self._assign_gift_to_rule(index, str(values[0]), str(values[2]), int(values[1] or 0))

    def _assign_gift_to_rule(self, index: int, gift_name: str, gift_id: str, coins: int) -> None:
        expected_coins = int(self.gift_actions[index].get("coin_value", 0) or 0)
        if coins > 0 and coins != expected_coins:
            messagebox.showerror(
                "Sai mốc xu",
                f"Quà '{gift_name}' có giá {coins} xu nhưng dòng đang chọn cần quà {expected_coins} xu.",
                parent=self.root,
            )
            return
        duplicate = next(
            (
                rule_index
                for rule_index, rule in enumerate(self.gift_actions)
                if rule_index != index
                and (
                    (gift_id and str(rule.get("gift_id", "")) == gift_id)
                    or str(rule.get("gift_name", "")).casefold() == gift_name.casefold()
                )
            ),
            None,
        )
        if duplicate is not None:
            messagebox.showerror(
                "Quà bị trùng",
                f"Quà '{gift_name}' đã được dùng ở dòng {duplicate + 1}. Mỗi quà chỉ được gán một lần.",
                parent=self.root,
            )
            return
        self.gift_actions[index]["gift_name"] = gift_name
        self.gift_actions[index]["gift_id"] = gift_id
        self.gift_actions[index]["vietnamese_name"] = gift_name
        self._refresh_mapping_tree(index)
        self._refresh_gift_catalog()
        self.status.set(f"Đã gán {gift_name} vào phần thưởng dòng {index + 1}")

    def _reset_default_gifts(self) -> None:
        self.gift_actions = [dict(rule) for rule in DEFAULT_GIFT_ACTIONS]
        self._refresh_mapping_tree(0)
        self._refresh_gift_catalog()
        self.status.set("Đã khôi phục 7 mốc quà mặc định")

    def _append_gift_rule(self, gift_name: str, gift_id: str = "") -> None:
        existing = next(
            (
                index
                for index, rule in enumerate(self.gift_actions)
                if (gift_id and str(rule.get("gift_id", "")) == gift_id)
                or str(rule.get("gift_name", "")).casefold() == gift_name.casefold()
            ),
            None,
        )
        if existing is not None:
            self._refresh_mapping_tree(existing)
            return
        self.gift_actions.append(
            {
                "gift_name": gift_name,
                "gift_id": gift_id,
                "vietnamese_name": gift_name,
                "action": "special",
                "target": "absorption",
                "amount": 1,
            }
        )
        self._refresh_mapping_tree(len(self.gift_actions) - 1)

    def _add_manual_gift(self) -> None:
        self._append_gift_rule("Quà mới", "")

    def _delete_selected_gift_rule(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        self.gift_actions.pop(index)
        self._refresh_mapping_tree(min(index, len(self.gift_actions) - 1))

    def _move_gift_rule(self, offset: int) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        target_index = max(0, min(len(self.gift_actions) - 1, index + offset))
        if target_index == index:
            return
        rule = self.gift_actions.pop(index)
        self.gift_actions.insert(target_index, rule)
        self._refresh_mapping_tree(target_index)

    def _load_selected_rule_editor(self, _event=None) -> None:
        index = self._selected_rule_index()
        if index is None:
            return
        rule = self.gift_actions[index]
        self.rule_gift_name.set(str(rule.get("gift_name", "")))
        self.rule_gift_id.set(str(rule.get("gift_id", "")))
        self.rule_vietnamese_name.set(str(rule.get("vietnamese_name", "")))
        self.rule_action.set(str(rule.get("action", "special")))
        self.rule_target.set(str(rule.get("target", "absorption")))
        self.rule_amount.set(str(rule.get("amount", 1)))
        self.rule_level.set(str(rule.get("level", 0 if str(rule.get("target", "")).startswith("enchant_") else 1)))
        entry = next(
            (
                item
                for item in self.reward_catalog
                if item.kind == self.rule_action.get() and item.target == self.rule_target.get()
            ),
            None,
        )
        self.reward_choice.set(f"[{entry.group}] {entry.display}" if entry else "")

    def _apply_reward_choice(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            messagebox.showwarning("Chưa chọn dòng", "Hãy chọn một dòng phần thưởng trước.", parent=self.root)
            return
        choice = self.reward_choice.get().strip()
        reward = next(
            (
                entry
                for entry in self.reward_catalog
                if choice == f"[{entry.group}] {entry.display}"
                or choice.casefold() == entry.target.casefold()
            ),
            None,
        )
        if reward is None:
            messagebox.showerror("Phần thưởng không hợp lệ", "Hãy chọn phần thưởng trong danh sách tìm kiếm.", parent=self.root)
            return
        try:
            amount = self._number(self.rule_amount.get(), "Số lượng mỗi quà", 1, 100, integer=True)
            level = self._number(self.rule_level.get(), "Cấp quà", 0 if reward.target.startswith("enchant_") else 1, 255, integer=True)
        except ValueError as error:
            messagebox.showerror("Số lượng không hợp lệ", str(error), parent=self.root)
            return
        self.gift_actions[index]["action"] = reward.kind
        self.gift_actions[index]["target"] = reward.target
        self.gift_actions[index]["amount"] = amount
        self.gift_actions[index]["level"] = level
        self._refresh_mapping_tree(index)

    def _apply_rule_editor(self) -> None:
        index = self._selected_rule_index()
        if index is None:
            messagebox.showwarning("Chưa chọn dòng", "Hãy chọn một dòng ánh xạ trước.", parent=self.root)
            return
        gift_name = self.rule_gift_name.get().strip()
        action = self.rule_action.get().strip().lower()
        target = self.rule_target.get().strip().lower()
        if not gift_name or action not in {"special", "mob", "item"} or not target:
            messagebox.showerror("Dữ liệu chưa hợp lệ", "Tên quà, loại và ID phần thưởng không được để trống.", parent=self.root)
            return
        try:
            amount = self._number(self.rule_amount.get(), "Số lượng mỗi quà", 1, 100, integer=True)
            level = self._number(self.rule_level.get(), "Cấp quà", 0 if target.startswith("enchant_") else 1, 255, integer=True)
        except ValueError as error:
            messagebox.showerror("Số lượng không hợp lệ", str(error), parent=self.root)
            return
        self.gift_actions[index] = {
            "gift_name": gift_name,
            "gift_id": self.rule_gift_id.get().strip(),
            "vietnamese_name": self.rule_vietnamese_name.get().strip() or gift_name,
            "action": action,
            "target": target,
            "amount": amount,
            "level": level,
        }
        self._refresh_mapping_tree(index)
        self._refresh_gift_catalog()

    def _selected_reward_entry(self) -> CatalogEntry | None:
        if self.reward_tree is None or not self.reward_tree.selection():
            return None
        values = self.reward_tree.item(self.reward_tree.selection()[0], "values")
        target = str(values[2])
        return next((entry for entry in self.reward_catalog if entry.target == target), None)

    def _apply_selected_reward(self, rule_index: int | None = None) -> None:
        index = self._selected_rule_index() if rule_index is None else rule_index
        reward = self._selected_reward_entry()
        if index is None or reward is None:
            return
        self.gift_actions[index]["action"] = reward.kind
        self.gift_actions[index]["target"] = reward.target
        self.gift_actions[index]["level"] = 0 if reward.target.startswith("enchant_") else 1
        self._refresh_mapping_tree(index)

    def _begin_catalog_drag(self, kind: str, event) -> None:
        tree = self.gift_source_tree if kind == "gift" else self.reward_tree
        row = tree.identify_row(event.y) if tree else ""
        self._drag_data = (kind, row) if row else None

    def _finish_catalog_drag(self, event) -> None:
        if self._drag_data is None or self.mapping_tree is None:
            return
        kind, row = self._drag_data
        self._drag_data = None
        target_widget = self.root.winfo_containing(event.x_root, event.y_root)
        if target_widget is not self.mapping_tree:
            return
        target_row = self.mapping_tree.identify_row(event.y_root - self.mapping_tree.winfo_rooty())
        target_index = int(target_row) if target_row else self._selected_rule_index()
        if kind == "gift" and self.gift_source_tree is not None:
            values = self.gift_source_tree.item(row, "values")
            if target_index is not None:
                self._assign_gift_to_rule(target_index, str(values[0]), str(values[2]), int(values[1] or 0))
        elif kind == "reward" and self.reward_tree is not None and target_index is not None:
            self.reward_tree.selection_set(row)
            self._apply_selected_reward(target_index)

    def _begin_mapping_drag(self, event) -> None:
        row = self.mapping_tree.identify_row(event.y) if self.mapping_tree else ""
        self._mapping_drag_index = int(row) if row else None

    def _finish_mapping_drag(self, event) -> None:
        if self._mapping_drag_index is None or self.mapping_tree is None:
            return
        source_index = self._mapping_drag_index
        self._mapping_drag_index = None
        row = self.mapping_tree.identify_row(event.y)
        if not row:
            return
        target_index = int(row)
        if source_index == target_index:
            return
        rule = self.gift_actions.pop(source_index)
        self.gift_actions.insert(target_index, rule)
        self._refresh_mapping_tree(target_index)

    def _collect_gift_actions(self) -> list[dict]:
        if not self.gift_actions:
            raise ValueError("Cần ít nhất một ánh xạ quà tặng.")
        cleaned: list[dict] = []
        used_gifts: set[str] = set()
        for index, rule in enumerate(self.gift_actions, start=1):
            gift_name = str(rule.get("gift_name", "")).strip()
            action = str(rule.get("action", "")).strip().lower()
            target = str(rule.get("target", "")).strip().lower()
            gift_id = str(rule.get("gift_id", "")).strip()
            if not gift_name or action not in {"special", "mob", "item"} or not target:
                raise ValueError(f"Ánh xạ quà dòng {index} chưa hợp lệ.")
            unique_key = f"id:{gift_id}" if gift_id else f"name:{gift_name.casefold()}"
            if unique_key in used_gifts:
                raise ValueError(f"Quà '{gift_name}' đang bị gán trùng. Mỗi quà chỉ được dùng một lần.")
            used_gifts.add(unique_key)
            if action == "special" and not any(
                entry.kind == "special" and entry.target == target for entry in SPECIAL_REWARDS
            ):
                raise ValueError(f"Hiệu ứng đặc biệt '{target}' ở dòng {index} không hợp lệ.")
            if action in {"mob", "item"} and target.startswith("minecraft:"):
                catalog = self.mob_catalog if action == "mob" else self.item_catalog
                if not any(entry.target == target for entry in catalog):
                    raise ValueError(f"ID {action} '{target}' ở dòng {index} không có trong danh mục.")
            cleaned.append(
                {
                    "gift_name": gift_name,
                    "gift_id": gift_id,
                    "vietnamese_name": str(rule.get("vietnamese_name", "")).strip() or gift_name,
                    "coin_value": self._number(str(rule.get("coin_value", 0)), "Giá xu", 1, 1_000_000, integer=True),
                    "action": action,
                    "target": target,
                    "amount": self._number(str(rule.get("amount", 1)), "Số lượng mỗi quà", 1, 100, integer=True),
                    "level": self._number(str(rule.get("level", 0 if target.startswith("enchant_") else 1)), "Cấp quà", 0, 255, integer=True),
                }
            )
        return cleaned

    @staticmethod
    def _number(value: str, label: str, minimum: float, maximum: float, integer: bool = False):
        try:
            parsed = int(value) if integer else float(value)
        except ValueError as error:
            raise ValueError(f"'{label}' phải là một con số.") from error
        if not minimum <= parsed <= maximum:
            raise ValueError(f"'{label}' phải từ {minimum:g} đến {maximum:g}.")
        return parsed

    def _collect_bridge_config(self) -> dict:
        data = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
        data.pop("gift_rewards", None)
        for key, variable in self.bridge_vars.items():
            data[key] = variable.get()
        for prefix in ("like", "comment", "share", "follow"):
            key = f"{prefix}_mob_type"
            data[key] = self._target_from_display(str(data[key]))
            if data[key].startswith("minecraft:") and not any(
                entry.target == data[key] for entry in self.mob_catalog
            ):
                raise ValueError(f"Mob '{data[key]}' không có trong danh mục Minecraft đã nạp.")
        int_fields = {
            "likes_per_skeleton": (1, 1_000_000),
            "like_spawn_count": (1, 100),
            "comment_spawn_count": (1, 100),
            "share_spawn_count": (1, 100),
            "follow_spawn_count": (1, 100),
            "comment_limit": (1, 100_000),
            "tts_max_characters": (1, 5_000),
            "tts_queue_size": (1, 10_000),
            "minecraft_port": (1_024, 65_535),
        }
        float_fields = {
            "comment_cooldown_seconds": (0.0, 86_400.0),
            "tts_pause_between_comments_seconds": (0.0, 600.0),
            "tts_trailing_silence_seconds": (0.0, 30.0),
            "tts_stability": (0.0, 1.0),
            "tts_similarity_boost": (0.0, 1.0),
            "tts_style": (0.0, 1.0),
            "tts_speed": (0.7, 1.2),
        }
        for key, bounds in int_fields.items():
            data[key] = self._number(str(data[key]), key, *bounds, integer=True)
        for key, bounds in float_fields.items():
            data[key] = self._number(str(data[key]), key, *bounds)
        for key in (
            "tts_enabled",
            "tts_read_username",
            "tts_use_speaker_boost",
            "tts_keep_latest_comment",
        ):
            data[key] = bool(self.bridge_vars[key].get())
        username = str(data["tiktok_username"]).strip().lstrip("@")
        if not username:
            raise ValueError("Tên tài khoản TikTok không được để trống.")
        data["tiktok_username"] = username
        if not str(data["minecraft_host"]).strip():
            raise ValueError("Máy chủ Minecraft không được để trống.")
        data["gift_actions"] = self._collect_gift_actions()
        return data

    def _collect_mod_config(self, bridge_port: int) -> dict:
        directory = self.minecraft_directory.get().strip()
        if not directory:
            raise ValueError("Thư mục Minecraft không được để trống.")
        data = load_json(mod_config_path(directory), DEFAULT_MOD_CONFIG)
        for key, variable in self.mod_vars.items():
            data[key] = variable.get()
        data["bridge_port"] = bridge_port
        int_fields = {
            "max_pending_events": (10, 100_000),
            "max_interactions_per_tick": (1, 1_000),
            "max_mobs_per_user": (1, 1_000),
            "money_gun_arrow_count": (1, 64),
            "universe_effect_level": (1, 10),
        }
        float_fields = {
            "mob_lifetime_seconds": (1.0, 86_400.0),
            "spawn_min_distance": (0.0, 128.0),
            "spawn_max_distance": (0.0, 128.0),
            "spawn_height_offset": (-64.0, 64.0),
            "notification_duration_seconds": (0.05, 300.0),
            "effect_duration_seconds": (0.05, 3_600.0),
            "absorption_hearts_per_rose": (0.5, 100.0),
        }
        for key, bounds in int_fields.items():
            data[key] = self._number(str(data[key]), key, *bounds, integer=True)
        for key, bounds in float_fields.items():
            data[key] = self._number(str(data[key]), key, *bounds)
        if data["spawn_max_distance"] < data["spawn_min_distance"]:
            raise ValueError("Khoảng cách sinh tối đa phải lớn hơn hoặc bằng khoảng cách tối thiểu.")
        for key in ("enderman_targets_player", "mobs_persistent", "show_countdown_in_name"):
            data[key] = bool(self.mod_vars[key].get())
        return data

    def _save_all(self, quiet: bool = False) -> bool:
        try:
            bridge = self._collect_bridge_config()
            mod = self._collect_mod_config(bridge["minecraft_port"])
            minecraft_directory = self.minecraft_directory.get().strip()
            save_json(BRIDGE_CONFIG_PATH, bridge)
            save_json(mod_config_path(minecraft_directory), mod)
            keep_running = bool(self.keep_minecraft_running.get())
            options_path = set_pause_on_lost_focus(minecraft_directory, pause=not keep_running)
            save_json(
                GUI_STATE_PATH,
                {
                    "minecraft_directory": minecraft_directory,
                    "keep_minecraft_running_in_background": keep_running,
                },
            )
            save_api_key(self.api_key.get())
            self.mod_vars["bridge_port"].set(str(bridge["minecraft_port"]))
            self.status.set("Đã lưu cấu hình")
            self._log("INFO", f"Đã lưu bridge và mod config tại {mod_config_path(minecraft_directory)}")
            self._log(
                "INFO",
                f"Đã đặt pauseOnLostFocus={str(not keep_running).lower()} tại {options_path}",
            )
            if not quiet:
                suffix = "\n\nBridge đang chạy: hãy dừng và chạy lại để áp dụng phần TikTok/TTS." if self._live_is_running() else ""
                messagebox.showinfo("Đã lưu", "Đã lưu toàn bộ thông số." + suffix, parent=self.root)
            return True
        except Exception as error:
            self.status.set("Lưu thất bại")
            self._log("ERROR", f"Lưu cấu hình thất bại: {error}")
            messagebox.showerror("Không thể lưu", str(error), parent=self.root)
            return False

    def _choose_minecraft_directory(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root,
            title="Chọn thư mục Minecraft có thư mục mods và logs",
            initialdir=self.minecraft_directory.get() or str(Path.home()),
        )
        if selected:
            current_targets = {
                prefix: self._target_from_display(self.bridge_vars[f"{prefix}_mob_type"].get())
                for prefix in ("like", "comment", "share", "follow")
            }
            self.minecraft_directory.set(selected)
            self.mob_catalog, self.item_catalog = load_minecraft_catalog(selected)
            self.reward_catalog = [*SPECIAL_REWARDS, *self.item_catalog, *self.mob_catalog]
            reward_values = [f"[{entry.group}] {entry.display}" for entry in self.reward_catalog]
            if self.reward_choice_box is not None:
                self.reward_choice_box._all_values = tuple(reward_values)
                self.reward_choice_box.configure(values=reward_values)
            mob_values = [
                self._mob_choice(entry)
                for entry in sorted(self.mob_catalog, key=lambda entry: (entry.group, entry.vietnamese_name.casefold()))
            ]
            for box in self.event_mob_boxes:
                box._all_values = tuple(mob_values)
                box.configure(values=mob_values)
            for prefix, target in current_targets.items():
                self.bridge_vars[f"{prefix}_mob_type"].set(self._mob_display(target))
            self._refresh_reward_catalog()
            self._refresh_mapping_tree()
            self.status.set(f"Đã nạp {len(self.mob_catalog)} mob, {len(self.item_catalog)} vật phẩm")

    def _live_is_running(self) -> bool:
        return self.live_process is not None and self.live_process.poll() is None

    def _start_live(self) -> None:
        if self._live_is_running():
            messagebox.showinfo("Đang chạy", "TikTok LIVE bridge đang chạy rồi.", parent=self.root)
            return
        if not self._save_all(quiet=True):
            return
        self.live_process = self._spawn_bridge([], "LIVE")
        if self.live_process:
            self.status.set("TikTok LIVE đang chạy")

    def _test_tts(self) -> None:
        if not self._save_all(quiet=True):
            return
        if not self.api_key.get().strip():
            messagebox.showwarning("Thiếu API key", "Hãy nhập ElevenLabs API key trước khi test giọng.", parent=self.root)
            return
        self._spawn_bridge(["--test-tts"], "TEST TTS")
        self.notebook.select(self.notebook.tabs()[-1])

    def _test_mobs(self) -> None:
        if not self._save_all(quiet=True):
            return
        self._spawn_bridge(["--test", "mobs"], "TEST MOB")
        self.notebook.select(self.notebook.tabs()[-1])

    def _test_gift_mappings(self) -> None:
        if not self._save_all(quiet=True):
            return
        self._spawn_bridge(["--test", "gifts"], "TEST QUÀ")
        self.notebook.select(self.notebook.tabs()[-1])

    def _install_mod(self) -> None:
        source = PROJECT_DIR / "release" / "tiktokmob-1.0.0.jar"
        minecraft_directory_text = self.minecraft_directory.get().strip()
        if not source.is_file():
            messagebox.showerror("Thiếu file mod", f"Không tìm thấy {source}", parent=self.root)
            return
        if not minecraft_directory_text:
            messagebox.showerror("Thiếu thư mục Minecraft", "Hãy chọn thư mục Minecraft trước.", parent=self.root)
            return
        minecraft_directory = Path(minecraft_directory_text).expanduser()
        try:
            mods_directory = minecraft_directory / "mods"
            mods_directory.mkdir(parents=True, exist_ok=True)
            destination = mods_directory / source.name
            shutil.copy2(source, destination)
            self._log("INFO", f"Đã cài mod mới vào {destination}")
            messagebox.showinfo(
                "Cài mod thành công",
                f"Đã chép mod vào:\n{destination}\n\nHãy khởi động lại Minecraft để dùng logic mob/vật phẩm mới.",
                parent=self.root,
            )
        except OSError as error:
            self._log("ERROR", f"Cài mod thất bại: {error}")
            messagebox.showerror("Cài mod thất bại", str(error), parent=self.root)

    def _spawn_bridge(self, arguments: list[str], label: str) -> subprocess.Popen | None:
        if not RUN_BRIDGE.is_file():
            messagebox.showerror("Thiếu launcher", f"Không tìm thấy {RUN_BRIDGE}", parent=self.root)
            return None
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONUNBUFFERED"] = "1"
        command = subprocess.list2cmdline([str(RUN_BRIDGE), *arguments])
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            process = subprocess.Popen(
                command,
                cwd=BRIDGE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                shell=True,
                creationflags=flags,
            )
        except Exception as error:
            self._log("ERROR", f"Không chạy được {label}: {error}")
            messagebox.showerror("Không chạy được", str(error), parent=self.root)
            return None
        self._log("INFO", f"Đã khởi chạy {label} (PID {process.pid}).")
        threading.Thread(target=self._read_process, args=(process, label), daemon=True).start()
        return process

    def _read_process(self, process: subprocess.Popen, label: str) -> None:
        if process.stdout:
            for line in process.stdout:
                self.output_queue.put(("PROCESS", f"[{label}] {line.rstrip()}"))
        exit_code = process.wait()
        level = "INFO" if exit_code == 0 else "ERROR"
        self.output_queue.put((level, f"{label} đã kết thúc với mã {exit_code}."))
        self.output_queue.put(("STATUS", label))

    def _drain_output_queue(self) -> None:
        try:
            while True:
                level, message = self.output_queue.get_nowait()
                if level == "STATUS":
                    if message == "LIVE" and not self._live_is_running():
                        self.live_process = None
                        self.status.set("TikTok LIVE đã dừng")
                else:
                    self._log(level, message)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_output_queue)

    def _stop_live(self) -> None:
        if not self._live_is_running():
            self.status.set("Không có LIVE đang chạy")
            return
        process = self.live_process
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    check=False,
                )
            else:
                process.terminate()
            self._log("WARN", "Đã gửi lệnh dừng TikTok LIVE bridge.")
            self.status.set("Đang dừng...")
        except Exception as error:
            self._log("ERROR", f"Không dừng được bridge: {error}")

    def _show_minecraft_log(self) -> None:
        log_path = Path(self.minecraft_directory.get().strip()) / "logs" / "latest.log"
        if not log_path.is_file():
            messagebox.showwarning("Chưa có log", f"Không tìm thấy {log_path}", parent=self.root)
            return
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
            self._log("INFO", f"===== 500 dòng cuối của {log_path} =====")
            for line in lines:
                if "TikTokMob" in line or "tiktokmob" in line.lower():
                    self._log("PROCESS", f"[MINECRAFT] {line}")
            self.notebook.select(self.notebook.tabs()[-1])
        except Exception as error:
            messagebox.showerror("Không đọc được log", str(error), parent=self.root)

    def _log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}\n"
        self.gui_log_file.write(line)
        if self.log_text:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line, level if level in ("INFO", "WARN", "ERROR", "PROCESS") else "PROCESS")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def _clear_log_display(self) -> None:
        if self.log_text:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

    def _open_path(self, path: Path) -> None:
        try:
            target = path if path.exists() else path.parent
            os.startfile(str(target))
        except Exception as error:
            messagebox.showerror("Không mở được", str(error), parent=self.root)

    def _reset_defaults(self) -> None:
        if not messagebox.askyesno(
            "Khôi phục mặc định",
            "Đưa các ô về mặc định? Bạn vẫn cần bấm 'Lưu toàn bộ' để ghi xuống tệp.",
            parent=self.root,
        ):
            return
        for key, variable in self.bridge_vars.items():
            variable.set(DEFAULT_BRIDGE_CONFIG[key])
        for prefix in ("like", "comment", "share", "follow"):
            key = f"{prefix}_mob_type"
            self.bridge_vars[key].set(self._mob_display(str(DEFAULT_BRIDGE_CONFIG[key])))
        for key, variable in self.mod_vars.items():
            variable.set(DEFAULT_MOD_CONFIG[key])
        self.keep_minecraft_running.set(True)
        self.gift_actions = [dict(rule) for rule in DEFAULT_GIFT_ACTIONS]
        self._refresh_mapping_tree()
        self._refresh_gift_catalog()
        self.status.set("Đã đưa về mặc định, chưa lưu")

    def _on_close(self) -> None:
        if self._live_is_running() and not messagebox.askyesno(
            "Bridge đang chạy",
            "Dừng TikTok LIVE bridge và đóng GUI?",
            parent=self.root,
        ):
            return
        if self._live_is_running():
            self._stop_live()
        self.gui_log_file.close()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
