from pathlib import Path
p=Path('TikTokMobForge/web/main.py');s=p.read_text(encoding='utf-8');a='    WEB_DIR / "main.py", BRIDGE_DIR / "bridge.py", BRIDGE_DIR / "test_runner.py"';b='    WEB_DIR / "main.py", BRIDGE_DIR / "bridge.py", BRIDGE_DIR / "test_runner.py",\n    BRIDGE_DIR / "reward_options.py", WEB_DIR / "live_panel.py"';assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
