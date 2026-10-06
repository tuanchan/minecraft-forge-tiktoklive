from pathlib import Path
p=Path('TikTokMobForge/src/main/java/vn/deadchan/tiktokmob/ServerPinnedCommentBoard.java');s=p.read_text(encoding='utf-8').replace('if (existing.level != player.level()) { freeze', 'if (existing.display.isRemoved() || existing.level != player.level()) { freeze');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/web/pinned-overlay.js');s=p.read_text(encoding='utf-8').replace("const message = {type:'frame', token:wanted.token, revision:++frameRevision, width:rect.width, height:rect.height};", "const message = {type:'frame', token:wanted.token, revision:++frameRevision, width:rect.width, height:rect.height, preserveExisting:wanted.token !== data.token};");p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/Desktop/PinOverlayForm.cs');s=p.read_text(encoding='utf-8').replace('                capturing = true;','''                if (data.TryGetProperty("preserveExisting", out var preserve) && preserve.ValueKind == JsonValueKind.True) {
                    var savedManifest = Path.Combine(frameRoot, token + ".json");
                    if (File.Exists(savedManifest)) {
                        using var saved = JsonDocument.Parse(await File.ReadAllTextAsync(savedManifest));
                        var savedFile = saved.RootElement.GetProperty("file").GetString() ?? "";
                        if (System.Text.RegularExpressions.Regex.IsMatch(savedFile, "^[a-f0-9]{32}\\\\.png$") && File.Exists(Path.Combine(frameRoot, savedFile))) {
                            await view.ExecuteScriptAsync($"window.capturedFrame={revision}");
                            return;
                        }
                    }
                }
                capturing = true;''');p.write_text(s,encoding='utf-8')
