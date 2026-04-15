import pygame
import random
import os
import sys
import threading
import cv2
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


class ThreadedVideoCapture:
    """Prefetch video frames on a worker thread so the game loop never blocks on OpenCV I/O."""

    def __init__(self, path):
        self.capture = cv2.VideoCapture(path)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._request_frame = threading.Event()
        self._frame_ready = threading.Event()
        self._latest_frame = None
        self._ended = False
        self._released = False
        self._thread = None
        self.fps = 30.0

        if self.capture.isOpened():
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            detected_fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 0.0)
            if detected_fps > 1.0:
                self.fps = detected_fps

            self._request_frame.set()
            self._thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._thread.start()

    def _reader_loop(self):
        while not self._stop_event.is_set():
            if not self._request_frame.wait(0.1):
                continue
            self._request_frame.clear()

            ok, frame = self.capture.read()
            with self._lock:
                if ok and frame is not None:
                    self._latest_frame = frame
                else:
                    self._latest_frame = None
                    self._ended = True
                self._frame_ready.set()

            if not ok or frame is None:
                break

    def isOpened(self):
        return self.capture is not None and self.capture.isOpened() and not self._released

    def read(self, timeout=0.0):
        """Return `(frame, ended)` where `frame=None` means not ready yet or stream ended."""
        if not self.isOpened():
            return None, True

        if not self._frame_ready.wait(timeout):
            return None, False

        with self._lock:
            frame = None if self._latest_frame is None else self._latest_frame.copy()
            ended = self._ended
            self._latest_frame = None
            self._frame_ready.clear()
            if not ended and not self._released:
                self._request_frame.set()

        return frame, ended

    def release(self):
        if self._released:
            return

        self._released = True
        self._stop_event.set()
        self._request_frame.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)

        if self.capture is not None:
            self.capture.release()


class Silksong:

    # Class-level image cache to avoid reloading
    _image_cache = {}
    
    @classmethod
    def _load_and_scale_image(cls, path, width=None, height=None):
        """Load an image, optionally scaling it, while using cache to avoid reloading."""
        cache_key = (path, width, height)
        if cache_key not in cls._image_cache:
            img = pygame.image.load(path)
            if img.get_alpha() is not None:
                img = img.convert_alpha()
            else:
                img = img.convert()
            if width is not None and height is not None:
                img = pygame.transform.scale(img, (width, height))
            cls._image_cache[cache_key] = img
        return cls._image_cache[cache_key]

    def __init__(self):
        """Set up the game window, assets, and subsystems."""
        # Create fullscreen display at actual screen size
        self.screen = pygame.display.set_mode((config.screen_width, config.screen_height), pygame.FULLSCREEN)
        
        pygame.display.set_caption("Silksong")
        self.running = True
        self.state = "title screen"
        self.clock = pygame.time.Clock()
        self.intro_video_path = os.path.join(os.path.dirname(__file__), "../assets/video/intro_cinematic.mp4")
        self.cutscene_capture = None
        self.cutscene_surface = None
        self.cutscene_rect = None
        self.cutscene_target_size = None
        self.cutscene_fps = 30.0
        self.cutscene_frame_timer = 0.0
        self.cutscene_next_state = None
        
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

        # Load and scale background image using cache
        background_img_path = os.path.join(os.path.dirname(__file__), "../assets/images/title_screen_bg.jpg")
        self.background_image = self._load_and_scale_image(background_img_path, config.screen_width, config.screen_height)
        
        game_background_img_path = os.path.join(os.path.dirname(__file__), "../assets/images/game_bg.png")
        self.game_background_image = self._load_and_scale_image(
            game_background_img_path,
            int(config.screen_width * 1.3),
            int(config.screen_height * 1),
        )

        arena_background_img_path = os.path.join(os.path.dirname(__file__), "../assets/images/arena_bg.png")
        self.arena_background_image = self._load_and_scale_image(arena_background_img_path, config.screen_width, config.screen_height)
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
        
        # Save file state
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

        # Create save file manager
        self.save_file = SaveFile()
        
        # Initialize particle system for title screen effects
        self.particle_system = ParticleSystem(config.screen_width, config.screen_height)
        ember_image_path = os.path.join(os.path.dirname(__file__), "../assets/images/ember_particle.png")
        self.particle_system.load_ember_image(ember_image_path)
        ember_round_image_path = os.path.join(os.path.dirname(__file__), "../assets/images/Texture2D/ember_particle_round.png")
        self.particle_system.load_ember_round_image(ember_round_image_path)
        
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
        self.player_camera_anchor_x = None
        self.player_camera_anchor_y = None
        self.mouse_locked = False
        self.boss_arena_rect = None
        self.boss_arena_camera = None
        self.camera_locked_to_arena = False
        self.arena_camera_lerp_speed = 6.0
        self.camera_shake_timer = 0.0
        self.camera_shake_duration = 0.0
        self.camera_shake_intensity = 0.0
        self.camera_shake_offset = (0, 0)
        self.falling_rocks = []
        self.rock_fall_gravity = 1800.0

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
        self.mossgrub_patrol_left = None
        self.mossgrub_patrol_right = None
        self.world_ground_y = int(config.screen_height * 0.62)

    def _build_ground_colliders(self):
        """Build world-space ground and platform colliders for the level."""
        if not self.player:
            self.ground_colliders = []
            self.boss_arena_rect = None
            self.boss_arena_camera = None
            self.mossgrub_patrol_left = None
            self.mossgrub_patrol_right = None
            return

        base_y = int(self.world_ground_y)
        start_x = config.screen_width // 2

        # Boss arena sized to exactly one camera view.

        
        arena_width = int(config.screen_width - 160)
        arena_height = int(config.screen_height - 80)
        arena_floor_y = base_y - 1800
        arena_ceiling_y = arena_floor_y - arena_height
        arena_left = start_x - arena_width
        arena_right = start_x
        wall_thickness = 30
        self.boss_arena_rect = pygame.Rect(arena_left, arena_ceiling_y, arena_width, arena_height)
        self.boss_arena_camera = (
            int(self.boss_arena_rect.centerx - (config.screen_width / 2)),
            int(self.boss_arena_rect.centery - (config.screen_height / 2)),
        )

        self.ground_colliders = [
            # Main ground
            pygame.Rect(-200000, base_y, 400000, 2000),
            # Low platform for ledge climb testing (right of start)
            pygame.Rect(start_x + 400, base_y - 220, 400, 220),
            # Wall jump corridor - left wall
            pygame.Rect(start_x + 750, base_y - 3000, 50, 3000),
            pygame.Rect(start_x - 1400, base_y - 1800, 50, 1800),
            pygame.Rect(start_x - 50, base_y - 1800, 50, 300),
            pygame.Rect(start_x - 900, base_y - 1500, 1450, 20),
            pygame.Rect(start_x, base_y - 3000, 750, 1000),
            pygame.Rect(start_x - 200, base_y - 100, 100, 20),
            pygame.Rect(start_x - 500, base_y - 300, 100, 20),
            pygame.Rect(start_x - 900, base_y - 1000, 100, 1000),
            pygame.Rect(start_x - 100, base_y - 950, 500, 20),
            pygame.Rect(start_x - 650, base_y - 1050, 300, 20),
            pygame.Rect(start_x - 1200, base_y - 1200, 100, 20),
            # Boss arena: one full screen wide by one full screen tall
            pygame.Rect(arena_left, arena_floor_y, arena_width, wall_thickness),
            pygame.Rect(arena_left, arena_ceiling_y, arena_width, wall_thickness),
            pygame.Rect(arena_left, arena_ceiling_y, wall_thickness, arena_height),
            pygame.Rect(arena_right, arena_ceiling_y, wall_thickness, arena_height - 200),
        ]

        # Keep bench anchored to world ground, not player-specific values.
        if self.player:
            self.player.bench.rect.midbottom = (self.screen.get_width() // 2, base_y)

    def _sync_camera_lock_to_boss_arena(self, player_world_rect, dt):
        """Lock the camera to the arena center while Hornet is inside the boss room."""
        if not self.player or not self.boss_arena_rect or not self.boss_arena_camera:
            self.camera_locked_to_arena = False
            
            return

        should_lock = self.boss_arena_rect.colliderect(player_world_rect)
        blend = min(1.0, self.arena_camera_lerp_speed * dt)

        if should_lock:
            target_camera_x, target_camera_y = self.boss_arena_camera
        elif self.camera_locked_to_arena:
            anchor_x = self.player_camera_anchor_x if self.player_camera_anchor_x is not None else int(self.player.rect.x)
            anchor_y = self.player_camera_anchor_y if self.player_camera_anchor_y is not None else int(self.player.rect.y)
            target_camera_x = int(player_world_rect.x - anchor_x)
            target_camera_y = int(player_world_rect.y - anchor_y)
        else:
            self.camera_locked_to_arena = False
            return

        self.camera_x += (target_camera_x - self.camera_x) * blend
        self.camera_y += (target_camera_y - self.camera_y) * blend

        if abs(target_camera_x - self.camera_x) < 0.5:
            self.camera_x = float(target_camera_x)
        if abs(target_camera_y - self.camera_y) < 0.5:
            self.camera_y = float(target_camera_y)

        self.player.rect.x = int(player_world_rect.x - self.camera_x)
        self.player.rect.y = int(player_world_rect.y - self.camera_y)

        if should_lock:
            self.camera_locked_to_arena = True
            return

        # As soon as Hornet leaves the arena, restore the normal follow camera
        # immediately so the camera tracks her exact movement again.
        self._reset_player_camera_follow(
            world_x=int(player_world_rect.x),
            world_y=int(player_world_rect.y),
        )

    def _is_floor_collider(self, collider_rect):
        """Return True for horizontal ground/platform colliders and False for vertical walls."""
        return collider_rect.width >= collider_rect.height

    def _get_ground_top_at_world_x(self, world_x):
        """Return the top Y of the highest floor collider under the given world X."""
        top_y = None
        for ground_rect in self.ground_colliders:
            if not self._is_floor_collider(ground_rect):
                continue
            if ground_rect.left <= world_x < ground_rect.right:
                if top_y is None or ground_rect.top < top_y:
                    top_y = ground_rect.top
        return top_y

    def _get_colliding_ground_top_for_world_rect(self, world_rect):
        """Return the top Y of the floor collider intersecting the given world-space rect."""
        colliding_top = None
        for ground_rect in self.ground_colliders:
            if not self._is_floor_collider(ground_rect):
                continue
            # Require horizontal overlap.
            if world_rect.right <= ground_rect.left or world_rect.left >= ground_rect.right:
                continue

            # Clamp only when the entity is within/under a collider's vertical span.
            if world_rect.bottom < ground_rect.top or world_rect.top > ground_rect.bottom:
                continue

            # Prefer the deepest colliding top (closest floor under the entity).
            if colliding_top is None or ground_rect.top > colliding_top:
                colliding_top = ground_rect.top

        return colliding_top

    def _clamp_player_above_colliding_ground(self):
        """Push Hornet above the ground if she is currently inside a collider."""
        if not self.player:
            return

        player_world_rect = self.player.rect.copy()
        player_world_rect.x += int(self.camera_x)
        player_world_rect.y += int(self.camera_y)
        ground_top = self._get_colliding_ground_top_for_world_rect(player_world_rect)
        if ground_top is None:
            return

        # Keep player at the anchored screen Y by solving camera_y from desired world bottom.
        self.camera_y = int(ground_top - self.player.rect.bottom)
        self.player.velocity_y = 0
        self.player.on_ground = True

    def _reset_player_camera_follow(self, world_x=None, world_y=None):
        """Return Hornet to the normal follow-camera behavior after arena lock or respawn."""
        if not self.player:
            return

        if world_x is None:
            world_x = int(self.player.rect.x + self.camera_x)
        if world_y is None:
            world_y = int(self.player.rect.y + self.camera_y)

        if self.player_camera_anchor_x is None:
            self.player_camera_anchor_x = int(self.player.rect.x)
        if self.player_camera_anchor_y is None:
            self.player_camera_anchor_y = int(self.player.rect.y)

        self.player.rect.x = int(self.player_camera_anchor_x)
        self.player.rect.y = int(self.player_camera_anchor_y)
        self.camera_x = float(world_x - self.player.rect.x)
        self.camera_y = float(world_y - self.player.rect.y)
        self.camera_locked_to_arena = False

    def _clamp_mossgrub_above_colliding_ground(self, world_x=None):
        """Push MossGrub above the ground if it is currently inside a collider."""
        if not self.mossgrub:
            return
        
        mossgrub_world_rect = self.mossgrub.rect.copy()
        mossgrub_world_rect.x += int(self.camera_x)
        mossgrub_world_rect.y += int(self.camera_y)
        if world_x is not None:
            mossgrub_world_rect.centerx = int(world_x)

        ground_top = self._get_colliding_ground_top_for_world_rect(mossgrub_world_rect)
        if ground_top is None:
            return

        mossgrub_world_rect.bottom = int(ground_top)
        self.mossgrub.rect.x = int(mossgrub_world_rect.x - self.camera_x)
        self.mossgrub.rect.y = int(mossgrub_world_rect.y - self.camera_y)
        self.mossgrub.velocity_y = 0
        self.mossgrub.on_ground = True

    def _set_mossgrub_patrol_on_platform(self, platform_rect, spawn_world_x=None):
        """Place MossGrub on a specific world-space platform and clamp its patrol to that surface."""
        if not self.mossgrub or platform_rect is None:
            self.mossgrub_patrol_left = None
            self.mossgrub_patrol_right = None
            return

        patrol_margin = max(18, self.mossgrub.rect.width // 2 + 6)
        patrol_left = int(platform_rect.left + patrol_margin)
        patrol_right = int(platform_rect.right - patrol_margin)
        if patrol_right <= patrol_left:
            patrol_left = int(platform_rect.centerx - 10)
            patrol_right = int(platform_rect.centerx + 10)

        if spawn_world_x is None:
            mossgrub_world_x = int((patrol_left + patrol_right) / 2)
        else:
            mossgrub_world_x = int(max(patrol_left, min(patrol_right, spawn_world_x)))

        self.mossgrub_patrol_left = patrol_left
        self.mossgrub_patrol_right = patrol_right

        self.mossgrub.rect.midbottom = (
            int(mossgrub_world_x - self.camera_x),
            int(platform_rect.top - self.camera_y),
        )
        self.mossgrub.velocity_y = 0
        self.mossgrub.on_ground = True
        if hasattr(self.mossgrub, "_frac_x"):
            self.mossgrub._frac_x = 0.0

    def _set_mossgrub_spawn_and_patrol(self):
        """Spawn MossGrub just above the start platform and keep its patrol bounds in world space."""
        if not self.mossgrub:
            self.mossgrub_patrol_left = None
            self.mossgrub_patrol_right = None
            return

        start_x = config.screen_width // 2

        if len(self.ground_colliders) > 1:
            spawn_platform = self.ground_colliders[1]
            self._set_mossgrub_patrol_on_platform(spawn_platform)
        else:
            ground_top = self.ground_colliders[0].top if self.ground_colliders else int(self.world_ground_y)
            fallback_platform = pygame.Rect(int(start_x + self.camera_x + 120), int(ground_top), 240, 10)
            self._set_mossgrub_patrol_on_platform(fallback_platform)

    def _update_mouse_lock(self):
        """Ensure the mouse stays unlocked for UI interaction."""
        if self.mouse_locked:
            pygame.event.set_grab(False)
            self.mouse_locked = False

    def trigger_camera_shake(self, duration=0.6, intensity=12.0):
        """Trigger a reusable screen shake effect for dramatic moments."""
        self.camera_shake_timer = max(self.camera_shake_timer, float(duration))
        self.camera_shake_duration = max(self.camera_shake_duration, float(duration))
        self.camera_shake_intensity = max(self.camera_shake_intensity, float(intensity))

    def _update_camera_shake(self, dt):
        """Advance the camera shake effect and update the render offset."""
        if self.camera_shake_timer > 0.0:
            self.camera_shake_timer = max(0.0, self.camera_shake_timer - dt)
            fade = self.camera_shake_timer / max(0.001, self.camera_shake_duration)
            intensity = max(0.0, self.camera_shake_intensity * fade)
            max_offset = int(round(intensity))
            self.camera_shake_offset = (
                random.randint(-max_offset, max_offset) if max_offset > 0 else 0,
                random.randint(-max_offset, max_offset) if max_offset > 0 else 0,
            )
        else:
            self.camera_shake_duration = 0.0
            self.camera_shake_intensity = 0.0
            self.camera_shake_offset = (0, 0)

    def _spawn_mossmother_cry_rocks(self):
        """Spawn three falling rock hazards inside the arena, one of which becomes a MossGrub."""
        if not self.boss_arena_rect:
            self.falling_rocks = []
            return

        rock_size = 56
        spawn_grub_index = random.randrange(3)
        x_positions = (0.2, 0.5, 0.8)
        self.falling_rocks = []

        for idx, fraction in enumerate(x_positions):
            rock_rect = pygame.Rect(0, 0, rock_size, rock_size)
            world_x = int(self.boss_arena_rect.left + self.boss_arena_rect.width * fraction)
            world_y = int(self.boss_arena_rect.top + 18 + idx * 12)
            rock_rect.midtop = (world_x, world_y)
            self.falling_rocks.append({
                "rect": rock_rect,
                "velocity_y": 0.0,
                "spawn_mossgrub": idx == spawn_grub_index,
            })

    def _start_mossmother_cry_attack(self):
        """Apply the cry-attack effects: shake, stun, and falling rocks."""
        self.trigger_camera_shake(duration=0.9, intensity=14.0)
        if self.player:
            self.player.start_stun(2.0)
        self._spawn_mossmother_cry_rocks()

    def _update_falling_rocks(self, dt, player_world_rect):
        """Advance falling cry-attack rocks, damage Hornet on contact, and spawn a MossGrub on one impact."""
        if not self.falling_rocks:
            return

        remaining_rocks = []
        for rock in self.falling_rocks:
            rock_rect = rock["rect"]
            rock["velocity_y"] += self.rock_fall_gravity * dt
            rock_rect.y += int(rock["velocity_y"] * dt)

            ground_top = self._get_colliding_ground_top_for_world_rect(rock_rect)
            if ground_top is not None and rock_rect.bottom >= ground_top:
                rock_rect.bottom = int(ground_top)
                if rock.get("spawn_mossgrub") and self.mossgrub:
                    self.mossgrub.health = self.mossgrub.max_health
                    arena_floor_rect = pygame.Rect(
                        int(self.boss_arena_rect.left),
                        int(self.boss_arena_rect.bottom),
                        int(self.boss_arena_rect.width),
                        10,
                    )
                    self._set_mossgrub_patrol_on_platform(arena_floor_rect, spawn_world_x=rock_rect.centerx)
                continue

            if self.player and player_world_rect.colliderect(rock_rect) and self.player_contact_damage_timer <= 0.0:
                knockback_direction = -1 if player_world_rect.centerx < rock_rect.centerx else 1
                self.player.take_damage(1, knockback_direction=knockback_direction)
                self.player_contact_damage_timer = self.player_contact_damage_cooldown

            remaining_rocks.append(rock)

        self.falling_rocks = remaining_rocks

    def create_buttons(self):
        """Create the title screen menu buttons."""
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

    def _release_cutscene_resources(self):
        """Release the intro cutscene resources."""
        if self.cutscene_capture is not None:
            self.cutscene_capture.release()
            self.cutscene_capture = None
        self.cutscene_surface = None
        self.cutscene_rect = None
        self.cutscene_target_size = None
        self.cutscene_fps = 30.0
        self.cutscene_frame_timer = 0.0

    def _cache_cutscene_frame(self, frame):
        """Convert an OpenCV frame into a screen-ready pygame surface."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_h, frame_w = rgb_frame.shape[:2]

        if self.cutscene_target_size is None:
            scale = min(config.screen_width / frame_w, config.screen_height / frame_h)
            scaled_width = max(1, int(frame_w * scale))
            scaled_height = max(1, int(frame_h * scale))
            self.cutscene_target_size = (scaled_width, scaled_height)

        if (frame_w, frame_h) != self.cutscene_target_size:
            rgb_frame = cv2.resize(rgb_frame, self.cutscene_target_size, interpolation=cv2.INTER_AREA)
            frame_w, frame_h = self.cutscene_target_size

        self.cutscene_surface = pygame.image.frombuffer(
            rgb_frame.tobytes(),
            (frame_w, frame_h),
            "RGB"
        ).convert()
        self.cutscene_rect = self.cutscene_surface.get_rect(center=(config.screen_width // 2, config.screen_height // 2))

    def _read_next_cutscene_frame(self, wait_timeout=0.0):
        """Read the next prefetched frame of the intro cinematic into the draw cache."""
        if self.cutscene_capture is None or not self.cutscene_capture.isOpened():
            return False

        frame, ended = self.cutscene_capture.read(timeout=wait_timeout)
        if frame is None:
            return False if ended else None

        self._cache_cutscene_frame(frame)
        return True

    def _finish_cutscene(self):
        """Close the intro cinematic and continue into the queued state."""
        next_state = self.cutscene_next_state or "game"
        self.cutscene_next_state = None
        self._release_cutscene_resources()
        if self.state != next_state:
            self.change_state(next_state)

    def _start_intro_cutscene(self, next_state="game"):
        """Open the intro cinematic before gameplay begins."""
        self.cutscene_next_state = next_state
        self._release_cutscene_resources()

        if not os.path.exists(self.intro_video_path):
            self.change_state(next_state)
            return

        self.cutscene_capture = ThreadedVideoCapture(self.intro_video_path)
        if not self.cutscene_capture.isOpened():
            self._release_cutscene_resources()
            self.change_state(next_state)
            return

        self.cutscene_fps = max(1.0, float(getattr(self.cutscene_capture, "fps", 30.0)))

        first_frame_status = self._read_next_cutscene_frame(wait_timeout=0.35)
        if first_frame_status is False:
            self._finish_cutscene()
            return

        self.change_state("cutscene")
    
    def update_cutscene(self, dt):
        """Advance the intro cinematic and transition into gameplay when it ends."""
        if self.transition_manager.active:
            return

        if self.cutscene_capture is None or not self.cutscene_capture.isOpened():
            self._finish_cutscene()
            return

        frame_duration = 1.0 / max(1.0, self.cutscene_fps)
        self.cutscene_frame_timer += dt

        while self.cutscene_frame_timer >= frame_duration:
            frame_status = self._read_next_cutscene_frame()
            if frame_status is False:
                self._finish_cutscene()
                return
            if frame_status is None:
                break

            self.cutscene_frame_timer -= frame_duration

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

        # Update camera position based on player movement unless the arena lock is active.
        if camera_movement and not self.camera_locked_to_arena:
            self.camera_x += camera_movement[0] * dt
            self.camera_y += camera_movement[1] * dt

        player.update(
            dt,
            collision_rects=self.ground_colliders,
            camera_x=self.camera_x,
            camera_y=self.camera_y,
            move_horizontally=self.camera_locked_to_arena
        )

        # Apply wall collision correction from player.
        if self.camera_locked_to_arena:
            self.player.rect.x += int(player.camera_x_correction)
        else:
            self.camera_x += player.camera_x_correction

        # Keep Hornet anchored on screen only while the camera is following her.
        if not self.camera_locked_to_arena:
            if self.player_camera_anchor_x is None:
                self.player_camera_anchor_x = int(player.rect.x)
            if self.player_camera_anchor_y is None:
                self.player_camera_anchor_y = int(player.rect.y)
            vertical_delta = int(player.rect.y - self.player_camera_anchor_y)
            if vertical_delta != 0:
                self.camera_y += vertical_delta
                player.rect.y = int(self.player_camera_anchor_y)

        player_world_rect = player.rect.copy()
        player_world_rect.x += int(self.camera_x)
        player_world_rect.y += int(self.camera_y)
        self._sync_camera_lock_to_boss_arena(player_world_rect, dt)

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
        if self.mossgrub_patrol_left is not None and self.mossgrub_patrol_right is not None:
            mossgrub_left_bound = int(self.mossgrub_patrol_left - self.camera_x)
            mossgrub_right_bound = int(self.mossgrub_patrol_right - self.camera_x)
        else:
            mossgrub_left_bound = int(player.rect.centerx - total_d / 2)
            mossgrub_right_bound = int(player.rect.centerx + total_d / 2)

        if self.boss_arena_rect:
            boss_left_bound = int(self.boss_arena_rect.left - self.camera_x)
            boss_right_bound = int(self.boss_arena_rect.right - self.camera_x)
        else:
            boss_left_bound = int(player.rect.centerx - total_d / 2)
            boss_right_bound = int(player.rect.centerx + total_d / 2)

        # Compute camera delta this frame for mossgrub
        camera_dx = self.camera_x - prev_camera_x
        camera_dy = self.camera_y - prev_camera_y

        if self.mossgrub and self.mossgrub.health > 0:
            self.mossgrub.update(mossgrub_left_bound, mossgrub_right_bound, dt,
                                collision_rects=self.ground_colliders,
                                camera_x=self.camera_x,
                                camera_y=self.camera_y,
                                camera_dx=camera_dx,
                                camera_dy=camera_dy)

        if self.mossmother and self.mossmother.health > 0:
            self.mossmother.update(boss_left_bound, boss_right_bound, dt,
                                collision_rects=self.ground_colliders,
                                camera_x=self.camera_x,
                                camera_y=self.camera_y,
                                camera_dx=camera_dx,
                                camera_dy=camera_dy,
                                player_world_rect=player_world_rect,
                                arena_rect=self.boss_arena_rect)
            if self.mossmother.consume_cry_attack_trigger():
                self._start_mossmother_cry_attack()

        self._update_falling_rocks(dt, player_world_rect)

        if player.consume_attack_trigger():
            player.start_attack_hitbox(
                camera_x=self.camera_x,
                camera_y=self.camera_y,
            )

        if player.attack_hitbox:
            attack_rect = player.attack_hitbox

            if self.mossgrub and self.mossgrub.health > 0:
                mossgrub_world = self.mossgrub.rect.copy()
                mossgrub_world.x += int(self.camera_x)
                mossgrub_world.y += int(self.camera_y)
                if attack_rect.colliderect(mossgrub_world):
                    if not player.attack_hit_mossgrub:
                        knockback_direction = 1 if player_world_rect.centerx < mossgrub_world.centerx else -1
                        self.mossgrub.take_damage(self.attack_damage, knockback_direction=knockback_direction)
                        player.apply_attack_recoil_on_hit()
                        player.gain_silk(self.silk_per_hit)
                        player.attack_hit_mossgrub = True
                    if player.attack_hitbox_direction == "down":
                        player.rebound_from_down_attack(enemy_rect=mossgrub_world, camera_y=self.camera_y)

            if self.mossmother and self.mossmother.health > 0:
                mossmother_world = self.mossmother.rect.copy()
                mossmother_world.x += int(self.camera_x)
                mossmother_world.y += int(self.camera_y)
                if attack_rect.colliderect(mossmother_world):
                    if not player.attack_hit_mossmother:
                        knockback_direction = 1 if player_world_rect.centerx < mossmother_world.centerx else -1
                        self.mossmother.take_damage(
                            self.attack_damage,
                            knockback_direction=knockback_direction,
                            apply_knockback=not self.mossmother.is_attacking,
                        )
                        player.apply_attack_recoil_on_hit()
                        player.gain_silk(self.silk_per_hit)
                        player.attack_hit_mossmother = True
                    if player.attack_hitbox_direction == "down":
                        player.rebound_from_down_attack(enemy_rect=mossmother_world, camera_y=self.camera_y)

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

    def _reset_encounter_state(self):
        """Clear temporary hazards and restore enemies to their encounter start state."""
        self.falling_rocks = []
        self.player_contact_damage_timer = 0.0
        self.camera_shake_timer = 0.0
        self.camera_shake_duration = 0.0
        self.camera_shake_intensity = 0.0
        self.camera_shake_offset = (0, 0)
        self.player_near_bench = False
        self.bench_interact_text = ""
        self._bench_interact_key_down = False

        if self.mossgrub:
            self.mossgrub.health = self.mossgrub.max_health
            self._set_mossgrub_spawn_and_patrol()

        if self.mossmother:
            if self.boss_arena_rect:
                arena_spawn_x = int(self.boss_arena_rect.centerx)
                arena_spawn_y = int(self.boss_arena_rect.top + self.mossmother.rect.height + 40)
                self.mossmother.reset_position(arena_spawn_x, arena_spawn_y)
            else:
                self.mossmother.reset_position(self.mossmother.rect.centerx, self.mossmother.rect.bottom)

    def respawn_player(self):
        """Respawn Hornet at the last bench rest position and reset the encounter."""
        if not self.player:
            return

        respawn_x = int(self.player.rect.x + self.camera_x)
        respawn_y = int(self.player.rect.y + self.camera_y)

        if isinstance(self.respawn_position, list) and len(self.respawn_position) >= 2:
            respawn_x = int(self.respawn_position[0])
            respawn_y = int(self.respawn_position[1])

        # Restore world-space respawn location and release any arena camera lock.
        self._reset_player_camera_follow(world_x=respawn_x, world_y=respawn_y)
        self._clamp_player_above_colliding_ground()
        self.player.reset_position(self.player.rect.centerx, self.player.rect.bottom)

        self.player.health = self.player.max_health
        self.player.cancel_heal_channel()
        self.player.is_resting = False
        self.player.rest_timer = 0.0
        self.player.on_ground = True

        self._reset_encounter_state()
        self.save_current_game_state(force=True)

    def respawn_mossgrub(self):
        """Respawn MossGrub and Moss Mother at full health."""
        self._reset_encounter_state()
        self.save_current_game_state(force=True)

    def save_current_game_state(self, force=False):
        """Save player progress to the current save slot if state changed."""
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
        """Transition to a new game state with a black fade."""
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
        
        # Draw small ember particles
        self.particle_system.draw_particles(self.screen, size_max=6.0)
        
        # Draw the Silksong title image
        title_rect = self.title_image.get_rect(center=(config.screen_width/2, int(config.screen_height/2 - 200 * config.scale_y)))
        self.screen.blit(self.title_image, title_rect)
        
        # Draw title spikes (boneforest images)
        self.screen.blit(self.title_needle, (int(1500 * config.scale_x), int(175 * config.scale_y)))
        self.screen.blit(self.title_pin, (int(1300 * config.scale_x), int(475 * config.scale_y)))
        self.screen.blit(self.title_boulder, (int(1050 * config.scale_x), int(850 * config.scale_y)))

        # Draw large ember particles (in front of boneforest)
        self.particle_system.draw_particles(self.screen, size_min=5.0)

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
        self.screen.fill((0, 0, 0))

        if self.cutscene_surface and self.cutscene_rect:
            self.screen.blit(self.cutscene_surface, self.cutscene_rect)

        hint_font = config.get_font(int(24 * config.scale_y))
        skip_text = hint_font.render("Press any key or click to skip", True, (220, 220, 220))
        skip_rect = skip_text.get_rect(midbottom=(config.screen_width // 2, config.screen_height - int(24 * config.scale_y)))
        self.screen.blit(skip_text, skip_rect)
    
    def draw_game(self):
        # Draw background (could add parallax later)
        # Get the look offset from the player (camera pans up/down)
        look_y = self.player.camera_look_y if self.player else 0
        shake_x, shake_y = self.camera_shake_offset

        bg_width, bg_height = self.game_background_image.get_size()
        bg_x = int((config.screen_width - bg_width) / 2 - self.camera_x * 0.18 + shake_x)
        bg_y = int((config.screen_height - bg_height) / 2 - self.camera_y * 0.12 - look_y * 0.35 + shake_y)

        # Draw one oversized background image and clamp it so it never tiles.
        bg_x = min(0, max(config.screen_width - bg_width, bg_x))
        bg_y = min(0, max(config.screen_height - bg_height, bg_y))
        self.screen.blit(self.game_background_image, (bg_x, bg_y))
        
        # Draw arena background
        if self.boss_arena_rect and getattr(self,"arena_background_image", None):
            arena_screen_x = int(self.boss_arena_rect.left - self.camera_x + shake_x)
            arena_screen_y = int(self.boss_arena_rect.top - self.camera_y - look_y + shake_y)
            arena_w = int(self.boss_arena_rect.width)
            arena_h = int(self.boss_arena_rect.height)
            arena_surf = pygame.transform.scale(self.arena_background_image, (arena_w, arena_h))
            self.screen.blit(arena_surf, (arena_screen_x, arena_screen_y))
        



        # Draw ground and platforms
        if self.ground_colliders:
            for cr in self.ground_colliders:
                screen_x = int(cr.left - self.camera_x + shake_x)
                screen_y = int(cr.top - self.camera_y - look_y + shake_y)
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
            self.player.bench.draw(self.screen, camera_x=self.camera_x, camera_y=self.camera_y, look_y_offset=look_y, screen_offset=(shake_x, shake_y))
            self.player.draw(self.screen, look_y_offset=-look_y, screen_offset=(shake_x, shake_y))
            # Debug: highlight Hornet collision rect.
            player_debug_rect = self.player.rect.copy()
            player_debug_rect.x += int(shake_x)
            player_debug_rect.y += int(shake_y - look_y)
            pygame.draw.rect(self.screen, (0, 255, 80), player_debug_rect, 2)

            # Debug: highlight Hornet attack hitbox while active.
            if self.player.attack_hitbox:
                attack_draw_rect = self.player.attack_hitbox.copy()
                attack_draw_rect.x -= int(self.camera_x - shake_x)
                attack_draw_rect.y -= int(self.camera_y + look_y - shake_y)

                attack_fill = pygame.Surface((attack_draw_rect.width, attack_draw_rect.height), pygame.SRCALPHA)
                attack_fill.fill((255, 200, 60, 85))
                self.screen.blit(attack_fill, attack_draw_rect.topleft)
                pygame.draw.rect(self.screen, (255, 230, 120), attack_draw_rect, 2)

        # Draw MossGrub (rect is now in screen space)
        if self.mossgrub and self.mossgrub.health > 0:
            enemy_draw_rect = self.mossgrub.rect.copy()
            enemy_draw_rect.x += int(shake_x)
            enemy_draw_rect.y += int(shake_y - look_y)

            if self.mossgrub.facing_right == 1:
                self.screen.blit(self.mossgrub.image_flipped, enemy_draw_rect)
            else:
                self.screen.blit(self.mossgrub.image, enemy_draw_rect)

            pygame.draw.rect(self.screen, (255, 70, 70), enemy_draw_rect, 2)

        # Draw Moss Mother (rect is now in screen space)
        if self.mossmother and self.mossmother.health > 0:
            mother_draw_rect = self.mossmother.rect.copy()
            mother_draw_rect.x += int(shake_x)
            mother_draw_rect.y += int(shake_y - look_y)

            if self.mossmother.facing_right:
                self.screen.blit(self.mossmother.image, mother_draw_rect)
            else:
                self.screen.blit(self.mossmother.image_flipped, mother_draw_rect)

            pygame.draw.rect(self.screen, (255, 170, 70), mother_draw_rect, 2)

        # Draw falling rock hitboxes for the cry attack.
        for rock in self.falling_rocks:
            rock_draw_rect = rock["rect"].copy()
            rock_draw_rect.x -= int(self.camera_x - shake_x)
            rock_draw_rect.y -= int(self.camera_y + look_y - shake_y)
            rock_fill = pygame.Surface((rock_draw_rect.width, rock_draw_rect.height), pygame.SRCALPHA)
            rock_fill.fill((255, 120, 80, 110))
            self.screen.blit(rock_fill, rock_draw_rect.topleft)
            pygame.draw.rect(self.screen, (255, 210, 120), rock_draw_rect, 2)

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

            if self.player.stun_timer > 0.0:
                stun_text = hud_font.render(f"Stunned... {self.player.stun_timer:.1f}s", True, (255, 220, 140))
                self.screen.blit(stun_text, (25, 160))

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
        """Render the current state to the screen."""
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
        """Update the current game state by dt seconds."""
        self._update_mouse_lock()
        self._update_camera_shake(dt)

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
        """Process all pending pygame events and dispatch by state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.state == "exit":
                self.running = False

            # Temporary: allow quitting with ESC from any state
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state == "cutscene":
                    self._finish_cutscene()
                    continue
                self.running = False
            
            # Skip input handling during transitions
            if self.transition_manager.active:
                continue

            if self.state == "cutscene":
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self._finish_cutscene()
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
                        base_y = int(self.world_ground_y)
                        self.player = Hornet(start_x, base_y, config.screen_width, config.screen_height)
                        self.mossgrub = MossGrub(start_x, 0, config.screen_width, config.screen_height)
                        self.mossmother = MossMother((start_x + 1200), (base_y - 1800) - 200, config.screen_width, config.screen_height)
                        self.player.reset_position(start_x, base_y)
                        self.player.on_ground = True
                        self._build_ground_colliders()
                        # Mossgrub will be placed after camera is finalized below
                        self.camera_x = 0
                        self.camera_y = 0
                        self.player_camera_anchor_x = int(self.player.rect.x)
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

                        # Only correct penetration if the loaded position intersects a floor collider.
                        self._clamp_player_above_colliding_ground()

                        # Place MossGrub using stable world-space platform bounds.
                        self._set_mossgrub_spawn_and_patrol()

                        if self.boss_arena_rect:
                            mossmother_world_x = int(self.boss_arena_rect.centerx)
                            mossmother_world_bottom = int(self.boss_arena_rect.top + self.mossmother.rect.height + 40)
                        else:
                            mossmother_world_x = int(start_x + self.camera_x - 240)
                            mossmother_world_bottom = int((self.ground_colliders[0].top if self.ground_colliders else int(self.world_ground_y)) - 180)

                        mossmother_screen_x = int(mossmother_world_x - self.camera_x)
                        mossmother_screen_bottom = int(mossmother_world_bottom - self.camera_y)
                        self.mossmother.rect.midbottom = (mossmother_screen_x, mossmother_screen_bottom)
                        self.mossmother.on_ground = False
                        self.mossmother.velocity_y = 0
                        self.mossmother.is_engaged = False

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
                            # Restore only sane world-space positions; otherwise keep the default platform spawn.
                            saved_mossgrub_world_x = int(saved_mossgrub_position[0])
                            saved_mossgrub_world_y = int(saved_mossgrub_position[1])
                            saved_mossgrub_world_rect = pygame.Rect(
                                saved_mossgrub_world_x,
                                saved_mossgrub_world_y,
                                self.mossgrub.rect.width,
                                self.mossgrub.rect.height,
                            )

                            within_patrol_x = True
                            if self.mossgrub_patrol_left is not None and self.mossgrub_patrol_right is not None:
                                within_patrol_x = self.mossgrub_patrol_left - 120 <= saved_mossgrub_world_rect.centerx <= self.mossgrub_patrol_right + 120

                            colliding_top = self._get_colliding_ground_top_for_world_rect(saved_mossgrub_world_rect)
                            near_valid_floor = colliding_top is not None and abs(saved_mossgrub_world_rect.bottom - colliding_top) <= 220

                            if within_patrol_x and near_valid_floor:
                                self.mossgrub.rect.x = saved_mossgrub_world_x - int(self.camera_x)
                                self.mossgrub.rect.y = saved_mossgrub_world_y - int(self.camera_y)

                                if saved_mossgrub_world_rect.bottom > colliding_top + 2:
                                    self._clamp_mossgrub_above_colliding_ground(world_x=saved_mossgrub_world_x)
                            else:
                                self._set_mossgrub_spawn_and_patrol()

                        saved_mossgrub_health = loaded_state.get("mossgrub_health", self.mossgrub.health)
                        self.mossgrub.health = max(0, min(self.mossgrub.max_health, int(saved_mossgrub_health)))

                        saved_mossmother_position = loaded_state.get("mossmother_position")
                        if self.mossmother and isinstance(saved_mossmother_position, list) and len(saved_mossmother_position) >= 2:
                            saved_mossmother_world = pygame.Rect(
                                int(saved_mossmother_position[0]),
                                int(saved_mossmother_position[1]),
                                self.mossmother.rect.width,
                                self.mossmother.rect.height,
                            )
                            if not self.boss_arena_rect or self.boss_arena_rect.colliderect(saved_mossmother_world):
                                self.mossmother.rect.x = int(saved_mossmother_position[0]) - int(self.camera_x)
                                self.mossmother.rect.y = int(saved_mossmother_position[1]) - int(self.camera_y)

                        saved_mossmother_health = loaded_state.get("mossmother_health", self.mossmother.health if self.mossmother else 0)
                        if self.mossmother:
                            self.mossmother.health = max(0, min(self.mossmother.max_health, int(saved_mossmother_health)))

                        self.player_contact_damage_timer = 0.0
                        self.player_near_bench = False
                        self.bench_interact_text = ""
                        self._bench_interact_key_down = False
                        self.player_camera_anchor_x = int(self.player.rect.x)
                        self.player_camera_anchor_y = int(self.player.rect.y)
                        # Persist state immediately so schema stays up-to-date
                        self.save_current_game_state(force=True)

                        # Start intro cutscene, then enter gameplay
                        self._start_intro_cutscene(next_state="game")
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
        self._release_cutscene_resources()
        
        pygame.quit()
 

# Run the game
if __name__ == "__main__":
    game = Silksong()
    game.run()