# ============================================================
#  cleanup.ps1 - Safe project cleanup for MokTradeDesk
#  Stages:
#    1 = safe files (caches, build output, backups, stray files)
#    2 = large files  (.venv, backend/node_modules, stray Node project)
#    3 = caution      (nested backend/.git - only if it has no commits)
#
#  Usage:
#    powershell -NoProfile -ExecutionPolicy Bypass -File cleanup.ps1 -Stage 1
#    powershell -NoProfile -ExecutionPolicy Bypass -File cleanup.ps1 -Stage all -DryRun
#    ... -Yes   (auto-confirm, skip Read-Host)
# ============================================================
[CmdletBinding()]
param(
    [ValidateSet('1','2','3','all')]
    [string]$Stage = '1',
    [switch]$DryRun,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
$Root = $Root.TrimEnd('\')
Write-Host "Root: $Root" -ForegroundColor White
if ($DryRun) { Write-Host "MODE: DRY RUN (nothing will be deleted)" -ForegroundColor Yellow }

$script:Deleted = New-Object System.Collections.ArrayList
$script:Kept    = New-Object System.Collections.ArrayList
$script:Failed  = New-Object System.Collections.ArrayList

function Get-PathSize([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return 0 }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer) {
        $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
                Measure-Object -Property Length -Sum).Sum
        if ($null -eq $sum) { return 0 }
        return [double]$sum
    }
    return [double]$item.Length
}

function Format-Size([double]$Bytes) {
    if ($Bytes -ge 1GB) { return ('{0:N1} GB' -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ('{0:N1} MB' -f ($Bytes / 1MB)) }
    if ($Bytes -ge 1KB) { return ('{0:N1} KB' -f ($Bytes / 1KB)) }
    return ('{0} B' -f [int]$Bytes)
}

function Remove-SafeItem([string]$Path, [string]$Reason = '') {
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Host ("   - skip (missing): {0}" -f (Split-Path $Path -Leaf)) -ForegroundColor DarkGray
        return
    }
    $full = (Get-Item -LiteralPath $Path -Force).FullName
    $rel  = $full.Substring($Root.Length).TrimStart('\')

    # Guard 1: never delete the project root
    if ($full.TrimEnd('\') -eq $Root) {
        Write-Host "   ! REFUSED: attempted to delete project root" -ForegroundColor Red
        return
    }
    # Guard 2: must stay inside the project
    if (-not $full.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Host ("   ! REFUSED (outside project): {0}" -f $full) -ForegroundColor Red
        return
    }

    $size = Get-PathSize $full
    if ($DryRun) {
        Write-Host ("   [dry-run] would delete: {0} ({1})" -f $rel, (Format-Size $size)) -ForegroundColor Yellow
        [void]$script:Deleted.Add([pscustomobject]@{ Path = $rel; Size = $size; Action = 'DryRun'; Reason = $Reason })
        return
    }
    try {
        Remove-Item -LiteralPath $full -Recurse -Force
        Write-Host ("   [OK] deleted: {0} ({1})" -f $rel, (Format-Size $size)) -ForegroundColor Green
        [void]$script:Deleted.Add([pscustomobject]@{ Path = $rel; Size = $size; Action = 'Deleted'; Reason = $Reason })
    } catch {
        Write-Host ("   [ERR] {0}: {1}" -f $rel, $_.Exception.Message) -ForegroundColor Red
        [void]$script:Failed.Add([pscustomobject]@{ Path = $rel; Error = $_.Exception.Message })
    }
}

function Confirm-Stage([string]$Title, [string]$Detail) {
    Write-Host ""
    Write-Host ("=== {0} ===" -f $Title) -ForegroundColor Cyan
    Write-Host $Detail -ForegroundColor Gray
    if ($DryRun) { return $true }
    if ($Yes)    { Write-Host "   (auto-confirmed via -Yes)" -ForegroundColor DarkGray; return $true }
    $ans = Read-Host "Proceed? (y/n)"
    return ($ans -match '^(y|yes)$')
}

function Invoke-Stage1 {
    $detail = "Delete: backend/.coverage, frontend/dist, frontend/temp_build*.log, __pycache__ dirs, " +
              "3 DB backups, backend/logs (if empty), 36 .pre*/.bak files, cmd.exe, storage/ (if empty), launch.py (if empty)"
    if (-not (Confirm-Stage "STAGE 1 - safe files" $detail)) { return }

    Remove-SafeItem (Join-Path $Root 'backend\.coverage')          'pytest-cov output'
    Remove-SafeItem (Join-Path $Root 'frontend\dist')              'build output'
    Remove-SafeItem (Join-Path $Root 'frontend\temp_build.log')    'temp build log'
    Remove-SafeItem (Join-Path $Root 'frontend\temp_build_err.log')'temp build log'

    # __pycache__ under backend, excluding venv/.venv/node_modules
    Get-ChildItem -LiteralPath (Join-Path $Root 'backend') -Recurse -Force -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notlike '*\venv\*' -and
            $_.FullName -notlike '*\.venv\*' -and
            $_.FullName -notlike '*\node_modules\*'
        } | ForEach-Object { Remove-SafeItem $_.FullName 'python cache' }

    # frontend/src backup files (.pre61, .pre7, .pre71, .pre8, .bak)
    Get-ChildItem -LiteralPath (Join-Path $Root 'frontend\src') -Recurse -Force -File -ErrorAction SilentlyContinue |
        Where-Object {
            $n = $_.Name
            $n -like '*.pre61' -or $n -like '*.pre7' -or $n -like '*.pre71' -or $n -like '*.pre8' -or $n -like '*.bak'
        } | ForEach-Object { Remove-SafeItem $_.FullName 'code backup' }

    # DB backups (never touch trading_desk.db)
    Get-ChildItem -LiteralPath (Join-Path $Root 'backend') -Force -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -ne 'trading_desk.db' -and
            ($_.Name -like 'trading_desk.db.backup*' -or $_.Name -like 'trading_desk.backup*')
        } | ForEach-Object { Remove-SafeItem $_.FullName 'database backup' }

    # backend/logs only if empty
    $logs = Join-Path $Root 'backend\logs'
    if (Test-Path -LiteralPath $logs) {
        $logFiles = Get-ChildItem -LiteralPath $logs -Recurse -Force -File -ErrorAction SilentlyContinue
        if (-not $logFiles) { Remove-SafeItem $logs 'empty logs dir' }
        else { [void]$script:Kept.Add('backend\logs (not empty)'); Write-Host "   - kept: backend\logs (not empty)" -ForegroundColor DarkYellow }
    }

    # cmd.exe at root only if not referenced by source
    $cmd = Join-Path $Root 'cmd.exe'
    if (Test-Path -LiteralPath $cmd) {
        $srcRoots = @((Join-Path $Root 'frontend\src'), (Join-Path $Root 'backend\app'))
        $refs = Get-ChildItem -LiteralPath $srcRoots -Recurse -File -ErrorAction SilentlyContinue |
                Select-String -Pattern 'cmd\.exe' -SimpleMatch -ErrorAction SilentlyContinue
        if ($refs) {
            [void]$script:Kept.Add('cmd.exe (referenced in source)')
            Write-Host "   - kept: cmd.exe (referenced in source)" -ForegroundColor DarkYellow
        } else {
            Remove-SafeItem $cmd 'foreign executable at project root'
        }
    }

    # root storage/ only if it has no files
    $stor = Join-Path $Root 'storage'
    if (Test-Path -LiteralPath $stor) {
        $storFiles = Get-ChildItem -LiteralPath $stor -Recurse -Force -File -ErrorAction SilentlyContinue
        if (-not $storFiles) { Remove-SafeItem $stor 'empty storage dir' }
        else { [void]$script:Kept.Add('storage\ (has files)'); Write-Host "   - kept: storage\ (has files)" -ForegroundColor DarkYellow }
    }

    # launch.py only if empty
    $launch = Join-Path $Root 'launch.py'
    if (Test-Path -LiteralPath $launch) {
        if ((Get-Item -LiteralPath $launch -Force).Length -eq 0) {
            Remove-SafeItem $launch 'empty file'
        } else {
            [void]$script:Kept.Add('launch.py (has content)')
            Write-Host "   - kept: launch.py (has content)" -ForegroundColor DarkYellow
        }
    }
}

function Invoke-Stage2 {
    $detail = "Delete: backend/.venv (~185MB), backend/node_modules (~50MB), backend/package.json, backend/pnpm-lock.yaml"
    if (-not (Confirm-Stage "STAGE 2 - large files" $detail)) { return }

    Remove-SafeItem (Join-Path $Root 'backend\.venv')          'redundant venv'
    Remove-SafeItem (Join-Path $Root 'backend\node_modules')   'stray node_modules'
    Remove-SafeItem (Join-Path $Root 'backend\package.json')   'stray node project'
    Remove-SafeItem (Join-Path $Root 'backend\pnpm-lock.yaml') 'stray lockfile'
}

function Invoke-Stage3 {
    $detail = "Delete: backend/.git (nested repo) - ONLY if it has zero commits"
    if (-not (Confirm-Stage "STAGE 3 - caution" $detail)) { return }

    $gitDir  = Join-Path $Root 'backend\.git'
    $backDir = Join-Path $Root 'backend'
    if (-not (Test-Path -LiteralPath $gitDir)) {
        Write-Host "   - backend/.git not present" -ForegroundColor DarkGray
        return
    }
    $count = -1
    try {
        $out = & git -C $backDir rev-list --all --count 2>$null
        if ($out) { $count = [int]$out }
    } catch { $count = -1 }

    if ($count -eq 0) {
        Remove-SafeItem $gitDir 'nested repo with no commits'
    } elseif ($count -gt 0) {
        [void]$script:Kept.Add("backend\.git (has $count commits)")
        Write-Host ("   - kept: backend/.git has {0} commits" -f $count) -ForegroundColor DarkYellow
    } else {
        [void]$script:Kept.Add('backend\.git (commit count unknown)')
        Write-Host "   - kept: backend/.git (commit count could not be determined)" -ForegroundColor DarkYellow
    }
}

# ── dispatch ──
switch ($Stage) {
    '1'   { Invoke-Stage1 }
    '2'   { Invoke-Stage2 }
    '3'   { Invoke-Stage3 }
    'all' { Invoke-Stage1; Invoke-Stage2; Invoke-Stage3 }
}

# ── summary ──
Write-Host ""
Write-Host "===== SUMMARY =====" -ForegroundColor Cyan
$deletedItems = @($script:Deleted | Where-Object { $_.Action -eq 'Deleted' })
$totalFreed = 0.0
if ($deletedItems.Count -gt 0) {
    $totalFreed = ($deletedItems | Measure-Object -Property Size -Sum).Sum
}
Write-Host ("Items processed : {0}" -f $script:Deleted.Count)
Write-Host ("Deleted         : {0} ({1})" -f $deletedItems.Count, (Format-Size ([double]$totalFreed)))
Write-Host ("Kept            : {0}" -f $script:Kept.Count)
Write-Host ("Errors          : {0}" -f $script:Failed.Count)

if ($script:Failed.Count -gt 0) {
    Write-Host "Failed items:" -ForegroundColor Red
    $script:Failed | ForEach-Object { Write-Host ("  - {0} : {1}" -f $_.Path, $_.Error) -ForegroundColor Red }
}

# ── log (to TEMP, keeps the repo clean) ──
$logPath = Join-Path $env:TEMP ("moktrade_cleanup_stage{0}{1}.log" -f $Stage, $(if ($DryRun) { '_dry' } else { '' }))
$lines = New-Object System.Collections.ArrayList
[void]$lines.Add(("# cleanup.ps1  stage={0}  dryRun={1}  {2}" -f $Stage, $DryRun, (Get-Date -Format 's')))
foreach ($d in $script:Deleted) { [void]$lines.Add(("{0}`t{1}`t{2}`t{3}" -f $d.Action, (Format-Size $d.Size), $d.Path, $d.Reason)) }
foreach ($k in $script:Kept)    { [void]$lines.Add(("KEPT`t-`t{0}" -f $k)) }
foreach ($f in $script:Failed)  { [void]$lines.Add(("FAILED`t-`t{0}`t{1}" -f $f.Path, $f.Error)) }
$lines | Set-Content -LiteralPath $logPath -Encoding UTF8
Write-Host ("Log: {0}" -f $logPath) -ForegroundColor DarkGray


