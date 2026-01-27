import pygame
import os

# Initialize Pygame
pygame.init()

# Constants

# Game resolution
game_width, game_height = 1920, 1080

# Actual screen dimensions - Fullscreen (Github Copilot)
info = pygame.display.Info()
screen_width, screen_height = info.current_w, info.current_h

# Calculate scale for dynamic screening
scale_x = screen_width / game_width
scale_y = screen_height / game_height

# Fonts
font_path = os.path.join(os.path.dirname(__file__), "../assets/fonts/Perpetua Regular.otf")
title_font_path = os.path.join(os.path.dirname(__file__), "../assets/fonts/TrajanPro-Regular.ttf")
font = pygame.font.Font(font_path, int(32 * scale_y))
title_font = pygame.font.Font(title_font_path, int(48 * scale_y))
super_title_font = pygame.font.Font(title_font_path, int(72 * scale_y))
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