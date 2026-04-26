import pygame
import os
import math

from runtime_paths import assets_path

# Initialize Pygame
pygame.init()

# Constants

# ============================================================================
# RESOLUTION SYSTEM
# ============================================================================
# The game operates in virtual space at a fixed resolution (game_width x game_height).
# All game logic, assets, positions, and colliders are defined in this virtual space.
# The virtual surface is then scaled to fit the actual screen resolution.
# This ensures all elements scale uniformly, fixing resolution-dependent issues.
# ============================================================================

# Virtual game resolution - all game logic and assets are designed for this
VIRTUAL_WIDTH = 1920
VIRTUAL_HEIGHT = 1080

# Actual screen dimensions - determined at runtime (fullscreen)
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

# Calculate uniform scale factor to maintain aspect ratio
# Use the minimum scale to ensure the virtual surface fits on screen
_scale_x = SCREEN_WIDTH / VIRTUAL_WIDTH
_scale_y = SCREEN_HEIGHT / VIRTUAL_HEIGHT
SCALE = min(_scale_x, _scale_y)

# For backward compatibility with existing code
game_width, game_height = VIRTUAL_WIDTH, VIRTUAL_HEIGHT
screen_width, screen_height = SCREEN_WIDTH, SCREEN_HEIGHT
scale_x = SCALE
scale_y = SCALE

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
        size = int(32 * scale_y)
    key = ('font', size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(font_path, size)
    return _font_cache[key]

def get_title_font(size=None):
    """Return the title font at the given size, cached for reuse."""
    if size is None:
        size = int(48 * scale_y)
    key = ('title_font', size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(title_font_path, size)
    return _font_cache[key]

def get_super_title_font(size=None):
    """Return the large title font at the given size, cached for reuse."""
    if size is None:
        size = int(72 * scale_y)
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
            "offset": (-135, -140),
            "scale": 0.625,
            "world_origin_override": None,
        },
        "lower": {
            "path": "collider_maps/collider_map_lower.png",
            "offset": (-140, -135),
            "scale": 0.625,
            "world_origin_override": None,
        },
    },
}