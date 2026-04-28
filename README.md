# Silksong (Fan Project)

## v0.1.1 Release Notes

- Added new audio files for improved in-game sound and effects.
- Fixed several bugs from earlier prototypes.
- **Known issues:** Major bugs still exist (such as phasing through walls/platforms and other collision problems). This is the first public version, so expect rough edges and incomplete features.


Silksong is a 2D action platformer fan game inspired by Hollow Knight: Silksong, built with Python and Pygame. You play as Hornet in a combat-focused vertical slice featuring platforming, wall movement, bench checkpoints, save slots, and a boss encounter.

## Current Features

- Playable title screen, settings menu, and save-file selection
- Intro cutscene for new saves (can be skipped)
- Core Hornet movement and combat
- Background music and sfx
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
- **Left Shift / Right Shift**: Heal (when silk is full)
- **W** near bench: Rest and set checkpoint
- **W / S** while standing still: Camera look up/down
- **Mouse**: Menu navigation
- **Esc**: Quit game (or skip cutscene while it is playing)

## Download and Play (v0.1.1)

### Windows

1. Open the latest release and download the Windows build asset.
2. Extract the archive.
3. Open the `Silksong-v0.1.1` folder.
4. Run `Silksong.exe`.

**Troubleshooting:** If you get "This app can't run on your pc", press on more info and then press run anyway


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

- This is the official game release (v0.1.1).
- Save data is stored in your user data directory and persists between sessions.