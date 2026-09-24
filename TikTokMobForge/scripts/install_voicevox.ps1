$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot 'runtime'
$downloadDir = Join-Path $runtimeRoot 'downloads'
$engineDir = Join-Path $runtimeRoot 'voicevox'
$installedMarker = Join-Path $engineDir '.installed-0.25.2'
$archive = Join-Path $downloadDir 'voicevox_engine-windows-cpu-0.25.2.7z.001'
$expectedHash = '2ab86e4bf29448e3317ee97327efb3211c4ecc1063b03a62ab72b15a92ec531d'
$downloadUrl = 'https://github.com/VOICEVOX/voicevox_engine/releases/download/0.25.2/voicevox_engine-windows-cpu-0.25.2.7z.001'
New-Item -ItemType Directory -Force -Path $downloadDir, $engineDir | Out-Null
if (-not (Test-Path -LiteralPath $archive) -or (Get-Item -LiteralPath $archive).Length -lt 1802304190) {
    Write-Host 'Downloading official VOICEVOX CPU 0.25.2 (1.8 GB)...'
    & curl.exe -L --fail --retry 3 -C - -o $archive $downloadUrl
    if ($LASTEXITCODE -ne 0) { throw 'Download failed. Run this script again to resume.' }
}
Write-Host 'Verifying SHA-256...'
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw "Archive checksum mismatch: $archive. Move the corrupt archive aside and retry."
}
if (-not (Test-Path -LiteralPath $installedMarker) -or -not (Get-ChildItem -LiteralPath $engineDir -Filter run.exe -File -Recurse | Select-Object -First 1)) {
    Write-Host 'Extracting portable engine...'
    $sevenZip = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
    if (Test-Path -LiteralPath $sevenZip) {
        & $sevenZip x -y -bsp0 -mmt=1 "-o$engineDir" $archive
    } else {
        & tar.exe -xf $archive -C $engineDir
    }
    if ($LASTEXITCODE -ne 0) { throw 'Extraction failed. The downloaded archive is retained for retry.' }
}
$engine = Get-ChildItem -LiteralPath $engineDir -Filter run.exe -File -Recurse | Select-Object -First 1
if (-not $engine) { throw 'Could not find run.exe in extracted package.' }
Set-Content -LiteralPath $installedMarker -Value $expectedHash -Encoding ASCII
Write-Host "VOICEVOX installed: $($engine.FullName)"
Write-Host 'The bridge will start the engine automatically when needed.'
