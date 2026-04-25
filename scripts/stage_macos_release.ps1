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

$appPath = Get-ChildItem -Path $tempExtract -Filter 'Silksong.app' -Recurse -Directory | Select-Object -First 1
if (-not $appPath) {
    # GitHub artifact downloads often wrap the real build zip inside another zip.
    $innerZip = Get-ChildItem -Path $tempExtract -Filter '*.zip' -Recurse -File | Select-Object -First 1
    if ($innerZip) {
        $innerExtract = Join-Path $tempExtract '_inner_zip'
        Expand-Archive -Path $innerZip.FullName -DestinationPath $innerExtract -Force
        $appPath = Get-ChildItem -Path $innerExtract -Filter 'Silksong.app' -Recurse -Directory | Select-Object -First 1
    }
}

if (-not $appPath) {
    throw 'Silksong.app not found after extracting artifact. Confirm the workflow completed successfully and produced Silksong.app.'
}

Copy-Item -Path $appPath.FullName -Destination $macosDir -Recurse -Force

if (Test-Path $outputZip) {
    Remove-Item -Force $outputZip
}

Compress-Archive -Path $macosDir -DestinationPath $outputZip -CompressionLevel Optimal

Remove-Item -Recurse -Force $tempExtract

Write-Output "Created: $outputZip"
Write-Output "Share this file with Mac players."
