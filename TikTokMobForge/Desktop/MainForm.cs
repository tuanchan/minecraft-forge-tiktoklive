using System.Diagnostics;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace TikTokMobForge.Desktop;

public sealed class MainForm : Form
{
    private readonly WebView2 browser = new() { Dock = DockStyle.Fill, DefaultBackgroundColor = Color.White };
    private readonly Label status = new() { Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleCenter, Text = "Đang mở bảng điều khiển…", ForeColor = Color.Black, BackColor = Color.White };
    private readonly CancellationTokenSource lifetime = new();
    private bool copyingPanel;
    private string? endpointFile;
    private string? appOrigin;
    private bool closing;
    private bool closeAllowed;

    public MainForm()
    {
        Text = "TikTok Mob Forge";
        ShowIcon = true;
        Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        FormBorderStyle = FormBorderStyle.Sizable;
        BackColor = Color.White;
        Padding = Padding.Empty;
        MinimumSize = new Size(1024, 700);
        Size = new Size(1380, 900);
        StartPosition = FormStartPosition.CenterScreen;
        Controls.Add(browser);
        Controls.Add(status);
        Shown += async (_, _) => await StartAsync();
        FormClosing += async (_, e) =>
        {
            if (closeAllowed) return;
            e.Cancel = true;
            if (closing) return;
            closing = true;
            try
            {
                if (browser.CoreWebView2 != null)
                {
                    // Flush pending autosave before destroying the WebView.
                    await browser.ExecuteScriptAsync("window.desktopSaveResult='pending';(async()=>{try{if(typeof autoSaveReady!=='undefined'&&autoSaveReady) await save(false);window.desktopSaveResult='ok';}catch(e){window.desktopSaveResult=String(e.message||e);}})();");
                    string result = "\"pending\"";
                    var deadline = DateTime.UtcNow.AddSeconds(8);
                    while (result == "\"pending\"" && DateTime.UtcNow < deadline)
                    {
                        await Task.Delay(100);
                        result = await browser.ExecuteScriptAsync("window.desktopSaveResult").WaitAsync(TimeSpan.FromSeconds(2));
                    }
                    if (result != "\"ok\"")
                    {
                        MessageBox.Show(this, "Chưa lưu được thay đổi. Hãy kiểm tra thông báo lưu trong ứng dụng.\n" + result, "Chưa thể đóng");
                        closing = false;
                        return;
                    }
                }
            }
            catch (Exception error)
            {
                MessageBox.Show(this, "Không thể hoàn tất lưu trước khi đóng: " + error.Message, "Lỗi lưu");
                closing = false;
                return;
            }
            closeAllowed = true;
            lifetime.Cancel();
            Close();
        };
        FormClosed += (_, _) => { lifetime.Cancel(); browser.Dispose(); if (endpointFile != null) { try { File.Delete(endpointFile); } catch (IOException) { } } };
    }

    private static string FindProject()
    {
        string? packagedRoot = null;
        for (var directory = new DirectoryInfo(AppContext.BaseDirectory); directory != null; directory = directory.Parent)
        {
            if (File.Exists(Path.Combine(directory.FullName, "web", "main.py"))) return directory.FullName;
            var packaged = Path.Combine(directory.FullName, "app");
            if (packagedRoot == null && File.Exists(Path.Combine(packaged, "web", "main.py"))) packagedRoot = packaged;
        }
        if (packagedRoot != null) return packagedRoot;
        throw new DirectoryNotFoundException("Không tìm thấy thư mục app/web của TikTokMobForge.");
    }

    private async Task StartAsync()
    {
        try
        {
            var root = FindProject();
            var python = new[] { Path.Combine(root, "bridge", ".venv", "Scripts", "pythonw.exe"), Path.Combine(root, "python", "pythonw.exe") }.FirstOrDefault(File.Exists)
                ?? throw new FileNotFoundException("Thiếu Python đi kèm. Hãy chạy pushlih.bat để tạo bản đầy đủ.");
            endpointFile = Path.Combine(Path.GetTempPath(), $"tiktokmob-{Guid.NewGuid():N}.url");
            var start = new ProcessStartInfo(python) { WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true };
            start.Environment["PYTHONUTF8"] = "1";
            start.ArgumentList.Add(Path.Combine(root, "web", "launch_gui.py"));
            start.ArgumentList.Add("--desktop");
            start.ArgumentList.Add("--url-file");
            start.ArgumentList.Add(endpointFile);
            using var backend = Process.Start(start) ?? throw new IOException("Không khởi động được dịch vụ GUI.");
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token);
            timeout.CancelAfter(TimeSpan.FromSeconds(60));
            while (!File.Exists(endpointFile))
            {
                if (backend.HasExited && backend.ExitCode != 0) throw new IOException("Dịch vụ GUI không khởi động được. Xem GUI/logs/gui_startup.log.");
                await Task.Delay(200, timeout.Token);
            }
            var url = (await File.ReadAllTextAsync(endpointFile, timeout.Token)).Trim();
            if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) || !uri.IsLoopback || uri.Scheme != "http") throw new IOException("Địa chỉ GUI không hợp lệ.");
            appOrigin = uri.GetLeftPart(UriPartial.Authority);
            var profile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TikTokMobForge", "WebView2");
            var environment = await CoreWebView2Environment.CreateAsync(null, profile);
            await browser.EnsureCoreWebView2Async(environment);
            AttachClipboard(browser);
            browser.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            browser.CoreWebView2.Settings.IsStatusBarEnabled = false;
            browser.CoreWebView2.Settings.AreDevToolsEnabled = false;
            browser.CoreWebView2.NavigationStarting += (_, e) =>
            {
                if (e.Uri.StartsWith(appOrigin + "/", StringComparison.OrdinalIgnoreCase)) return;
                e.Cancel = true;
                OpenExternal(e.Uri);
            };
            browser.CoreWebView2.NewWindowRequested += (_, e) =>
            {
                e.Handled = true;
                if (e.Uri.StartsWith(appOrigin + "/", StringComparison.OrdinalIgnoreCase))
                {
                    var panel = new Form { Text = "Panel tương tác", Icon = Icon, Size = new Size(1100, 650), StartPosition = FormStartPosition.CenterParent };
                    var view = new WebView2 { Dock = DockStyle.Fill, CreationProperties = new CoreWebView2CreationProperties { UserDataFolder = profile }, Source = new Uri(e.Uri) };
                    panel.Controls.Add(view);
                    panel.FormClosed += (_, _) => view.Dispose();
                    panel.Shown += async (_, _) =>
                    {
                        try { await view.EnsureCoreWebView2Async(environment); AttachClipboard(view); }
                        catch (Exception error) { MessageBox.Show(panel, error.Message, "Không mở được panel"); }
                    };
                    panel.Show(this);
                }
                else OpenExternal(e.Uri);
            };
            browser.CoreWebView2.Navigate(url + "?view=events&desktop=1");
            status.Visible = false;
        }
        catch (Exception error) when (!lifetime.IsCancellationRequested)
        {
            status.Text = "Không mở được GUI.\n" + error.Message + "\n\nCần Microsoft Edge WebView2 Runtime để hiển thị giao diện.";
        }
        catch (OperationCanceledException) { }
    }

    private void AttachClipboard(WebView2 view)
    {
        view.CoreWebView2.WebMessageReceived += async (_, args) =>
        {
            if (appOrigin == null || !args.Source.StartsWith(appOrigin + "/", StringComparison.OrdinalIgnoreCase)) return;
            if (args.WebMessageAsJson == "\"copy-panel\"") await CopyPanelAsync(view);
        };
    }

    private async Task CopyPanelAsync(WebView2 view)
    {
        if (copyingPanel || view.CoreWebView2 == null) return;
        copyingPanel = true;
        try
        {
            // Use Chromium's renderer to capture the entire panel, including rows
            // outside the viewport. No screenshot of the title bar or desktop.
            const string prepare = """
                (async () => {
                    if (typeof state === 'undefined' || !state) throw new Error('GUI chưa tải xong');
                    showTab('live');
                    const panel = document.querySelector('.minecraft-stage .live-grid');
                    document.body.classList.add('copying-panel');
                    window.panelCaptureControls = [...panel.querySelectorAll('button, .link, [data-go]')].map(node => ({node, style:node.getAttribute('style')}));
                    window.panelCaptureControls.forEach(({node}) => node.style.setProperty('display','none','important'));
                    await Promise.all([...panel.querySelectorAll('img')].map(img => img.decode().catch(() => {})));
                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                    const r = panel.getBoundingClientRect();
                    return {x:r.left+scrollX,y:r.top+scrollY,width:r.width,height:r.height,scale:2};
                })()
                """;
            var response = await view.CoreWebView2.CallDevToolsProtocolMethodAsync("Runtime.evaluate",
                JsonSerializer.Serialize(new { expression = prepare, awaitPromise = true, returnByValue = true })).WaitAsync(TimeSpan.FromSeconds(20));
            using var result = JsonDocument.Parse(response);
            if (result.RootElement.TryGetProperty("exceptionDetails", out _)) throw new IOException("Không lấy được panel. Hãy đợi giao diện tải xong rồi thử lại.");
            var clip = result.RootElement.GetProperty("result").GetProperty("value");
            var capture = await view.CoreWebView2.CallDevToolsProtocolMethodAsync("Page.captureScreenshot",
                JsonSerializer.Serialize(new { format = "png", captureBeyondViewport = true, fromSurface = true, clip })).WaitAsync(TimeSpan.FromSeconds(20));
            using var screenshot = JsonDocument.Parse(capture);
            using var stream = new MemoryStream(Convert.FromBase64String(screenshot.RootElement.GetProperty("data").GetString()!));
            using var bitmap = new Bitmap(stream);
            using var clipboardImage = new Bitmap(bitmap);
            var data = new DataObject();
            data.SetData(DataFormats.Bitmap, clipboardImage);
            Clipboard.SetDataObject(data, true, 5, 100);
            await view.ExecuteScriptAsync("toast('Đã sao chép ảnh panel. Nhấn Ctrl+V để dán.');");
        }
        catch (Exception error)
        {
            MessageBox.Show(this, "Không sao chép được ảnh panel: " + error.Message, "Sao chép ảnh");
        }
        finally
        {
            try
            {
                if (!view.IsDisposed && view.CoreWebView2 != null)
                    await view.ExecuteScriptAsync("document.body.classList.remove('copying-panel');(window.panelCaptureControls||[]).forEach(({node,style})=>{if(style===null)node.removeAttribute('style');else node.setAttribute('style',style);});delete window.panelCaptureControls;");
            }
            catch (Exception) { /* Window may have closed while capturing. */ }
            copyingPanel = false;
        }
    }

    private static void OpenExternal(string url)
    {
        if (Uri.TryCreate(url, UriKind.Absolute, out var uri) && uri.Scheme is "https" or "http")
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    }

}
