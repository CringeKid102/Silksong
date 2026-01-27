import pygame
import os
import json

class SaveFile:
    """"Class to handle saving and loading game state to/from JSON files."""

    def __init__(self):
        # Define the 3 save slots
        self.save_slots = {
            1: "savegame_1.json",
            2: "savegame_2.json",
            3: "savegame_3.json"
        }

    def create_game_file(self, slot=1):
        """
        Creates a new game file with default game state for the specified slot.
        Args:
            slot (int): The save slot number (1, 2, or 3).
        """
        if slot not in self.save_slots:
            print(f"Invalid slot number. Please use 1, 2, or 3.")
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
        except IOError as e:
            print(f"An error occurred while creating the game file: {e}")

    def save_game_file(self, game_state, slot=1):
        """
        Saves the current game state to a JSON file in the specified slot.
        Args:
            game_state (dict): A dictionary containing the current game state.
            slot (int): The save slot number (1, 2, or 3).
        """
        if slot not in self.save_slots:
            print(f"Invalid slot number. Please use 1, 2, or 3.")
            return
        
        filename = self.save_slots[slot]
        try:
            with open(filename, 'w') as f:
                json.dump(game_state, f, indent=4)
            print(f"Game state saved to {filename}")
        except IOError as e:
            print(f"An error occurred while saving the game state: {e}")
    
    def load_game_file(self, slot=1):
        """
        Loads the game state from a JSON file in the specified slot.
        Args:
            slot (int): The save slot number (1, 2, or 3).
        Returns:
            dict: The loaded game state, or None if the file doesn't exist or an error occurs.
        """
        if slot not in self.save_slots:
            print(f"Invalid slot number. Please use 1, 2, or 3.")
            return None
        
        filename = self.save_slots[slot]
        try:
            if not os.path.exists(filename):
                print(f"Save file not found: {filename}")
                return None
            
            with open(filename, 'r') as f:
                game_state = json.load(f)
            print(f"Game state loaded from {filename}")
            return game_state
        except IOError as e:
            print(f"An error occurred while loading the game state: {e}")
            return None
    
    def draw_save_files(self, screen, save_slot_buttons, config):
        """
        Draw the save file selection screen.
        Args:
            screen: Pygame screen surface to draw on.
            save_slot_buttons: Dictionary of buttons for save slots.
            config: Configuration module with colors, fonts, and scaling.
        """
        screen.fill(config.dark_blue)
        
        # Draw title
        title_text = config.font.render("Select Save Slot", True, config.white)
        title_rect = title_text.get_rect(center=(config.screen_width/2, int(config.screen_height/2 - 300 * config.scale_y)))
        screen.blit(title_text, title_rect)
        
        # Draw save slot buttons with status
        for slot_num in [1, 2, 3]:
            button = save_slot_buttons[slot_num]
            button.draw(screen)
            
            # Check if save file exists and display status
            game_state = self.load_game_file(slot_num)
            if game_state:
                status = f"Level {game_state.get('level', 1)} - Score: {game_state.get('score', 0)}"
                status_font = pygame.font.Font(config.title_font_path, int(20 * config.scale_y))
                status_text = status_font.render(status, True, config.gray)
                status_rect = status_text.get_rect(center=(config.screen_width/2, button.y + int(30 * config.scale_y)))
                screen.blit(status_text, status_rect)
            else:
                status_font = pygame.font.Font(config.title_font_path, int(20 * config.scale_y))
                status_text = status_font.render("Empty Slot", True, config.gray)
                status_rect = status_text.get_rect(center=(config.screen_width/2, button.y + int(30 * config.scale_y)))
                screen.blit(status_text, status_rect)
        
        # Draw back button
        save_slot_buttons["back"].draw(screen)