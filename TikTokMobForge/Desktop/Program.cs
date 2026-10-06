namespace TikTokMobForge.Desktop;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        if (args.Length == 2 && args[0] == "--pin-overlay" &&
            Uri.TryCreate(args[1], UriKind.Absolute, out var uri) && uri.IsLoopback && uri.Scheme == "http")
        {
            var overlay = new PinOverlayForm();
            overlay.Shown += async (_, _) =>
            {
                var profile = Path.Combine(Path.GetTempPath(), "TikTokMobForge-overlay-preview");
                var environment = await Microsoft.Web.WebView2.Core.CoreWebView2Environment.CreateAsync(null, profile);
                await overlay.InitializeAsync(environment, uri.GetLeftPart(UriPartial.Authority));
            };
            Application.Run(overlay);
            return;
        }
        Application.Run(new MainForm());
    }
}
