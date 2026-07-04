<#
.SYNOPSIS
    Renames Hive-style 'date=' partition dirs to 'extract_date=' under each source dir.
.EXAMPLE
    # Dry run first (recommended)
    .\scripts\rename_hive_date_key.ps1 -DryRun
    # Actual rename
    .\scripts\rename_hive_date_key.ps1
#>
param(
    [string]$RawDir = "data/raw",
    [string]$OldKey = "date",
    [string]$NewKey = "extract_date",
    [switch]$DryRun
)

if (-not (Test-Path $RawDir)) {
    Write-Error "Raw data directory not found: $RawDir"
    exit 1
}

$pattern = "^" + [regex]::Escape("$OldKey=")

# Iterate over all source=* dirs (works for both old 'source=' and new key later)
Get-ChildItem -Path $RawDir -Directory | ForEach-Object {
    Get-ChildItem -Path $_.FullName -Directory -Filter "$OldKey=*" | ForEach-Object {
        $newName = $_.Name -replace $pattern, "$NewKey="
        if ($DryRun) {
            Write-Host "[DRY RUN] $($_.FullName) -> $newName"
        } else {
            Rename-Item -Path $_.FullName -NewName $newName
            Write-Host "Renamed: $($_.FullName) -> $newName"
        }
    }
}