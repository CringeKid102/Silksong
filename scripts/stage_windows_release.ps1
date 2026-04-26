Param()

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseRoot = Join-Path $repoRoot 'release'
$windowsRoot = Join-Path $releaseRoot 'windows'
$buildDir = Join-Path $windowsRoot 'Silksong'
$shareZip = Join-Path $releaseRoot 'Silksong-Windows-x64-share.zip'
$shareManifest = Join-Path $releaseRoot 'Silksong-Windows-x64-checksums.txt'
$exePath = Join-Path $buildDir 'Silksong.exe'

if (-not (Test-Path $exePath)) {
    throw "Build output not found: $exePath"
}

if (Test-Path $shareZip) {
    Remove-Item $shareZip -Force
}

Compress-Archive -Path $buildDir -DestinationPath $shareZip -Force

$exeHash = Get-FileHash -Path $exePath -Algorithm SHA256
$zipHash = Get-FileHash -Path $shareZip -Algorithm SHA256

@(
    'Silksong Windows release checksums'
    ''
    "EXE  SHA256  $($exeHash.Hash)"
    "ZIP  SHA256  $($zipHash.Hash)"
    ''
    'Share the zip file, not the extracted folder.'
    'Players should extract the entire zip before running Silksong.exe.'
) | Set-Content -Path $shareManifest -Encoding ASCII

Write-Output "Created: $shareZip"
Write-Output "Created: $shareManifest"
Write-Output 'Share the zip and verify hashes on the receiving PC if launch fails.'