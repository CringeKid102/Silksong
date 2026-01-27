import pygame
import random
import os
import sys
import config
from animation import Animation
from audio import AudioManager
from button import Button
from particles import ParticleSystem
from slider import Slider
from transition import TransitionManager, TransitionType
from settings import SettingsMenu
from save_file import SaveFile

# Initialize pygame
pygame.init()

class Silksong:

    def __init__(self):
        """Initialize the game."""
        # Create fullscreen display at actual screen size
        self.screen = pygame.display.set_mode((config.screen_width, config.screen_height), pygame.FULLSCREEN)
        
        pygame.display.set_caption("Silksong")
        self.running = True
        self.state = "title screen"
        self.clock = pygame.time.Clock()
        
        # Load and scale title image
        title_img = pygame.image.load(os.path.join(os.path.dirname(__file__), "../assets/images/Title.png"))
        self.title_image = pygame.transform.scale(title_img, (int(880 * config.scale_x), int(440 * config.scale_y)))
        
        # Load and scale background image
        background_img = pygame.image.load(os.path.join(os.path.dirname(__file__), "../assets/images/Title Screen Bg.png"))
        self.background_image = pygame.transform.scale(background_img, (config.screen_width, config.screen_height))
        
        # Initialize audio manager
        self.audio_manager = AudioManager()
        
        # Initialize save file system
        self.save_file = SaveFile()
        self.current_slot = 1
        self.game_state = None
        
        # Initialize transition manager
        self.transition_manager = TransitionManager(
            screen_width=config.screen_width,
            screen_height=config.screen_height,
            default_speed=1.5
        )
        
        # Create settings menu
        self.settings_menu = SettingsMenu(config.screen_width, config.screen_height, self.audio_manager, Button)
        self.settings_menu.game = self  # Link settings menu to game for save/load
        self.settings_menu.transition_manager = self.transition_manager  # Link transition manager to settings
        
        # Create buttons
        self.create_buttons() # Normal buttons
        self.create_save_slot_buttons() # Save slot buttons

    def create_buttons(self):
        """Create buttons for the title screen."""
        # Scale positions to actual screen size
        button_spacing = int(80 * config.scale_y)
        shifty = int(200 * config.scale_y)
        button_font_size = int(40 * config.scale_y)
        
        self.buttons = {
            "start": Button(config.screen_width/2, config.screen_height/2 - button_spacing+shifty, "Start Game", config.white, config.title_font_path, button_font_size),
            "settings": Button(config.screen_width/2, config.screen_height/2+shifty, "Options", config.white, config.title_font_path, button_font_size),
            "exit": Button(config.screen_width/2, config.screen_height/2 + button_spacing+shifty, "Exit", config.white, config.title_font_path, button_font_size),
            }
    
    def create_save_slot_buttons(self):
        """Create buttons for save slot selection."""
        button_spacing = int(150 * config.scale_y)
        button_font_size = int(40 * config.scale_y)
        
        self.save_slot_buttons = {
            1: Button(config.screen_width/2, config.screen_height/2 - button_spacing, "Slot 1", config.white, config.title_font_path, button_font_size),
            2: Button(config.screen_width/2, config.screen_height/2, "Slot 2", config.white, config.title_font_path, button_font_size),
            3: Button(config.screen_width/2, config.screen_height/2 + button_spacing, "Slot 3", config.white, config.title_font_path, button_font_size),
            "back": Button(config.screen_width/2, config.screen_height/2 + button_spacing * 2, "Back", config.white, config.title_font_path, button_font_size),
        }

    def update_title_screen(self, dt):
        for button in self.buttons.values():
            button.update(dt)
    
    def update_settings(self, dt):
        self.settings_menu.update(dt)
    
    def update_save_files(self, dt):
        for button in self.save_slot_buttons.values():
            button.update(dt)
    
    def update_cutscene(self, dt):
        pass

    def update_game(self, dt):
        pass
    
    def change_state(self, new_state):
        """Change game state with black fade transition."""
        def on_state_change(target_state):
            self.state = target_state
        
        self.transition_manager.start_transition(
            target_state=new_state,
            
            transition_type=TransitionType.FADE_COLOR,
            speed=2.0,
            state_change_callback=on_state_change,
            color=(0, 0, 0)
        )
    
    def draw_title_screen(self):
        # Draw background
        self.screen.blit(self.background_image, (0, 0))
        
        # Draw the Silksong title image
        title_rect = self.title_image.get_rect(center=(config.screen_width/2, int(config.screen_height/2 - 200 * config.scale_y)))
        self.screen.blit(self.title_image, title_rect)
        
        # Draw buttons
        for button in self.buttons.values():
            button.draw(self.screen)
                
    def draw_settings(self):
        self.screen.fill(config.dark_blue)
        self.settings_menu.draw(self.screen, config.font)
    
    def draw_save_files(self):
        self.save_file.draw_save_files(self.screen, self.save_slot_buttons, config)
    
    def draw_cutscene(self):
        self.screen.fill(config.black)
    
    def draw_game(self):
        self.screen.fill(config.black)
    
    def draw(self):
        """Render the game."""
        self.screen.blit(self.background_image, (0, 0))
        if self.state == "title screen":
            self.draw_title_screen()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "save files":
            self.draw_save_files()
        elif self.state == "cutscene":
            self.draw_cutscene()
        elif self.state == "game":
            self.draw_game()
        
        # Draw transition overlay on top of everything
        if self.transition_manager.active:
            self.transition_manager.draw(self.screen)
        
        pygame.display.flip()

    def update(self, dt):
        """
        Update the game state.
        Args:
            dt (float): Delta time since last update.
        """
        # Update transition manager
        self.transition_manager.update(dt)

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
            
            # Skip input handling during transitions
            if self.transition_manager.active:
                continue
            
            # Handle settings menu events
            if self.state == "settings":
                
                
                if self.settings_menu.handle_event(event):
                    continue
                # Return to title screen if settings menu was closed
                if not self.settings_menu.visible:
                    self.change_state("title screen")
                    continue
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()  # Mouse coordinates

                if self.state == "title screen":
                    if self.buttons['start'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.change_state("save files")
                    if self.buttons['exit'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.running = False
                    if self.buttons['settings'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.settings_menu.show()
                        self.change_state("settings")
                
                elif self.state == "save files":
                    # Handle save slot selection
                    background_img = pygame.image.load(os.path.join(os.path.dirname(__file__), "../assets/images/Title Screen Bg.png"))
                    self.background_image = pygame.transform.scale(background_img, (config.screen_width, config.screen_height))
                    for slot_num in [1, 2, 3]:
                        if self.save_slot_buttons[slot_num].is_clicked(pos):
                            self.audio_manager.play_sfx("button_click")
                            self.current_slot = slot_num
                            
                            # Try to load existing save
                            loaded_state = self.save_file.load_game_file(slot_num)
                            if loaded_state:
                                self.game_state = loaded_state
                            else:
                                # Create new save file for this slot
                                self.save_file.create_game_file(slot_num)
                                self.game_state = {
                                    "level": 1,
                                    "score": 0,
                                    "player_position": [0, 0],
                                    "inventory": []
                                }
                            
                            self.change_state("game")  # Start the game with transition
                    
                    if self.save_slot_buttons["back"].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.change_state("title screen")
    
    def reset():
        pass

    def run(self):
        while self.running:
            dt = self.clock.tick(config.fps) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
 

# Run the game
if __name__ == "__main__":
    game = Silksong()
    game.run()