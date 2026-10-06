from pathlib import Path
p=Path('TikTokMobForge/tests/test_settings.py');s=p.read_text(encoding='utf-8').replace('import main as web\n','import main as web\nimport live_panel\n').replace('        stack.enter_context(patch.object(web, "GUI_STATE_PATH", root / "gui.json"))','        stack.enter_context(patch.object(web, "GUI_STATE_PATH", root / "gui.json"))\n        stack.enter_context(patch.object(live_panel, "PATH", root / "live-panel.json"))');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/tests/test_live_panel.py');p.write_text('''import unittest
from test_settings import isolated_settings
import live_panel

class LivePanelTests(unittest.TestCase):
    def test_display_only_snapshot_persists(self):
        with isolated_settings():
            live_panel.publish({"html": '<div class="live-grid"><img src="/assets/test.png" onerror="alert(1)"><button>Control</button><iframe src="/api/state"></iframe></div>',
                "appearance":{"--panel-mob":"96px","--other":"url(/api/state)"},"api_key":"must-not-copy","width":1300})
            result=live_panel.snapshot()
            self.assertEqual(set(result),{'html','appearance','revision','width'})
            self.assertNotIn('onerror',result['html'])
            self.assertNotIn('<button',result['html'])
            self.assertNotIn('<iframe',result['html'])
            self.assertEqual(result['appearance'],{'--panel-mob':'96px'})
            self.assertEqual(result['width'],1300)
            first=result['revision']
            live_panel.publish({'html':'<div>Changed</div>'})
            self.assertNotEqual(live_panel.snapshot()['revision'],first)

    def test_invalid_width_does_not_replace_snapshot(self):
        with isolated_settings():
            live_panel.publish({'html':'<div>Keep</div>'})
            before=live_panel.snapshot()
            with self.assertRaises(ValueError):
                live_panel.publish({'html':'<div>Bad</div>','width':float('nan')})
            self.assertEqual(live_panel.snapshot(),before)

if __name__=='__main__':unittest.main()
''',encoding='utf-8')
