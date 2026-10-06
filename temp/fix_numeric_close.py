from pathlib import Path
r=Path('TikTokMobForge')
p=r/'web/app.js';s=p.read_text(encoding='utf-8').replace("['fuse_seconds', 'Thời gian nổ TNT (giây)', 4, 0.1, 3600]", "['fuse_seconds', 'Thời gian nổ TNT (giây; 0 = nổ ngay)', 4, 0, 3600]").replace('class="reward-option" data-option="${key}" type="number" step="0.1"','class="reward-option" data-option="${key}" type="number" step="any"')
a='    $$(".reward-option", row).forEach(input => input.addEventListener("input", event => updateMapping(index, input.dataset.option, Number(event.target.value))));'
b='''    $$(".reward-option", row).forEach(input => {
      input.addEventListener("input", () => {
        // Empty and partially typed numbers are drafts, never Number('') == 0.
        if (input.value !== '' && Number.isFinite(input.valueAsNumber) && input.checkValidity())
          updateMapping(index, input.dataset.option, input.valueAsNumber);
      });
      input.addEventListener("blur", () => {
        if (input.value === '' || !Number.isFinite(input.valueAsNumber)) {
          const field = rewardOptionFields[mappings[index].target].find(([key]) => key === input.dataset.option);
          input.value = mappings[index][input.dataset.option] ?? field[2];
          scheduleAutoSave();
        }
      });
    });''';assert a in s;s=s.replace(a,b)
s=s.replace('    if (autoSaveReady && !document.body.classList.contains("detached-panel")', '    if (!window.desktopClosing && autoSaveReady && !document.body.classList.contains("detached-panel")')
p.write_text(s,encoding='utf-8')
p=r/'bridge/reward_options.py';s=p.read_text(encoding='utf-8').replace('"fuse_seconds": (4, 0.1, 3600)', '"fuse_seconds": (4, 0, 3600)');p.write_text(s,encoding='utf-8')
p=r/'src/main/java/vn/deadchan/tiktokmob/RewardOptions.java';s=p.read_text(encoding='utf-8').replace('number(payload, key, fallback, 0.1, 3600)', 'number(payload, key, fallback, key.equals("fuse_seconds") ? 0 : 0.1, 3600)');p.write_text(s,encoding='utf-8')
p=r/'Desktop/MainForm.cs';s=p.read_text(encoding='utf-8').replace('                    await browser.ExecuteScriptAsync("window.desktopSaveResult=', '                    await browser.ExecuteScriptAsync("window.desktopSaveResult=')
s=s.replace('}})();");','}})();").WaitAsync(TimeSpan.FromSeconds(2));',1)
a='''                        MessageBox.Show(this, "Chưa lưu được thay đổi. Hãy kiểm tra thông báo lưu trong ứng dụng.\\n" + result, "Chưa thể đóng");
                        closing = false;
                        return;'''
b='''                        if (MessageBox.Show(this, "Chưa lưu được thay đổi cuối cùng.\\n" + result +
                            "\\n\\nĐóng tool và bỏ các thay đổi chưa lưu? Chọn Không để tiếp tục chỉnh sửa.",
                            "Đóng tool", MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) != DialogResult.Yes) {
                            closing = false;
                            return;
                        }''';assert a in s;s=s.replace(a,b)
a='''                MessageBox.Show(this, "Không thể hoàn tất lưu trước khi đóng: " + error.Message, "Lỗi lưu");
                closing = false;
                return;''';b='''                if (MessageBox.Show(this, "Không thể hoàn tất lưu: " + error.Message + "\\n\\nVẫn đóng tool? Các thay đổi chưa lưu sẽ bị bỏ.",
                    "Đóng tool", MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) != DialogResult.Yes) {
                    closing = false;
                    return;
                }''';assert a in s;s=s.replace(a,b)
s=s.replace('            closeAllowed = true;', '''            try {
                if (browser.CoreWebView2 != null)
                    await browser.ExecuteScriptAsync("window.desktopClosing=true;window.onbeforeunload=null;").WaitAsync(TimeSpan.FromSeconds(2));
            } catch (Exception) { }
            closeAllowed = true;''')
p.write_text(s,encoding='utf-8')
