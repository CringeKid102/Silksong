import pygame
import os
import json
import config
from button import Button
from audio import AudioManager
from hornet import Hornet

class SaveFile:
    """Class to handle saving and loading game state to/from JSON files."""

    def __init__(self):
        # Define the 4 save slots
        self.save_slots = {
            1: "save_1.json",
            2: "save_2.json",
            3: "save_3.json",
            4: "save_4.json"
        }
        self.current_slot = None
        self.game_state = None  # Current game state dictionary

        # Initialize audio manager
        self.audio_manager = AudioManager()

        button_spacing = int(150 * config.scale_y)
        button_font_size = int(40 * config.scale_y)
        
        self.save_slot_buttons = {
            1: Button(config.screen_width/2 - button_spacing*3, config.screen_height - 300, "Slot 1", config.white, config.title_font_path, button_font_size),
            2: Button(config.screen_width/2-button_spacing*1, config.screen_height - 300, "Slot 2", config.white, config.title_font_path, button_font_size),
            3: Button(config.screen_width/2 + button_spacing*1, config.screen_height - 300, "Slot 3", config.white, config.title_font_path, button_font_size),
            4: Button(config.screen_width/2 + button_spacing*3, config.screen_height - 300, "Slot 4", config.white, config.title_font_path, button_font_size)
        }
        self.delete_slot_buttons = {
            1: Button(config.screen_width/2 - button_spacing*3, config.screen_height - 100, "Delete Slot 1", config.red, config.font_path, button_font_size),
            2: Button(config.screen_width/2 - button_spacing*1, config.screen_height - 100, "Delete Slot 2", config.red, config.font_path, button_font_size),
            3: Button(config.screen_width/2 + button_spacing*1, config.screen_height - 100, "Delete Slot 3", config.red, config.font_path, button_font_size),
            4: Button(config.screen_width/2 + button_spacing*3, config.screen_height - 100, "Delete Slot 4", config.red, config.font_path, button_font_size)
        }
        self.close_button = Button(config.screen_width/2, config.screen_height/2 + button_spacing * 2, "Back", config.white, config.font_path, button_font_size)

        # Cache for save slot status to avoid repeated loading
        self.slot_status_cache = {}
        
        # Load delete icon once
        delete_icon_path = os.path.join(os.path.dirname(__file__), "../assets/images/Trash.png")
        if os.path.exists(delete_icon_path):
            self.delete_icon = pygame.image.load(delete_icon_path)
            self.delete_icon = pygame.transform.scale(self.delete_icon, (int(100 * config.scale_x), int(100 * config.scale_y)))
        else:
            self.delete_icon = None
        
        # Initialize cache
        self.refresh_slot_status()
        
        # Pre-load font for status text using config's cached fonts
        self.status_font = config.get_font(int(20 * config.scale_y))

    def create_game_file(self, slot=1):
        """
        Creates a new game file with default game state for the specified slot.
        Args:
            slot (int): The save slot number (1, 2, 3, or 4).
        """
        if slot not in self.save_slots:
            print(f"Invalid slot number. Please use 1, 2, 3, or 4.")
            return
        
        filename = self.save_slots[slot]
        default_game_state = {
            "level": 1,
            "score": 0,
            "player_position": [0, 0],
            "inventory": []
        }
        try:
            with open(filename, 'w') as f:
                json.dump(default_game_state, f, indent=4)
            print(f"New game file created: {filename}")
            # Update cache
            self.slot_status_cache[slot] = default_game_state
        except IOError as e:
            print(f"An error occurred while creating the game file: {e}")

    def save_game_file(self, game_state, slot=1):
        """
        Saves the current game state to a JSON file in the specified slot.
        Args:
            game_state (dict): A dictionary containing the current game state.
            slot (int): The save slot number (1, 2, 3, or 4).
        """
        if slot not in self.save_slots:
            print(f"Invalid slot number. Please use 1, 2, 3, or 4.")
            return
        
        filename = self.save_slots[slot]
        try:
            with open(filename, 'w') as f:
                json.dump(game_state, f, indent=4)
            print(f"Game state saved to {filename}")
            # Update cache
            self.slot_status_cache[slot] = game_state
        except IOError as e:
            print(f"An error occurred while saving the game state: {e}")
    
    def load_game_file(self, slot=1):
        """
        Loads the game state from a JSON file in the specified slot.
        Args:
            slot (int): The save slot number (1, 2, 3, or 4).
        Returns:
            dict: The loaded game state, or None if the file doesn't exist or an error occurs.
        """
        if slot not in self.save_slots:
            print(f"Invalid slot number. Please use 1, 2, 3, or 4.")
            return None
        
        filename = self.save_slots[slot]
        try:
            if not os.path.exists(filename):
                print(f"Save file not found: {filename}")
                return None
            
            with open(filename, 'r') as f:
                game_state = json.load(f)
            print(f"Game state loaded from {filename}")
            # Update cache
            self.slot_status_cache[slot] = game_state
            return game_state
        except IOError as e:
            print(f"An error occurred while loading the game state: {e}")
            return None
    
    def delete_game_file(self, slot=1):
        """
        Deletes the game file in the specified slot.
        Args:
            slot (int): The save slot number (1, 2, 3, or 4).
        """
        if slot not in self.save_slots:
            print(f"Invalid slot number. Please use 1, 2, 3, or 4.")
            return
        
        filename = self.save_slots[slot]
        try:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Game file deleted: {filename}")
                # Update cache
                self.slot_status_cache[slot] = None
            else:
                print(f"No save file to delete in slot {slot}.")
        except IOError as e:
            print(f"An error occurred while deleting the game file: {e}")
    
    def refresh_slot_status(self):
        """Refresh the cache of save slot statuses by checking all save files."""
        self.slot_status_cache.clear()
        for slot_num in [1, 2, 3, 4]:
            filename = self.save_slots[slot_num]
            try:
                if os.path.exists(filename):
                    with open(filename, 'r') as f:
                        game_state = json.load(f)
                    self.slot_status_cache[slot_num] = game_state
                else:
                    self.slot_status_cache[slot_num] = None
            except (IOError, json.JSONDecodeError):
                self.slot_status_cache[slot_num] = None

    def handle_event(self):
        """
        Handle Pygame events for save file selection.
        Returns:
            str: 'close' if back button clicked, 'delete_{slot}' if delete button clicked,
                 'start_{slot}' if save slot selected, or None if no action
        """
        pos = pygame.mouse.get_pos()  # Mouse coordinates
        
        # Check delete buttons first
        for slot_num in [1, 2, 3, 4]:
            if self.delete_slot_buttons[slot_num].is_clicked(pos):
                self.audio_manager.play_sfx("button_click")
                self.delete_game_file(slot_num)
                self.refresh_slot_status()
                return f"delete_{slot_num}"
        
        # Check save slot buttons
        for slot_num in [1, 2, 3, 4]:
            if self.save_slot_buttons[slot_num].is_clicked(pos):
                self.audio_manager.play_sfx("button_click")
                self.current_slot = slot_num
                
                # Try to load existing save
                loaded_state = self.load_game_file(slot_num)
                if loaded_state:
                    self.game_state = loaded_state
                else:
                    # Create new save file for this slot
                    self.create_game_file(slot_num)
                    self.game_state = {
                        "level": 1,
                        "score": 0,
                        "player_position": [0, 0],
                        "inventory": []
                    }
                
                # Return signal to start game with this slot
                return f"start_{slot_num}"
        
        # Check close button
        if self.close_button.is_clicked(pos):
            self.audio_manager.play_sfx("button_click")
            return "close"
        
        return None 
    
    def draw(self, screen):
        """
        Draw the save file selection screen.
        Args:
            screen: Pygame screen surface to draw on.
        """
        screen.fill(config.dark_blue)
        
        # Draw title
        title_text = config.super_title_font.render("Select Save Slot", True, config.white)
        title_rect = title_text.get_rect(center=(config.screen_width/2, int(config.screen_height/2 - 300 * config.scale_y)))
        screen.blit(title_text, title_rect)  
        
        # Draw save slot buttons with status
        for slot_num in [1, 2, 3, 4]:
            button = self.save_slot_buttons[slot_num]
            button.draw(screen)
            
            # Use cached status instead of loading every frame
            game_state = self.slot_status_cache.get(slot_num)
            if game_state:
                status = f"Level {game_state.get('level', 1)} - Score: {game_state.get('score', 0)}"
                status_text = self.status_font.render(status, True, config.gray)
                status_rect = status_text.get_rect(center=(config.screen_width/2, button.y + int(30 * config.scale_y)))
                screen.blit(status_text, status_rect)
            else:
                status_text = self.status_font.render("Empty Slot", True, config.gray)
                status_rect = status_text.get_rect(center=(config.screen_width/2, button.y + int(30 * config.scale_y)))
                screen.blit(status_text, status_rect)
        
        # Draw delete icon if loaded
        if self.delete_icon:
            icon_rect = self.delete_icon.get_rect(center=(config.screen_width/2, int(config.screen_height/2 - 350 * config.scale_y)))
            screen.blit(self.delete_icon, icon_rect)
        
        # Draw delete slot buttons
        for slot_num in [1, 2, 3, 4]:
            button = self.delete_slot_buttons[slot_num]
            button.draw(screen)

        # Draw back button
        self.close_button.draw(screen)

        

#title_img = pygame.image.load(os.path.join(os.path.dirname(__file__), "../assets/images/Title.png"))