using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using System.Text.Json;

namespace TikTokMobForge.Desktop;

// Off-screen HTML renderer only. Minecraft draws the resulting texture in world space.
public sealed class PinOverlayForm : Form
{
    private readonly WebView2 view = new() { Dock = DockStyle.Fill, DefaultBackgroundColor = Color.Transparent };
    private readonly string frameRoot = Environment.GetEnvironmentVariable("PIN_BOARD_FRAME_ROOT") ??
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TikTokMobForge", "pinned-board");
    private bool capturing;
    protected override bool ShowWithoutActivation => true;
    protected override CreateParams CreateParams
    {
        get { var cp = base.CreateParams; cp.ExStyle |= 0x08000000 | 0x80; return cp; }
    }

    public PinOverlayForm()
    {
        FormBorderStyle = FormBorderStyle.None;
        ShowInTaskbar = false;
        StartPosition = FormStartPosition.Manual;
        Location = new Point(-30000, -30000);
        ClientSize = new Size(2600, 1400);
        Controls.Add(view);
    }

    public async Task InitializeAsync(CoreWebView2Environment environment, string origin)
    {
        _ = Handle;
        await view.EnsureCoreWebView2Async(environment);
        view.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
        view.CoreWebView2.Settings.IsStatusBarEnabled = false;
        view.CoreWebView2.NavigationStarting += (_, e) =>
            e.Cancel = !e.Uri.StartsWith(origin + "/", StringComparison.OrdinalIgnoreCase);
        view.CoreWebView2.WebMessageReceived += async (_, e) =>
        {
            if (!e.Source.StartsWith(origin + "/", StringComparison.OrdinalIgnoreCase) || capturing) return;
            try
            {
                using var message = JsonDocument.Parse(e.WebMessageAsJson);
                var data = message.RootElement;
                if (!data.TryGetProperty("type", out var type) || type.GetString() != "frame") return;
                var token = data.GetProperty("token").GetString() ?? "";
                if (!System.Text.RegularExpressions.Regex.IsMatch(token, "^[a-f0-9]{32}$")) return;
                var width = data.GetProperty("width").GetDouble();
                var height = data.GetProperty("height").GetDouble();
                if (!double.IsFinite(width) || !double.IsFinite(height) || width < 1 || height < 1 || width > 2600 || height > 1400) return;
                int revision = data.GetProperty("revision").GetInt32();
                if (data.TryGetProperty("preserveExisting", out var preserve) && preserve.ValueKind == JsonValueKind.True) {
                    var savedManifest = Path.Combine(frameRoot, token + ".json");
                    if (File.Exists(savedManifest)) {
                        using var saved = JsonDocument.Parse(await File.ReadAllTextAsync(savedManifest));
                        var savedFile = saved.RootElement.GetProperty("file").GetString() ?? "";
                        if (System.Text.RegularExpressions.Regex.IsMatch(savedFile, "^[a-f0-9]{32}\\.png$") && File.Exists(Path.Combine(frameRoot, savedFile))) {
                            await view.ExecuteScriptAsync($"window.capturedFrame={revision}");
                            return;
                        }
                    }
                }
                capturing = true;
                var scale = Math.Min(2.0, 4096.0 / Math.Max(width, height));
                var response = await view.CoreWebView2.CallDevToolsProtocolMethodAsync("Page.captureScreenshot",
                    JsonSerializer.Serialize(new { format = "png", captureBeyondViewport = true,
                        clip = new { x = 0, y = 0, width, height, scale } }));
                using var capture = JsonDocument.Parse(response);
                var png = Convert.FromBase64String(capture.RootElement.GetProperty("data").GetString()!);
                Directory.CreateDirectory(frameRoot);
                var filename = Guid.NewGuid().ToString("N") + ".png";
                await File.WriteAllBytesAsync(Path.Combine(frameRoot, filename), png);
                // PNG IHDR dimensions are authoritative, including Chromium's scaling rounding.
                int pixelWidth = System.Buffers.Binary.BinaryPrimitives.ReadInt32BigEndian(png.AsSpan(16, 4));
                int pixelHeight = System.Buffers.Binary.BinaryPrimitives.ReadInt32BigEndian(png.AsSpan(20, 4));
                var manifest = JsonSerializer.Serialize(new { token, file = filename, width = pixelWidth, height = pixelHeight });
                var temp = Path.Combine(frameRoot, Guid.NewGuid().ToString("N") + ".json");
                await File.WriteAllTextAsync(temp, manifest);
                File.Move(temp, Path.Combine(frameRoot, "frame.json"), true);
                // Index every board separately; capturing a new comment must not evict an older one.
                var tokenManifest = Path.Combine(frameRoot, token + ".json");
                string? oldFile = null;
                if (File.Exists(tokenManifest)) {
                    try {
                        using var previous = JsonDocument.Parse(await File.ReadAllTextAsync(tokenManifest));
                        oldFile = previous.RootElement.GetProperty("file").GetString();
                    } catch (Exception) { }
                }
                var tokenTemp = Path.Combine(frameRoot, Guid.NewGuid().ToString("N") + ".json");
                await File.WriteAllTextAsync(tokenTemp, manifest);
                File.Move(tokenTemp, tokenManifest, true);
                if (oldFile != null && oldFile != filename && System.Text.RegularExpressions.Regex.IsMatch(oldFile, "^[a-f0-9]{32}\\.png$")) {
                    try { File.Delete(Path.Combine(frameRoot, oldFile)); } catch (IOException) { }
                }
                await view.ExecuteScriptAsync($"window.capturedFrame={revision}");
            }
            catch (Exception error)
            {
                System.Diagnostics.Trace.WriteLine("WebView 3D board capture: " + error.Message);
            }
            finally { capturing = false; }
        };
        // A shown, off-screen host keeps Chromium compositing without placing a window over the game.
        if (!Visible) Show();
        view.CoreWebView2.Navigate(origin + "/pinned-overlay.html?texture=1");
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) view.Dispose();
        base.Dispose(disposing);
    }
}
