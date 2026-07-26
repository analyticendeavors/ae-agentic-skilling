<#
.SYNOPSIS
  Install (or update) the ae-pbi CLI used by the AE PBI skills.

.DESCRIPTION
  Downloads the latest signed ae-pbi.exe from the newest GitHub release whose
  tag starts with "pbi-cli-" on analyticendeavors/ae-agentic-skilling, places it
  at $HOME\.ae-pbi\bin\ae-pbi.exe, and adds that folder to the current user's
  PATH. Windows only (the binary is a Windows console executable).

.PARAMETER Version
  Optional exact tag to install, e.g. "pbi-cli-v1.0.0". Defaults to the latest.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-ae-pbi.ps1
#>
[CmdletBinding()]
param(
    [string]$Version
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo    = "analyticendeavors/ae-agentic-skilling"
$prefix  = "pbi-cli-"
$asset   = "ae-pbi.exe"
$binDir  = Join-Path $HOME ".ae-pbi\bin"
$target  = Join-Path $binDir $asset

Write-Host "Resolving release from $repo ..."
$headers = @{ "Accept" = "application/vnd.github+json"; "User-Agent" = "ae-pbi-installer" }
$releases = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases" -Headers $headers -TimeoutSec 20

$candidates = $releases | Where-Object { $_.tag_name -like "$prefix*" -and -not $_.draft }
if ($Version) {
    $release = $candidates | Where-Object { $_.tag_name -eq $Version } | Select-Object -First 1
    if (-not $release) { throw "Release '$Version' not found (tags must start with '$prefix')." }
} else {
    # Sort by the numeric version embedded after the prefix, descending.
    $release = $candidates |
        Sort-Object -Property @{ Expression = { [version]( ($_.tag_name -replace "^$prefix" , "") -replace "^v", "" ) } } -Descending |
        Select-Object -First 1
}
if (-not $release) {
    throw "No '$prefix*' release found on $repo. Has the CLI been published yet?"
}

$dl = $release.assets | Where-Object { $_.name -eq $asset } | Select-Object -First 1
if (-not $dl) { throw "Release '$($release.tag_name)' has no asset named '$asset'." }

Write-Host "Installing $($release.tag_name) -> $target"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Invoke-WebRequest -Uri $dl.browser_download_url -OutFile $target -TimeoutSec 120

# Add the bin dir to the user PATH if missing.
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $binDir) {
    Write-Host "Adding $binDir to your user PATH (restart shells to pick it up)."
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
}
$env:Path = "$env:Path;$binDir"

Write-Host "Done. Verifying:"
& $target --version
