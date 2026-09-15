<#
.SYNOPSIS
    Automates the part of documentation/E2E_TEST_PLAN.md's pipeline that
    comes AFTER Spacer has produced a compiled ZEN: deploy it into a real
    Gothic II install, point the startup world at it, launch the game,
    and do a best-effort check of the engine's log for known problems.

    Spacer's "compile world" / "compile light" step itself has no known
    scripting interface (see E2E_TEST_PLAN.md's automation table) and is
    NOT covered here - this script starts from "I already have a
    compiled ZEN file on disk".

.DESCRIPTION
    NOT VERIFIED END TO END - written without a Gothic install or Spacer
    available to test against. Fill in the Config block below for your
    machine, then run with -WhatIf first.

.PARAMETER WhatIf
    Standard PowerShell dry-run switch - prints every action (copy, ini
    edit, launch) without performing it.

.EXAMPLE
    .\deploy_and_launch.ps1 -CompiledZenPath 'C:\dev\MyLevel_compiled.zen' -WhatIf
    .\deploy_and_launch.ps1 -CompiledZenPath 'C:\dev\MyLevel_compiled.zen'
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # The compiled ZEN produced by Spacer's File -> Save As (Phase 6 of
    # E2E_TEST_PLAN.md). Required.
    [Parameter(Mandatory = $true)]
    [string]$CompiledZenPath,

    # Any extra asset files/folders (new textures, meshes) the compiled
    # ZEN references that aren't already in the install - copied
    # alongside it. Optional.
    [string[]]$ExtraAssetPaths = @(),

    # Seconds to let the game run before checking its log. Adjust to
    # however long it takes your install to reach the loading screen.
    [int]$LogCheckDelaySeconds = 20
)

# ---------------------------------------------------------------------
# Config - EDIT THIS BLOCK for your machine. Nothing below this block
# should need changing per test run.
# ---------------------------------------------------------------------
$GothicInstallRoot = 'C:\Games\Gothic II'          # TODO: your install root
$GothicExeName      = 'Gothic2.exe'                 # TODO: or your loader's launcher exe (e.g. SystemPack's)
$WorldsDestFolder   = Join-Path $GothicInstallRoot '_work\Data\Worlds\MOD'   # TODO: match your mod folder
$IniPath            = Join-Path $GothicInstallRoot 'Gothic.ini'             # TODO: or SystemPack.ini/Union.ini - confirm which your loader reads
$LogPath            = Join-Path $GothicInstallRoot 'System.log'             # TODO: confirm your install's actual log filename/location once

# Known bad patterns to grep the log for - a first guess, not confirmed
# against a real install. Refine after seeing your own log output once.
$LogErrorPatterns = @(
    'ERROR',
    'not found',
    'missing',
    'FATAL'
)
# ---------------------------------------------------------------------

function Backup-Ini {
    param([string]$Path)
    $backup = "$Path.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    if ($PSCmdlet.ShouldProcess($Path, "Back up to $backup")) {
        Copy-Item -LiteralPath $Path -Destination $backup -Force
        Write-Host "Backed up $Path -> $backup"
    }
    return $backup
}

function Set-ZStartWorld {
    param(
        [string]$IniPath,
        [string]$WorldFileName
    )
    if (-not (Test-Path -LiteralPath $IniPath)) {
        throw "Ini file not found: $IniPath - confirm `$IniPath in the config block matches your loader (Gothic.ini / SystemPack.ini / Union.ini)."
    }

    $content = Get-Content -LiteralPath $IniPath -Raw
    # Targeted line replace, not a full ini-library round-trip - Gothic's
    # ini format doesn't reliably survive being reparsed and rewritten by
    # a generic ini library, so this only ever touches the ZSTART= line.
    $pattern = '(?im)^ZSTART\s*=.*$'
    $replacement = "ZSTART=$WorldFileName"

    if ($content -notmatch $pattern) {
        throw "No 'ZSTART=' line found under [INFO] in $IniPath - check the file by hand once; this script only edits an existing line, it won't add a new section."
    }

    $newContent = [regex]::Replace($content, $pattern, $replacement)

    if ($PSCmdlet.ShouldProcess($IniPath, "Set ZSTART=$WorldFileName")) {
        Set-Content -LiteralPath $IniPath -Value $newContent -NoNewline
        Write-Host "Set ZSTART=$WorldFileName in $IniPath"
    }
}

function Deploy-CompiledZen {
    param(
        [string]$CompiledZenPath,
        [string]$DestFolder,
        [string[]]$ExtraAssetPaths
    )
    if (-not (Test-Path -LiteralPath $CompiledZenPath)) {
        throw "Compiled ZEN not found: $CompiledZenPath"
    }
    if ($PSCmdlet.ShouldProcess($DestFolder, "Create destination folder")) {
        New-Item -ItemType Directory -Force -Path $DestFolder | Out-Null
    }
    if ($PSCmdlet.ShouldProcess($CompiledZenPath, "Copy to $DestFolder")) {
        Copy-Item -LiteralPath $CompiledZenPath -Destination $DestFolder -Force
    }
    foreach ($asset in $ExtraAssetPaths) {
        if (-not (Test-Path -LiteralPath $asset)) {
            Write-Warning "Extra asset path not found, skipping: $asset"
            continue
        }
        if ($PSCmdlet.ShouldProcess($asset, "Copy to $DestFolder")) {
            Copy-Item -LiteralPath $asset -Destination $DestFolder -Recurse -Force
        }
    }
    Write-Host "Deployed $(Split-Path -Leaf $CompiledZenPath) to $DestFolder"
}

function Start-GothicAndCheckLog {
    param(
        [string]$ExePath,
        [string]$LogPath,
        [int]$DelaySeconds,
        [string[]]$ErrorPatterns
    )
    if (-not (Test-Path -LiteralPath $ExePath)) {
        throw "Game executable not found: $ExePath - check `$GothicInstallRoot/`$GothicExeName in the config block."
    }

    if (-not $PSCmdlet.ShouldProcess($ExePath, 'Launch')) {
        return
    }

    # Line-count baseline, not byte-length - a byte offset from Get-Item
    # can't be sliced back out of a decoded string safely (multi-byte
    # encoding, CRLF normalization), but line counts round-trip cleanly.
    $logBaselineLineCount = 0
    if (Test-Path -LiteralPath $LogPath) {
        $logBaselineLineCount = @(Get-Content -LiteralPath $LogPath).Count
    }

    Write-Host "Launching $ExePath ..."
    $proc = Start-Process -FilePath $ExePath -PassThru

    Write-Host "Waiting $DelaySeconds s before checking the log (adjust -LogCheckDelaySeconds if your install needs longer to reach the loading screen)..."
    Start-Sleep -Seconds $DelaySeconds

    if (-not (Test-Path -LiteralPath $LogPath)) {
        Write-Warning "Log file not found at $LogPath - confirm `$LogPath in the config block matches your install's actual log filename/location, this varies by patch/loader."
        return
    }

    $allLines = @(Get-Content -LiteralPath $LogPath)
    $newLines = if ($allLines.Count -gt $logBaselineLineCount) {
        $allLines[$logBaselineLineCount..($allLines.Count - 1)]
    } else {
        @()
    }
    $newContent = $newLines -join "`n"

    $hits = @()
    foreach ($pattern in $ErrorPatterns) {
        if ($newContent -match $pattern) {
            $hits += $pattern
        }
    }

    if ($hits.Count -gt 0) {
        Write-Warning "Log contains possible error patterns since launch: $($hits -join ', ') - check $LogPath by hand (Phase 8/9 of E2E_TEST_PLAN.md)."
    } else {
        Write-Host "No known error patterns found in the log since launch - not a guarantee, just a first-pass smoke signal. Still do the manual checks in Phase 8/9."
    }

    Write-Host "Game process PID $($proc.Id) launched - proceed to Phase 9's manual in-game checklist."
}

# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
Backup-Ini -Path $IniPath | Out-Null
Deploy-CompiledZen -CompiledZenPath $CompiledZenPath -DestFolder $WorldsDestFolder -ExtraAssetPaths $ExtraAssetPaths
Set-ZStartWorld -IniPath $IniPath -WorldFileName (Split-Path -Leaf $CompiledZenPath)
Start-GothicAndCheckLog -ExePath (Join-Path $GothicInstallRoot $GothicExeName) -LogPath $LogPath -DelaySeconds $LogCheckDelaySeconds -ErrorPatterns $LogErrorPatterns
