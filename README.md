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

## Sources

[1] GeeksforGeeks, "Python Program for Breadth First Search (BFS) for a Graph," Jul. 23, 2025. [Online]. Available: https://www.geeksforgeeks.org/python/python-program-for-breadth-first-search-or-bfs-for-a-graph/
[2] A. Rosebrock, "Increasing Webcam FPS with Python and OpenCV," PyImageSearch, Dec. 21, 2015. [Online]. Available: https://pyimagesearch.com/2015/12/21/increasing-webcam-fps-with-python-and-opencv/
[3] “How do you scale a design resolution to other resolutions with Pygame?,” Stack Overflow. [Online]. Available: https://stackoverflow.com/questions/43196126/how-do-you-scale-a-design-resolution-to-other-resolutions-with-pygame/
[4] ScriptLine Studios, “Pygame Tutorial - Save/Load System,” YouTube, 2021. [Online]. Available: https://www.youtube.com/watch?v=3IfQQHZ_rqM
[5] baraltech, “Easy Way to Make Jumping in PyGame! (7 Mins),” YouTube, 2022. [Online]. Available: https://www.youtube.com/watch?v=ST-Qq3WBZBE
[6] Kenny Yip Coding, “Pygame Tutorial 9 - Enemies,” YouTube, 2025. [Online]. Available: https://www.youtube.com/watch?v=rmobkgItFkk
[7] Clear Code, “Cameras in Pygame,” YouTube, 2022. [Online]. Available: https://www.youtube.com/watch?v=u7LPRqrzry8
[8] GitHub Copilot, “How do I make the screen compatible with all kinds of computers,” AI-generated suggestion, GitHub, 2026.
[9] GitHub Copilot, “How to create ember particles that can vary in sizes and speed,” AI-generated suggestion, GitHub, 2026.
[10] GitHub Copilot, “Can you make the player able to wall jump and to be able to rebound after a jump attack,” AI-generated suggestion, GitHub, 2026.
[11] GitHub Copilot, “Can you optimize the ember particles,” AI-generated suggestion, GitHub, 2026.
[12] GitHub Copilot, “How can I transition smoothly the fixed player camera to arena camera,” AI-generated suggestion, GitHub, 2026.
[13] GitHub Copilot, “How to add a video in Pygame,” AI-generated suggestion, GitHub, 2026.
[14] GitHub Copilot, “Can you take 2 screenshots of the ground_colliders separated at y = -945,” AI-generated suggestion, GitHub, 2026.
[15] GitHub Copilot, “Can you optimize the animations,” AI-generated suggestion, GitHub, 2026.
[16] GeeksforGeeks, “Pygame – Creating Sprites,” [Online]. Available: https://www.geeksforgeeks.org/python/pygame-creating-sprites/
[17] GitHub Copilot, “Can you download an exe file,” AI-generated suggestion, GitHub, 2026.
[18] GitHub Copilot, “How can I fix hornet and enemies phasing,” AI-generated suggestion, GitHub, 2026.
[19] GitHub Copilot, “Make the transition in hornet mantle climb smoother,” AI-generated suggestion, GitHub, 2026.
[20] GitHub Copilot, “Can you take a screenshot of the current ground_colliders,” AI-generated suggestion, GitHub, 2026.
[21] GitHub Copilot, “Can you remove all particles when they are off screen for optimization,” AI-generated suggestion, GitHub, 2026.
[22] “Game sprite assets (environment, characters, effects),” Google Drive folder. [Online]. Available: https://drive.google.com/drive/folders/1SpZV0e6Io3d2Mi_vHv2o5Y6Zp89C6MKk
[23] “Supplementary texture and particle assets,” MEGA file repository. [Online]. Available: https://mega.nz/folder/zwEwiT7Y#9TT0XrUE2WKRNO5Kd8hi5g
[24] Google Gemini, “AI-generated images used for game assets,” AI-generated content, Google, 2026.