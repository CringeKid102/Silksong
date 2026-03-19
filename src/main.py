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
from moss_mother import MossMother


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
        self.game_back_button = Button(
            int(config.screen_width - 90 * config.scale_x),
            int(45 * config.scale_y),
            "Back",
            config.white,
            config.title_font_path,
            int(30 * config.scale_y),
        )
        
        # Initialize player (Hornet)
        self.player = None  # Will be created when game starts
        self.mossgrub = None # Will be created when game starts
        self.mossmother = None # Will be created when game starts
        
        # Camera system
        self.camera_x = 0
        self.camera_y = 0
        self.player_camera_anchor_y = None
        self.mouse_locked = False

        # Cache last saved state so we can save only when something changes
        self._last_saved_signature = None

        # Combat tuning
        self.player_contact_damage_cooldown = 0.75
        self.player_contact_damage_timer = 0.0
        self.attack_damage = 1
        self.silk_per_hit = 1
        self.player_near_bench = False
        self.bench_interact_text = ""
        self._bench_interact_key_down = False
        self.respawn_position = None
        self.ground_colliders = []
        self.world_ground_y = int(config.screen_height * 0.62)

    def _build_ground_colliders(self):
        """Build world-space ground and platform colliders."""
        if not self.player:
            self.ground_colliders = []
            return

        base_y = int(self.world_ground_y)
        start_x = config.screen_width // 2
        self.ground_colliders = [
            # Main ground
            pygame.Rect(-200000, base_y, 400000, 2000),
            # Low platform for ledge climb testing (right of start)
            pygame.Rect(start_x + 400, base_y - 220, 250, 220),
            # Wall jump corridor - left wall
            pygame.Rect(start_x + 800, base_y - 500, 50, 500),
            # Wall jump corridor - right wall
            pygame.Rect(start_x + 1000, base_y - 500, 50, 500),
            # Top platform above wall jump corridor
            pygame.Rect(start_x + 780, base_y - 530, 290, 30),
        ]

        # Keep bench anchored to world ground, not player-specific values.
        if self.player:
            self.player.bench.rect.midbottom = (self.screen.get_width() // 2, base_y)

    def _get_ground_top_at_world_x(self, world_x):
        """Return top Y of the highest ground collider under a world X."""
        top_y = None
        for ground_rect in self.ground_colliders:
            if ground_rect.left <= world_x < ground_rect.right:
                if top_y is None or ground_rect.top < top_y:
                    top_y = ground_rect.top
        return top_y

    def _snap_player_to_ground(self):
        """Snap Hornet onto the ground/platform at current world X and reset vertical state."""
        if not self.player:
            return

        player_world_center_x = int(self.player.rect.centerx + self.camera_x)
        ground_top = self._get_ground_top_at_world_x(player_world_center_x)
        if ground_top is None:
            ground_top = int(self.world_ground_y)

        # Keep player at the anchored screen Y by solving camera_y from desired world bottom.
        self.camera_y = int(ground_top - self.player.rect.bottom)
        self.player.velocity_y = 0
        self.player.on_ground = True

    def _snap_mossgrub_to_ground(self, world_x=None):
        """Snap MossGrub onto the ground/platform at a world X and reset vertical state."""
        if not self.mossgrub:
            return

        if world_x is None:
            world_x = int(self.mossgrub.rect.centerx + self.camera_x)

        ground_top = self._get_ground_top_at_world_x(int(world_x))
        if ground_top is None:
            ground_top = int(self.world_ground_y)

        self.mossgrub.rect.centerx = int(world_x - self.camera_x)
        self.mossgrub.rect.bottom = int(ground_top - self.camera_y)
        self.mossgrub.velocity_y = 0
        self.mossgrub.on_ground = True

    def _update_mouse_lock(self):
        """Keep mouse unlocked so in-game UI remains clickable."""
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
        self.game_back_button.update(dt)

        if self.player is None:
            return

        player = self.player

        # Track camera before updates to compute delta for mossgrub
        prev_camera_x = self.camera_x
        prev_camera_y = self.camera_y

        # Get keyboard state
        keys = pygame.key.get_pressed()
        camera_movement = player.handle_input(keys)

            # Update camera position based on player movement
        if camera_movement:
            self.camera_x += camera_movement[0] * dt
            self.camera_y += camera_movement[1] * dt

        player.update(
            dt,
            collision_rects=self.ground_colliders,
            camera_x=self.camera_x,
            camera_y=self.camera_y
        )

        # Apply wall collision correction from player
        self.camera_x += player.camera_x_correction

            # Keep Hornet vertically anchored on screen and move camera instead.
        if self.player_camera_anchor_y is None:
            self.player_camera_anchor_y = int(player.rect.y)
        vertical_delta = int(player.rect.y - self.player_camera_anchor_y)
        if vertical_delta != 0:
            self.camera_y += vertical_delta
            player.rect.y = int(self.player_camera_anchor_y)

        player_world_rect = player.rect.copy()
        player_world_rect.x += int(self.camera_x)
        player_world_rect.y += int(self.camera_y)

        bench_rect = player.bench.rect
        self.player_near_bench = player_world_rect.colliderect(bench_rect)
        self.bench_interact_text = ""

        interact_pressed = keys[pygame.K_w]
        can_rest = self.player_near_bench and player.on_ground and not player.is_resting
        if can_rest:
            self.bench_interact_text = "Bench - Press W to Rest"
            if interact_pressed and not self._bench_interact_key_down:
                player.start_rest()
                self.respawn_position = [int(player_world_rect.x), int(player_world_rect.y)]
                self.save_current_game_state(force=True)

        self._bench_interact_key_down = interact_pressed

        if player.health <= 0:
            self.respawn_player()
            return

        if self.player_contact_damage_timer > 0.0:
            self.player_contact_damage_timer = max(0.0, self.player_contact_damage_timer - dt)
            
            # Update enemy and resolve combat interactions
            
        total_d = 300
        grubleftground = player.rect.centerx - total_d / 2
        grubrightbound = player.rect.centerx + total_d / 2

        # Compute camera delta this frame for mossgrub
        camera_dx = self.camera_x - prev_camera_x
        camera_dy = self.camera_y - prev_camera_y

        if self.mossgrub and self.mossgrub.health > 0:
            self.mossgrub.update(grubleftground, grubrightbound, dt,
                                collision_rects=self.ground_colliders,
                                camera_x=self.camera_x,
                                camera_y=self.camera_y,
                                camera_dx=camera_dx,
                                camera_dy=camera_dy)

        if self.mossmother and self.mossmother.health > 0:
            self.mossmother.update(grubleftground, grubrightbound, dt,
                                collision_rects=self.ground_colliders,
                                camera_x=self.camera_x,
                                camera_y=self.camera_y,
                                camera_dx=camera_dx,
                                camera_dy=camera_dy,
                                player_world_rect=player_world_rect)

        if player.consume_attack_trigger():
            attack_rect = player.start_attack_hitbox(
                camera_x=self.camera_x,
                camera_y=self.camera_y,
            )

            if self.mossgrub and self.mossgrub.health > 0:
                mossgrub_world = self.mossgrub.rect.copy()
                mossgrub_world.x += int(self.camera_x)
                mossgrub_world.y += int(self.camera_y)
                if attack_rect.colliderect(mossgrub_world):
                    knockback_direction = 1 if player_world_rect.centerx < mossgrub_world.centerx else -1
                    self.mossgrub.take_damage(self.attack_damage, knockback_direction=knockback_direction)
                    player.gain_silk(self.silk_per_hit)

            if self.mossmother and self.mossmother.health > 0:
                mossmother_world = self.mossmother.rect.copy()
                mossmother_world.x += int(self.camera_x)
                mossmother_world.y += int(self.camera_y)
                if attack_rect.colliderect(mossmother_world):
                    knockback_direction = 1 if player_world_rect.centerx < mossmother_world.centerx else -1
                    self.mossmother.take_damage(self.attack_damage, knockback_direction=knockback_direction)
                    player.gain_silk(self.silk_per_hit)

        # Contact damage: compare both in screen space
        if self.mossgrub and self.mossgrub.health > 0 and player.rect.colliderect(self.mossgrub.rect) and self.player_contact_damage_timer <= 0.0:
            mossgrub_world = self.mossgrub.rect.copy()
            mossgrub_world.x += int(self.camera_x)
            mossgrub_world.y += int(self.camera_y)
            knockback_direction = -1 if player_world_rect.centerx < mossgrub_world.centerx else 1
            player.take_damage(1, knockback_direction=knockback_direction)
            self.player_contact_damage_timer = self.player_contact_damage_cooldown

        if self.mossmother and self.mossmother.health > 0:
            mossmother_world = self.mossmother.rect.copy()
            mossmother_world.x += int(self.camera_x)
            mossmother_world.y += int(self.camera_y)

            if self.mossmother.is_attacking:
                if not self.mossmother.attack_contact_registered and mossmother_world.colliderect(player_world_rect):
                    self.mossmother.attack_contact_registered = True
                    self.mossmother.phase_through = True
                    knockback_direction = -1 if player_world_rect.centerx < mossmother_world.centerx else 1
                    player.take_damage(1, knockback_direction=knockback_direction)
                    self.player_contact_damage_timer = self.player_contact_damage_cooldown
            else:
                if player.rect.colliderect(self.mossmother.rect) and self.player_contact_damage_timer <= 0.0:
                    knockback_direction = -1 if player_world_rect.centerx < mossmother_world.centerx else 1
                    player.take_damage(1, knockback_direction=knockback_direction)
                    self.player_contact_damage_timer = self.player_contact_damage_cooldown
        if self.mossgrub and self.mossgrub.health <= 0:
            if self._bench_interact_key_down:
                self.respawn_mossgrub()

        # Persist whenever tracked game state changes (including mid-air positions)
        self.save_current_game_state()

    def respawn_player(self):
        """Respawn Hornet at the latest rested bench position."""
        respawn_x = int(self.player.rect.x)

        if isinstance(self.respawn_position, list) and len(self.respawn_position) >= 2:
            respawn_x = int(self.respawn_position[0])

        # Restore world X from respawn, then snap vertically to actual ground.
        self.camera_x = respawn_x - self.player.rect.x
        self._snap_player_to_ground()

        self.player.velocity_x = 0
        self.player.velocity_y = 0
        self.player.health = self.player.max_health
        self.player.cancel_heal_channel()
        self.player.is_resting = False
        self.player.rest_timer = 0.0
        self.player.velocity_y = 0
        self.player.on_ground = True
        self.player_contact_damage_timer = 0.0
        self.save_current_game_state(force=True)

    def respawn_mossgrub(self):
        """Respawn MossGrub at the latest rested bench position."""
        self.mossgrub.health = self.mossgrub.max_health
        self._snap_mossgrub_to_ground()
        if self.mossmother:
            self.mossmother.health = self.mossmother.max_health
            self.mossmother.reset_position(self.mossmother.rect.centerx, self.mossmother.rect.bottom)
        self.save_current_game_state(force=True)

    def save_current_game_state(self, force=False):
        """Save core player progress to the currently selected save slot."""
        if not self.player or self.current_slot not in self.save_file.save_slots:
            return

        # Player horizontal travel is represented by camera_x, not rect.x.
        # Save world-space position so ground movement persists.
        player_world_x = int(self.player.rect.x + self.camera_x)
        player_world_y = int(self.player.rect.y + self.camera_y)

        mossgrub_position = None
        mossgrub_health = None
        mossmother_position = None
        mossmother_health = None
        if self.mossgrub:
            # Convert screen-space rect to world space for saving
            mossgrub_position = [
                int(self.mossgrub.rect.x + self.camera_x),
                int(self.mossgrub.rect.y + self.camera_y)
            ]
            mossgrub_health = self.mossgrub.health
        if self.mossmother:
            mossmother_position = [
                int(self.mossmother.rect.x + self.camera_x),
                int(self.mossmother.rect.y + self.camera_y)
            ]
            mossmother_health = self.mossmother.health

        state_signature = (
            player_world_x,
            player_world_y,
            self.player.health,
            self.player.silk,
            self.player.facing_right,
            tuple(self.respawn_position) if self.respawn_position else None,
            tuple(mossgrub_position) if mossgrub_position else None,
            mossgrub_health,
            tuple(mossmother_position) if mossmother_position else None,
            mossmother_health,
        )

        if not force and state_signature == self._last_saved_signature:
            return

        base_state = dict(self.game_state) if isinstance(self.game_state, dict) else {}
        base_state.update({
            "player_position": [player_world_x, player_world_y],
            "player_position_space": "world",
            "player_health": self.player.health,
            "player_silk": self.player.silk,
            "player_facing_right": self.player.facing_right,
            "player_respawn_position": self.respawn_position,
            "mossgrub_position": mossgrub_position,
            "mossgrub_health": mossgrub_health,
            "mossmother_position": mossmother_position,
            "mossmother_health": mossmother_health,
        })
        self.save_file.save_game_file(base_state, self.current_slot)
        self.game_state = base_state
        self._last_saved_signature = state_signature
    
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
        
        # Draw ground and platforms
        if self.ground_colliders:
            for cr in self.ground_colliders:
                screen_x = int(cr.left - self.camera_x)
                screen_y = int(cr.top - self.camera_y - look_y)
                if cr.width > 5000:
                    # Main ground: blue highlighted strip
                    ground_band = pygame.Rect(0, screen_y, config.screen_width, max(2, config.screen_height - screen_y))
                    pygame.draw.rect(self.screen, (55, 95, 165), ground_band)
                    pygame.draw.line(self.screen, (140, 185, 255), (0, screen_y), (config.screen_width, screen_y), 3)
                else:
                    # Elevated platform: draw filled rectangle
                    platform_rect = pygame.Rect(screen_x, screen_y, cr.width, cr.height)
                    pygame.draw.rect(self.screen, (100, 100, 120), platform_rect)
                    pygame.draw.rect(self.screen, (200, 200, 220), platform_rect, 2)
        
        # Draw player (offset by look_y so player moves with the world)
        if self.player:
            self.player.bench.draw(self.screen, camera_x=self.camera_x, camera_y=self.camera_y, look_y_offset=look_y)
            self.player.draw(self.screen, look_y_offset=-look_y)

            # Debug: highlight Hornet collision rect.
            player_debug_rect = self.player.rect.copy()
            player_debug_rect.y -= int(look_y)
            pygame.draw.rect(self.screen, (0, 255, 80), player_debug_rect, 2)

            # Debug: highlight Hornet attack hitbox while active.
            if self.player.attack_hitbox:
                attack_draw_rect = self.player.attack_hitbox.copy()
                attack_draw_rect.x -= int(self.camera_x)
                attack_draw_rect.y -= int(self.camera_y + look_y)

                attack_fill = pygame.Surface((attack_draw_rect.width, attack_draw_rect.height), pygame.SRCALPHA)
                attack_fill.fill((255, 200, 60, 85))
                self.screen.blit(attack_fill, attack_draw_rect.topleft)
                pygame.draw.rect(self.screen, (255, 230, 120), attack_draw_rect, 2)

        # Draw MossGrub (rect is now in screen space)
        if self.mossgrub and self.mossgrub.health > 0:
            enemy_draw_rect = self.mossgrub.rect.copy()
            enemy_draw_rect.y -= int(look_y)

            if self.mossgrub.facing_right == 1:
                self.screen.blit(self.mossgrub.image_flipped, enemy_draw_rect)
            else:
                self.screen.blit(self.mossgrub.image, enemy_draw_rect)

            pygame.draw.rect(self.screen, (255, 70, 70), enemy_draw_rect, 2)

        # Draw Moss Mother (rect is now in screen space)
        if self.mossmother and self.mossmother.health > 0:
            mother_draw_rect = self.mossmother.rect.copy()
            mother_draw_rect.y -= int(look_y)

            if self.mossmother.facing_right:
                self.screen.blit(self.mossmother.image, mother_draw_rect)
            else:
                self.screen.blit(self.mossmother.image_flipped, mother_draw_rect)

            pygame.draw.rect(self.screen, (255, 170, 70), mother_draw_rect, 2)

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

            if self.player.is_resting:
                rest_text = hud_font.render("Resting...", True, config.white)
                self.screen.blit(rest_text, (25, 125))

            if self.bench_interact_text:
                prompt_font = config.get_font(int(32 * config.scale_y))
                prompt_surface = prompt_font.render(self.bench_interact_text, True, config.white)
                prompt_rect = prompt_surface.get_rect(center=(config.screen_width // 2, int(130 * config.scale_y)))
                bg_rect = prompt_rect.inflate(24, 14)
                bg = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 150))
                self.screen.blit(bg, bg_rect.topleft)
                self.screen.blit(prompt_surface, prompt_rect)

        self.game_back_button.draw(self.screen)
    
    def draw(self):
        """Render the game."""
        if self.cursor_image:
            pygame.mouse.set_visible(False)
        else:
            pygame.mouse.set_visible(True)

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
        if self.cursor_image:
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
                pos = event.pos

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
                    action = self.save_file.handle_event(pos)
                    if action == "close":
                        # Close button was clicked, return to title screen
                        self.change_state("title screen")
                    elif action and action.startswith("start_"):
                        # Save slot was selected, start game
                        slot_num = int(action.split("_")[1])
                        self.current_slot = slot_num
                        loaded_state = self.save_file.load_game_file(slot_num) or {}
                        self.game_state = loaded_state
                        self._last_saved_signature = None

                        # Create player when starting game
                        start_x = config.screen_width // 2
                        self.player = Hornet(start_x, 0, config.screen_width, config.screen_height)
                        self.mossgrub = MossGrub(start_x, 0, config.screen_width, config.screen_height)
                        self.mossmother = MossMother(start_x, 0, config.screen_width, config.screen_height)
                        self.player.reset_position(start_x, self.world_ground_y)
                        self.player.on_ground = True
                        self._build_ground_colliders()
                        # Mossgrub will be placed after camera is finalized below
                        self.camera_x = 0
                        self.camera_y = 0
                        self.player_camera_anchor_y = int(self.player.rect.y)
                        self.respawn_position = [
                            int(self.player.rect.x + self.camera_x),
                            int(self.player.rect.y + self.camera_y)
                        ]

                        # Restore player stats from selected save slot
                        saved_health = loaded_state.get("player_health", self.player.health)
                        saved_silk = loaded_state.get("player_silk", self.player.silk)
                        saved_facing_right = loaded_state.get("player_facing_right", self.player.facing_right)
                        self.player.health = max(0, min(self.player.max_health, int(saved_health)))
                        self.player.silk = max(0, min(self.player.max_silk, int(saved_silk)))
                        self.player.facing_right = bool(saved_facing_right)

                        saved_position = loaded_state.get("player_position")
                        saved_position_space = loaded_state.get("player_position_space", "screen")
                        if isinstance(saved_position, list) and len(saved_position) >= 2:
                            saved_x = int(saved_position[0])
                            saved_y = int(saved_position[1])
                            # Ignore legacy/default placeholder coordinates from new save files
                            if not (saved_x == 0 and saved_y == 0):
                                if saved_position_space == "world":
                                    # Keep player centered on screen and restore world location via camera offset
                                    self.camera_x = saved_x - self.player.rect.x
                                    self.camera_y = saved_y - self.player.rect.y
                                else:
                                    # Backward compatibility for older saves that stored rect coordinates
                                    self.player.rect.x = saved_x
                                    self.player.rect.y = saved_y

                        # Rebuild colliders after loading world position so spawn platform is under Hornet.
                        self._build_ground_colliders()

                        # Force a valid floor spawn to prevent falling into void from stale/corrupt Y saves.
                        self._snap_player_to_ground()

                        # Place mossgrub now that camera is finalized.
                        # Spawn above a platform so gravity behavior is easy to test.
                        if len(self.ground_colliders) > 1:
                            spawn_platform = self.ground_colliders[1]
                            mossgrub_world_x = int(spawn_platform.centerx)
                            mossgrub_world_bottom = int(spawn_platform.top - 120)
                            mossmother_world_x = int(spawn_platform.centerx + 240)
                            mossmother_world_bottom = int(spawn_platform.top - 180)
                        else:
                            ground_top = self.ground_colliders[0].top if self.ground_colliders else int(self.world_ground_y)
                            mossgrub_world_x = int(start_x + self.camera_x + 240)
                            mossgrub_world_bottom = int(ground_top - 120)
                            mossmother_world_x = int(start_x + self.camera_x - 240)
                            mossmother_world_bottom = int(ground_top - 180)

                        mossgrub_screen_x = int(mossgrub_world_x - self.camera_x)
                        mossgrub_screen_bottom = int(mossgrub_world_bottom - self.camera_y)
                        self.mossgrub.rect.midbottom = (mossgrub_screen_x, mossgrub_screen_bottom)
                        self.mossgrub.on_ground = False
                        self.mossgrub.velocity_y = 0

                        mossmother_screen_x = int(mossmother_world_x - self.camera_x)
                        mossmother_screen_bottom = int(mossmother_world_bottom - self.camera_y)
                        self.mossmother.rect.midbottom = (mossmother_screen_x, mossmother_screen_bottom)
                        self.mossmother.on_ground = False
                        self.mossmother.velocity_y = 0

                        saved_respawn_position = loaded_state.get("player_respawn_position")
                        if isinstance(saved_respawn_position, list) and len(saved_respawn_position) >= 2:
                            self.respawn_position = [int(saved_respawn_position[0]), int(saved_respawn_position[1])]
                        else:
                            self.respawn_position = [
                                int(self.player.rect.x + self.camera_x),
                                int(self.player.rect.y + self.camera_y)
                            ]

                        saved_mossgrub_position = loaded_state.get("mossgrub_position")
                        if isinstance(saved_mossgrub_position, list) and len(saved_mossgrub_position) >= 2:
                            # Convert saved world-space position to screen space
                            self.mossgrub.rect.x = int(saved_mossgrub_position[0]) - int(self.camera_x)
                            self.mossgrub.rect.y = int(saved_mossgrub_position[1]) - int(self.camera_y)

                        saved_mossgrub_health = loaded_state.get("mossgrub_health", self.mossgrub.health)
                        self.mossgrub.health = max(0, min(self.mossgrub.max_health, int(saved_mossgrub_health)))

                        saved_mossmother_position = loaded_state.get("mossmother_position")
                        if self.mossmother and isinstance(saved_mossmother_position, list) and len(saved_mossmother_position) >= 2:
                            self.mossmother.rect.x = int(saved_mossmother_position[0]) - int(self.camera_x)
                            self.mossmother.rect.y = int(saved_mossmother_position[1]) - int(self.camera_y)

                        saved_mossmother_health = loaded_state.get("mossmother_health", self.mossmother.health if self.mossmother else 0)
                        if self.mossmother:
                            self.mossmother.health = max(0, min(self.mossmother.max_health, int(saved_mossmother_health)))

                        self.player_contact_damage_timer = 0.0
                        self.player_near_bench = False
                        self.bench_interact_text = ""
                        self._bench_interact_key_down = False
                        self.player_camera_anchor_y = int(self.player.rect.y)
                        # Persist state immediately so schema stays up-to-date
                        self.save_current_game_state(force=True)

                        # Start game
                        self.change_state("game")
                    # Delete actions are handled within save_file.handle_event

                elif self.state == "game":
                    if self.game_back_button.is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.save_current_game_state(force=True)
                        self.change_state("title screen")

    def run(self):
        while self.running:
            dt = self.clock.tick(config.fps) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        # Save one last time before exiting
        self.save_current_game_state(force=True)
        
        pygame.quit()
 

# Run the game
if __name__ == "__main__":
    game = Silksong()
    game.run()