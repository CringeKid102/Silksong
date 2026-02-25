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
from hornet import Hornet
from mossgrub import MossGrub


# Initialize pygame
pygame.init()

class Silksong:

    # Class-level image cache to avoid reloading
    _image_cache = {}
    
    @classmethod
    def _load_and_scale_image(cls, path, width, height):
        """Load and scale an image with caching."""
        cache_key = (path, width, height)
        if cache_key not in cls._image_cache:
            img = pygame.image.load(path)
            if img.get_alpha() is not None:
                img = img.convert_alpha()
            else:
                img = img.convert()
            cls._image_cache[cache_key] = pygame.transform.scale(img, (width, height))
        return cls._image_cache[cache_key]

    def __init__(self):
        """Initialize the game."""
        # Create fullscreen display at actual screen size
        self.screen = pygame.display.set_mode((config.screen_width, config.screen_height), pygame.FULLSCREEN)
        
        pygame.display.set_caption("Silksong")
        self.running = True
        self.state = "title screen"
        self.clock = pygame.time.Clock()
        
        # Load and scale title image using cache
        title_img_path = os.path.join(os.path.dirname(__file__), "../assets/images/title.png")
        self.title_image = self._load_and_scale_image(title_img_path, int(880 * config.scale_x), int(440 * config.scale_y))
        
        # Load and scale title element (needle)
        title_needle_path = os.path.join(os.path.dirname(__file__), "../assets/images/hornet_title_screen_boneforest_0003_hornet_needle.png")
        title_needle = self._load_and_scale_image(title_needle_path, int(186*config.scale_x), int(864*config.scale_y))
        self.title_needle = title_needle

        
        # Load and scale title element (pin)
        title_pin_path = os.path.join(os.path.dirname(__file__), "../assets/images/hornet_title_screen_boneforest_0002_lace_pin.png")
        title_pin_scaled = self._load_and_scale_image(title_pin_path, int(94*config.scale_x), int(613*config.scale_y))
        self.title_pin = pygame.transform.rotate(title_pin_scaled, -5)  # Rotate 15 degrees to the right (negative = clockwise)

        # Load and scale title element (boulder)
        title_boulder_path = os.path.join(os.path.dirname(__file__), "../assets/images/hornet_title_screen_boneforest_0000_bone_cliff_01.png")
        self.title_boulder = self._load_and_scale_image(title_boulder_path, int(552*config.scale_x), int(236*config.scale_y))

        # Load and scale title element (spike)
        title_spike_path = os.path.join(os.path.dirname(__file__), "../assets/images/hornet_title_screen_boneforest_0001_bone_cliff_02.png")
        self.title_spike = self._load_and_scale_image(title_spike_path, int(197*config.scale_x), int(142*config.scale_y))

        # Load and scale title element (pin)
        #title_pin = pygame.image.load(os.path.join(os.path.dirname(__file__), ""))
        

        # Load and scale background image using cache
        background_img_path = os.path.join(os.path.dirname(__file__), "../assets/images/title_screen_bg.jpg")
        self.background_image = self._load_and_scale_image(background_img_path, config.screen_width, config.screen_height)

        # Load custom cursor image
        self.cursor_image = None
        self.cursor_hotspot = (0, 0)
        cursor_candidates = [
            os.path.join(os.path.dirname(__file__), "../assets/images/cursor.png"),
            os.path.join(os.path.dirname(__file__), "../assets/images/Cursor.png"),
        ]
        for cursor_path in cursor_candidates:
            if os.path.exists(cursor_path):
                self.cursor_image = pygame.image.load(cursor_path).convert_alpha()
                break
        pygame.mouse.set_visible(self.cursor_image is None)

        
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
        self.settings_menu = SettingsMenu(config.screen_width, config.screen_height)
        self.settings_menu.game = self  # Link settings menu to game for save/load
        self.settings_menu.transition_manager = self.transition_manager  # Link transition manager to settings
        self.settings_menu.load_progress()

        # Create save file menu
        self.save_file = SaveFile()
        
        # Initialize particle system for title screen effects
        self.particle_system = ParticleSystem(config.screen_width, config.screen_height)
        ember_image_path = os.path.join(os.path.dirname(__file__), "../assets/images/ember_particle.png")
        self.particle_system.load_ember_image(ember_image_path)
        
        # Create buttons
        self.create_buttons() # Normal buttons
        
        # Initialize player (Hornet)
        self.player = None  # Will be created when game starts
        self.mossgrub = None # Will be created when game starts
        
        # Camera system
        self.camera_x = 0
        self.camera_y = 0
        self.mouse_locked = False

        # Autosave timer for in-game progress
        self.autosave_interval = 1.0
        self.autosave_timer = 0.0

        # Combat tuning
        self.player_contact_damage_cooldown = 0.75
        self.player_contact_damage_timer = 0.0
        self.attack_damage = 1
        self.attack_range = 70
        self.attack_height_padding = 25
        self.silk_per_hit = 1

    def _update_mouse_lock(self):
        """Lock mouse during gameplay and release it in non-game states."""
        if self.state == "game":
            if not self.mouse_locked:
                pygame.event.set_grab(True)
                pygame.mouse.get_rel()  # Reset relative movement accumulator
                self.mouse_locked = True
            # Keep cursor pinned to center so it cannot drift
            pygame.mouse.set_pos((config.screen_width // 2, config.screen_height // 2))
        else:
            if self.mouse_locked:
                pygame.event.set_grab(False)
                self.mouse_locked = False

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

    def update_title_screen(self, dt):
        for button in self.buttons.values():
            button.update(dt)
        
        # Enable ember spawning and update particle system
        self.particle_system.enable_ember_spawning(True)
        self.particle_system.update(dt)
    
    def update_settings(self, dt):
        self.settings_menu.update(dt)
    
    def update_save_files(self, dt):
        self.save_file.update(dt)
    
    def update_cutscene(self, dt):
        pass

    def update_game(self, dt):
        if self.player:
            # Get keyboard state
            keys = pygame.key.get_pressed()
            camera_movement = self.player.handle_input(keys)
            self.player.update(dt)

            if self.player_contact_damage_timer > 0.0:
                self.player_contact_damage_timer = max(0.0, self.player_contact_damage_timer - dt)
            
            # Update camera position based on player movement
            if camera_movement:
                self.camera_x += camera_movement[0] * dt
                self.camera_y += camera_movement[1] * dt

            # Update enemy and resolve combat interactions
            if self.mossgrub and self.mossgrub.health > 0:
                self.mossgrub.update(self.player.rect.centerx + 400, self.player.rect.centerx - 400, dt)

                player_world_rect = self.player.rect.copy()
                player_world_rect.x += int(self.camera_x)

                if self.player.consume_attack_trigger():
                    if self.player.facing_right:
                        attack_rect = pygame.Rect(
                            player_world_rect.right,
                            player_world_rect.top + self.attack_height_padding,
                            self.attack_range,
                            max(10, player_world_rect.height - self.attack_height_padding * 2)
                        )
                    else:
                        attack_rect = pygame.Rect(
                            player_world_rect.left - self.attack_range,
                            player_world_rect.top + self.attack_height_padding,
                            self.attack_range,
                            max(10, player_world_rect.height - self.attack_height_padding * 2)
                        )

                    if attack_rect.colliderect(self.mossgrub.rect):
                        self.mossgrub.take_damage(self.attack_damage)
                        self.player.gain_silk(self.silk_per_hit)

                if player_world_rect.colliderect(self.mossgrub.rect) and self.player_contact_damage_timer <= 0.0:
                    self.player.take_damage(1)
                    self.player_contact_damage_timer = self.player_contact_damage_cooldown

            # Periodically persist player state in current save slot
            self.autosave_timer += dt
            if self.autosave_timer >= self.autosave_interval:
                self.save_current_game_state()
                self.autosave_timer = 0.0

    def save_current_game_state(self):
        """Save core player progress to the currently selected save slot."""
        if not self.player or self.current_slot not in self.save_file.save_slots:
            return

        base_state = dict(self.game_state) if isinstance(self.game_state, dict) else {}
        base_state.update({
            "player_position": [self.player.rect.x, self.player.rect.y],
            "player_health": self.player.health,
            "player_silk": self.player.silk,
        })
        self.save_file.save_game_file(base_state, self.current_slot)
        self.game_state = base_state
    
    def change_state(self, new_state):
        """Change game state with black fade transition."""
        def on_state_change(target_state):
            self.state = target_state
            # Refresh save slot cache when entering save files screen
            if target_state == "save files":
                self.save_file.refresh_slot_status()
        
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
        
        # Draw ember particles
        self.particle_system.draw_particles(self.screen)
        
        # Draw the Silksong title image
        title_rect = self.title_image.get_rect(center=(config.screen_width/2, int(config.screen_height/2 - 200 * config.scale_y)))
        self.screen.blit(self.title_image, title_rect)
        
        # Draw title spikes (you can adjust positions as needed)
        self.screen.blit(self.title_needle, (int(1500 * config.scale_x), int(175 * config.scale_y)))
        self.screen.blit(self.title_pin, (int(1300 * config.scale_x), int(475 * config.scale_y)))
        self.screen.blit(self.title_boulder, (int(1050 * config.scale_x), int(850 * config.scale_y)))
        self.screen.blit(self.title_spike, (int(1050 * config.scale_x), int(850 * config.scale_y)))

        # Draw buttons
        for button in self.buttons.values():
            button.draw(self.screen)
                
    def draw_settings(self):
        self.screen.blit(self.background_image, (0, 0))
        self.settings_menu.draw(self.screen, config.font)

    def draw_save_file(self):
        self.screen.blit(self.background_image, (0, 0))
        self.save_file.draw(self.screen)
    
    def draw_cutscene(self):
        self.screen.blit(self.background_image, (0, 0))
    
    def draw_game(self):
        # Draw background (could add parallax later)
        # Get the look offset from the player (camera pans up/down)
        look_y = self.player.camera_look_y if self.player else 0

        bg_width, bg_height = self.background_image.get_size()
        bg_x = int(-self.camera_x * 0.5)
        bg_y = int(-self.camera_y * 0.5 - look_y * 0.5)

        # Tile background to prevent side-edge artifacts when camera offsets shift
        base_x = (bg_x % bg_width) - bg_width
        base_y = (bg_y % bg_height) - bg_height
        for x_offset in (0, bg_width, bg_width * 2):
            for y_offset in (0, bg_height, bg_height * 2):
                self.screen.blit(self.background_image, (base_x + x_offset, base_y + y_offset))
        
        # Draw ground line for visual reference (with camera offset)
        hornet_width = self.player.rect.width if self.player else 0
        ground_y = config.screen_height // 2 + hornet_width
        line_y = int(ground_y - self.camera_y - look_y)
        pygame.draw.line(self.screen, (255, 255, 255), (int(-self.camera_x), line_y), (int(config.screen_width * 3 - self.camera_x), line_y), 2)
        
        # Draw player (offset by look_y so player moves with the world)
        if self.player:
            self.player.draw(self.screen, look_y_offset=-look_y)

        # Draw enemy with camera offset
        if self.mossgrub and self.mossgrub.health > 0:
            enemy_draw_rect = self.mossgrub.rect.copy()
            enemy_draw_rect.x -= int(self.camera_x)
            enemy_draw_rect.y -= int(self.camera_y + look_y)

            if self.mossgrub.facing_right == 1:
                self.screen.blit(self.mossgrub.image, enemy_draw_rect)
            else:
                self.screen.blit(self.mossgrub.image_flipped, enemy_draw_rect)

        # HUD: health, silk, and healing state
        if self.player:
            hud_font = config.get_font(int(28 * config.scale_y))
            hp_text = hud_font.render(f"HP: {self.player.health}/{self.player.max_health}", True, config.white)
            silk_text = hud_font.render(f"Silk: {self.player.silk}", True, config.white)
            self.screen.blit(hp_text, (25, 20))
            self.screen.blit(silk_text, (25, 55))

            if self.player.is_healing:
                heal_text = hud_font.render(f"Healing... {self.player.heal_channel_timer:.1f}s", True, config.white)
                self.screen.blit(heal_text, (25, 90))
    
    def draw(self):
        """Render the game."""
        if self.cursor_image:
            pygame.mouse.set_visible(False)
        else:
            pygame.mouse.set_visible(self.state != "game")

        if self.state == "title screen":
            self.draw_title_screen()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "save files":
            self.draw_save_file()
        elif self.state == "cutscene":
            self.draw_cutscene()
        elif self.state == "game":
            self.draw_game()

        # Apply brightness setting to the rendered scene (1.0 = normal, 0.0 = fully dark)
        brightness = self.settings_menu.settings_data.get('brightness', 0.8)
        brightness = max(0.0, min(1.0, brightness))
        if brightness < 1.0:
            darkness_alpha = int((1.0 - brightness) * 255)
            brightness_overlay = pygame.Surface((config.screen_width, config.screen_height), pygame.SRCALPHA)
            brightness_overlay.fill((0, 0, 0, darkness_alpha))
            self.screen.blit(brightness_overlay, (0, 0))
        
        # Draw transition overlay on top of everything
        if self.transition_manager.active:
            self.transition_manager.draw(self.screen)

        # Draw custom cursor on top of all UI
        if self.cursor_image and self.state != "game":
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.screen.blit(self.cursor_image, (mouse_x - self.cursor_hotspot[0], mouse_y - self.cursor_hotspot[1]))
        
        pygame.display.flip()

    def update(self, dt):
        """
        Update the game state.
        Args:
            dt (float): Delta time since last update.
        """
        self._update_mouse_lock()

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

            # Temporary: allow quitting with ESC from any state
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
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
                    action = self.save_file.handle_event()
                    if action == "close":
                        # Close button was clicked, return to title screen
                        self.change_state("title screen")
                    elif action and action.startswith("start_"):
                        # Save slot was selected, start game
                        slot_num = int(action.split("_")[1])
                        self.current_slot = slot_num
                        loaded_state = self.save_file.load_game_file(slot_num) or {}
                        self.game_state = loaded_state

                        # Create player when starting game
                        start_x = config.screen_width // 2
                        self.player = Hornet(start_x, 0, config.screen_width, config.screen_height)
                        self.mossgrub = MossGrub(start_x, 0, config.screen_width, config.screen_height)
                        self.player.reset_position(start_x, self.player.ground_level)
                        self.player.on_ground = True
                        self.mossgrub.reset_position(start_x + 240, self.mossgrub.ground_level)
                        self.mossgrub.on_ground = True

                        # Restore player stats from selected save slot
                        saved_health = loaded_state.get("player_health", self.player.health)
                        saved_silk = loaded_state.get("player_silk", self.player.silk)
                        self.player.health = max(0, min(self.player.max_health, int(saved_health)))
                        self.player.silk = max(0, min(self.player.max_silk, int(saved_silk)))

                        saved_position = loaded_state.get("player_position")
                        if isinstance(saved_position, list) and len(saved_position) >= 2:
                            self.player.rect.x = int(saved_position[0])
                            self.player.rect.y = int(saved_position[1])

                        # Reset camera
                        self.camera_x = 0
                        self.camera_y = 0
                        self.player_contact_damage_timer = 0.0
                        self.autosave_timer = 0.0

                        # Persist state immediately so schema stays up-to-date
                        self.save_current_game_state()

                        # Start game
                        self.change_state("game")
                    # Delete actions are handled within save_file.handle_event

    def run(self):
        while self.running:
            dt = self.clock.tick(config.fps) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        # Save one last time before exiting
        self.save_current_game_state()
        
        pygame.quit()
 

# Run the game
if __name__ == "__main__":
    game = Silksong()
    game.run()