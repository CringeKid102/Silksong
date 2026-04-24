Silksong macOS share folder

What this folder is for:
- Put the built Silksong.app bundle here, then zip this folder to share.

Important:
- You cannot build a real macOS .app on Windows.
- Build the app using one of these:
  1) GitHub Actions workflow: Build macOS app
  2) Running PyInstaller on a real Mac

After build:
1) Place Silksong.app inside this folder so you have:
   release/macos/Silksong.app
2) Zip the release/macos folder.
3) Share the zip with Mac players.

First-run instructions for players:
- If macOS blocks the app, right-click Silksong.app, choose Open, then confirm.
