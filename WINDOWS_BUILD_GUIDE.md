# Windows Build & Compatibility Guide

## Building for Windows

### Prerequisites
- Python 3.8+ (64-bit recommended)
- PyInstaller: `pip install pyinstaller`
- All project dependencies installed

### Building the Windows Executable

1. **From the project root directory:**
   ```bash
   pyinstaller Silksong.spec
   ```

2. **The build output will be in:** `dist/Silksong/`

3. **To distribute:** Zip the `dist/Silksong` folder and share with users.

## Common Compatibility Issues & Solutions

### Issue 1: "This app can't run on your pc"

**Cause:** Usually architecture mismatch or missing Visual C++ runtime.

**Solutions:**

#### Check Architecture (32-bit vs 64-bit)
- **Your build PC:** Open Command Prompt → `wmic os get osarchitecture`
  - Returns: "64-bit" or "32-bit"
- **Player's PC:** Same command on their machine
- **Match them!** If your PC is 64-bit but their PC is 32-bit, you need a 32-bit build.

#### Building for Different Architectures

**For 64-bit Windows (recommended - most common):**
- In `Silksong.spec`, line with `target_arch='x64'` ✓ Already set

**For 32-bit Windows:**
- Change `target_arch='x64'` to `target_arch='x86'` in `Silksong.spec`
- Rebuild: `pyinstaller Silksong.spec`

**For Both (best practice):**
- Build on a 64-bit system for x64 version: `target_arch='x64'`
- Build on a 32-bit system (or in 32-bit Python on 64-bit Windows) for x86 version
- Provide both downloads to players

#### Fix: Install Visual C++ Runtime

Players may need to install Microsoft Visual C++ Redistributable:
- **Download:** https://support.microsoft.com/en-us/help/2977003/
- **Choose version matching their Windows:**
  - Windows 10/11: Download "Visual C++ Redistributable for Visual Studio 2022"
  - Windows 7/8: Download "Visual C++ Redistributable for Visual Studio 2019"

### Issue 2: Missing DLL Files

**Cause:** OpenCV (cv2) or other libraries not bundling correctly.

**Solution:** Explicitly list binaries in the spec:
```python
binaries=[
    # Add paths to any DLL files if needed
    # Example: ('C:/path/to/dll', '.')
],
```

### Issue 3: Windows 7 Incompatibility

**Python 3.9+ doesn't support Windows 7.** If players use Windows 7:
- Use Python 3.8.x for the build
- Or inform players they need Windows 8+

### Issue 4: Slow Launch or Antivirus False Positives

**Cause:** PyInstaller-compiled executables sometimes trigger antivirus warnings.

**Solution:**
- Code signing the executable (requires a certificate)
- Include a README explaining it's safe
- Recommend users disable antivirus temporarily if trusted

## Testing Your Build

Before distributing:

1. **On your PC:** Test the .exe manually
2. **On another PC with different specs:** 
   - Test on both 32-bit and 64-bit if possible
   - Test on older Windows (7/8 if applicable)
3. **Check that assets load:** Title screen, images, sounds should work

## Quick Checklist Before Release

- [ ] Built with `pyinstaller Silksong.spec`
- [ ] `dist/Silksong/Silksong.exe` exists and runs
- [ ] Assets folder is in `dist/Silksong/`
- [ ] Tested on target Windows versions
- [ ] Architecture matches target systems (x64 for modern, x86 for legacy)
- [ ] Zipped `dist/Silksong` folder for distribution

## Provide Support Info

Include in release notes:
```
If you get "This app can't run on your pc":
1. Right-click Silksong.exe → Properties → Compatibility
2. Try running in Compatibility Mode (Windows 8, Windows 7, etc.)
3. Or install Visual C++ Redistributable:
   https://support.microsoft.com/en-us/help/2977003/

For 32-bit Windows, download the x86 version instead of x64.
```
