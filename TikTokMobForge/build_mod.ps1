[CmdletBinding()]
param([switch]$SkipTests)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$jdkPackageId = 'EclipseAdoptium.Temurin.25.JDK'

function Get-JavaVersionText {
    param([Parameter(Mandatory = $true)][string]$JavaExe)

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $JavaExe
    $startInfo.Arguments = '-version'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = [System.Diagnostics.Process]::Start($startInfo)
    $standardOutput = $process.StandardOutput.ReadToEnd()
    $standardError = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    return "$standardOutput$standardError"
}

function Test-Java25 {
    param([Parameter(Mandatory = $true)][string]$JavaHome)

    $javaExe = Join-Path $JavaHome 'bin\java.exe'
    if (-not (Test-Path -LiteralPath $javaExe -PathType Leaf)) {
        return $false
    }

    $versionText = Get-JavaVersionText -JavaExe $javaExe
    return $versionText -match '(?:java|openjdk) version "25(?:[\."-])'
}

function Find-Java25Home {
    $candidates = [System.Collections.Generic.List[string]]::new()

    foreach ($scope in 'Process', 'User', 'Machine') {
        $javaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', $scope)
        if ($javaHome) {
            $candidates.Add($javaHome)
        }
    }

    $javaCommand = Get-Command java.exe -ErrorAction SilentlyContinue
    if ($javaCommand) {
        $candidates.Add((Split-Path -Parent (Split-Path -Parent $javaCommand.Source)))
    }

    $searchRoots = @(
        (Join-Path $env:ProgramFiles 'Eclipse Adoptium'),
        (Join-Path $env:ProgramFiles 'Java'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Eclipse Adoptium')
    )

    foreach ($root in $searchRoots) {
        if (Test-Path -LiteralPath $root -PathType Container) {
            Get-ChildItem -LiteralPath $root -Directory -Filter 'jdk-25*' -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { $candidates.Add($_.FullName) }
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-Java25 -JavaHome $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

try {
    $javaHome = Find-Java25Home

    if (-not $javaHome) {
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) {
            throw 'Khong tim thay winget. Hay cai App Installer tu Microsoft Store roi chay lai BUILD_MOD.bat.'
        }

        Write-Host 'Chua co JDK 25. Dang tu dong cai Eclipse Temurin JDK 25...'
        & $winget.Source install --id $jdkPackageId --exact --source winget --silent --disable-interactivity --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "winget cai JDK 25 that bai (ma loi $LASTEXITCODE)."
        }

        $javaHome = Find-Java25Home
        if (-not $javaHome) {
            throw 'Da chay bo cai nhung khong tim thay JDK 25. Hay mo lai terminal va chay lai BUILD_MOD.bat.'
        }
    }

    $env:JAVA_HOME = $javaHome
    $env:Path = "$(Join-Path $javaHome 'bin');$env:Path"

    Write-Host "Dang dung JDK: $javaHome"
    Write-Host (Get-JavaVersionText -JavaExe (Join-Path $javaHome 'bin\java.exe'))

    Write-Host 'Dang build mod...'
    if ($SkipTests) {
        & (Join-Path $PSScriptRoot 'gradlew.bat') --no-daemon assemble
    } else {
        & (Join-Path $PSScriptRoot 'gradlew.bat') --no-daemon clean build
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle build that bai (ma loi $LASTEXITCODE)."
    }

    $builtJar = Join-Path $PSScriptRoot 'build\libs\tiktokmob-1.0.0.jar'
    if (-not (Test-Path -LiteralPath $builtJar -PathType Leaf)) {
        throw "Build xong nhung khong tim thay file: $builtJar"
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($builtJar)
    try {
        foreach ($entry in @('META-INF/mods.toml', 'pack.mcmeta',
            'assets/tiktokmob/lang/vi_vn.json', 'assets/tiktokmob/textures/gui/iconbaggift.png',
            'vn/deadchan/tiktokmob/TikTokMobMod.class', 'vn/deadchan/tiktokmob/SpecialRewards.class')) {
            if ($null -eq $archive.GetEntry($entry)) {
                throw "JAR khong hop le, thieu: $entry. Khong phat hanh ban build nay."
            }
        }
    } finally {
        $archive.Dispose()
    }

    $releaseDir = Join-Path $PSScriptRoot 'release'
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
    $releaseJar = Join-Path $releaseDir 'tiktokmob-1.0.0.jar'
    Copy-Item -LiteralPath $builtJar -Destination $releaseJar -Force

    Write-Host "Build thanh cong: $releaseJar" -ForegroundColor Green
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
