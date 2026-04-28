import pygame
import os

from runtime_paths import assets_path

# Initialize Pygame
pygame.init()

# Constants

# Game resolution — fixed at 1920x1080 for all machines
game_width, game_height = 1920, 1080
screen_width, screen_height = game_width, game_height

# Camera viewport — the visible window into the game world during gameplay.
# Arena size is 1380×760; viewport is slightly bigger (40px padding each side).
# HUD elements (health, silk, instructions) draw at fixed screen positions, unaffected.
_arena_w = 1380
_arena_h = 760
camera_viewport_width  = _arena_w + 80   # 1460  (40px padding each side)
camera_viewport_height = _arena_h + 60   # 820   (30px padding each side)
camera_viewport_x = (game_width  - camera_viewport_width)  // 2   # 230
camera_viewport_y = (game_height - camera_viewport_height) // 2   # 130

# No dynamic scaling: all layout values are authored at 1920x1080
scale_x = 1.0
scale_y = 1.0

# Character sizing multipliers
HORNET_SCALE_MULTIPLIER = 1.3
ENEMY_SCALE_MULTIPLIER = 1.3

# Fonts
font_path = assets_path("fonts", "Perpetua Regular.otf")
title_font_path = assets_path("fonts", "TrajanPro-Regular.ttf")

# Font cache for efficient reuse
_font_cache = {}

def get_font(size=None):
    """Return the regular font at the given size, cached for reuse."""
    if size is None:
        size = 32
    key = ('font', size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(font_path, size)
    return _font_cache[key]

def get_title_font(size=None):
    """Return the title font at the given size, cached for reuse."""
    if size is None:
        size = 48
    key = ('title_font', size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(title_font_path, size)
    return _font_cache[key]

def get_super_title_font(size=None):
    """Return the large title font at the given size, cached for reuse."""
    if size is None:
        size = 72
    key = ('super_title_font', size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(title_font_path, size)
    return _font_cache[key]

# Create default font instances (will be cached)
font = get_font()
title_font = get_title_font()
super_title_font = get_super_title_font()

# FPS
fps = 60

# Colors
black = (0, 0, 0)
white = (255, 255, 255)
red = (255, 0, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
yellow = (255, 255, 0)
gray = (100, 100, 100)
dark_gray = (50, 50, 50)
dark_blue = (0, 0, 100)
dark_green = (0, 100, 0)

# Collider map overlay tuning.
# Change scale to resize both maps, then use global_offset or per-layer offsets
# to nudge them in world space without touching main.py.
collider_map_overlay = {
    "enabled": True,
    "scale": 1.0,
    "alpha": 255,
    "padding": 40,
    "split_y_offset": 1480,
    "global_offset": (0, 0),
    "layers": {
        "upper": {
            "path": "collider_maps/collider_map_upper.png",
            "offset": (-760, -135),
            "scale": 0.625,
            "world_origin_override": None,
        },
        "lower": {
            "path": "collider_maps/collider_map_lower.png",
            "offset": (-760, -135),
            "scale": 0.625,
            "world_origin_override": None,
        },
    },
}