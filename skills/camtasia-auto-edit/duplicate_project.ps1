# Duplicate a Camtasia .tscproj folder so you can write markers into a copy
# without touching the original (useful if Camtasia is open with the original).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File duplicate_project.ps1 `
#     -Source 'C:\path\to\My Project.tscproj' `
#     -Destination 'C:\path\to\My Project - automarked.tscproj'

param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Destination
)

if (-not (Test-Path $Source)) {
    Write-Error "Source path does not exist: $Source"
    exit 1
}

if (Test-Path $Destination) {
    Write-Host "Removing existing destination..."
    Remove-Item $Destination -Recurse -Force
}

Write-Host "Copying $Source -> $Destination"
Copy-Item $Source $Destination -Recurse

# Camtasia stores its JSON file inside the .tscproj folder using the same name
# as the folder. When you copy the folder, rename the inner JSON to match.
$srcFolderName = (Get-Item $Source).Name
$dstFolderName = (Get-Item $Destination).Name

if ($srcFolderName -ne $dstFolderName) {
    $innerOld = Join-Path $Destination $srcFolderName
    $innerNew = Join-Path $Destination $dstFolderName
    if (Test-Path $innerOld) {
        Rename-Item $innerOld $innerNew
        Write-Host "Renamed inner JSON: $srcFolderName -> $dstFolderName"
    }
}

Get-ChildItem $Destination | Select-Object Name, Length | Format-Table -AutoSize
