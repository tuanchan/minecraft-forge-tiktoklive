[CmdletBinding()]
param([string]$GuiStatePath)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
try {
    # Use the most recently saved GUI settings, including the installed desktop app.
    if (-not $GuiStatePath) {
        $candidates = @(
            (Join-Path $projectRoot 'GUI\gui_state.json'),
            (Join-Path $projectRoot 'artifacts\desktop\app\GUI\gui_state.json'),
            (Join-Path $env:LOCALAPPDATA 'Programs\TikTokMobForge\app\GUI\gui_state.json')
        )
        $stateFile = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
            ForEach-Object { Get-Item -LiteralPath $_ } |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
        if (-not $stateFile) { throw 'Chua co cai dat GUI. Hay chon thu muc Minecraft va luu trong GUI truoc.' }
        $GuiStatePath = $stateFile.FullName
    }
    $state = Get-Content -LiteralPath $GuiStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $minecraftRoot = [string]$state.minecraft_directory
    if ([string]::IsNullOrWhiteSpace($minecraftRoot) -or -not [IO.Path]::IsPathRooted($minecraftRoot)) {
        throw 'minecraft_directory trong cai dat GUI phai la duong dan day du.'
    }
    $minecraftRoot = [IO.Path]::GetFullPath($minecraftRoot)
    if (-not (Test-Path -LiteralPath $minecraftRoot -PathType Container)) { throw "Khong tim thay thu muc Minecraft: $minecraftRoot" }
    $modsRoot = Join-Path $minecraftRoot 'mods'
    Write-Host "Cai dat GUI: $GuiStatePath"
    Write-Host "Thu muc mod: $modsRoot"

    # Separate process: build_mod.ps1 uses exit and must not end this script.
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $projectRoot 'build_mod.ps1') -SkipTests
    if ($LASTEXITCODE -ne 0) { throw 'Build mod that bai. Chua thay doi mod Minecraft.' }
    $source = Join-Path $projectRoot 'release\tiktokmob-1.0.0.jar'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($source)
    try {
        if ($null -eq $archive.GetEntry('vn/deadchan/tiktokmob/TikTokMobMod.class')) { throw 'JAR thieu lop TikTokMobMod.' }
    } finally { $archive.Dispose() }

    New-Item -ItemType Directory -Path $modsRoot -Force | Out-Null
    $oldJars = @(Get-ChildItem -LiteralPath $modsRoot -File -Filter 'tiktokmob-*.jar')
    if ($oldJars.Count) {
        $backupRoot = Join-Path $projectRoot ('release\backups\deploy-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        foreach ($oldJar in $oldJars) { Copy-Item -LiteralPath $oldJar.FullName -Destination $backupRoot }
        Write-Host "Sao luu mod cu: $backupRoot"
    }
    $destination = Join-Path $modsRoot ([IO.Path]::GetFileName($source))
    Copy-Item -LiteralPath $source -Destination $destination -Force
    $expectedHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $expectedHash) { throw 'SHA256 mod da chep khong khop.' }
    foreach ($oldJar in $oldJars) {
        if ($oldJar.FullName -ne $destination) { Remove-Item -LiteralPath $oldJar.FullName }
    }
    Write-Host "Da cap nhat mod: $destination" -ForegroundColor Green
    Write-Host "SHA256: $expectedHash"
    Write-Host 'Khoi dong lai Minecraft de nap mod moi. Tao GUI moi bang pushlih.bat.'
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
