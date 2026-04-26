@echo off
REM Windows Build Script for Silksong
REM Usage: build_windows.bat [x64|x86]
REM Default: x64 (64-bit)

setlocal enabledelayedexpansion

REM Get target architecture from argument or default to x64
set TARGET_ARCH=x64
if not "%1"=="" (
    set TARGET_ARCH=%1
)

echo.
echo =====================================
echo Silksong Windows Build Script
echo Target Architecture: %TARGET_ARCH%
echo =====================================
echo.

REM Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed.
    echo Please install it first: pip install pyinstaller
    pause
    exit /b 1
)

REM Update the spec file with target architecture
echo [*] Updating build configuration for %TARGET_ARCH%...
python -c "
import sys
spec_file = 'Silksong.spec'
with open(spec_file, 'r') as f:
    content = f.read()

# Replace target_arch
if '%TARGET_ARCH%' == 'x86':
    content = content.replace(\"target_arch='x64'\", \"target_arch='x86'\")
    print('[*] Building for 32-bit Windows (x86)')
else:
    content = content.replace(\"target_arch='x86'\", \"target_arch='x64'\")
    print('[*] Building for 64-bit Windows (x64)')

with open(spec_file, 'w') as f:
    f.write(content)
"

REM Clean previous builds
echo [*] Cleaning previous builds...
if exist build rmdir /s /q build >nul 2>&1
if exist dist rmdir /s /q dist >nul 2>&1

REM Build the executable
echo [*] Building executable with PyInstaller...
echo.
pyinstaller Silksong.spec
if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

REM Verify build
if exist dist\Silksong\Silksong.exe (
    echo.
    echo =====================================
    echo [SUCCESS] Build completed!
    echo =====================================
    echo.
    echo Output location: dist\Silksong\
    echo Executable: dist\Silksong\Silksong.exe
    echo.
    echo Next steps:
    echo 1. Test the executable
    echo 2. Zip the "dist\Silksong" folder for distribution
    echo.
    pause
) else (
    echo [ERROR] Build verification failed - Silksong.exe not found!
    pause
    exit /b 1
)
