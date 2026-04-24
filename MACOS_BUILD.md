# Build and run on macOS

This project now includes a macOS PyInstaller spec and a GitHub Actions workflow that builds a `.app` bundle.

## Option 1: Build in GitHub Actions (from Windows)

1. Push your latest code to GitHub.
2. Open the **Actions** tab in your repo.
3. Run the workflow: **Build macOS app**.
4. Download the artifact named **Silksong-macOS**.
5. Unzip `Silksong-macOS.zip` on a Mac.
6. Open `Silksong.app`.

To stage a share folder and create a zip from Windows after downloading the artifact:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stage_macos_release.ps1 -ArtifactZipPath "path\to\Silksong-macOS.zip"
```

This creates:

- `release/macos/Silksong.app`
- `release/Silksong-macOS-share.zip`

If macOS blocks the app the first time:
- Right-click the app and choose **Open**, then confirm.

## Option 2: Build directly on a Mac

From the repo root:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller pygame opencv-python
pyinstaller Silksong.macos.spec --noconfirm --clean
```

Output app bundle:

- `dist/Silksong.app`

## Notes

- `.exe` is Windows-only. On macOS, the equivalent is a `.app` bundle.
- To distribute outside your own machine without warnings, you will eventually need Apple code-signing and notarization.
