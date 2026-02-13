import pygame
import os
import json
import config
from button import Button
from audio import AudioManager
from hornet import Hornet
from animation import Animation


class SaveSlotButton:
    """Custom button for save slots with hover pointers and background."""
    
    def __init__(self, x: int, y: int, width: int, height: int, slot_num: int, save_exists: bool, background_img=None):
        """
        Initialize a save slot button.
        Args:
            x (int): X position (top-left corner)
            y (int): Y position (top-left corner)
            width (int): Width of the button
            height (int): Height of the button
            slot_num (int): Save slot number
            save_exists (bool): Whether save file exists
            background_img: Background image if save exists
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.slot_num = slot_num
        self.save_exists = save_exists
        self.background_img = background_img
        self.rect = pygame.Rect(x, y, width, height)
        
        # Load cursor pointer for hover effect (different from button.py pointer)
        cursor_path = os.path.join(os.path.dirname(__file__), "../assets/images/Cursor.png")
        if os.path.exists(cursor_path):
            self.hover_pointer = pygame.image.load(cursor_path).convert_alpha()
            # Scale cursor to appropriate size
            pointer_size = int(40 * config.scale_x)
            self.hover_pointer = pygame.transform.scale(self.hover_pointer, (pointer_size, pointer_size))
        else:
            self.hover_pointer = None
        
        
        # Font for "New File" text
        self.font = config.get_font(int(36 * config.scale_y))
        self.title_font = config.get_title_font(int(28 * config.scale_y))
        
        # State
        self.is_hovering = False
        self.active = True
        
    def update_save_status(self, save_exists: bool, background_img=None):
        """Update whether save exists and background image."""
        self.save_exists = save_exists
        self.background_img = background_img
    
    def update(self, dt: float):
        """Update button state."""
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovering = self.rect.collidepoint(mouse_pos) and self.active
    
    def draw(self, screen: pygame.Surface):
        """Draw the save slot button."""
        # Draw background or "New File" text
        if self.save_exists and self.background_img:
            # Draw background image
            screen.blit(self.background_img, (self.x, self.y))
        else:
            # Draw empty slot with "New File" text
            pygame.draw.rect(screen, config.dark_gray, self.rect)
            pygame.draw.rect(screen, config.gray, self.rect, 3)  # Border
            
            new_file_text = self.font.render("New File", True, config.white)
            text_rect = new_file_text.get_rect(center=self.rect.center)
            screen.blit(new_file_text, text_rect)
        
        # Draw border when hovering
        if self.is_hovering:
            pygame.draw.rect(screen, config.white, self.rect, 4)
            
            # Draw cursor pointers on both sides
            if self.hover_pointer:
                # Left pointer
                left_pointer_rect = self.hover_pointer.get_rect(
                    right=self.rect.left - 20, 
                    centery=self.rect.centery
                )
                screen.blit(self.hover_pointer, left_pointer_rect)
                
                # Right pointer
                right_pointer_rect = self.hover_pointer.get_rect(
                    left=self.rect.right + 20, 
                    centery=self.rect.centery
                )
                screen.blit(self.hover_pointer, right_pointer_rect)
    
    def is_clicked(self, pos):
        """Check if button is clicked."""
        return self.rect.collidepoint(pos) and self.active


class TrashButton:
    """Custom trash button with hover animation and pointer effects."""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        """
        Initialize a trash button.
        Args:
            x (int): X position (center)
            y (int): Y position (center)
            width (int): Width of the button
            height (int): Height of the button
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x - width//2, y - height//2, width, height)
        
        # Load trash icon animation (2 frames: normal and hover)
        trash_path = os.path.join(os.path.dirname(__file__), "../assets/images/trash.png")
        if os.path.exists(trash_path):
            trash_sheet = pygame.image.load(trash_path).convert_alpha()
            # Assuming trash.png has 2 frames side by side
            sheet_width = trash_sheet.get_width()
            sheet_height = trash_sheet.get_height()
            frame_width = sheet_width // 2  # 2 frames
            
            # Extract frames
            self.trash_normal = trash_sheet.subsurface(pygame.Rect(0, 0, frame_width, sheet_height))
            self.trash_hover = trash_sheet.subsurface(pygame.Rect(frame_width, 0, frame_width, sheet_height))
            
            # Scale frames
            self.trash_normal = pygame.transform.scale(self.trash_normal, (width, height))
            self.trash_hover = pygame.transform.scale(self.trash_hover, (width, height))
        else:
            # Fallback to colored rectangles
            self.trash_normal = pygame.Surface((width, height))
            self.trash_normal.fill(config.red)
            self.trash_hover = pygame.Surface((width, height))
            self.trash_hover.fill(config.yellow)
        
        # Pointer animation (same as button module)
        pointer_sheet = os.path.join(os.path.dirname(__file__), "../assets/images/pointer.png")
        self.pointer_anim = Animation(pointer_sheet, frame_width=36, frame_height=44)
        self._load_pointer_animations()
        
        # State
        self.is_hovering = False
        self.is_pressed = False
        self.active = True
        self.current_state = "normal"
        self.press_timer = 0.0
        self.press_duration = 0.12
        self.was_hovering = False
    
    def _load_pointer_animations(self):
        """Load pointer animations from the spritesheet."""
        # Hover state
        self.pointer_anim.add_animation(
            "hover",
            row=0,
            start_col=0,
            num_frames=10,
            speed=0.01,
            loop=False
        )
        
        # Pressed state
        self.pointer_anim.add_animation(
            "pressed",
            row=1,
            start_col=0,
            num_frames=10,
            speed=0.01,
            loop=False
        )
        
        # Release state
        self.pointer_anim.add_animation(
            "release",
            row=1,
            start_col=0,
            num_frames=10,
            speed=0.01,
            loop=False
        )
    
    def update(self, dt: float):
        """Update button state and animation."""
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovering = self.rect.collidepoint(mouse_pos) and self.active
        
        # Update pointer animation state
        if self.press_timer > 0:
            self.press_timer = max(0.0, self.press_timer - dt)
            new_state = "pressed"
        elif self.is_hovering:
            new_state = "hover"
        else:
            # Determine if we should play release animation or go to normal
            if self.was_hovering:
                new_state = "release"
            else:
                new_state = "normal"
        
        # Change animation if state changed
        if new_state != self.current_state:
            self.current_state = new_state
            if new_state in ("pressed", "release", "hover"):
                # Play animation forward
                self.pointer_anim.set_animation(new_state, reset=True, reverse=False)
        
        # Update tracking for hover state
        if self.is_hovering and not self.was_hovering:
            self.was_hovering = True
        elif not self.is_hovering and self.was_hovering and self.current_state == "normal":
            self.was_hovering = False
        
        # Update animation
        if self.current_state != "normal":
            self.pointer_anim.update(dt)
    
    def draw(self, screen: pygame.Surface):
        """Draw the trash button with pointer animation when hovering."""
        # Draw trash icon (frame based on hover state)
        if self.is_hovering:
            screen.blit(self.trash_hover, self.rect.topleft)
        else:
            screen.blit(self.trash_normal, self.rect.topleft)
        
        # Draw pointers when hovering or pressed
        if self.is_hovering or self.press_timer > 0:
            # Get current pointer frame based on state
            if self.current_state == "normal":
                pointer_frame = self.pointer_anim.extract_frames(0, 0, 1)[0]
            else:
                pointer_frame = self.pointer_anim.get_current_frame()
            
            # Draw left pointer
            left_rect = pointer_frame.get_rect(right=self.rect.left - 10, centery=self.y)
            screen.blit(pointer_frame, left_rect)
            
            # Draw right pointer
            right_pointer = pygame.transform.flip(pointer_frame, True, False)
            right_rect = right_pointer.get_rect(left=self.rect.right + 10, centery=self.y)
            screen.blit(right_pointer, right_rect)
    
    def is_clicked(self, pos):
        """Check if button is clicked."""
        return self.rect.collidepoint(pos) and self.active
    
    def press(self):
        """Trigger the button press animation."""
        self.press_timer = self.press_duration

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

        # Cache for save slot status to avoid repeated loading
        self.slot_status_cache = {}
        
        # Initialize cache
        self.refresh_slot_status()
        
        # Pre-load font for status text using config's cached fonts
        self.status_font = config.get_font(int(20 * config.scale_y))
        
        # Load background image for existing save files
        played_file_path = os.path.join(os.path.dirname(__file__), "../assets/images/mosscave_area_art.png")
        self.played_file = self._load_and_scale_image(played_file_path, int(353*config.scale_x), int(640*config.scale_y))
        

        # Create custom save slot buttons
        slot_width = int(353 * config.scale_x)
        slot_height = int(640 * config.scale_y)
        slot_spacing = int(400 * config.scale_x)
        start_x = int(config.screen_width / 2 - 2 * slot_spacing + 14)  # Need to figure out how to scale the 14 pixel offset for the border
        start_y = int(200 * config.scale_y)
        
        self.save_slot_buttons = {}
        self.trash_buttons = {}
        
        for i in range(1, 5):
            x = start_x + (i - 1) * slot_spacing
            save_exists = self.slot_status_cache.get(i) is not None
            bg_img = self.played_file if save_exists else None

            self.save_slot_buttons[i] = SaveSlotButton(
                x, start_y, slot_width, slot_height, i, save_exists, bg_img
            )
            
            # Trash button at bottom of save slot
            trash_size = int(60 * config.scale_x)
            trash_x = x + slot_width // 2
            trash_y = start_y + slot_height + int(40 * config.scale_y)
            self.trash_buttons[i] = TrashButton(trash_x, trash_y, trash_size, trash_size)
        
        # Back button
        button_font_size = int(40 * config.scale_y)
        self.close_button = Button(
            config.screen_width/2, 
            config.screen_height - 100, 
            "Back", 
            config.white, 
            config.font_path, 
            button_font_size
        )

    def _load_and_scale_image(self, image_path, width, height):
        """
        Load and scale an image.
        Args:
            image_path (str): Path to the image file.
            width (int): Target width.
            height (int): Target height.
        Returns:
            pygame.Surface: Scaled image surface.
        """
        if os.path.exists(image_path):
            image = pygame.image.load(image_path).convert_alpha()
            return pygame.transform.scale(image, (width, height))
        else:
            # Return a placeholder surface if image doesn't exist
            surface = pygame.Surface((width, height))
            surface.fill((100, 100, 100))
            return surface

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
        
        # Check trash buttons first (they have priority)
        for slot_num in [1, 2, 3, 4]:
            if self.trash_buttons[slot_num].is_clicked(pos):
                self.audio_manager.play_sfx("button_click")
                self.trash_buttons[slot_num].press()
                self.delete_game_file(slot_num)
                self.refresh_slot_status()
                # Update save slot button status
                save_exists = self.slot_status_cache.get(slot_num) is not None
                bg_img = self.played_file if save_exists else None
                self.save_slot_buttons[slot_num].update_save_status(save_exists, bg_img)
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
                    # Update the button status
                    self.save_slot_buttons[slot_num].update_save_status(True, self.played_file)
                
                # Return signal to start game with this slot
                return f"start_{slot_num}"
        
        # Check close button
        if self.close_button.is_clicked(pos):
            self.audio_manager.play_sfx("button_click")
            return "close"
        
        return None 
    def update(self, dt: float):
        """
        Update all button states and animations.
        Args:
            dt (float): Delta time since last update.
        """
        # Update all save slot buttons
        for slot_num in [1, 2, 3, 4]:
            self.save_slot_buttons[slot_num].update(dt)
            self.trash_buttons[slot_num].update(dt)
        
        # Update close button
        self.close_button.update(dt)
    
    def draw(self, screen):
        """
        Draw the save file selection screen.
        Args:
            screen: Pygame screen surface to draw on.
        """
        screen.fill(config.dark_blue)
        
        # Draw title
        title_text = config.super_title_font.render("Select Save Slot", True, config.white)
        title_rect = title_text.get_rect(center=(config.screen_width/2, int(100 * config.scale_y)))
        screen.blit(title_text, title_rect) 
        
        # Draw save slot buttons with status and trash buttons
        for slot_num in [1, 2, 3, 4]:
            # Draw save slot button
            button = self.save_slot_buttons[slot_num]
            button.draw(screen)
            

            
            # Draw save info text if save exists
            game_state = self.slot_status_cache.get(slot_num)
            if game_state:
                # Draw slot number above the save
                slot_text = config.get_title_font(int(32 * config.scale_y)).render(f"Slot {slot_num}", True, config.white)
                slot_rect = slot_text.get_rect(centerx=button.rect.centerx, bottom=button.rect.top - int(10 * config.scale_y))
                screen.blit(slot_text, slot_rect)
                
                # Draw level and score info on the save image
                level_text = self.status_font.render(f"Level {game_state.get('level', 1)}", True, config.white)
                level_rect = level_text.get_rect(centerx=button.rect.centerx, top=button.rect.top + int(20 * config.scale_y))
                screen.blit(level_text, level_rect)
                
                score_text = self.status_font.render(f"Score: {game_state.get('score', 0)}", True, config.white)
                score_rect = score_text.get_rect(centerx=button.rect.centerx, top=level_rect.bottom + int(10 * config.scale_y))
                screen.blit(score_text, score_rect)
            else:
                # Draw slot number for empty slots
                slot_text = config.get_title_font(int(32 * config.scale_y)).render(f"Slot {slot_num}", True, config.white)
                slot_rect = slot_text.get_rect(centerx=button.rect.centerx, bottom=button.rect.top - int(10 * config.scale_y))
                screen.blit(slot_text, slot_rect)
            
            # Draw trash button
            self.trash_buttons[slot_num].draw(screen)
        # Load borders for all save files
        borders_path = os.path.join(os.path.dirname(__file__), "../assets/images/save_file_border.png")
        self.borders = self._load_and_scale_image(borders_path, int(377*config.scale_x), int(669*config.scale_y))
        slot_spacing = int(400 * config.scale_x)
        start_x = int(config.screen_width / 2 - 2 * slot_spacing)
        start_y = int(200 * config.scale_y - 14) # Need to figure out how to scale the 14 pixel offset
        #Draw borders
        for i in range(0,4):
            screen.blit(self.borders, (start_x + i * slot_spacing , start_y))
        
        # Draw back button
        self.close_button.draw(screen)