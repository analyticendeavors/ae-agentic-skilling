<#
.SYNOPSIS
  Keep this machine's AE PBI skills current and discoverable by Claude Code.

.DESCRIPTION
  Two things, idempotent:
   1. Registers a daily Scheduled Task that runs `git pull --ff-only` on this repo.
   2. Junctions every skills\pbi-* (and any other skill) into %USERPROFILE%\.claude\skills
      so Claude Code discovers them.
  Junctions are used (not symlinks) so no admin/Developer Mode is needed for the links.
  Registering the scheduled task may prompt for elevation.

.PARAMETER RepoPath
  Path to the cloned ae-agentic-skilling repo. Defaults to this script's repo root.

.PARAMETER Hour
  Hour of day (0-23) to run the daily pull. Default 9 (09:00 local).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-sync.ps1
#>
[CmdletBinding()]
param(
    [string]$RepoPath = (Split-Path -Parent $PSScriptRoot),
    [int]$Hour = 9
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoPath = (Resolve-Path $RepoPath).Path
$skillsSrc = Join-Path $RepoPath "skills"
$claudeSkills = Join-Path $HOME ".claude\skills"

if (-not (Test-Path $skillsSrc)) { throw "skills folder not found under repo: $skillsSrc" }
New-Item -ItemType Directory -Force -Path $claudeSkills | Out-Null

# --- 1) Link each skill into ~/.claude/skills via a junction ---------------
Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
    $name = $_.Name
    $link = Join-Path $claudeSkills $name
    if (Test-Path $link) {
        $item = Get-Item $link -Force
        $isLink = $item.Attributes -band [IO.FileAttributes]::ReparsePoint
        if ($isLink) {
            Write-Host "Re-linking $name"
            Remove-Item $link -Force
        } else {
            Write-Warning "Skipping $name : a real folder already exists at $link"
            return
        }
    }
    New-Item -ItemType Junction -Path $link -Target $_.FullName | Out-Null
    Write-Host "Linked $name -> $($_.FullName)"
}

# --- 2) Daily git pull via Scheduled Task ----------------------------------
$git = (Get-Command git -ErrorAction SilentlyContinue)
if (-not $git) { throw "git not found on PATH. Install Git, then re-run." }

$taskName = "AE-PBI-Skills-Sync"
$action = New-ScheduledTaskAction -Execute $git.Source `
    -Argument "-C `"$RepoPath`" pull --ff-only"
$trigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::Today.AddHours($Hour))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Daily ff-only pull of ae-agentic-skilling" -Force | Out-Null

Write-Host ""
Write-Host "Scheduled task '$taskName' registered: daily git pull at $($Hour):00."
Write-Host "Run on both your desktop and laptop. Done."
