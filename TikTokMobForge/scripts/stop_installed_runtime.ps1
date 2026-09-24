param([Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
try {
    $root = [IO.Path]::GetFullPath($InstallRoot)
    $desktop = Join-Path $root 'TikTokMobForge.Desktop.exe'
    $pythonExecutables = @(
        (Join-Path $root 'app\python\python.exe'),
        (Join-Path $root 'app\python\pythonw.exe')
    )
    # Let the form save settings before shutting down its background services.
    foreach ($entry in @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $desktop })) {
        $process = Get-Process -Id $entry.ProcessId -ErrorAction SilentlyContinue
        if ($null -eq $process) { continue }
        if (-not $process.CloseMainWindow()) { throw 'Close the TikTok Mob window and retry installation.' }
        if (-not $process.WaitForExit(15000)) { throw 'TikTok Mob is still saving. Close its window and retry.' }
    }
    # Match full executable paths; never stop other Python installations.
    foreach ($entry in @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -in $pythonExecutables })) {
        $process = Get-Process -Id $entry.ProcessId -ErrorAction SilentlyContinue
        if ($null -eq $process) { continue }
        if ($process.Path -notin $pythonExecutables) { continue }
        $process.Kill()
        if (-not $process.WaitForExit(10000)) { throw 'The installed Python runtime did not exit.' }
    }
    $remaining = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -in $pythonExecutables -or $_.ExecutablePath -eq $desktop })
    if ($remaining.Count) { throw 'TikTok Mob restarted during installation. Close it and retry.' }
    exit 0
} catch {
    Write-Error $_
    exit 1
}
