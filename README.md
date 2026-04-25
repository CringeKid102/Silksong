# Silksong (Fan Project)

Silksong is a 2D action platformer prototype inspired by Hollow Knight: Silksong, built with Python and Pygame. You play as Hornet in a combat-focused vertical slice featuring platforming, wall movement, bench checkpoints, save slots, and a boss encounter.

## Current Features

- Playable title screen, settings menu, and save-file selection
- Intro cutscene for new saves (can be skipped)
- Core Hornet movement and combat
- Wall jumping and air control
- Bench rest/checkpoint system with respawn
- Enemy encounters including MossGrub and a Moss Mother boss phase
- In-game audio settings and brightness control
- Save/load support for player state and encounter progress

## Controls

- **A / D**: Move left/right
- **Space**: Jump (also wall jump while airborne near walls)
- **J**: Attack
- **W + J**: Up attack
- **S + J** (in air): Down attack
- **K**: Dash
- **Left Shift / Right Shift**: Heal (when silk is full)
- **W** near bench: Rest and set checkpoint
- **W / S** while standing still: Camera look up/down
- **Mouse**: Menu navigation
- **Esc**: Quit game (or skip cutscene while it is playing)

## Download and Play (v0.1.0)

### Windows

1. Open the latest release and download the Windows build asset.
2. Extract the archive.
3. Open the `Silksong` folder.
4. Run `Silksong.exe`.

### macOS

1. Open the latest release and download the macOS build asset.
2. Extract the archive.
3. Open `Silksong.app`.
4. If macOS blocks the app on first launch, right-click the app, choose **Open**, then confirm.

## Run From Source

1. Install Python 3.
2. Install dependencies:

```bash
pip install pygame opencv-python numpy
```

3. Run:

```bash
python src/main.py
```

## Notes

- This is an early prototype release (v0.1.0).
- Save data is stored in your user data directory and persists between sessions.
