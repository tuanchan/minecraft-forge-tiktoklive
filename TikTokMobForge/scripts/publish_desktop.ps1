[CmdletBinding()]
param([switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$finalRoot = Join-Path $projectRoot 'artifacts\desktop'
$publishRoot = Join-Path $projectRoot ('artifacts\p-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
$appRoot = Join-Path $publishRoot 'app'
$pythonSource = Join-Path $projectRoot 'bridge\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonSource)) { throw 'Thieu bridge\.venv. Hay cai dependencies bridge truoc khi dong goi.' }
& $pythonSource (Join-Path $PSScriptRoot 'export_default_profile.py')
if ($LASTEXITCODE -ne 0) { throw 'Khong xuat duoc cau hinh mac dinh tu ban BAT.' }
# Public runtime data only; never package local config.json, .env or GUI state.
$runtimeFiles = @(
    'GUI\default_profile.json',
    'bridge\common_gifts.json',
    'tooltt\TikTokGiftDownloader_v2\TikTokGiftDownloader\main.py',
    'tooltt\TikTokGiftDownloader_v2\TikTokGiftDownloader\README.txt',
    'tooltt\TikTokGiftDownloader_v2\TikTokGiftDownloader\requirements.txt'
)
foreach ($relativePath in $runtimeFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relativePath) -PathType Leaf)) {
        throw "Thieu file runtime bat buoc: $relativePath"
    }
}
$commonGifts = Get-Content -LiteralPath (Join-Path $projectRoot 'bridge\common_gifts.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($commonGifts).Count -eq 0) { throw 'Danh sach common_gifts.json rong.' }
$inventoryRoot = Join-Path $projectRoot 'web\assets\minecraft-inventory'
$inventoryManifest = Join-Path $inventoryRoot 'manifest.json'
if (-not (Test-Path -LiteralPath $inventoryManifest)) { throw 'Thieu bo icon vat pham. Chay scripts/download_item_icons.py voi duong dan client JAR 26.2 truoc.' }
$inventory = Get-Content -LiteralPath $inventoryManifest -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($item in $inventory.items.PSObject.Properties) {
    if (-not (Test-Path -LiteralPath (Join-Path $inventoryRoot ($item.Name + '.png')))) { throw "Thieu icon vat pham: $($item.Name)" }
}

function Copy-Tree([string]$Source, [string]$Destination, [string[]]$ExcludeDirs = @(), [string[]]$ExcludeFiles = @()) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $copyArgs = @($Source, $Destination, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1')
    if ($ExcludeDirs.Count) { $copyArgs += '/XD'; $copyArgs += $ExcludeDirs }
    if ($ExcludeFiles.Count) { $copyArgs += '/XF'; $copyArgs += $ExcludeFiles }
    & robocopy.exe @copyArgs | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Khong copy duoc $Source (robocopy $LASTEXITCODE)" }
}

Write-Host 'Build Forge mod (khong chay test)...'
& (Join-Path $projectRoot 'build_mod.ps1') -SkipTests
if ($LASTEXITCODE -ne 0) { throw 'Build mod that bai.' }

Write-Host 'Publish WinForms self-contained win-x64...'
& $pythonSource (Join-Path $PSScriptRoot 'build_app_icon.py')
if ($LASTEXITCODE -ne 0) { throw 'Chuyen iconapp.png sang ICO that bai.' }
& dotnet publish (Join-Path $projectRoot 'Desktop\TikTokMobForge.Desktop.csproj') -c Release -r win-x64 --self-contained true -o $publishRoot
if ($LASTEXITCODE -ne 0) { throw 'Publish WinForms that bai.' }

Write-Host 'Dong goi backend va Python runtime...'
New-Item -ItemType Directory -Path $appRoot -Force | Out-Null
Copy-Tree (Join-Path $projectRoot 'web') (Join-Path $appRoot 'web') @('__pycache__') @('*.pyc')
foreach ($folder in @('GUI', 'bridge')) {
    $target = Join-Path $appRoot $folder
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Get-ChildItem -LiteralPath (Join-Path $projectRoot $folder) -File |
        Where-Object { $_.Extension -in @('.py', '.bat') -or $_.Name -eq 'requirements.txt' } |
        Copy-Item -Destination $target -Force
}
New-Item -ItemType Directory -Path (Join-Path $appRoot 'release') -Force | Out-Null
foreach ($relativePath in $runtimeFiles) {
    $destination = Join-Path $appRoot $relativePath
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $projectRoot $relativePath) -Destination $destination -Force
    $sourceHash = (Get-FileHash -LiteralPath (Join-Path $projectRoot $relativePath) -Algorithm SHA256).Hash
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $sourceHash) {
        throw "File runtime dong goi khong khop: $relativePath"
    }
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'release\tiktokmob-1.0.0.jar') -Destination (Join-Path $appRoot 'release') -Force

$pythonBase = (& $pythonSource -c 'import sys; print(sys.base_prefix)').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $pythonBase 'python.exe'))) { throw 'Khong xac dinh duoc Python runtime.' }
$pythonTarget = Join-Path $appRoot 'python'
New-Item -ItemType Directory -Path $pythonTarget -Force | Out-Null
Get-ChildItem -LiteralPath $pythonBase -File |
    Where-Object { $_.Extension -in @('.exe', '.dll') -or $_.Name -eq 'LICENSE.txt' } |
    Copy-Item -Destination $pythonTarget -Force
Copy-Tree (Join-Path $pythonBase 'DLLs') (Join-Path $pythonTarget 'DLLs')
Copy-Tree (Join-Path $pythonBase 'Lib') (Join-Path $pythonTarget 'Lib') @('site-packages', '__pycache__', 'test', 'tests', 'idlelib') @('*.pyc')
Copy-Tree (Join-Path $projectRoot 'bridge\.venv\Lib\site-packages') (Join-Path $pythonTarget 'Lib\site-packages') @('__pycache__', 'tests', 'elevenlabs') @('*.pyc')
# The pure-Python ElevenLabs SDK has filenames exceeding Windows installer path
# limits. Python's standard zipimport loads the unchanged package from this archive.
& $pythonSource (Join-Path $PSScriptRoot 'package_python_sdk.py') (Join-Path $projectRoot 'bridge\.venv\Lib\site-packages') (Join-Path $pythonTarget 'Lib\site-packages')
if ($LASTEXITCODE -ne 0) { throw 'Dong goi ElevenLabs SDK that bai.' }
# Ship the Tcl runtime for existing optional Tk-based utilities.
if (Test-Path -LiteralPath (Join-Path $pythonBase 'tcl')) { Copy-Tree (Join-Path $pythonBase 'tcl') (Join-Path $pythonTarget 'tcl') }
Copy-Item -LiteralPath (Join-Path $projectRoot 'Desktop\README.md') -Destination (Join-Path $publishRoot 'HUONG_DAN.md') -Force

if (-not $SkipInstaller) {
    $compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
    if (-not (Test-Path -LiteralPath $compiler)) { throw 'Can Inno Setup 6 de build file .iss. Co the dung -SkipInstaller de chi publish.' }
    $deps = Join-Path $projectRoot 'artifacts\dependencies'
    New-Item -ItemType Directory -Path $deps -Force | Out-Null
    $webviewSetup = Join-Path $deps 'MicrosoftEdgeWebview2Setup.exe'
    if (-not (Test-Path -LiteralPath $webviewSetup)) {
        Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $webviewSetup -UseBasicParsing
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $webviewSetup
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*') { throw 'Chu ky bo cai WebView2 khong hop le.' }
    & $compiler "/DPublishDir=$publishRoot" (Join-Path $projectRoot 'TikTokMobForge.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Build installer that bai.' }
}
$expectedParent = [IO.Path]::GetFullPath((Join-Path $projectRoot 'artifacts'))
foreach ($publishPath in @($publishRoot, $finalRoot)) {
    if ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($publishPath)) -ne $expectedParent) { throw 'Duong dan publish khong hop le.' }
}
if (Test-Path -LiteralPath $finalRoot) {
    $previousRoot = Join-Path $projectRoot ('artifacts\desktop-previous-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    # Both paths are explicit children of this project's artifacts directory.
    if ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($finalRoot)) -ne $expectedParent -or
        [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($previousRoot)) -ne $expectedParent) { throw 'Duong dan publish khong hop le.' }
    Move-Item -LiteralPath $finalRoot -Destination $previousRoot
}
Move-Item -LiteralPath $publishRoot -Destination $finalRoot
Write-Host "Hoan thanh: $finalRoot\TikTokMobForge.Desktop.exe" -ForegroundColor Green
Write-Host 'Mod: release\tiktokmob-1.0.0.jar'
if (-not $SkipInstaller) { Write-Host 'Installer: artifacts\installer (xem ten file trong ket qua Inno Setup)' }
exit 0
