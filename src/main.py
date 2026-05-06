import pygame
import random
import os
import threading
import cv2
import config
from asset_paths import resolve_image_path
from animation import Animation
from audio import AudioManager
from button import Button
from particles import ParticleSystem
from transition import TransitionManager, TransitionType
from settings import SettingsMenu
from save_file import SaveFile
from hornet import Hornet
from mossgrub import MossGrub
from moss_mother import MossMother
from tutorial import Tutorial
from runtime_paths import assets_path, images_path

# [8] github copilot
# Enable bilinear filtering for pygame.SCALED so the 1920×1080 logical surface
import os
os.environ["SDL_RENDER_SCALE_QUALITY"] = "linear"

# Initialize pygame
pygame.init()

# [13] github copilot
class ThreadedVideoCapture:
    """Prefetch video frames on a worker thread so the game loop never blocks on OpenCV I/O."""

    def __init__(self, path):
        """
        Open the video file and start the reader thread if successful. The latest frame is cached for immediate retrieval by the main thread, and the reader thread is signaled to read the next frame as soon as the main thread consumes it. The reader thread also tracks when the video ends so the main thread can stop waiting for new frames.
        arg:
            path (str): The file path to the video to open.
        """
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
        """Worker thread loop that waits for a signal to read the next frame, reads it, caches it, and signals the main thread that a new frame is ready. Also tracks when the video ends so the main thread can stop waiting for new frames."""
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
        """
        Return True if the video file was successfully opened and the reader thread is running.
        returns:
            bool: True if the video file was successfully opened and the reader thread is running, False otherwise.
        """
        return self.capture is not None and self.capture.isOpened() and not self._released

    def read(self, timeout=0.0):
        """
        Return `(frame, ended)` where `frame=None` means not ready yet or stream ended.
        args:
            timeout (float): How long to wait for the next frame to be ready before giving up
        returns:
            tuple: (frame, ended) where `frame` is the next video frame as a numpy array or None if not ready or stream ended, and `ended` is a boolean that is True if the video has ended and no more frames will be available.
        """
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
        """Release the video capture and stop the reader thread."""
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
    """Main game class that manages the game loop, state, rendering, and subsystems."""

    # Class-level image cache to avoid reloading
    _image_cache = {}
    
    @classmethod
    def _load_and_scale_image(cls, path, width=None, height=None):
        """
        Load an image, optionally scaling it, while using cache to avoid reloading.
        arg:
            path (str): The file path to the image to load.
            width (int, optional): The desired width to scale the image to. If None, no horizontal scaling is applied.
            height (int, optional): The desired height to scale the image to. If None, no vertical scaling is applied.
        returns:
            pygame.Surface: The loaded (and possibly scaled) image surface.
        """
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

    def _load_collider_map_overlays(self):
        """Load collider map layers using the editable overlay settings in config."""
        self._collider_map_layers = {}
        overlay_config = getattr(config, "collider_map_overlay", {})
        if not overlay_config.get("enabled", True):
            return

        base_scale = float(overlay_config.get("scale", 1.0))
        base_alpha = max(0, min(255, int(overlay_config.get("alpha", 255))))
        image_root = images_path()

        for layer_name, layer_config in overlay_config.get("layers", {}).items():
            relative_path = layer_config.get("path")
            if not relative_path:
                continue

            try:
                layer_image = pygame.image.load(os.path.join(image_root, relative_path)).convert_alpha()
            except Exception:
                continue

            layer_scale = base_scale * float(layer_config.get("scale", 1.0))
            if layer_scale != 1.0:
                scaled_size = (
                    max(1, int(round(layer_image.get_width() * layer_scale))),
                    max(1, int(round(layer_image.get_height() * layer_scale))),
                )
                layer_image = pygame.transform.smoothscale(layer_image, scaled_size)

            layer_image.set_alpha(base_alpha)
            self._collider_map_layers[layer_name] = {
                "image": layer_image,
                "world_origin": None,
                "offset": tuple(layer_config.get("offset", (0, 0))),
                "world_origin_override": layer_config.get("world_origin_override"),
            }

    def _ensure_game_render_assets(self):
        """Load gameplay-only visual assets on first use instead of during app startup."""
        if self.game_background_image is None:
            game_background_img_path = resolve_image_path("game_bg.png")
            self.game_background_image = self._load_and_scale_image(
                game_background_img_path,
                int(config.screen_width * 1.3),
                int(config.screen_height * 1),
            )

        if self.moss_collapse_plat_image is None:
            collapse_plat_path = resolve_image_path("sprite/moss_collapse_plat.png")
            self.moss_collapse_plat_image = self._load_and_scale_image(
                collapse_plat_path,
                self.moss_collapse_plat_size,
                self.moss_collapse_plat_size,
            )

        if self._rock_explode_frames is None:
            rock_explode_path = resolve_image_path("spritesheet/enemy/rock_explode.png")
            sheet = pygame.image.load(rock_explode_path).convert_alpha()
            frame_w, frame_h = 530, 463
            num_frames = sheet.get_width() // frame_w
            target_w = 120
            scale = target_w / frame_w
            target_h = max(1, int(frame_h * scale))
            self._rock_explode_frames = []
            for i in range(num_frames):
                frame_surf = sheet.subsurface(pygame.Rect(i * frame_w, 0, frame_w, frame_h)).copy()
                self._rock_explode_frames.append(
                    pygame.transform.smoothscale(frame_surf, (target_w, target_h))
                )

        if self._collider_map_layers is None:
            self._load_collider_map_overlays()
            if self.ground_colliders:
                self._rebuild_collider_map_overlays(int(self.world_ground_y))

    def _rebuild_collider_map_overlays(self, base_y):
        """
        Recompute world-space origins for the collider map overlay layers.
        args:
            base_y (int): The world Y coordinate of the main ground level, used to split upper and lower collider layers.
        """
        if not getattr(self, "_collider_map_layers", None):
            return

        overlay_config = getattr(config, "collider_map_overlay", {})
        padding = int(overlay_config.get("padding", 40))
        global_offset_x, global_offset_y = tuple(overlay_config.get("global_offset", (0, 0)))
        split_y = base_y - int(overlay_config.get("split_y_offset", 1480))

        all_rects = self.ground_colliders[1:]
        upper_rects, lower_rects = [], []
        for collider_rect in all_rects:
            if collider_rect.top < split_y:
                clipped = collider_rect.clip(
                    pygame.Rect(collider_rect.left, -1000000, collider_rect.width, split_y + 1000000)
                )
                if clipped.width > 0 and clipped.height > 0:
                    upper_rects.append(clipped)
            if collider_rect.bottom > split_y:
                clipped = collider_rect.clip(
                    pygame.Rect(collider_rect.left, split_y, collider_rect.width, 1000000)
                )
                if clipped.width > 0 and clipped.height > 0:
                    lower_rects.append(clipped)

        layer_rects = {
            "upper": upper_rects,
            "lower": lower_rects,
        }

        for layer_name, layer_data in self._collider_map_layers.items():
            override_origin = layer_data.get("world_origin_override")
            if override_origin is not None:
                layer_data["world_origin"] = (int(override_origin[0]), int(override_origin[1]))
                continue

            rects = layer_rects.get(layer_name, [])
            if not rects:
                layer_data["world_origin"] = None
                continue

            offset_x, offset_y = layer_data.get("offset", (0, 0))
            layer_data["world_origin"] = (
                min(rect.left for rect in rects) - padding + int(global_offset_x) + int(offset_x),
                min(rect.top for rect in rects) - padding + int(global_offset_y) + int(offset_y),
            )

    def __init__(self):
        """Set up the game window, assets, and subsystems."""
        # [3] stack overflow, [8] github copilot
        # Create fullscreen display using pygame.SCALED so the game's 1920×1080 
        # Logical resolution is smoothly upscaled on larger monitors instead of using nearest-neighbor (pixelated)
        # The world always renders at 1920×1080 to an intermediate surface, and then a viewport-sized crop of that is scaled to the actual screen each frame for the zoom effect.
        self.screen = pygame.display.set_mode(
            (config.game_width, config.game_height),
            pygame.FULLSCREEN | pygame.SCALED,
        )
        # Intermediate surface: the full 1920×1080 world renders here each frame.
        # A viewport-sized crop is then smoothscaled to the screen for the zoom effect.
        self._world_surface = pygame.Surface((config.game_width, config.game_height)).convert()
        # Pre-allocated destination for the per-frame smoothscale
        # Avoids creating a new 1920×1080 surface every frame, which was the main render-thread bottleneck.
        self._zoom_surface = pygame.Surface((config.game_width, config.game_height)).convert()

        pygame.display.set_caption("Silksong")
        self.running = True
        self.state = "title screen"
        self.clock = pygame.time.Clock()
        self.intro_video_path = assets_path("video", "intro_cinematic.mp4")
        self.cutscene_capture = None
        self.cutscene_surface = None
        self.cutscene_rect = None
        self.cutscene_target_size = None
        self.cutscene_fps = 30.0
        self.cutscene_frame_timer = 0.0
        self.cutscene_next_state = None
        
        # Load and scale title image using cache
        title_img_path = resolve_image_path("title.png")
        self.title_image = self._load_and_scale_image(title_img_path, 880, 440)
        
        # Load and scale title element (needle)
        title_needle_path = resolve_image_path("hornet_title_screen_boneforest_0003_hornet_needle.png")
        title_needle = self._load_and_scale_image(title_needle_path, 186, 864)
        self.title_needle = title_needle
    
        # Load and scale title element (pin)
        title_pin_path = resolve_image_path("hornet_title_screen_boneforest_0002_lace_pin.png")
        title_pin_scaled = self._load_and_scale_image(title_pin_path, 94, 613)
        self.title_pin = pygame.transform.rotate(title_pin_scaled, -5)  # Rotate 15 degrees to the right (negative = clockwise)
        
        # Load and scale title element (boulder)
        title_boulder_path = resolve_image_path("hornet_title_screen_boneforest_0000_bone_cliff_01.png")
        self.title_boulder = self._load_and_scale_image(title_boulder_path, 552, 236)

        # Load and scale background image using cache
        background_img_path = resolve_image_path("title_screen_bg.jpg")
        self.background_image = self._load_and_scale_image(background_img_path, config.screen_width, config.screen_height)
        
        # Gameplay assets (loaded on first use by _ensure_game_render_assets to reduce initial load time)
        self.game_background_image = None
        self._collider_map_layers = None
        self.moss_collapse_plat_image = None
        self.moss_collapse_plat_size = 56
        self._rock_explode_frames = None

        # Load custom cursor image
        self.cursor_image = None
        self.cursor_hotspot = (0, 0)
        cursor_candidates = ["cursor.png", "Cursor.png"]
        for cursor_path in cursor_candidates:
            try:
                self.cursor_image = pygame.image.load(resolve_image_path(cursor_path)).convert_alpha()
                break
            except FileNotFoundError:
                continue
        pygame.mouse.set_visible(self.cursor_image is None)
        
        # Initialize audio manager
        self.audio_manager = AudioManager()
        self._load_game_sounds()
        self.audio_manager.play_music("Title", loop=True)

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

        # Tutorial (shown once after the intro cutscene for new saves)
        self.tutorial = Tutorial(config.screen_width, config.screen_height)
        self.tutorial.on_complete = lambda: self.change_state("game")
        
        # Initialize particle system for title screen effects
        self.particle_system = ParticleSystem(config.screen_width, config.screen_height)
        ember_image_path = resolve_image_path("ember_particle.png")
        self.particle_system.load_ember_image(ember_image_path)
        ember_round_image_path = resolve_image_path("particle/ember_particle.png")
        self.particle_system.load_ember_round_image(ember_round_image_path)
        self.particle_system.load_gameplay_particle_images(
            resolve_image_path("particle/fung_mote.png"),
            resolve_image_path("particle/mossbone_particle_small.png"),
            resolve_image_path("particle/coral_particle.png"),
            resolve_image_path("particle/aspid_particle.png"),
        )
        
        # Create buttons
        self.create_buttons() # Normal buttons
        self.game_back_button = Button(
            config.screen_width - 90,
            45,
            "Back",
            config.white,
            config.title_font_path,
            30,
        )
        self._game_back_button_was_hovered = False
        self.game_back_click_delay = 0.2
        self.pending_game_back_timer = 0.0
        self.title_button_click_delay = 0.2
        self.pending_title_action = None
        self.pending_title_timer = 0.0
        self.save_files_back_click_delay = 0.2
        self.pending_save_files_back_timer = 0.0

        # Render caches for frequently redrawn UI text/overlays.
        self._cutscene_skip_hint_surface = None
        self._cutscene_skip_hint_rect = None
        self._bench_prompt_cache_text = None
        self._bench_prompt_cache_surface = None
        self._bench_prompt_cache_rect = None
        self._bench_prompt_cache_bg = None
        self._bench_prompt_cache_bg_topleft = (0, 0)
        self._brightness_overlay = pygame.Surface((config.screen_width, config.screen_height), pygame.SRCALPHA)
        self._brightness_overlay_alpha = None

        # Global UI flash for non-gameplay states (title/save/settings).
        self.ui_flash_active = False
        self.ui_flash_anchor = (config.screen_width // 2, config.screen_height // 2)
        self.ui_flash_anim = Animation(
            resolve_image_path("spritesheet/HUD/flash.png"),
            frame_width=1696,
            frame_height=396,
            scale=0.7,
        )
        flash_sheet = self.ui_flash_anim._get_sprite_sheet()
        flash_frame_count = max(1, flash_sheet.get_width() // self.ui_flash_anim.frame_width)
        self.ui_flash_anim.add_animation("play", row=0, start_col=0, num_frames=flash_frame_count, speed=0.03, loop=False)
        
        # Initialize player (Hornet)
        self.player = None  # Will be created when game starts
        self.mossgrub = None # Overworld mossgrub reference
        self.mossgrubs = {"overworld": None, "arena": {}}
        self._next_arena_mossgrub_id = 1
        self.mossmother = None # Will be created when game starts
        
        # [7] clear code
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
        # Smoothly-lerped viewport crop center used during arena transitions.
        # None = use Hornet's direct screen position (no transition active).
        self._crop_cx = None
        self._crop_cy = None
        self.camera_shake_timer = 0.0
        self.camera_shake_duration = 0.0
        self.camera_shake_intensity = 0.0
        self.camera_shake_offset = (0, 0)
        self.falling_rocks = []
        self.rock_fall_gravity = 1800.0
        self.rock_explosions = []

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
        self.pending_death_respawn_transition = False
        self.ground_colliders = []
        self.mossgrub_patrol_left = None
        self.mossgrub_patrol_right = None
        self.world_ground_y = int(config.screen_height * 0.62)
        self._arena_mossgrub_saved_positions = []
        self._arena_mossmother_exit_position = None

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
        arena_width = 1380
        arena_height = 760
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

        # Colliders are defined as rects in world space, but the player and camera positions are floats, so use ints for collider rects to avoid subtle sub-pixel bugs where the player can get stuck on edges due to inconsistent rounding.
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
        self._rebuild_collider_map_overlays(base_y)

        # Keep bench anchored to world ground, not player-specific values.
        if self.player:
            self.player.bench.rect.midbottom = (self.screen.get_width() // 2, base_y)

    # [12] github copilot
    def _sync_camera_lock_to_boss_arena(self, player_world_rect, dt):
        """
        Lock the camera to the arena center while Hornet is inside the boss room.
        args:
            player_world_rect (pygame.Rect): The player's rectangle in world coordinates, used to determine if they are inside the boss arena.
            dt (float): The delta time since the last frame, used for smooth camera interpolation.
        """
        if not self.player or not self.boss_arena_rect or not self.boss_arena_camera:
            self.camera_locked_to_arena = False
            self._crop_cx = None
            self._crop_cy = None
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

        # As soon as Hornet leaves the arena, restore the normal follow camera immediately so the camera tracks her exact movement again.
        self._reset_player_camera_follow(
            world_x=int(player_world_rect.x),
            world_y=int(player_world_rect.y),
        )

    def _update_arena_crop_center(self, player_world_rect, dt):
        """
        Lerp the viewport crop center toward the arena center (when locked) or back
        to Hornet (when unlocking).  This prevents the hard visual jump that would
        occur if draw_game switched crop targets based on a boolean.
        """
        blend = min(1.0, self.arena_camera_lerp_speed * dt)
        if self.camera_locked_to_arena and self.boss_arena_rect:
            target_cx = float(self.boss_arena_rect.centerx - self.camera_x)
            target_cy = float(self.boss_arena_rect.centery - self.camera_y)
            if self._crop_cx is None:
                # First frame entering the arena: seed from Hornet's current screen pos.
                self._crop_cx = float(self.player.rect.centerx)
                self._crop_cy = float(self.player.rect.centery)
            self._crop_cx += (target_cx - self._crop_cx) * blend
            self._crop_cy += (target_cy - self._crop_cy) * blend
        elif self._crop_cx is not None:
            # Camera just unlocked; lerp crop center back to Hornet.
            target_cx = float(self.player.rect.centerx)
            target_cy = float(self.player.rect.centery)
            self._crop_cx += (target_cx - self._crop_cx) * blend
            self._crop_cy += (target_cy - self._crop_cy) * blend
            if abs(target_cx - self._crop_cx) < 0.5 and abs(target_cy - self._crop_cy) < 0.5:
                self._crop_cx = None
                self._crop_cy = None

    def _is_floor_collider(self, collider_rect):
        """
        Return True for horizontal ground/platform colliders and False for vertical walls.
        args:
            collider_rect (pygame.Rect): The rectangle representing the collider to check. 
        returns:
            bool: True if the collider is a horizontal floor/platform, False if it is a vertical wall.
        """
        return collider_rect.width >= collider_rect.height

    def _get_ground_top_at_world_x(self, world_x):
        """
        Return the top Y of the highest floor collider under the given world X.
        args:
            world_x (int): The world X coordinate to check.
        returns:
            int or None: The top Y of the highest floor collider under the given world X, or None if no collider is found.
        """
        top_y = None
        for ground_rect in self.ground_colliders:
            if not self._is_floor_collider(ground_rect):
                continue
            if ground_rect.left <= world_x < ground_rect.right:
                if top_y is None or ground_rect.top < top_y:
                    top_y = ground_rect.top
        return top_y

    def _get_colliding_ground_top_for_world_rect(self, world_rect):
        """
        Return the top Y of the floor collider intersecting the given world-space rect.
        args:
            world_rect (pygame.Rect): The rectangle in world coordinates to check for collision.
        returns:
            int or None: The top Y of the floor collider intersecting the given world-space rect, or None if no collider is found.
        """
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

    def _snap_player_to_floor(self, search_radius=8):
        """Snap Hornet exactly onto the nearest floor at or below her current world position.
        args:
            search_radius (int): The maximum distance above or below the player's current world bottom to search for a floor collider to snap to.
        """
        if not self.player:
            return

        world_bottom = self.player.rect.bottom + int(self.camera_y)
        world_left   = self.player.rect.left   + int(self.camera_x)
        world_right  = self.player.rect.right  + int(self.camera_x)

        # Search from slightly above current bottom downward.
        search_top    = world_bottom - search_radius
        search_bottom = world_bottom + search_radius

        best_floor_top = None
        for collider_rect in self.ground_colliders:
            if not self._is_floor_collider(collider_rect):
                continue
            if world_right <= collider_rect.left or world_left >= collider_rect.right:
                continue
            if collider_rect.top < search_top or collider_rect.top > search_bottom:
                continue
            # Among matching floors pick the one whose top is closest to world_bottom
            if best_floor_top is None or abs(collider_rect.top - world_bottom) < abs(best_floor_top - world_bottom):
                best_floor_top = collider_rect.top

        if best_floor_top is not None:
            self.camera_y = int(best_floor_top - self.player.rect.bottom)
            self.player.velocity_y = 0
            self.player.on_ground = True

    def _snap_grub_to_floor(self, grub, search_radius=12):
        """
        Snap any MossGrub entity onto the nearest floor at or below its current world position.
        args:
            search_radius (int): The maximum distance above or below the MossGrub's current world bottom to search for a floor collider to snap to.
        """
        if grub is None:
            return

        world_bottom = grub.rect.bottom + int(self.camera_y)
        world_left   = grub.rect.left   + int(self.camera_x)
        world_right  = grub.rect.right  + int(self.camera_x)

        search_top    = world_bottom - search_radius
        search_bottom = world_bottom + search_radius

        best_floor_top = None
        for collider_rect in self.ground_colliders:
            if not self._is_floor_collider(collider_rect):
                continue
            if world_right <= collider_rect.left or world_left >= collider_rect.right:
                continue
            if collider_rect.top < search_top or collider_rect.top > search_bottom:
                continue
            if best_floor_top is None or abs(collider_rect.top - world_bottom) < abs(best_floor_top - world_bottom):
                best_floor_top = collider_rect.top

        if best_floor_top is not None:
            grub.rect.bottom = int(best_floor_top) - int(self.camera_y)
            grub.velocity_y = 0
            grub.on_ground = True

    def _reset_player_camera_follow(self, world_x=None, world_y=None):
        """
        Return Hornet to the normal follow-camera behavior after arena lock or respawn.
        args:
            world_x (int or None): The world X coordinate to reset the camera to. If None, uses the player's current world X.
            world_y (int or None): The world Y coordinate to reset the camera to. If None, uses the player's current world Y.
        """
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
        """
        Push MossGrub above the ground if it is currently inside a collider.
        args:
            world_x (int or None): The world X coordinate to check. If None, uses the MossGrub's current world X.
        """
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

    def _is_valid_mossgrub_world_rect(self, world_rect, vertical_tolerance=220):
        """
        Return True when a MossGrub world rect is close to a valid floor and patrol span.
        args:
            world_rect (pygame.Rect): The world rectangle of the MossGrub to check.
            vertical_tolerance (int): The maximum vertical distance from the floor to consider valid.
        """
        if not self.mossgrub or world_rect is None:
            return False

        within_patrol_x = True
        if self.mossgrub_patrol_left is not None and self.mossgrub_patrol_right is not None:
            within_patrol_x = self.mossgrub_patrol_left - 120 <= world_rect.centerx <= self.mossgrub_patrol_right + 120

        floor_top = self._get_colliding_ground_top_for_world_rect(world_rect)
        if floor_top is None:
            floor_top = self._get_ground_top_at_world_x(world_rect.centerx)

        near_valid_floor = floor_top is not None and abs(world_rect.bottom - floor_top) <= vertical_tolerance
        return within_patrol_x and near_valid_floor

    def _set_mossgrub_patrol_on_platform(self, platform_rect, spawn_world_x=None):
        """
        Place MossGrub on a specific world-space platform and clamp its patrol to that surface.
        args:
            platform_rect (pygame.Rect): The rectangle representing the platform in world coordinates.
            spawn_world_x (int or None): The world X coordinate to spawn MossGrub at. If None, uses the center of the platform.
        """
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

        # Clamp patrol bounds so the grub can't walk into vertical wall colliders that sit within the patrol zone at platform height.
        for wall_rect in self.ground_colliders:
            if self._is_floor_collider(wall_rect):
                continue
            if wall_rect.top > platform_rect.top or wall_rect.bottom < platform_rect.top:
                continue
            if wall_rect.right <= patrol_left or wall_rect.left >= patrol_right:
                continue
            # Wall straddles the right half → push patrol right inward
            if wall_rect.centerx >= (patrol_left + patrol_right) / 2:
                patrol_right = min(patrol_right, wall_rect.left - patrol_margin)
            else:
                patrol_left = max(patrol_left, wall_rect.right + patrol_margin)
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
            int(mossgrub_world_x) - int(self.camera_x),
            int(platform_rect.top) - int(self.camera_y),
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

        # Spawn on the main ground (ground_colliders[0]) to the left of start_x so the grub is reliably on solid ground on every save state.
        ground_top = self.ground_colliders[0].top if self.ground_colliders else int(self.world_ground_y)
        spawn_platform = pygame.Rect(int(start_x) - 700, ground_top, 400, 20)
        self._set_mossgrub_patrol_on_platform(spawn_platform)

    def _register_overworld_mossgrub(self, mossgrub):
        """Register the persistent overworld MossGrub entity."""
        self.mossgrub = mossgrub
        self.mossgrubs["overworld"] = mossgrub

    def _iter_mossgrub_entities(self):
        """Yield all active MossGrub entities as (entity, is_arena_spawn)."""
        overworld = self.mossgrubs.get("overworld")
        if overworld is not None:
            yield overworld, False
        for arena_grub in self.mossgrubs.get("arena", {}).values():
            yield arena_grub, True

    def _clear_arena_mossgrubs(self):
        """Remove all temporary arena-spawned MossGrub entities."""
        self.mossgrubs["arena"] = {}

    def _spawn_arena_mossgrub(self, spawn_world_x, spawn_world_y=None):
        """
        Spawn a temporary MossGrub in the arena without touching overworld MossGrub state.
        args:
            spawn_world_x (int): The x-coordinate in the world to spawn the MossGrub.
            spawn_world_y (int, optional): The y-coordinate in the world to spawn the MossGrub. Defaults to None.
        """
        if not self.boss_arena_rect:
            return

        arena_id = self._next_arena_mossgrub_id
        self._next_arena_mossgrub_id += 1

        arena_grub = MossGrub(0, 0, config.screen_width, config.screen_height)
        arena_grub.health = arena_grub.max_health

        if spawn_world_y is not None:
            world_bottom = int(spawn_world_y)
            # Clamp to valid floor area inside the arena so rocks that land on the ceiling collider don't push the grub outside the arena.
            world_bottom = max(
                self.boss_arena_rect.top + arena_grub.rect.height,
                min(int(self.boss_arena_rect.bottom), world_bottom),
            )
        else:
            world_bottom = int(self.boss_arena_rect.bottom)
        world_x = int(max(self.boss_arena_rect.left + arena_grub.rect.width // 2,
                          min(self.boss_arena_rect.right - arena_grub.rect.width // 2, spawn_world_x)))
        arena_grub.rect.midbottom = (
            int(world_x) - int(self.camera_x),
            int(world_bottom) - int(self.camera_y),
        )
        arena_grub.velocity_x = 0
        arena_grub.velocity_y = 0
        arena_grub.on_ground = True
        # Snap to the nearest floor collider so float-precision errors don't leave the grub floating above or embedded in the ground on spawn.
        self._snap_grub_to_floor(arena_grub)

        self.mossgrubs["arena"][arena_id] = arena_grub

    def _activate_arena_mossgrub(self, spawn_world_x, spawn_world_y=None):
        """
        Spawn an arena-specific MossGrub entity.
        args:
            spawn_world_x (int): The x-coordinate in the world to spawn the MossGrub.
            spawn_world_y (int, optional): The y-coordinate in the world to spawn the MossGrub. Defaults to None.
        """
        self._spawn_arena_mossgrub(spawn_world_x, spawn_world_y=spawn_world_y)

    def _save_arena_exit_positions(self):
        """Snapshot world positions of arena mossgrubs and mossmother before Hornet exits."""
        self._arena_mossgrub_saved_positions = []
        for grub in self.mossgrubs.get("arena", {}).values():
            if grub.is_dying or grub.health <= 0:
                continue
            self._arena_mossgrub_saved_positions.append({
                "world_centerx": int(grub.rect.centerx) + int(self.camera_x),
                "world_bottom":  int(grub.rect.bottom)  + int(self.camera_y),
                "health":        grub.health,
            })
        if self.mossmother:
            self._arena_mossmother_exit_position = {
                "world_x": int(self.mossmother.rect.x + self.camera_x),
                "world_y": int(self.mossmother.rect.y + self.camera_y),
            }

    def _restore_mossgrub_overworld_state(self):
        """Clear temporary arena MossGrubs when leaving the boss arena."""
        self._save_arena_exit_positions()
        self._clear_arena_mossgrubs()

    def _update_mouse_lock(self):
        """Ensure the mouse stays unlocked for UI interaction."""
        if self.mouse_locked:
            pygame.event.set_grab(False)
            self.mouse_locked = False

    def trigger_camera_shake(self, duration=0.6, intensity=12.0):
        """
        Trigger a reusable screen shake effect for dramatic moments.
        args:
            duration (float): The duration of the camera shake in seconds.
            intensity (float): The intensity of the camera shake.
        """
        self.camera_shake_timer = max(self.camera_shake_timer, float(duration))
        self.camera_shake_duration = max(self.camera_shake_duration, float(duration))
        self.camera_shake_intensity = max(self.camera_shake_intensity, float(intensity))

    def _update_camera_shake(self, dt):
        """
        Advance the camera shake effect and update the render offset.
        args:
            dt (float): The time delta in seconds since the last update.
        """
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

        rock_size = self.moss_collapse_plat_size
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
            self.audio_manager.play_sfx("hornet_roar_lock")
        self._spawn_mossmother_cry_rocks()

    def _update_falling_rocks(self, dt, player_world_rect):
        """
        Advance falling cry-attack rocks, damage Hornet on contact, and spawn a MossGrub on one impact.
        args:
            dt (float): The time delta in seconds since the last update.
            player_world_rect (pygame.Rect): The player's world-space rectangle for collision detection.
        """
        if not self.falling_rocks and not self.rock_explosions:
            return

        # Advance existing rock explosion animations
        active_explosions = []
        for exp in self.rock_explosions:
            exp["elapsed"] += dt
            if exp["elapsed"] >= exp["frame_speed"]:
                exp["elapsed"] -= exp["frame_speed"]
                exp["frame"] += 1
            if exp["frame"] < exp["total_frames"]:
                active_explosions.append(exp)
        self.rock_explosions = active_explosions

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
                self.audio_manager.play_sfx("rock_break")
                if self._rock_explode_frames:
                    self.rock_explosions.append({
                        "world_x": rock_rect.centerx,
                        "world_y": rock_rect.bottom,
                        "frame": 0,
                        "elapsed": 0.0,
                        "frame_speed": 0.07,
                        "total_frames": len(self._rock_explode_frames),
                    })
                if rock.get("spawn_mossgrub"):
                    self._activate_arena_mossgrub(spawn_world_x=rock_rect.centerx, spawn_world_y=rock_rect.bottom)
                continue

            if self.player and player_world_rect.colliderect(rock_rect) and self.player_contact_damage_timer <= 0.0:
                knockback_direction = -1 if player_world_rect.centerx < rock_rect.centerx else 1
                self.player.take_damage(1, knockback_direction=knockback_direction)
                self.player_contact_damage_timer = self.player_contact_damage_cooldown

            remaining_rocks.append(rock)

        self.falling_rocks = remaining_rocks

    def _spawn_enemy_death_fung_motes(self, enemy_world_rect):
        """
        Spawn fung mote burst at enemy death position and let motes fall to local ground.
        args:
            enemy_world_rect (pygame.Rect): The world-space rectangle of the enemy.
        """
        if enemy_world_rect is None:
            return

        ground_y = self._get_ground_top_at_world_x(enemy_world_rect.centerx)
        if ground_y is None:
            ground_y = enemy_world_rect.bottom + 220

        self.particle_system.spawn_fung_mote_death_burst(
            enemy_world_rect.centerx,
            enemy_world_rect.centery,
            ground_y=ground_y,
        )

    def _update_enemy_death_particle_triggers(self):
        """Emit one fung-mote death burst per enemy death event."""
        for grub, _ in self._iter_mossgrub_entities():
            if grub.health > 0:
                grub._fung_mote_death_spawned = False
                continue

            if getattr(grub, "_fung_mote_death_spawned", False):
                continue

            grub_world_rect = grub.rect.copy()
            grub_world_rect.x += int(self.camera_x)
            grub_world_rect.y += int(self.camera_y)
            self._spawn_enemy_death_fung_motes(grub_world_rect)
            grub._fung_mote_death_spawned = True

        if self.mossmother:
            if self.mossmother.health > 0:
                self.mossmother._fung_mote_death_spawned = False
            elif not getattr(self.mossmother, "_fung_mote_death_spawned", False):
                mossmother_world_rect = self.mossmother.rect.copy()
                mossmother_world_rect.x += int(self.camera_x)
                mossmother_world_rect.y += int(self.camera_y)
                self._spawn_enemy_death_fung_motes(mossmother_world_rect)
                self.mossmother._fung_mote_death_spawned = True

    def create_buttons(self):
        """Create the title screen menu buttons."""
        # Scale positions to actual screen size
        button_spacing = 80
        shifty = 200
        button_font_size = 40
        
        self.buttons = {
            "start": Button(config.screen_width/2, config.screen_height/2 - button_spacing+shifty, "Start Game", config.white, config.title_font_path, button_font_size),
            "settings": Button(config.screen_width/2, config.screen_height/2+shifty, "Options", config.white, config.title_font_path, button_font_size),
            "exit": Button(config.screen_width/2, config.screen_height/2 + button_spacing+shifty, "Exit", config.white, config.title_font_path, button_font_size),
            }

    def update_title_screen(self, dt):
        """
        Update the title screen elements, including buttons and particle effects.
        args:
            dt (float): The time delta in seconds since the last update.
        """
        for button in self.buttons.values():
            button.update(dt)

        if self.pending_title_timer > 0.0:
            self.pending_title_timer = max(0.0, self.pending_title_timer - dt)
            if self.pending_title_timer <= 0.0 and self.pending_title_action is not None:
                action = self.pending_title_action
                self.pending_title_action = None
                if action == "start":
                    self.change_state("save files")
                elif action == "settings":
                    self.settings_menu.show()
                    self.change_state("settings")
                elif action == "exit":
                    self.running = False
        
        # Enable ember spawning and update particle system
        self.particle_system.enable_ember_spawning(True)
        self.particle_system.update(dt)
    
    def update_settings(self, dt):
        """
        Update the settings menu elements and handle interactions.
        args:
            dt (float): The time delta in seconds since the last update.
        """
        self.settings_menu.update(dt)
    
    def update_save_files(self, dt):
        """
        Update the save files menu elements and handle interactions.
        args:
            dt (float): The time delta in seconds since the last update.
        """
        if self.pending_save_files_back_timer > 0.0:
            self.pending_save_files_back_timer = max(0.0, self.pending_save_files_back_timer - dt)
            if self.pending_save_files_back_timer <= 0.0:
                self.change_state("title screen")
                return

        self.save_file.update(dt)

    def trigger_ui_flash(self, x=None, y=None):
        """
        Play a one-shot UI flash animation centered at the given point.
        args:
            x (int, optional): The x-coordinate of the flash center. Defaults to None.
            y (int, optional): The y-coordinate of the flash center. Defaults to None.
        """
        if x is None or y is None:
            self.ui_flash_anchor = (config.screen_width // 2, config.screen_height // 2)
        else:
            self.ui_flash_anchor = (int(x), int(y))
        self.ui_flash_active = True
        self.ui_flash_anim.set_animation("play", reset=True)

    def _update_ui_flash(self, dt):
        """
        Advance global UI flash animation state.
        args:
            dt (float): The time delta in seconds since the last update.
        """
        if not self.ui_flash_active:
            return
        self.ui_flash_anim.update(dt)
        if self.ui_flash_anim.is_finished():
            self.ui_flash_active = False

    def _draw_ui_flash(self):
        """Draw global UI flash centered on screen when active."""
        if not self.ui_flash_active:
            return
        flash_frame = self.ui_flash_anim.get_current_frame()
        if flash_frame is None:
            return
        flash_rect = flash_frame.get_rect(center=self.ui_flash_anchor)
        self.screen.blit(flash_frame, flash_rect)

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
        """
        Convert an OpenCV frame into a screen-ready pygame surface.
        args:
            frame (numpy.ndarray): The OpenCV frame to convert.
        """
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
        """
        Read the next prefetched frame of the intro cinematic into the draw cache.
        args:
            wait_timeout (float): The maximum time to wait for a frame in seconds.
        returns:
            bool: True if a new frame was read and cached, False if the cutscene has
            ended, or None if no new frame is available yet but the cutscene is still ongoing."""
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

    def _mark_intro_cutscene_seen(self):
        """Persist that this save slot has already consumed the intro cutscene."""
        if self.current_slot not in self.save_file.save_slots:
            return

        current_state = dict(self.game_state) if isinstance(self.game_state, dict) else {}
        if current_state.get("intro_cutscene_seen"):
            self.game_state = current_state
            return

        current_state["intro_cutscene_seen"] = True
        self.game_state = current_state
        self.save_file.save_game_file(current_state, self.current_slot)

    def _start_intro_cutscene(self, next_state="game"):
        """
        Open the intro cinematic before gameplay begins.
        args:
            next_state (str): The state to transition to after the cutscene ends.
        """
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
        """
        Advance the intro cinematic and transition into gameplay when it ends.
        args:
            dt (float): The time elapsed since the last update in seconds.
        """
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

    def update_tutorial(self, dt):
        """
        Advance tutorial slide transitions and hover state.
        args:
            dt (float): The time elapsed since the last update in seconds.
        """
        if self.transition_manager.active:
            return
        mouse_pos = pygame.mouse.get_pos()
        self.tutorial.update(dt, mouse_pos)

    def update_game(self, dt):
        """
        Update the main game state, including player, enemies, camera, and interactions.
        args:
            dt (float): The time elapsed since the last update in seconds.
        """
        self.game_back_button.update(dt)

        if self.pending_game_back_timer > 0.0:
            self.pending_game_back_timer = max(0.0, self.pending_game_back_timer - dt)
            if self.pending_game_back_timer <= 0.0:
                self.save_current_game_state(force=True)
                self.change_state("title screen")
                return

        back_hovered = self.game_back_button.is_hovered()
        if back_hovered and not self._game_back_button_was_hovered and self.player is not None:
            self.player.trigger_hud_flash()
        self._game_back_button_was_hovered = back_hovered

        if self.player is None:
            return

        player = self.player

        # Track camera before updates to compute delta for mossgrub
        prev_camera_x = self.camera_x
        prev_camera_y = self.camera_y

        # Exact world-space position before ANY movement this frame.
        # Used by the post-update tunneling check below.
        prev_player_world_x = int(player.rect.x + self.camera_x)

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

        # Final post-update wall sweep: catches both residual overlaps (corner clips) and full tunnels (high-velocity shots past a thin wall). Uses the exact pre-move world position so detection is frame-rate independent.
        _curr_wx = int(player.rect.x + self.camera_x)
        _curr_wy = int(player.rect.y + self.camera_y)
        _pw = player.rect.width
        _ph = player.rect.height

        for _wall in self.ground_colliders:
            if self._is_floor_collider(_wall):
                continue
            # Vertical guard: skip if Hornet is entirely above or below the wall.
            if _curr_wy + _ph <= _wall.top + 4 or _curr_wy >= _wall.bottom:
                continue

            _pl = _curr_wx
            _pr = _curr_wx + _pw

            if _pr > _wall.left and _pl < _wall.right:
                # Overlap — push out to nearest face.
                if _pl + _pw // 2 < _wall.centerx:
                    _curr_wx = _wall.left - _pw
                    player.touching_wall_right = True
                    player.knockback_velocity_x = min(0.0, player.knockback_velocity_x)
                    player.attack_recoil_velocity_x = min(0.0, player.attack_recoil_velocity_x)
                    player.velocity_x = min(0.0, player.velocity_x)
                else:
                    _curr_wx = _wall.right
                    player.touching_wall_left = True
                    player.knockback_velocity_x = max(0.0, player.knockback_velocity_x)
                    player.attack_recoil_velocity_x = max(0.0, player.attack_recoil_velocity_x)
                    player.velocity_x = max(0.0, player.velocity_x)
            else:
                # No overlap — swept/tunneling check using exact pre-move position.
                _ppl = prev_player_world_x
                _ppr = _ppl + _pw
                if _ppr <= _wall.left and _pr > _wall.left:
                    _curr_wx = _wall.left - _pw
                    player.touching_wall_right = True
                    player.knockback_velocity_x = min(0.0, player.knockback_velocity_x)
                    player.attack_recoil_velocity_x = min(0.0, player.attack_recoil_velocity_x)
                    player.velocity_x = min(0.0, player.velocity_x)
                elif _ppl >= _wall.right and _pl < _wall.right:
                    _curr_wx = _wall.right
                    player.touching_wall_left = True
                    player.knockback_velocity_x = max(0.0, player.knockback_velocity_x)
                    player.attack_recoil_velocity_x = max(0.0, player.attack_recoil_velocity_x)
                    player.velocity_x = max(0.0, player.velocity_x)
                else:
                    continue

            # Apply correction immediately so subsequent walls use the updated pos.
            if self.camera_locked_to_arena:
                player.rect.x = int(_curr_wx - self.camera_x)
            else:
                self.camera_x = float(_curr_wx - player.rect.x)

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

        camera_world_rect = pygame.Rect(int(self.camera_x), int(self.camera_y), config.screen_width, config.screen_height)
        self.particle_system.update_gameplay_particles(dt, camera_world_rect, ground_colliders=self.ground_colliders)
        player_world_hitbox = player.get_world_hitbox(camera_x=self.camera_x, camera_y=self.camera_y)
        self._sync_camera_lock_to_boss_arena(player_world_rect, dt)

        player_world_rect = player.rect.copy()
        player_world_rect.x += int(self.camera_x)
        player_world_rect.y += int(self.camera_y)
        self._update_arena_crop_center(player_world_rect, dt)

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
                self._reset_encounter_state()
                self.save_current_game_state(force=True)

        _prev_bench_interact_key_down = self._bench_interact_key_down
        self._bench_interact_key_down = interact_pressed

        if player.is_dead:
            if player.death_animation_complete:
                self._start_death_respawn_transition()
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

        for grub, is_arena_spawn in self._iter_mossgrub_entities():
            if is_arena_spawn and self.boss_arena_rect:
                arena_left = int(self.boss_arena_rect.left - self.camera_x)
                arena_right = int(self.boss_arena_rect.right - self.camera_x)
                min_bound, max_bound = arena_left, arena_right
            else:
                min_bound, max_bound = mossgrub_left_bound, mossgrub_right_bound

            grub.update(min_bound, max_bound, dt,
                        collision_rects=self.ground_colliders,
                        camera_x=self.camera_x,
                        camera_y=self.camera_y,
                        camera_dx=camera_dx,
                        camera_dy=camera_dy)

            # Post-update: hard-clamp overworld grub out of any wall collider it may have been pushed into by knockback or a bad saved position.
            if not is_arena_spawn:
                grub_world_rect = grub.rect.copy()
                grub_world_rect.x += int(self.camera_x)
                grub_world_rect.y += int(self.camera_y)
                for _wall in self.ground_colliders:
                    if self._is_floor_collider(_wall):
                        continue
                    if not grub_world_rect.colliderect(_wall):
                        continue
                    if grub_world_rect.bottom <= _wall.top + 4:
                        continue
                    if grub_world_rect.centerx < _wall.centerx:
                        grub_world_rect.right = _wall.left
                    else:
                        grub_world_rect.left = _wall.right
                    grub.rect.x = int(grub_world_rect.x - self.camera_x)
                    break

        if self.mossmother and (self.mossmother.health > 0 or self.mossmother.is_dying):
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
            egg_break_world = self.mossmother.consume_egg_break_trigger()
            if egg_break_world:
                egg_rect = pygame.Rect(0, 0, 40, 60)
                egg_rect.center = egg_break_world
                self._spawn_enemy_death_fung_motes(egg_rect)
            if self.mossmother.consume_death_roar_trigger() and self.player and not self.player.is_dead:
                self.player.start_stun(duration=self.mossmother.death_roar_duration)
                self.audio_manager.play_sfx("hornet_roar_lock")

            if self.player.stun_timer > 0.0 and (self.mossmother.is_crying or self.mossmother.death_roar_active):
                mossmother_world_hitbox = self.mossmother.get_world_hitbox(camera_x=self.camera_x, camera_y=self.camera_y)
                self.player.facing_right = mossmother_world_hitbox.centerx >= player_world_rect.centerx

        if (not self.mossgrubs["arena"] and self._arena_mossgrub_saved_positions
                and self.boss_arena_rect and self.boss_arena_rect.colliderect(player_world_rect)):
            # Hornet re-entered the arena mid-session: restore saved grubs
            saved = list(self._arena_mossgrub_saved_positions)
            self._arena_mossgrub_saved_positions = []
            for pos_data in saved:
                self._spawn_arena_mossgrub(
                    spawn_world_x=int(pos_data.get("world_centerx", 0)),
                    spawn_world_y=int(pos_data.get("world_bottom", 0)),
                )
                last_id = self._next_arena_mossgrub_id - 1
                grub = self.mossgrubs["arena"].get(last_id)
                if grub:
                    grub.health = max(1, int(pos_data.get("health", grub.max_health)))

        self._update_enemy_death_particle_triggers()

        self._update_falling_rocks(dt, player_world_hitbox)

        if player.consume_attack_trigger():
            player.start_attack_hitbox(
                camera_x=self.camera_x,
                camera_y=self.camera_y,
            )

        if player.attack_hitbox:
            attack_rect = player.attack_hitbox

            for grub, _ in self._iter_mossgrub_entities():
                if player.attack_hit_mossgrub:
                    break
                if grub.is_dying or grub.health <= 0:
                    continue
                mossgrub_world = grub.rect.copy()
                mossgrub_world.x += int(self.camera_x)
                mossgrub_world.y += int(self.camera_y)
                if attack_rect.colliderect(mossgrub_world):
                    knockback_direction = 1 if player_world_rect.centerx < mossgrub_world.centerx else -1
                    grub.take_damage(self.attack_damage, knockback_direction=knockback_direction)
                    player.apply_attack_recoil_on_hit(enemy_rect=mossgrub_world)
                    player.gain_silk(self.silk_per_hit)
                    player.attack_hit_mossgrub = True
                    if player.attack_hitbox_direction == "down":
                        player.rebound_from_down_attack(enemy_rect=mossgrub_world, camera_y=self.camera_y)

            if self.mossmother and self.mossmother.health > 0:
                mossmother_hitbox_world = self.mossmother.get_world_hitbox(camera_x=self.camera_x, camera_y=self.camera_y)
                if attack_rect.colliderect(mossmother_hitbox_world):
                    if not player.attack_hit_mossmother:
                        knockback_direction = 1 if player_world_rect.centerx < mossmother_hitbox_world.centerx else -1
                        self.mossmother.take_damage(
                            self.attack_damage,
                            knockback_direction=knockback_direction,
                            apply_knockback=not self.mossmother.is_attacking,
                        )
                        player.apply_attack_recoil_on_hit(enemy_rect=mossmother_hitbox_world)
                        player.gain_silk(self.silk_per_hit)
                        player.attack_hit_mossmother = True
                    if player.attack_hitbox_direction == "down":
                        player.rebound_from_down_attack(enemy_rect=mossmother_hitbox_world, camera_y=self.camera_y)

        # Contact damage: compare both in screen space
        if self.player_contact_damage_timer <= 0.0:
            for grub, _ in self._iter_mossgrub_entities():
                if grub.is_dying or grub.health <= 0:
                    continue
                mossgrub_world = grub.rect.copy()
                mossgrub_world.x += int(self.camera_x)
                mossgrub_world.y += int(self.camera_y)
                if player_world_hitbox.colliderect(mossgrub_world):
                    knockback_direction = -1 if player_world_hitbox.centerx < mossgrub_world.centerx else 1
                    player.take_damage(1, knockback_direction=knockback_direction)
                    self.player_contact_damage_timer = self.player_contact_damage_cooldown
                    break

        if self.mossmother and self.mossmother.health > 0:
            mossmother_hitbox_world = self.mossmother.get_world_hitbox(camera_x=self.camera_x, camera_y=self.camera_y)

            if self.mossmother.is_attacking:
                if not self.mossmother.attack_contact_registered and mossmother_hitbox_world.colliderect(player_world_hitbox):
                    self.mossmother.attack_contact_registered = True
                    self.mossmother.phase_through = True
                    knockback_direction = -1 if player_world_hitbox.centerx < mossmother_hitbox_world.centerx else 1
                    player.take_damage(1, knockback_direction=knockback_direction)
                    self.player_contact_damage_timer = self.player_contact_damage_cooldown
            else:
                if player_world_hitbox.colliderect(mossmother_hitbox_world) and self.player_contact_damage_timer <= 0.0:
                    knockback_direction = -1 if player_world_hitbox.centerx < mossmother_hitbox_world.centerx else 1
                    player.take_damage(1, knockback_direction=knockback_direction)
                    self.player_contact_damage_timer = self.player_contact_damage_cooldown
        if self.mossgrub and self.mossgrub.health <= 0:
            if self.player_near_bench and interact_pressed and not _prev_bench_interact_key_down:
                self.respawn_mossgrub()

        # Persist whenever tracked game state changes (including mid-air positions)
        self.save_current_game_state()

    def _reset_encounter_state(self):
        """Clear temporary hazards and restore enemies to their encounter start state."""
        self.falling_rocks = []
        self.rock_explosions = []
        self.player_contact_damage_timer = 0.0
        self.camera_shake_timer = 0.0
        self.camera_shake_duration = 0.0
        self.camera_shake_intensity = 0.0
        self.camera_shake_offset = (0, 0)
        self.player_near_bench = False
        self.bench_interact_text = ""
        self._bench_interact_key_down = False

        if self.mossgrub:
            self._clear_arena_mossgrubs()
            self.mossgrub.health = self.mossgrub.max_health
            self.mossgrub.is_dying = False
            self.mossgrub.death_landed = False
            self.mossgrub.death_finished = False
            self.mossgrub.velocity_y = 0
            self._set_mossgrub_spawn_and_patrol()

        if self.mossmother:
            if self.boss_arena_rect:
                arena_spawn_x = int(self.boss_arena_rect.centerx)
                arena_spawn_y = int(self.boss_arena_rect.top + self.mossmother.rect.height + 40)
                self.mossmother.reset_position(arena_spawn_x, arena_spawn_y)
            else:
                self.mossmother.reset_position(self.mossmother.rect.centerx, self.mossmother.rect.bottom)
            self.mossmother.health = self.mossmother.max_health

    def _start_death_respawn_transition(self):
        """Fade to black, respawn Hornet at midpoint, then fade back to gameplay."""
        if self.pending_death_respawn_transition:
            return

        started = self.transition_manager.start_transition(
            target_state=None,
            transition_type=TransitionType.FADE_COLOR,
            speed=1.6,
            state_change_callback=lambda _target_state: self.respawn_player(),
            completion_callback=self._finish_death_respawn_transition,
            easing="ease_in_out",
            midpoint_hold=0.12,
            color=(0, 0, 0),
        )
        if started:
            self.pending_death_respawn_transition = True

    def _finish_death_respawn_transition(self):
        """Clear the in-progress death/respawn transition flag."""
        self.pending_death_respawn_transition = False

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
        # Snap to nearest floor (handles 1-3px float-truncation gap as well as penetration).
        self._snap_player_to_floor()
        self.player.reset_position(self.player.rect.centerx, self.player.rect.bottom)

        self.player.health = self.player.max_health
        self.player._start_respawn_on_bench()

        self._reset_encounter_state()
        self.save_current_game_state(force=True)

    def respawn_mossgrub(self):
        """Respawn MossGrub and Moss Mother at full health."""
        self._reset_encounter_state()
        self.save_current_game_state(force=True)

    def save_current_game_state(self, force=False):
        """
        Save player progress to the current save slot if state changed.
        Args:
            force (bool): If True, force saving even if state hasn't changed.
        """
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
            mossgrub_world_rect = self.mossgrub.rect.copy()
            mossgrub_world_rect.x += int(self.camera_x)
            mossgrub_world_rect.y += int(self.camera_y)
            if not self.mossgrub.is_dying and self._is_valid_mossgrub_world_rect(mossgrub_world_rect):
                mossgrub_position = [
                    int(mossgrub_world_rect.x),
                    int(mossgrub_world_rect.y)
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
            tuple(tuple(sorted(d.items())) for d in self._arena_mossgrub_saved_positions)
                if self._arena_mossgrub_saved_positions else (),
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
            "arena_mossgrub_positions": list(self._arena_mossgrub_saved_positions)
                if self._arena_mossgrub_saved_positions else [],
        })
        self.save_file.save_game_file(base_state, self.current_slot)
        self.game_state = base_state
        self._last_saved_signature = state_signature
    
    def _load_game_sounds(self):
        """Register every game sound effect with the audio manager."""
        self.audio_manager.load_sounds({
            # UI
            "button_click": "button",
            # Hornet movement
            "hornet_jump": "hornet_jump",
            "hornet_wall_jump": "hornet_wall_jump",
            "hornet_land_moss": "hornet_land_moss",
            "hornet_wall_land": "hornet_wall_land",
            "hornet_footstep_1": "hornet_footstep_moss_1",
            "hornet_footstep_2": "hornet_footstep_moss_2",
            "hornet_footstep_3": "hornet_footstep_moss_3",
            "hornet_footstep_4": "hornet_footstep_moss_4",
            "hornet_mantle_grab": "hornet_mantle_grab",
            # Hornet combat
            "hornet_sword": "hornet_sword",
            "hornet_attack_scream_1": "hornet_attack_scream_1",
            "hornet_attack_scream_2": "hornet_attack_scream_2",
            "hornet_attack_scream_3": "hornet_attack_scream_3",
            "hornet_attack_scream_4": "hornet_attack_scream_4",
            # Hornet silk / healing
            "hornet_silkcharge": "hornet_silkcharge",
            "hornet_bind_ready": "hornet_bind_ready",
            "hornet_bind_1": "hornet_bind_1",
            "hornet_bind_2": "hornet_bind_2",
            "hornet_bind_break": "hornet_bind_break",
            "hornet_bind_scream_1": "hornet_bind_scream_1",
            "hornet_bind_scream_2": "hornet_bind_scream_2",
            # Hornet life events
            "hornet_death": "hornet_death",
            "hornet_death_scream": "hornet_death_scream",
            "hornet_roar_lock": "hornet_roar_lock_grunt",
            "hornet_wake_up": "hornet_wake_up",
            "bench_rest": "bench_rest",
            # Boss / enemies
            "boss_death_1": "boss_death_1",
            "boss_death_2": "boss_death_2",
            "boss_stun": "boss_stun",
            "boss_wall_hit": "boss_wall_hit",
            "enemy_death": "enemy_death",
            "enemy_corpse_land": "enemy_corpse_land",
            "mossgrub_scream": "mossgrub_scream",
            # Atmosphere
            "atmos_moss_cave": "atmos_moss_cave",
            # Moss Mother boss
            "moss_mother_attack": "moss_mother_attack",
            "moss_mother_attack_scream_1": "moss_mother_attack_scream_1",
            "moss_mother_attack_scream_2": "moss_mother_attack_scream_2",
            "moss_mother_ceiling_dash": "moss_mother_ceiling_dash",
            "moss_mother_ceiling_hit": "moss_mother_ceiling_hit",
            "moss_mother_egg_break": "moss_mother_egg_break",
            "moss_mother_fly": "moss_mother_fly",
            "moss_mother_scream": "moss_mother_scream",
            "moss_mother_stun": "moss_mother_stun",
            "mossbone_particle": "mossbone_particle",
            "rock_break": "rock_break",
        })

    def change_state(self, new_state):
        """
        Transition to a new game state with a black fade.
        Args:
            new_state (str): The target game state to transition to.
        """
        def on_state_change(target_state):
            """
            Callback to update the current state at the midpoint of the transition.
            Args:
                target_state (str): The state to switch to after the fade-out completes.
            """
            self.state = target_state
            # Refresh save slot cache when entering save files screen
            if target_state == "save files":
                self.save_file.refresh_slot_status()
            # Stop all SFX on state change to avoid channel bleed from previous session
            self.audio_manager.stop_all_sfx()
            # Music and atmosphere transitions
            if target_state in ("title screen", "settings", "save files"):
                self.audio_manager.play_music("Title", loop=True)
                self.audio_manager.stop_atmosphere()
            elif target_state == "game":
                self.audio_manager.play_music("main", loop=True)
                self.audio_manager.play_atmosphere("atmos_moss_cave")
            elif target_state == "cutscene":
                self.audio_manager.play_music("intro_cinematics", loop=False)
                self.audio_manager.stop_atmosphere()
            elif target_state == "tutorial":
                self.audio_manager.stop_music(fade_out=1.0)
                self.audio_manager.stop_atmosphere()
                self.tutorial.reset()

        self.transition_manager.start_transition(
            target_state=new_state,

            transition_type=TransitionType.FADE_COLOR,
            speed=2.0,
            state_change_callback=on_state_change,
            color=(0, 0, 0)
        )
    
    def draw_title_screen(self):
        """Render the title screen, including background, particles, title image, and buttons."""
        # Draw background
        self.screen.blit(self.background_image, (0, 0))
        
        # Draw small ember particles
        self.particle_system.draw_particles(self.screen, size_max=6.0)
        
        # Draw the Silksong title image
        title_rect = self.title_image.get_rect(center=(config.screen_width/2, config.screen_height//2 - 200))
        self.screen.blit(self.title_image, title_rect)
        
        # Draw title spikes (boneforest images)
        self.screen.blit(self.title_needle, (1500, 175))
        self.screen.blit(self.title_pin, (1300, 475))
        self.screen.blit(self.title_boulder, (1050, 850))

        # Draw large ember particles (in front of boneforest)
        self.particle_system.draw_particles(self.screen, size_min=5.0)

        # Draw buttons
        for button in self.buttons.values():
            button.draw(self.screen)
                
    def draw_settings(self):
        """Render the settings overlay on top of the background."""
        self.screen.blit(self.background_image, (0, 0))
        self.settings_menu.draw(self.screen, self.settings_menu.font)

    def draw_save_file(self):
        """Render the save-file selection screen."""
        self.screen.blit(self.background_image, (0, 0))
        self.save_file.draw(self.screen)
    
    def draw_cutscene(self):
        """Render the active cutscene frame with a skip hint."""
        self.screen.fill((0, 0, 0))

        if self.cutscene_surface and self.cutscene_rect:
            self.screen.blit(self.cutscene_surface, self.cutscene_rect)

        if self._cutscene_skip_hint_surface is None:
            hint_font = config.get_font(24)
            self._cutscene_skip_hint_surface = hint_font.render("Press any key or click to skip", True, (220, 220, 220))
            self._cutscene_skip_hint_rect = self._cutscene_skip_hint_surface.get_rect(
                midbottom=(config.screen_width // 2, config.screen_height - 24)
            )
        self.screen.blit(self._cutscene_skip_hint_surface, self._cutscene_skip_hint_rect)

    def draw_tutorial(self):
        """Render the tutorial overlay (dark background + slide panel)."""
        self.screen.fill((0, 0, 0))
        self.tutorial.draw(self.screen)

    def draw_game(self):
        """Render the main game world, HUD, and all active entities."""
        self._ensure_game_render_assets()

        # All world content renders into _world_surface at full 1920×1080.
        # A viewport-sized crop centered on Hornet is then smoothscaled to
        # fill self.screen, producing a zoom effect without moving anything.
        look_y = self.player.camera_look_y if self.player else 0
        shake_x, shake_y = self.camera_shake_offset

        ws = self._world_surface
        # Only clear the viewport region — the rest of _world_surface is never displayed.
        vw = config.camera_viewport_width
        vh = config.camera_viewport_height
        if self.player:
            if self._crop_cx is not None:
                _fill_cx = self._crop_cx
                _fill_cy = self._crop_cy
            else:
                _fill_cx = float(self.player.rect.centerx)
                _fill_cy = float(self.player.rect.centery)
            _fill_x = max(0, min(config.game_width - vw, int(_fill_cx - vw // 2)))
            _fill_y = max(0, min(config.game_height - vh, int(_fill_cy - vh // 2)))
        else:
            _fill_x = (config.game_width - vw) // 2
            _fill_y = (config.game_height - vh) // 2
        ws.fill((0, 0, 0), pygame.Rect(_fill_x, _fill_y, vw, vh))

        bg_width, bg_height = self.game_background_image.get_size()
        bg_x = int((config.screen_width - bg_width) / 2 - self.camera_x * 0.18 + shake_x)
        bg_y = int((config.screen_height - bg_height) / 2 - self.camera_y * 0.12 - look_y * 0.35 + shake_y)
        bg_x = min(0, max(config.screen_width - bg_width, bg_x))
        bg_y = min(0, max(config.screen_height - bg_height, bg_y))
        ws.blit(self.game_background_image, (bg_x, bg_y))

        # Draw collider map overlay layers aligned to world space.
        for layer_data in getattr(self, "_collider_map_layers", {}).values():
            layer_image = layer_data.get("image")
            layer_origin = layer_data.get("world_origin")
            if layer_image is None or layer_origin is None:
                continue
            world_x, world_y = layer_origin
            screen_x = int(world_x - self.camera_x + shake_x)
            screen_y = int(world_y - self.camera_y - look_y + shake_y)
            ws.blit(layer_image, (screen_x, screen_y))

        self.particle_system.draw_gameplay_particles(
            ws,
            camera_x=self.camera_x,
            camera_y=self.camera_y,
            look_y_offset=look_y,
            screen_offset=(shake_x, shake_y),
        )

        for grub, _ in self._iter_mossgrub_entities():
            grub.draw(ws, look_y_offset=-look_y, screen_offset=(shake_x, shake_y))

        if self.mossmother and (self.mossmother.health > 0 or self.mossmother.is_dying):
            self.mossmother.draw(ws, look_y_offset=-look_y, screen_offset=(shake_x, shake_y))

        # Draw egg sprite at arena spawn point while mossmother is waiting to emerge
        if (self.mossmother and self.mossmother.showing_egg
                and self.mossmother.egg_image is not None):
            egg_world_x, egg_world_y = self.mossmother._egg_spawn_world
            egg_img = self.mossmother.egg_image
            ex = int(egg_world_x - self.camera_x + shake_x) - egg_img.get_width() // 2
            ey = int(egg_world_y - self.camera_y - look_y + shake_y) - egg_img.get_height() // 2
            ws.blit(egg_img, (ex, ey))

        if self.moss_collapse_plat_image is not None:
            for rock in self.falling_rocks:
                rock_draw_rect = rock["rect"].copy()
                rock_draw_rect.x -= int(self.camera_x - shake_x)
                rock_draw_rect.y -= int(self.camera_y + look_y - shake_y)
                ws.blit(self.moss_collapse_plat_image, rock_draw_rect)

        if self._rock_explode_frames:
            for exp in self.rock_explosions:
                frame_surf = self._rock_explode_frames[exp["frame"]]
                screen_x = int(exp["world_x"] - self.camera_x + shake_x) - frame_surf.get_width() // 2
                screen_y = int(exp["world_y"] - self.camera_y - look_y + shake_y) - frame_surf.get_height() // 2
                ws.blit(frame_surf, (screen_x, screen_y))

        if self.player:
            self.player.bench.draw(ws, camera_x=self.camera_x, camera_y=self.camera_y, look_y_offset=look_y, screen_offset=(shake_x, shake_y))
            self.player.draw(
                ws,
                look_y_offset=-look_y,
                screen_offset=(shake_x, shake_y),
                camera_x=self.camera_x,
                camera_y=self.camera_y,
            )

        # Zoom: crop _world_surface (viewport size) and smoothscale to fill the display.
        # When Hornet is inside the boss arena, lock the crop center to the arena center so the entire arena is always visible.  Otherwise follow Hornet.
        vw = config.camera_viewport_width
        vh = config.camera_viewport_height
        if self.player:
            if self._crop_cx is not None:
                cx = self._crop_cx + shake_x
                cy = self._crop_cy - look_y + shake_y
            else:
                cx = self.player.rect.centerx + shake_x
                cy = self.player.rect.centery - look_y + shake_y
            crop_x = max(0, min(config.game_width - vw, int(cx - vw // 2)))
            crop_y = max(0, min(config.game_height - vh, int(cy - vh // 2)))
        else:
            crop_x = (config.game_width - vw) // 2
            crop_y = (config.game_height - vh) // 2
        pygame.transform.smoothscale(
            ws.subsurface(pygame.Rect(crop_x, crop_y, vw, vh)),
            (config.game_width, config.game_height),
            self._zoom_surface,
        )
        self.screen.blit(self._zoom_surface, (0, 0))

        # HUD and UI draw directly on self.screen at fixed positions — unaffected by zoom.
        if self.player:
            if self.bench_interact_text:
                if self._bench_prompt_cache_text != self.bench_interact_text:
                    prompt_font = config.get_font(32)
                    self._bench_prompt_cache_surface = prompt_font.render(self.bench_interact_text, True, config.white)
                    self._bench_prompt_cache_rect = self._bench_prompt_cache_surface.get_rect(
                        center=(config.screen_width // 2, 130)
                    )
                    bg_rect = self._bench_prompt_cache_rect.inflate(24, 14)
                    self._bench_prompt_cache_bg = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                    self._bench_prompt_cache_bg.fill((0, 0, 0, 150))
                    self._bench_prompt_cache_bg_topleft = bg_rect.topleft
                    self._bench_prompt_cache_text = self.bench_interact_text
                self.screen.blit(self._bench_prompt_cache_bg, self._bench_prompt_cache_bg_topleft)
                self.screen.blit(self._bench_prompt_cache_surface, self._bench_prompt_cache_rect)

            self.player.draw_hud(self.screen)

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
        elif self.state == "tutorial":
            self.draw_tutorial()
        elif self.state == "game":
            self.draw_game()

        # Apply brightness setting to the rendered scene (1.0 = normal, 0.0 = fully dark)
        brightness = self.settings_menu.settings_data.get('brightness', 0.8)
        brightness = max(0.0, min(1.0, brightness))
        if brightness < 1.0:
            darkness_alpha = int((1.0 - brightness) * 255)
            if self._brightness_overlay_alpha != darkness_alpha:
                self._brightness_overlay.fill((0, 0, 0, darkness_alpha))
                self._brightness_overlay_alpha = darkness_alpha
            self.screen.blit(self._brightness_overlay, (0, 0))

        self._draw_ui_flash()
        
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
        Update the current game state by dt seconds.
        args:
            dt (float): The time elapsed since the last update in seconds.
        """
        self._update_mouse_lock()
        self._update_camera_shake(dt)
        self._update_ui_flash(dt)

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
        elif self.state == "tutorial":
            self.update_tutorial(dt)
        elif self.state == "game":
            self.update_game(dt)
            
    def handle_events(self):
        """Process all pending pygame events and dispatch by state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.state == "exit":
                self.running = False

            # ESC shortcuts for non-gameplay overlays
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state == "cutscene":
                    self._finish_cutscene()
                    continue
                if self.state == "tutorial":
                    self.change_state("game")
                    continue
            
            # Skip input handling during transitions
            if self.transition_manager.active:
                continue

            if self.state == "cutscene":
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self._finish_cutscene()
                continue

            if self.state == "tutorial":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.tutorial.handle_click(event.pos)
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
                    if self.pending_title_timer > 0.0:
                        continue

                    if self.buttons['start'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.trigger_ui_flash(self.buttons['start'].x, self.buttons['start'].y)
                        self.buttons['start'].press()
                        self.pending_title_action = "start"
                        self.pending_title_timer = self.title_button_click_delay
                    if self.buttons['exit'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.trigger_ui_flash(self.buttons['exit'].x, self.buttons['exit'].y)
                        self.buttons['exit'].press()
                        self.pending_title_action = "exit"
                        self.pending_title_timer = self.title_button_click_delay
                    if self.buttons['settings'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.trigger_ui_flash(self.buttons['settings'].x, self.buttons['settings'].y)
                        self.buttons['settings'].press()
                        self.pending_title_action = "settings"
                        self.pending_title_timer = self.title_button_click_delay
                
                elif self.state == "save files":
                    if self.pending_save_files_back_timer > 0.0:
                        continue

                    action = self.save_file.handle_event(pos)
                    if action == "close":
                        # Close button was clicked, return to title screen after a short delay.
                        self.audio_manager.play_sfx("button_click")
                        self.trigger_ui_flash(pos[0], pos[1])
                        self.pending_save_files_back_timer = self.save_files_back_click_delay
                    elif action and (action.startswith("start_") or action.startswith("start_new_")):
                        # Save slot was selected, start game
                        is_new_save = action.startswith("start_new_")
                        slot_num = int(action.split("_")[-1])
                        self.current_slot = slot_num
                        loaded_state = self.save_file.load_game_file(slot_num) or {}
                        self.game_state = loaded_state
                        self._last_saved_signature = None

                        # Create player when starting game

                        start_x = config.screen_width // 2
                        base_y = int(self.world_ground_y)
                        self.player = Hornet(start_x, base_y, config.screen_width, config.screen_height)
                        self._register_overworld_mossgrub(MossGrub(start_x, 0, config.screen_width, config.screen_height))
                        self._clear_arena_mossgrubs()
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

                        # Snap to nearest floor — handles both penetration and float-truncation gaps.
                        self._snap_player_to_floor()

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

                            colliding_top = self._get_colliding_ground_top_for_world_rect(saved_mossgrub_world_rect)

                            if self._is_valid_mossgrub_world_rect(saved_mossgrub_world_rect):
                                self.mossgrub.rect.x = saved_mossgrub_world_x - int(self.camera_x)
                                self.mossgrub.rect.y = saved_mossgrub_world_y - int(self.camera_y)
                                # Snap to nearest floor regardless of penetration amount.
                                self._snap_grub_to_floor(self.mossgrub)
                            else:
                                self._set_mossgrub_spawn_and_patrol()

                        saved_mossgrub_health = loaded_state.get("mossgrub_health", self.mossgrub.health)
                        self.mossgrub.health = max(0, min(self.mossgrub.max_health, int(saved_mossgrub_health)))
                        if self.mossgrub.health <= 0:
                            self.mossgrub.is_dying = True
                            self.mossgrub.death_landed = True
                            self.mossgrub.death_finished = True
                            self.mossgrub.velocity_y = 0
                            death_anim_name = "death_land_right" if self.mossgrub.display_facing_right else "death_land_left"
                            self.mossgrub._set_animation(death_anim_name, reset=True)
                            self.mossgrub.animation.current_frame = self.mossgrub.animation.get_animation_frame_count(death_anim_name) - 1
                            self.mossgrub.image = self.mossgrub.animation.get_current_frame()
                        else:
                            self.mossgrub.is_dying = False
                            self.mossgrub.death_landed = False
                            self.mossgrub.death_finished = False

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

                        # Restore arena mossgrubs saved at the last arena exit if the
                        # boss fight is still in progress (mossmother alive).
                        saved_arena_grubs = loaded_state.get("arena_mossgrub_positions")
                        self._arena_mossgrub_saved_positions = []
                        if (isinstance(saved_arena_grubs, list) and saved_arena_grubs
                                and self.mossmother and self.mossmother.health > 0):
                            self._arena_mossgrub_saved_positions = [
                                d for d in saved_arena_grubs if isinstance(d, dict)
                            ]
                            for pos_data in self._arena_mossgrub_saved_positions:
                                self._spawn_arena_mossgrub(
                                    spawn_world_x=int(pos_data.get("world_centerx", 0)),
                                    spawn_world_y=int(pos_data.get("world_bottom", 0)),
                                )
                                # Set the restored health on the freshly-spawned grub.
                                last_id = self._next_arena_mossgrub_id - 1
                                grub = self.mossgrubs["arena"].get(last_id)
                                if grub:
                                    grub.health = max(1, int(pos_data.get("health", grub.max_health)))

                        self.player_contact_damage_timer = 0.0
                        self.player_near_bench = False
                        self.bench_interact_text = ""
                        self._bench_interact_key_down = False
                        self.player_camera_anchor_x = int(self.player.rect.x)
                        self.player_camera_anchor_y = int(self.player.rect.y)

                        if is_new_save:
                            self.game_state["intro_cutscene_seen"] = False
                        elif "intro_cutscene_seen" not in self.game_state:
                            self.game_state["intro_cutscene_seen"] = True

                        # Persist state immediately so schema stays up-to-date
                        self.save_current_game_state(force=True)

                        # Only brand-new saves get the intro cinematic.
                        if is_new_save:
                            self._mark_intro_cutscene_seen()
                            self._start_intro_cutscene(next_state="tutorial")
                        else:
                            self.change_state("game")
                    # Delete actions are handled within save_file.handle_event

                elif self.state == "game":
                    if self.game_back_button.is_clicked(pos) and self.pending_game_back_timer <= 0.0:
                        self.audio_manager.play_sfx("button_click")
                        self.trigger_ui_flash(self.game_back_button.x, self.game_back_button.y)
                        if self.player is not None:
                            self.player.trigger_hud_flash()
                        self.pending_game_back_timer = self.game_back_click_delay

    def run(self):
        """Run the main game loop until the window is closed."""
        while self.running:
            dt = self.clock.tick(config.fps) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        # Save one last time before exiting
        self.save_current_game_state(force=True)
        self._release_cutscene_resources()
        # Stop all SFX channels on exit
        self.audio_manager.stop_all_sfx()
        pygame.quit()

# Run the game
if __name__ == "__main__":
    game = Silksong()
    game.run()