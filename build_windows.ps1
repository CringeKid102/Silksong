# Windows Build Script for Silksong (PowerShell version)
# Usage: .\build_windows.ps1 -Arch x64 (or x86)
# Default: x64 (64-bit)

param(
    [ValidateSet('x64', 'x86')]
    [string]$Arch = 'x64'
)

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Silksong Windows Build Script" -ForegroundColor Cyan
Write-Host "Target Architecture: $Arch" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if PyInstaller is installed
Write-Host "[*] Checking for PyInstaller..." -ForegroundColor Yellow
$pyInstallerCheck = python -m pip show pyinstaller 2>$null
if (-not $pyInstallerCheck) {
    Write-Host "[ERROR] PyInstaller is not installed." -ForegroundColor Red
    Write-Host "Please install it first: pip install pyinstaller" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "[OK] PyInstaller found" -ForegroundColor Green
Write-Host ""

# Update the spec file with target architecture
Write-Host "[*] Updating build configuration for $Arch..." -ForegroundColor Yellow
$specFile = "Silksong.spec"
$content = Get-Content $specFile -Raw

if ($Arch -eq 'x86') {
    $content = $content -replace "target_arch='x64'", "target_arch='x86'"
    Write-Host "[*] Building for 32-bit Windows (x86)" -ForegroundColor Green
} else {
    $content = $content -replace "target_arch='x86'", "target_arch='x64'"
    Write-Host "[*] Building for 64-bit Windows (x64)" -ForegroundColor Green
}

Set-Content -Path $specFile -Value $content
Write-Host ""

# Clean previous builds
Write-Host "[*] Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force | Out-Null
}
if (Test-Path "dist") {
    Remove-Item "dist" -Recurse -Force | Out-Null
}
Write-Host "[OK] Clean complete" -ForegroundColor Green
Write-Host ""

# Build the executable
Write-Host "[*] Building executable with PyInstaller..." -ForegroundColor Yellow
Write-Host ""
& pyinstaller Silksong.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    pause
    exit 1
}

# Verify build
Write-Host ""
if (Test-Path "dist\Silksong\Silksong.exe") {
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Build completed!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Output location: dist\Silksong\" -ForegroundColor Cyan
    Write-Host "Executable: dist\Silksong\Silksong.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Test the executable" -ForegroundColor White
    Write-Host "2. Zip the 'dist\Silksong' folder for distribution" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "[ERROR] Build verification failed - Silksong.exe not found!" -ForegroundColor Red
    pause
    exit 1
}
