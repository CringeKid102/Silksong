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
WIDTH, HEIGHT = 1000, 700
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
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.running = True
        self.state = "title screen"
        self.clock = pygame.time.Clock()
        self.create_buttons()

    def create_buttons(self):
        self.buttons = {
            "start": Button(WIDTH/2, HEIGHT/2, WIDTH/10, HEIGHT/10, "Start", DARK_BLUE, BLUE),
            "exit": Button(WIDTH/2, HEIGHT/2, WIDTH/10, HEIGHT/10, "Exit", DARK_GRAY, GRAY)
            }

    def handle_events(self):
        """Handle user input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.state == "exit":
                self.running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                if self.state == "title screen":
                    if self.buttons['exit'].is_clicked(pos):
                        self.running = False
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            "self.update_background(dt)"

            self.handle_events()
            "self.update(dt)"
            "self.draw()"
        
        "self.transition_manager.clear()"
        
        pygame.quit()
 

# Initialization

if __name__ == "__main__":
    game = Silksong()
    game.run()

    
