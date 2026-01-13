import pygame
import random
import os
import sys
from animation import Animation
from audio import AudioManager
from button import Button
from particles import ParticleSystem
from slider import Slider
from transition import TransitionManager
from button import Button
 
# Intialize python
pygame.init()

# Constants

# Design resolution (what we design for - max resolution)
DESIGN_WIDTH, DESIGN_HEIGHT = 1920, 1080

# Actual screen dimensions - Fullscreen
info = pygame.display.Info()
SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h

# Calculate scale factors
SCALE_X = SCREEN_WIDTH / DESIGN_WIDTH
SCALE_Y = SCREEN_HEIGHT / DESIGN_HEIGHT

# Use screen dimensions for game
WIDTH, HEIGHT = SCREEN_WIDTH, SCREEN_HEIGHT

FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
DARK_BLUE = (0, 0, 100)
DARK_GREEN = (0, 100, 0)

class Silksong:
    def __init__(self):
        """Initialize the game"""
        # Create fullscreen display at actual screen size
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        
        pygame.display.set_caption("Silksong")
        self.running = True
        self.state = "title screen"
        self.clock = pygame.time.Clock()
        # Scale font based on screen size
        self.font = pygame.font.SysFont("Arial", int(30 * SCALE_Y))
        # Load and scale title image at load time
        title_img = pygame.image.load(os.path.join(os.path.dirname(__file__), "../assets/Silksong Title.png"))
        # Scale to fit screen
        max_width = int(DESIGN_WIDTH * 0.45 * SCALE_X)
        max_height = int(DESIGN_HEIGHT * 0.3 * SCALE_Y)
        self.title_image = pygame.transform.scale(title_img, (max_width, max_height))
        self.create_buttons()

    def create_buttons(self):
        # Scale button dimensions to current screen size
        button_width = int(200 * SCALE_X)
        button_height = int(80 * SCALE_Y)
        button_spacing = int(150 * SCALE_Y)
        
        # Scale positions to actual screen size
        self.buttons = {
            "start": Button(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - button_spacing, button_width, button_height, "Start", DARK_GRAY, GRAY),
            "exit": Button(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + button_spacing, button_width, button_height, "Exit", DARK_GRAY, GRAY),
            "settings": Button(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, button_width, button_height, "Settings", DARK_GRAY, GRAY)
            }
    
    def update_title_screen(self, dt):
        for button in self.buttons.values():
            button.update(dt)
    
    def update_settings(self, dt):
        pass
    
    def update_save_files(self, dt):
        pass
    
    def update_cutscene(self, dt):
        pass

    def update_game(self, dt):
        pass
    
    def draw_title_screen(self):
        self.screen.fill(DARK_BLUE)
        # Draw the Silksong title image (scaled at load time)
        title_rect = self.title_image.get_rect(center=(SCREEN_WIDTH/2, int(SCREEN_HEIGHT/2 - 200 * SCALE_Y)))
        self.screen.blit(self.title_image, title_rect)
        # Draw buttons
        for button in self.buttons.values():
            button.draw(self.screen, self.font)
    
    def draw_cutscene(self):
        self.screen.fill(BLACK)
    
    def draw_game(self):
        self.screen.fill(BLACK)
    
    def draw(self):
        """Render the game."""
        if self.state == "title screen":
            self.draw_title_screen()
        elif self.state == "save files":
            self.draw_cutscene()
        elif self.state == "game":
            self.draw_game()
        
        pygame.display.flip()

    def update(self, dt):
        """
        Update the game state.
        Args:
            dt (float): Delta time since last update.
        """

        if self.state == "title screen":
            self.update_title_screen(dt)
        elif self.state == "settings":
            self.update_settings(dt)
        elif self.state == "save files":
            self.update_save_files(dt)
        elif self.state == "cutscene":
            self.update_cutscene(dt)
        elif self.state == "game":
            self.update_game(dt)
            
    def handle_events(self):
        """Handle user input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.state == "exit":
                self.running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()  # Mouse coordinates are now directly usable

                if self.state == "title screen":
                    if self.buttons['start'].is_clicked(pos):
                        self.state = "save files"
                    if self.buttons['exit'].is_clicked(pos):
                        self.running = False
                    if self.buttons['settings'].is_clicked(pos):
                        self.state = "settings"
        
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
 

# Initialization

if __name__ == "__main__":
    game = Silksong()
    game.run()

    
