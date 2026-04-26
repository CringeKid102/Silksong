Param(
    [Parameter(Mandatory = $true)]
    [string]$ArtifactZipPath
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseRoot = Join-Path $repoRoot 'release'
$macosDir = Join-Path $releaseRoot 'macos'
$tempExtract = Join-Path $releaseRoot '_macos_extract_tmp'
$outputZip = Join-Path $releaseRoot 'Silksong-macOS-share.zip'
$stagedFromZip = $null

if (-not (Test-Path $ArtifactZipPath)) {
    throw "Artifact zip not found: $ArtifactZipPath"
}

if (Test-Path $tempExtract) {
    Remove-Item -Recurse -Force $tempExtract
}

if (Test-Path $macosDir) {
    Get-ChildItem -Path $macosDir -Force | Where-Object { $_.Name -ne 'README.txt' } | Remove-Item -Recurse -Force
}

Expand-Archive -Path $ArtifactZipPath -DestinationPath $tempExtract -Force

# IMPORTANT: Do not create a new zip on Windows from Silksong.app.
# Re-zipping on Windows can strip macOS metadata and execute permissions.
# Always preserve and share the mac-built zip produced by the macOS runner.

# If the supplied path is already the mac-built share zip, keep it as-is only
# when it directly contains Silksong.app entries. Artifact wrapper zips can have
# the same filename pattern but contain an inner zip instead.
$artifactFileName = [System.IO.Path]::GetFileName($ArtifactZipPath)
if ($artifactFileName -like 'Silksong-macOS*.zip') {
    $zipContainsApp = $false
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zipFile = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path $ArtifactZipPath))
    try {
        foreach ($entry in $zipFile.Entries) {
            if ($entry.FullName -like 'Silksong.app/*' -or $entry.FullName -like '*/Silksong.app/*') {
                $zipContainsApp = $true
                break
            }
        }
    }
    finally {
        $zipFile.Dispose()
    }

    if ($zipContainsApp) {
        $stagedFromZip = $ArtifactZipPath
    }
}

# GitHub artifact downloads often wrap the real build zip inside another zip.
if (-not $stagedFromZip) {
    $innerZip = Get-ChildItem -Path $tempExtract -Filter 'Silksong-macOS*.zip' -Recurse -File | Select-Object -First 1
    if ($innerZip) {
        $stagedFromZip = $innerZip.FullName
    }
}

if (-not $stagedFromZip) {
    throw 'Could not find a mac-built Silksong-macOS.zip inside the artifact. Re-run the Build macOS app workflow and share that zip directly.'
}

# Copy the intact mac-built zip so metadata is preserved for players.
Copy-Item -Path $stagedFromZip -Destination $outputZip -Force

# Also extract it into release/macos for local inspection.
$innerExtract = Join-Path $tempExtract '_inner_zip'
if (Test-Path $innerExtract) {
    Remove-Item -Recurse -Force $innerExtract
}
Expand-Archive -Path $stagedFromZip -DestinationPath $innerExtract -Force

$appPath = Get-ChildItem -Path $innerExtract -Filter 'Silksong.app' -Recurse -Directory | Select-Object -First 1

if (-not $appPath) {
    throw 'Silksong.app not found after extracting the mac-built zip. Confirm the workflow completed successfully.'
}

Copy-Item -Path $appPath.FullName -Destination $macosDir -Recurse -Force

Remove-Item -Recurse -Force $tempExtract

Write-Output "Created: $outputZip"
Write-Output "Share this file with Mac players (metadata preserved)."
