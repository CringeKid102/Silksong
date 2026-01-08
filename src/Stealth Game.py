import pygame
import random
import math
import time
import os
import cv2
from animation import Animation
from button import Button
from guard import Guard
from particles import ParticleSystem
from transition import TransitionManager, TransitionType
from audio import AudioManager
from settings import SettingsMenu

# Initialize Pygame
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
    
class StealthGame:
    def __init__(self):
        """
        Initialize the game.
        """
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Terminal Infiltration")
        self.clock = pygame.time.Clock()
        self.running = True

        # Reusable render canvas to avoid reallocating each frame
        self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()

        # Initialize fonts
        self.title_font = pygame.font.Font(None, 48)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)

        # Static text cache
        self._static_text_cache = {}

        self.state = "menu"
        self.paused = False
        self.show_pause_menu = False
        self._load_icons()
        
        # Game parameters
        self.mission_time = 60
        self.time_remaining = self.mission_time
        self.detection_level = 0
        self.max_detection = 100
        self.objective_progress = 0
        self.objectives_needed = 5
        self.secondary_objectives = []
        
        # Player upgrades and currency
        self.perks = {
            'cooldown_reduction': 0.0,
            'camera_disable_bonus': 0.0,
        }
        self.unlocked_perks = set()
        self.currency = 0
        self.pending_credits = 0
        
        # Statistics tracking
        self.best_objectives = 0
        self.best_time = 0
        
        # Game state flags
        self.debug_draw = False
        self.upgrade_menu_open = False
        self.show_quit_confirmation = False
        self.show_reset_confirmation = False

        # Credit animation
        self.credit_animation_timer = 0.0
        self.credit_animation_amount = 0

        # End screen animation
        self.end_screen_timer = 0.0
        self.animated_end_objectives = 0
        self.animated_end_detection = 0
        self.animated_end_time = 0

        # Difficulty settings
        self.difficulty = 'normal'
        self.difficulty_params = {
            'easy': {'guards': 2, 'detection_rate': 0.8, 'patrol_randomness': 0.8},
            'normal': {'guards': 3, 'detection_rate': 1.0, 'patrol_randomness': 1.0},
            'hard': {'guards': 5, 'detection_rate': 1.3, 'patrol_randomness': 1.3},
        }
        self.available_difficulties = ['easy', 'normal', 'hard']
        self.current_difficulty_index = self.available_difficulties.index(self.difficulty)
        self.scale_params = self.difficulty_params.get(self.difficulty, self.difficulty_params['normal'])

        # Guard initialization
        num_guards = self.scale_params['guards']
        self.guards = []
        for i in range(num_guards):
            patrol_time = int(8 + random.uniform(-2, 2) * self.scale_params['patrol_randomness'])
            self.guards.append(Guard(i + 1, patrol_time))
        self.load_guard_animations()

        # Smooth animated values
        self.animated_time = self.mission_time
        self.animated_detection = 0.0
        self.animated_objectives = 0.0

        # Camera blink animation
        self.camera_blink_time = 0.0
        self.camera_blink_active = False

        num_guards = self.scale_params['guards']
        self.guards = []
        for i in range(num_guards):
            patrol_time = int(8 + random.uniform(-2, 2) * self.scale_params['patrol_randomness'])
            self.guards.append(Guard(i + 1, patrol_time))
        self.load_guard_animations()

        # Initialize difficulty display names before button creation
        self.difficulty_menu_open = False
        self.difficulty_display_names = ['Easy', 'Normal', 'Hard']

        self.create_buttons()

        # Reset confirmation buttons
        self.reset_yes_btn = Button(WIDTH//2 - 120, HEIGHT//2 + 80, 100, 40, "YES", RED, DARK_GRAY)
        self.reset_no_btn = Button(WIDTH//2 + 20, HEIGHT//2 + 80, 100, 40, "NO", GREEN, DARK_GRAY)

        # Pause menu buttons
        self.pause_resume_btn = Button(WIDTH//2 - 100, HEIGHT//2 - 20, 200, 50, "RESUME", GREEN, DARK_GREEN)
        self.pause_menu_btn = Button(WIDTH//2 - 100, HEIGHT//2 + 50, 200, 50, "RETURN TO MENU", BLUE, DARK_BLUE)

        # System states
        self.camera_disabled = False
        self.camera_disable_time = 0
        self.lights_disabled = False
        self.lights_disable_time = 0

        self.event_timer = 0
        self.current_event = None

        # Initialize background video
        self.init_background()
        
        # messages to show feedback to player
        self.feedback_messages = []

        # UI animation timer used for pulsing effects
        self.ui_time = 0.0

        # particle system
        self.particle_sys = ParticleSystem()

        # Initialize transition system
        self.transition_manager = TransitionManager(WIDTH, HEIGHT, 700)
        self.toasts = []

        # Audio
        self.audio_manager = AudioManager()
        try:
            # Custom sound list for your game  
            custom_sounds = {
                'button_click': 'button_click', 'button_hover': 'button_hover', 
                'alert_beep': 'alert_beep', 'footsteps': 'footsteps',
                'hack_success': 'hack_success', 'hack_fail': 'hack_fail', 
                'camera_disable': 'camera_disable', 'lights_cut': 'lights_cut', 
                'distraction': 'distraction', 'system_startup': 'system_startup', 
                'countdown_tick': 'countdown_tick', 'mission_complete': 'mission_complete', 
                'mission_failed': 'mission_failed'
            }
            self.audio_manager.load_sounds(custom_sounds)
        except Exception as e:
            print(f"Error initializing AudioManager: {e}")
        
        # Settings menu
        try:
            self.settings_menu = SettingsMenu(WIDTH, HEIGHT, self.audio_manager, Button)
            self.settings_menu.game = self
        except Exception as e:
            print(f"Error initializing SettingsMenu: {e}")
            self.settings_menu = None
           
        # Difficulty selection already initialized above

        # Auto-load progress on startup
        if self.settings_menu:
            self.settings_menu.load_progress()

        # Text rendering cache for performance
        self._text_cache = {}

    def get_cached_text(self, text, font, color):
        """Cache rendered text to improve performance."""
        cache_key = (text, id(font), color)
        if cache_key not in self._text_cache:
            self._text_cache[cache_key] = font.render(text, True, color).convert_alpha()
        return self._text_cache[cache_key]

    def get_static_text(self, key, text, font, color):
        """Cache static rendered text."""
        if key not in self._static_text_cache:
            self._static_text_cache[key] = font.render(text, True, color).convert_alpha()
        return self._static_text_cache[key]

    def purchase_upgrade(self, key):
        """
        Purchase an upgrade/perk for the player.
        Args:
            key (str): The upgrade key to purchase.
        Returns:
            bool: True if purchase was successful, False otherwise.
        """
        # Calculate cost based on previous purchases
        if not hasattr(self, 'upgrade_purchase_count'):
            self.upgrade_purchase_count = {
                'cooldown_reduction': 0,
                'camera_disable_bonus': 0, 
                'detection_resistance': 0
                }
        
        # Base costs
        base_costs = {'cooldown_reduction': 5, 'camera_disable_bonus': 8, 'detection_resistance': 12}

        # Calculate cost with exponential scaling
        purchase_count = self.upgrade_purchase_count.get(key, 0)
        costs = int(base_costs[key] * (4 ** purchase_count))
        
        # Attempt purchase
        if self.currency >= costs:
            self.currency -= costs
            self.upgrade_purchase_count[key] = purchase_count + 1
            if key == 'cooldown_reduction':
                self.perks['cooldown_reduction'] = self.perks.get('cooldown_reduction', 0) + 0.2
                self.unlocked_perks.add('cooldown_reduction')
            elif key == 'camera_disable_bonus':
                self.perks['camera_disable_bonus'] = self.perks.get('camera_disable_bonus', 0) + 3.0
                self.unlocked_perks.add('camera_disable_bonus')
            elif key == 'detection_resistance':
                self.perks['detection_resistance'] = self.perks.get('detection_resistance', 0) + 0.15
                self.unlocked_perks.add('detection_resistance')
            self.add_toast(f"Purchased {key}", GREEN, 2.0)
            return True
        else:
            self.add_toast("Not enough credits", RED, 1.5)
            return False

    def _on_state_change(self, target_state: str):
        """
        Called when transition reaches midpoint to change game state.
        Args:
            target_state (str): The state to switch to.
        """
        self.state = target_state
        # Reset button text when transitioning to menu
        if target_state == "menu" and hasattr(self, 'buttons'):
            self.buttons['menu'].text = "START MISSION"
 
    def create_icon(self, color, symbol):
        """
        Create a simple icon surface.
        Args:
            color (Tuple[int,int,int]): Color of the icon.
            symbol (str): Symbol to draw on the icon.
        Returns:
            pygame.Surface: Icon surface.
        """
        icon_size =  24
        surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (icon_size//2, icon_size//2), icon_size//2-2)
        font = pygame.font.Font(None, 20)
        text = font.render(symbol, True, WHITE)
        surf.blit(text, text.get_rect(center=(icon_size//2, icon_size//2)))
        return surf

    def _load_icons(self):
        """Load button icons."""
        self.icons = {
            'clock': self.create_icon((100, 150, 255), 'T').convert_alpha(),
            'radar': self.create_icon((255, 100, 100), 'D').convert_alpha(),
            'target': self.create_icon((100, 255, 100), 'O').convert_alpha(),
            'camera': self.create_icon((100, 100, 200), 'C').convert_alpha(),
            'light': self.create_icon((200, 200, 100), 'L').convert_alpha(),
            'distract': self.create_icon((200, 100, 200), 'D').convert_alpha(),
            'hack': self.create_icon((100, 200, 100), 'H').convert_alpha(),
        }
    
    def load_guard_animations(self):
        """
        Load guard animations.
        """
        base = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "sprites"))
        sheet_path = os.path.join(base, "guard_sheet.png")
        try:
            for guard in self.guards:
                guard_set = {}
                animations = [
                    ('idle', {'row': 0, 'start_col': 0, 'num_frames': 4, 'speed': 0.2, 'loop': True}),
                    ('walk', {'row': 1, 'start_col': 0, 'num_frames': 6, 'speed': 0.1, 'loop': True}),
                    ('alert', {'row': 2, 'start_col': 0, 'num_frames': 4, 'speed': 0.15, 'loop': True})
                ]
                
                for name, params in animations:
                    anim = Animation(sheet_path, 32, 48)
                    # params already includes 'loop'; avoid passing it twice
                    anim.add_animation(name, **params)
                    # Ensure the animation object has an active animation set
                    anim.set_animation(name, reset=True)
                    guard_set[name] = anim
                
                guard.animation_set = guard_set
                guard.current_anim_name = 'idle'
        except Exception as e:
            pass
        
        # Randomize guard timings
        for guard in self.guards:
            guard.current_time = random.uniform(0, guard.patrol_time)
    
    def init_background(self):
        """
        Initialize background video.
        """
        self.bg_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "videos", "hacking bg.mp4"))
        self.bg_cap = None
        self.bg_frame_surf = None
        self.bg_scaled_surf = None
        self.bg_frame_count = 0
        try:
            self.bg_cap = cv2.VideoCapture(self.bg_path)
            if not self.bg_cap.isOpened():
                self.bg_cap = None
            else:
                ret, frame = self.bg_cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                    self.bg_frame_surf = surf.convert()
                    self.bg_scaled_surf = pygame.transform.scale(surf, (WIDTH, HEIGHT)).convert()
        except Exception:
            self.bg_cap = None
            self.bg_frame_surf = None
    
    def update_background(self, dt):
        """
        Update the background video frame.
        Args:
            dt (float): Delta time since last update.
        """
        if not self.bg_cap:
            return

        # Skep frames
        self.bg_frame_count += 1
        if self.bg_frame_count % 2 != 0:
            return
        
        ret, frame = self.bg_cap.read()
        if not ret:
            self.bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.bg_cap.read()
            if not ret:
                return
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            self.bg_frame_surf = surf.convert()
            # Pre-scale background to avoid scaling every frame
            self.bg_scaled_surf = pygame.transform.scale(surf, (WIDTH, HEIGHT)).convert()
        except Exception:
            pass

    def create_buttons(self):
        """Create action buttons for the game."""
        button_y = 500
        button_width = 140
        button_height = 50
        spacing = 160
        start_x = 100

        self.buttons = {
            'camera': Button(start_x, button_y, button_width, button_height, "Disable Cams", DARK_BLUE, BLUE,
                             tooltip="Disable security cameras\nReduces detection by 15%\nCooldown: 7s",
                             icon=self.icons['camera'], hotkey="1"),
            'lights': Button(start_x + spacing, button_y, button_width, button_height, "Cut Lights", DARK_BLUE, BLUE,
                             tooltip="Cut the lights in the area\nReduces detection by 10%\nCooldown: 6s",
                             icon=self.icons['light'], hotkey="2"),
            'distract': Button(start_x + 2 * spacing, button_y, button_width, button_height, "Distraction", DARK_BLUE, BLUE,
                             tooltip="Create a distraction to lure guards away\nReduces detection by 20%\nCooldown: 8s",
                             icon=self.icons['distract'], hotkey="3"),
            'hack': Button(start_x + 3 * spacing, button_y, button_width, button_height, "Hack System", DARK_GREEN, GREEN,
                           tooltip="Hack into the security system\nGain objective progress\nRisk vs Reward\nCooldown: 3-5s",
                           icon=self.icons['hack'], hotkey="4"),
            'menu': Button(WIDTH//2 - 100, HEIGHT//2 + 100, 200, 50, "START MISSION", DARK_GREEN, GREEN),
            'exit': Button(WIDTH//2 - 100, HEIGHT//2 + 170, 200, 50, "EXIT", RED, (255, 100, 100)),
            'settings': Button(WIDTH - 240, 20, 120, 40, "SETTINGS", DARK_GRAY, GRAY),
            'upgrades': Button(WIDTH - 380, 20, 120, 40, "UPGRADES", DARK_GRAY, GRAY),
            'reset': Button(WIDTH - 100, 20, 80, 40, "RESET", RED, DARK_GRAY),
            'pause_game': Button(WIDTH - 100, 20, 80, 40, "QUIT", RED, (255, 100, 100)),
            'difficulty': Button(WIDTH//2 - 100, HEIGHT//2 + 240, 200, 50, f"Difficulty: {self.difficulty_display_names[self.current_difficulty_index]}", DARK_GRAY, GRAY)
        }

    def add_toast(self, text: str, color, duration: float = 2.0):
        """
        Add a toast notification.
        Args:
            text (str): The text of the toast.
            color (Tuple[int,int,int]): The color of the toast text.
            duration (float): Duration in seconds the toast should be visible.
        """
        self.toasts.append({
            'text': text,
            'color': color,
            'time': duration,
            'duration': duration,
        })

    def add_credit_animation(self, amount: int):
        """
        Start credit gain animation.
        Args:
            amount (int): Amount of credits gained.
        """
        self.credit_animation_timer = 2.0  # 2 seconds
        self.credit_animation_amount = amount

    def draw_quit_confirmation(self):
        """Draw quit confirmation dialog."""
        # Background overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Dialog panel
        panel_width, panel_height = 400, 200
        panel_x = (WIDTH - panel_width) // 2
        panel_y = (HEIGHT - panel_height) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        
        pygame.draw.rect(self.screen, (60, 60, 80), panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, RED, panel_rect, 3, border_radius=10)
        
        # Warning text
        warning_text = self.get_static_text("quit_warning", "WARNING!", self.font, RED)
        warning_rect = warning_text.get_rect(center=(panel_x + panel_width//2, panel_y + 40))
        self.screen.blit(warning_text, warning_rect)
        
        # Message
        msg1 = self.get_static_text("quit_msg1", "If you quit now, you will lose", self.small_font, WHITE)
        pending = getattr(self, 'pending_credits', 0)
        if pending > 0:
            msg2 = self.small_font.render(f"{pending} pending credits!", True, YELLOW)
        else:
            msg2 = self.small_font.render("No credits will be lost.", True, GREEN)
        msg3 = self.small_font.render("Are you sure?", True, WHITE)

        msg1_rect = msg1.get_rect(center=(panel_x + panel_width//2, panel_y + 80))
        msg2_rect = msg2.get_rect(center=(panel_x + panel_width//2, panel_y + 100))
        msg3_rect = msg3.get_rect(center=(panel_x + panel_width//2, panel_y + 120))
        
        self.screen.blit(msg1, msg1_rect)
        self.screen.blit(msg2, msg2_rect)
        self.screen.blit(msg3, msg3_rect)
        
        # Buttons
        yes_btn = Button(panel_x + 50, panel_y + 150, 100, 30, "YES, QUIT", RED, (255, 100, 100))
        no_btn = Button(panel_x + 250, panel_y + 150, 100, 30, "NO, STAY", GREEN, (100, 255, 100))
        
        yes_btn.draw(self.screen, self.small_font)
        no_btn.draw(self.screen, self.small_font)
        
        # Store button references for event handling
        self.quit_yes_btn = yes_btn
        self.quit_no_btn = no_btn

    def reset_game(self):
        """
        Reset the game state.
        """
        self.time_remaining = self.mission_time
        self.animated_time = self.mission_time
        self.detection_level = 0
        self.animated_detection = 0.0
        self.objective_progress = 0
        self.animated_objectives = 0.0
        self.pending_credits = 0
        self.camera_disabled = False
        self.camera_disable_time = 0
        self.camera_blink_time = 0.0
        self.camera_blink_active = False
        self.lights_disabled = False
        self.lights_disable_time = 0
        self.event_timer = 0
        self.current_event = None

        num_guards = self.scale_params['guards']
        self.guards = []
        for i in range(num_guards):
            patrol_time = int(8 + random.uniform(-2, 2) * self.scale_params['patrol_randomness'])
            self.guards.append(Guard(i + 1, patrol_time))
        self.load_guard_animations()

        self.create_buttons()

        for guard in self.guards:
            guard.alert = False
            guard.alert_time = 0.0
            guard.current_time = random.uniform(0, guard.patrol_time)
        
        self.secondary_objectives.clear()

        # Reset quit confirmation buttons
        self.reset_yes_btn = Button(WIDTH//2 - 120, HEIGHT//2 + 80, 100, 40, "YES", RED, DARK_GRAY)
        self.reset_no_btn = Button(WIDTH//2 + 20, HEIGHT//2 + 80, 100, 40, "NO", GREEN, DARK_GRAY)

        # Reset menu button text when returning to menu
        self.buttons['menu'].text = "START MISSION"
        self.particle_sys.clear()
        self.toasts.clear()
        self.feedback_messages.clear()

    def reset_all_progress(self):
        """
        Reset all game progress including upgrades and stats.
        """
        self.currency = 0
        self.pending_credits = 0
        self.perks = {
            'cooldown_reduction': 0.0,
            'camera_disable_bonus': 0.0,
        }
        self.unlocked_perks = set()
        if hasattr(self, 'upgrade_purchase_count'):
            self.upgrade_purchase_count = {
                'cooldown_reduction': 0,
                'camera_disable_bonus': 0,
                'detection_resistance': 0
            }
        self.best_objectives = 0
        self.best_time = 0
        self.upgrade_menu_open = False
        self.show_reset_confirmation = False
        if hasattr(self, 'settings_menu') and self.settings_menu:
            self.settings_menu.save_progress()
        self.add_toast("All progress reset", YELLOW, 3.0)

    def handle_events(self):
        """Handle user input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Settings menu gets priority for event handling
            if self.settings_menu.handle_event(event):
                continue
            
            if event.type == pygame.KEYDOWN:
                self._handle_keyboard(event.key)

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                if self.state == "menu":
                    # Handle reset confirmation dialog clicks
                    if self.show_reset_confirmation:
                        if self.reset_yes_btn.is_clicked(pos):
                            self.audio_manager.play_sfx("button_click")
                            self.reset_all_progress()
                        elif self.reset_no_btn.is_clicked(pos):
                            self.audio_manager.play_sfx("button_click")
                            self.show_reset_confirmation = False
                        return

                    # Handle menu button clicks
                    if self.buttons['menu'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.reset_game()
                        video_path = os.path.join(os.path.dirname(__file__), "..", "assets", "videos", "hacking bg.mp4")
                        self.transition_manager.start_transition(
                            "playing",
                            TransitionType.FADE_VIDEO,
                            speed=500,
                            state_change_callback=self._on_state_change,
                            video_path=video_path,
                            video_speed=3
                        )

                    # Handle exit button clicks
                    elif self.buttons['exit'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.running = False

                    # Handle settings button clicks
                    elif self.buttons['settings'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.settings_menu.show()

                    # Handle upgrades button clicks
                    elif self.buttons['upgrades'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        if self.upgrade_menu_open:
                            self.upgrade_menu_open = False
                        else:
                            self.upgrade_menu_open = True

                    # Handle reset button clicks
                    elif self.buttons['reset'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.show_reset_confirmation = True

                    # Handle difficulty button clicks
                    elif self.buttons['difficulty'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        # Cycle through difficulties
                        self.current_difficulty_index = (self.current_difficulty_index + 1) % len(self.difficulty_display_names)
                        difficulty_name = self.difficulty_display_names[self.current_difficulty_index]
                        self.buttons['difficulty'].text = f"Difficulty: {difficulty_name}"
                        
                        # Update internal difficulty key
                        self.difficulty = self.available_difficulties[self.current_difficulty_index]
                        
                        # Apply difficulty settings using consistent params
                        self.scale_params = self.difficulty_params.get(self.difficulty, self.difficulty_params['normal'])

                # Handle reset confirmation dialog clicks
                elif self.state == "playing":
                    if self.show_quit_confirmation:
                        if hasattr(self, 'quit_yes_btn') and self.quit_yes_btn.is_clicked(pos):
                            self.audio_manager.play_sfx("button_click")
                            self.pending_credits = 0
                            self.show_quit_confirmation = False
                            self.show_pause_menu = False
                            self.paused = False
                            self.reset_game()
                            self.state = "menu"
                            return
                        elif hasattr(self, 'quit_no_btn') and self.quit_no_btn.is_clicked(pos):
                            self.audio_manager.play_sfx("button_click")
                            self.show_quit_confirmation = False
                            return
                    # Handle pause menu clicks
                    if self.show_pause_menu:
                        if self.pause_resume_btn.is_clicked(pos):
                            self.audio_manager.play_sfx("button_click")
                            self.show_pause_menu = False
                            self.paused = False
                            return
                        elif self.pause_menu_btn.is_clicked(pos):
                            self.audio_manager.play_sfx("button_click")
                            self.show_quit_confirmation = True
                            return
                    
                    if self.buttons['settings'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.settings_menu.show()
                    elif self.buttons['pause_game'].is_clicked(pos):
                        self.audio_manager.play_sfx("button_click")
                        self.show_pause_menu = True
                        self.paused = True
                    else:
                        self._handle_game_clicks(pos)
                
                # Handle endgame menu clicks
                elif self.state in ["success", "failure"]:
                    if self.buttons['menu'].is_clicked(pos):
                        # Reset button text before transitioning
                        self.buttons['menu'].text = "START MISSION"
                        self.reset_game()
                        self.transition_manager.start_transition(
                            target_state="menu",
                            transition_type=TransitionType.SLIDE_DOWN,
                            speed=600,
                            state_change_callback=self._on_state_change,
                            color=(20, 20, 40)
                        )
                    elif self.buttons['exit'].is_clicked(pos):
                        self.running = False

    def _handle_keyboard(self, key):
        """
        Handle keyboard shortcuts for buttons.
        Args:
            key (int): The pygame key code.
        """
        if self.state == "playing":
            if key == pygame.K_ESCAPE:
                if self.show_pause_menu:
                    if self.show_quit_confirmation:
                        self.show_quit_confirmation = False
                    else:
                        self.show_pause_menu = False
                        self.paused = False
                else:
                    self.show_pause_menu = True
                    self.paused = True
                    self.audio_manager.play_sfx("button_click")
                return
            
            if self.paused:
                return

            action_map = {
                pygame.K_1: 'camera',
                pygame.K_2: 'lights',
                pygame.K_3: 'distract',
            }

            button_key = action_map.get(key)
            if button_key and self.buttons[button_key].active:
                self._handle_game_clicks(self.buttons[button_key].rect.center)
            
            if key == pygame.K_4 and self.buttons['hack'].active:
                self._handle_game_clicks(self.buttons['hack'].rect.center)

        # upgrade shortcuts when upgrade menu open
        if self.upgrade_menu_open:
            if key == pygame.K_1:
                self.purchase_upgrade('cooldown_reduction')
            elif key == pygame.K_2:
                self.purchase_upgrade('camera_disable_bonus')
            elif key == pygame.K_3:
                self.purchase_upgrade('detection_resistance')
            elif key == pygame.K_ESCAPE:
                if self.upgrade_menu_open:
                    self.upgrade_menu_open = False
                elif self.show_reset_confirmation:
                    self.show_reset_confirmation = False
            return

    def _handle_game_clicks(self, pos):
        """
        Handle clicks on game action buttons and secondary objectives.
        Args:
            pos (Tuple[int, int]): The position of the mouse click.
        """
        # Check for secondary objective clicks first
        for so in list(self.secondary_objectives):
            if not so['active']:
                continue
            distance = math.sqrt((pos[0] - so['x'])**2 + (pos[1] - so['y'])**2)
            if distance <= 20:  # Click radius
                self.secondary_objectives.remove(so)
                self.audio_manager.play_sfx("coin_collect")
                # Store credit as pending
                if not hasattr(self, 'pending_credits'):
                    self.pending_credits = 0
                self.pending_credits += so['reward']
                self.add_credit_animation(so['reward'])
                return
            
        if self.buttons['camera'].is_clicked(pos):
            self.buttons['camera'].press()
            self.audio_manager.play_sfx("camera_disable")
            self.camera_disabled = True
            # Apply camera disable bonus from perks
            base_time = 8
            bonus_time = self.perks.get('camera_disable_bonus', 0.0)
            self.camera_disable_time = base_time + bonus_time
            # Apply cooldown reduction from perks
            base_cooldown = 7
            cooldown_reduction = self.perks.get('cooldown_reduction', 0.0)
            self.buttons['camera'].set_cooldown(max(1.0, base_cooldown - cooldown_reduction))
            self.add_toast("Cameras Disabled", BLUE, 2.0)
            self.camera_blink_time = 0.5
            self.camera_blink_active = True
            delta = -15
            self.detection_level = max(0, self.detection_level + delta)
            bx, by = self.buttons['camera'].rect.center
            self.particle_sys.spawn_smoke(bx, by, count=12)
            self.particle_sys.add_detection_popup(delta, bx, by)

        elif self.buttons['lights'].is_clicked(pos):
            self.buttons['lights'].press()
            self.audio_manager.play_sfx("lights_cut")
            self.lights_disabled = True
            self.lights_disable_time = 6
            # Apply cooldown reduction from perks
            base_cooldown = 5
            cooldown_reduction = self.perks.get('cooldown_reduction', 0.0)
            self.buttons['lights'].set_cooldown(max(1.0, base_cooldown - cooldown_reduction))
            self.add_toast("Lights Cut", BLUE, 2.0)
            delta = -10
            self.detection_level = max(0, self.detection_level + delta)
            lx, ly = self.buttons['lights'].rect.center
            self.particle_sys.spawn_smoke(lx, ly, count=8)
            self.particle_sys.add_detection_popup(delta, lx, ly)
        
        elif self.buttons['distract'].is_clicked(pos):
            self.buttons['distract'].press()
            self.audio_manager.play_sfx("distraction")
            # Clear all guard alerts
            for guard in self.guards:
                guard.alert = False
            delta = -20
            self.detection_level = max(0, self.detection_level + delta)
            dx, dy = self.buttons['distract'].rect.center
            self.particle_sys.spawn_smoke(dx, dy, count=14)
            self.particle_sys.add_detection_popup(delta, dx, dy)
            # Apply cooldown reduction from perks
            base_cooldown = 10
            cooldown_reduction = self.perks.get('cooldown_reduction', 0.0)
            self.buttons['distract'].set_cooldown(max(1.0, base_cooldown - cooldown_reduction))
            self.add_toast("Distraction Created", BLUE, 2.0)
        
        elif self.buttons['hack'].is_clicked(pos):
            # Check if hack button is on cooldown
            if self.buttons['hack'].cooldown > 0:
                return
            
            self.buttons['hack'].press()
            self.audio_manager.play_sfx("system_startup")
               
            # Instant hack with risk/reward
            progress_gain = 2
            detection_increase = 15
            base_success = max(0.4, 0.85 - (self.detection_level / 120.0))
            success_chance = base_success
            
            if random.random() <= success_chance:
                self.objective_progress += progress_gain
                self.detection_level = max(0, self.detection_level + (detection_increase * 0.3))
                self.add_toast(f"HACK SUCCESS +{progress_gain}", GREEN, 2.5)
                cooldown_time = 3.0 - self.perks.get('cooldown_reduction', 0.0)
                self.buttons['hack'].set_cooldown(max(1.0, cooldown_time))
                if self.audio_manager:
                    self.audio_manager.play_sfx('hack_success')
            else:
                self.detection_level = min(self.max_detection, self.detection_level + detection_increase)
                self.add_toast(f"HACK FAILED +{detection_increase}%", RED, 2.5)
                cooldown_time = 5.0 - self.perks.get('cooldown_reduction', 0.0)
                self.buttons['hack'].set_cooldown(max(2.0, cooldown_time))
                if self.audio_manager:
                    self.audio_manager.play_sfx('hack_fail')
            
    def update(self, dt):
        """
        Update the game state.
        Args:
            dt (float): Delta time since last update.
        """
        transition_result = self.transition_manager.update(dt)

        if transition_result['active']:
            return
        
        if self.state in ["success", "failure"]:
            self.update_end_screen_animations(dt)

        if self.settings_menu:
            self.settings_menu.update(dt)

        if self.state == "menu":
            if not self.audio_manager.is_music_playing():
                self.audio_manager.play_music("menu_theme", loop=True)
            return
        if self.state != "playing" or self.paused:
            return

        # Update timers
        self.time_remaining -= dt
        self.ui_time += dt
        
        # Optimize secondary objective generation - reduce calls to heavy functions
        if random.random() < 0.02:  # Only check if playing state
            if not hasattr(self, '_obj_counter'):
                self._obj_counter = 0
            self._obj_counter += 1
            sx = random.randint(200, WIDTH - 200)
            sy = random.randint(200, 350)
            obj = {'id': f'so{self._obj_counter}', 'x': sx, 'y': sy, 'reward': random.randint(1,3), 
                   'time_left': random.uniform(15, 30), 'active': True}
            self.secondary_objectives.append(obj)
        
        for so in list(self.secondary_objectives):
            so['time_left'] -= dt
            if so['time_left'] <= 0:
                self.secondary_objectives.remove(so)

        # Update credit animation
        if self.credit_animation_timer > 0:
            self.credit_animation_timer -= dt
            if self.credit_animation_timer <= 0:
                self.credit_animation_amount = 0

        # Smooth interpolation for animated values (cached function)
        interp_factor = min(1.0, dt * 4.0)
        self.animated_time += (self.time_remaining - self.animated_time) * interp_factor
        self.animated_detection += (self.detection_level - self.animated_detection) * interp_factor
        self.animated_objectives += (self.objective_progress - self.animated_objectives) * interp_factor

        # Camera blink animation
        if self.camera_blink_time > 0:
            self.camera_blink_time -= dt
            if self.camera_blink_time <= 0:
                self.camera_blink_active = False

        for key in ['camera', 'lights', 'distract', 'hack']:
            self.buttons[key].update(dt)
                
        if self.camera_disable_time > 0:
            self.camera_disable_time -= dt
            if self.camera_disable_time <= 0:
                self.camera_disabled = False
                self.camera_blink_time = 0.3
                self.camera_blink_active = True
        
        if self.lights_disable_time > 0:
            self.lights_disable_time -= dt
        else:
            self.lights_disabled = False
        
        for guard in self.guards:
            guard.update(dt)
        
        # Base detection increases over time
        base_detection = 2 * dt
        if self.camera_disabled:
            base_detection *= 0.3
        if self.lights_disabled:
            base_detection *= 0.5
        
        self.detection_level += base_detection

        # Guards can spot player in danger zone
        danger_zone_start = 0.4
        danger_zone_end = 0.6
        total_detection_multiplier = (2 if not self.lights_disabled else 1) * (1.5 if not self.camera_disabled else 1)
        base_detection_chance = 0.02 * total_detection_multiplier

        for i, guard in enumerate(self.guards):
            if danger_zone_start < guard.position < danger_zone_end:
                if random.random() < base_detection_chance:
                    guard.alert = True
                    delta = 5
                    self.detection_level += delta
                    gx = 100 + int(guard.position * 800)
                    gy = 150 + (i * 60) + 20
                    self.particle_sys.spawn_sparks(gx, gy, count=6, color=(255,180,80))
                    self.particle_sys.add_detection_popup(+delta, gx, gy)
        
        self.event_timer += dt
        if self.event_timer >= 5:
            self.event_timer = 0
            self.trigger_random_event()
        
        # handle current event effects
        if isinstance(self.current_event, dict):
            dps = self.current_event.get('dps', 0)
            if dps:
                self.detection_level += dps * dt
            self.current_event['time_left'] -= dt
            if self.current_event['time_left'] <= 0:
                self.current_event = None
        
        self.particle_sys.update(dt)
        
        # Cleanup feedback messages
        for m in list(self.feedback_messages):
            m['time'] -= dt
            if m['time'] <= 0:
                self.feedback_messages.remove(m)

        # Check win/loss conditions
        self.detection_level = max(0, min(self.detection_level, self.max_detection))
        if self.objective_progress >= self.objectives_needed:
            # Update best scores
            if self.objective_progress > self.best_objectives:
                self.best_objectives = self.objective_progress
            if self.time_remaining > self.best_time:
                self.best_time = self.time_remaining
            
            # Award pending credits on victory
            if hasattr(self, 'pending_credits') and self.pending_credits > 0:
                self.currency += self.pending_credits
                self.pending_credits = 0
            
            # Auto-save progress
            if hasattr(self, 'settings_menu') and self.settings_menu:
                self.settings_menu.save_progress()
            
            self.end_screen_timer = 0.0
            self.animated_end_objectives = 0
            self.animated_end_detection = 0
            self.animated_end_time = 0
            
            self.state = "success"
            self.particle_sys.clear()

        elif self.detection_level >= self.max_detection or self.time_remaining <= 0:
            # Mission failed and clear pending credits
            self.state = "failure"
            self.particle_sys.clear()
            self.pending_credits = 0

            self.end_screen_timer = 0.0
            self.animated_end_objectives = 0
            self.animated_end_detection = 0
            self.animated_end_time = 0

        # Update toasts
        for toast in list(self.toasts):
            toast['time'] -= dt
            if toast['time'] <= 0:
                self.toasts.remove(toast)
            else:
                alpha_ratio = toast['time'] / toast['duration'] if toast['duration'] > 0 else 1.0
                toast['alpha'] = int(255 * min(1.0, alpha_ratio * 2.0))
    
    def update_end_screen_animations(self, dt):
        """Update the animated values for the end screen."""
        self.end_screen_timer += dt

        progress = min(1.0, self.end_screen_timer / 1.5)
        eased_progress = 1 - pow(1 - progress, 3)
        
        self.animated_end_objectives = int(self.objective_progress * eased_progress)
        self.animated_end_detection = int(self.detection_level * eased_progress)
        self.animated_end_time = int(self.time_remaining * eased_progress)
        
    def trigger_random_event(self):
        """
        Trigger a random security event.
        """
        events = [
            {'text': "Security sweep initiated", 'duration': 6.0, 'instant': random.randint(5, 12), 'dps': 1.0},
            {'text': "Guard shift change", 'duration': 8.0, 'instant': 0, 'dps': 0.5},
            {'text': "System scan detected", 'duration': 5.0, 'instant': random.randint(8, 16), 'dps': 1.5},
            ]
        ev = random.choice(events)
        inst = ev.get('instant', 0)
        if inst:
            ex, ey = WIDTH//2, 200
            self.particle_sys.spawn_sparks(ex, ey, count=18, color=(255,200,140))
            self.particle_sys.add_detection_popup(+inst, ex, ey)
        self.detection_level += inst
        ev['time_left'] = ev['duration']
        self.current_event = ev
        if inst >= 10:
            self.particle_sys.start_shake(9.0, 0.5)
    
    def draw(self):
        """
        Draw the current game state.
        """
        # render everything to a temp canvas so we can blit with screen shake offset
        self.canvas.fill((0,0,0))
        old_screen = self.screen
        self.screen = self.canvas

        if self.bg_scaled_surf:
            self.screen.blit(self.bg_scaled_surf, (0, 0))
        else:
            self.screen.fill(BLACK)

        self.particle_sys.draw_particles(self.screen)

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
            if self.paused:
                self.draw_pause_menu()
                if self.show_quit_confirmation:
                    self.draw_quit_confirmation()
        elif self.state == "success":
            self.draw_end_screen("MISSION SUCCESS", GREEN)
        elif self.state == "failure":
            self.draw_end_screen("MISSION FAILED", RED)

        # Shake offset
        ox, oy = self.particle_sys.get_shake_offset()
        
        self.particle_sys.draw_float_texts(self.screen, self.font)

        # restore screen and blit canvas with offset
        self.screen = old_screen
        self.screen.fill(BLACK)
        self.screen.blit(self.canvas, (ox, oy))

        self.transition_manager.draw(self.screen)

        pygame.display.flip()
    
    def draw_menu(self):
        """Draw the main menu."""
        title = self.get_static_text("menu_title", "Terminal Infiltration", self.title_font, GREEN)
        title_rect = title.get_rect(center=(WIDTH//2, 150))
        self.screen.blit(title, title_rect)

        instructions = [
            "Your agent is infiltrating a secure facility.",
            "Use the terminal to help them avoid detection.",
            "Complete 5 hacks before time runs out.",
            "Don't let the detection reach 100%!"
        ]

        y = 250
        for i, line in enumerate(instructions):
            text = self.get_static_text(f"menu_inst_{i}", line, self.font, WHITE)
            text_rect = text.get_rect(center=(WIDTH//2, y))
            self.screen.blit(text, text_rect)
            y += 40

        self.buttons['menu'].draw(self.screen, self.font)
        self.buttons['exit'].draw(self.screen, self.font)
        self.buttons['settings'].draw(self.screen, self.font)
        self.buttons['upgrades'].draw(self.screen, self.font)
        self.buttons['reset'].draw(self.screen, self.font)
        self.buttons['difficulty'].draw(self.screen, self.font)

        # Draw upgrade menu
        self.draw_upgrade_menu()

        # Draw reset confirmation dialog
        if self.show_reset_confirmation:
            self.draw_reset_confirmation()
        
        # Draw settings menu
        if self.settings_menu:
            self.settings_menu.draw(self.screen, self.font)

    def draw_game(self):
        """Draw the main game UI."""
        # Draw title
        title = self.get_static_text("game_title", "SECURITY TERMINAL", self.title_font, GREEN)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))

        # Draw status bars
        self.draw_status_bars(25, 90, 300, 30, "TIME", self.animated_time, self.mission_time, BLUE, self.icons['clock'])
        self.draw_status_bars(WIDTH - 325, 90, 300, 30, "DETECTION", self.animated_detection, self.max_detection, RED, self.icons['radar'])
        self.draw_mission_progress(WIDTH//2 - 150, 90, 300, 30)
        
        # Draw currency
        if self.credit_animation_timer > 0:
            # Show animated credit gain
            pending = getattr(self, 'pending_credits', 0)
            current_earned = self.currency - self.credit_animation_amount
            base_text = f"Credits: {current_earned}"
            anim_text = f" +{self.credit_animation_amount}"
            final_text = f" ={self.currency + pending}"
            
            base_surf = self.small_font.render(base_text, True, YELLOW)
            anim_surf = self.small_font.render(anim_text, True, GREEN)
            final_surf = self.small_font.render(final_text, True, YELLOW)
            
            self.screen.blit(base_surf, (20, 20))
            self.screen.blit(anim_surf, (20 + base_surf.get_width(), 20))
            self.screen.blit(final_surf, (20 + base_surf.get_width() + anim_surf.get_width(), 20))
        else:
            pending = getattr(self, 'pending_credits', 0)
            total_credits = self.currency + pending
            currency_text = self.small_font.render(f"Credits: {total_credits}", True, YELLOW)
            self.screen.blit(currency_text, (20, 20))
        
        # Draw current difficulty (moved below credits)
        difficulty_text = self.small_font.render(f"Difficulty: {self.difficulty.capitalize()}", True, WHITE)
        self.screen.blit(difficulty_text, (20, 45))

        # Show feedback messages
        for i, msg in enumerate(self.feedback_messages):
            txt = self.font.render(msg['text'], True, msg['color'])
            txt_rect = txt.get_rect(center=(WIDTH//2, 160 + i * 30))
            self.screen.blit(txt, txt_rect)

        # Draw guard monitors
        monitor_y = 150
        for i, guard in enumerate(self.guards):
            guard.draw(self.screen, 100, monitor_y + i * 60, 800, 40)

        # System statuses
        status_y = 150 + (len(self.guards) * 60) + 10
        systems = [
            ("CAMERAS", "OFFLINE" if self.camera_disabled else "ONLINE", 
             GREEN if self.camera_disabled else RED, self.camera_blink_active),
            ("LIGHTS", "OFFLINE" if self.lights_disabled else "ONLINE", GREEN if self.lights_disabled else RED)
        ]

        # Draw system statuses
        for i, sys_data in enumerate(systems):
            if len(sys_data) < 3:
                continue  # Skip malformed system data
            name = sys_data[0]
            status = sys_data[1]
            color = sys_data[2]
            blink = sys_data[3] if len(sys_data) > 3 else False
            if blink and int(self.ui_time * 10) % 2 == 0:
                color = YELLOW
            text = self.get_cached_text(f"{name}: {status}", self.small_font, color)
            self.screen.blit(text, (100 + i * 250, status_y))
        
        # Show current event
        if self.current_event:
            ev_text = self.current_event['text'] if isinstance(self.current_event, dict) else str(self.current_event)
            event_text = self.small_font.render(f"! {ev_text}", True, YELLOW)
            event_y = 150 + (len(self.guards) * 60) + 50
            self.screen.blit(event_text, (WIDTH//2 - event_text.get_width()//2, event_y))

        # Draw action buttons
        for key in ['camera', 'lights', 'distract', 'hack']:
            show_tooltip = self.buttons[key].is_hovered()
            self.buttons[key].draw(self.screen, self.small_font, show_tooltip)
        
        # Draw button hints
        hints = [
            ("[1] Camera", self.buttons['camera'].rect.centerx),
            ("[2] Lights", self.buttons['lights'].rect.centerx),
            ("[3] Distract", self.buttons['distract'].rect.centerx),
            ("[4] Hack", self.buttons['hack'].rect.centerx),
        ]
        hint_y = self.buttons['hack'].rect.bottom + 10
        for hint_text, hint_x in hints:
            hint = self.get_static_text(f"hint_{hint_text}", hint_text, self.small_font, (150, 150, 150))
            hint_rect = hint.get_rect(center=(hint_x, hint_y))
            self.screen.blit(hint, hint_rect)

        esc_hint = self.get_static_text("esc_hint", "[ESC] Pause", self.small_font, (150, 150, 150))
        self.screen.blit(esc_hint, (WIDTH - esc_hint.get_width() - 10, 65))

        # Draw upgrade shop
        self.draw_upgrade_menu()
        
        # Draw secondary objectives
        if not hasattr(self, '_last_pulse_time'):
            self._last_pulse_time = time.time()
        if random.random() < 0.1:
            self._last_pulse_time = time.time()
        current_time = self._last_pulse_time
        for so in self.secondary_objectives:
            if not so['active']:
                continue
            # Make objectives more visible with pulsing effect
            pulse = abs(math.sin(current_time * 3)) * 0.3 + 0.7
            radius = int(20 * pulse)
            # Draw outer glow
            pygame.draw.circle(self.screen, (255, 255, 0, 100), (so['x'], so['y']), radius + 5)
            # Draw main circle
            pygame.draw.circle(self.screen, YELLOW, (so['x'], so['y']), radius)
            # Draw border
            pygame.draw.circle(self.screen, WHITE, (so['x'], so['y']), radius, 2)
            # Draw text
            txt = self.get_cached_text(f"+{so['reward']}", self.font, BLACK)
            self.screen.blit(txt, (so['x'] - txt.get_width()//2, so['y'] - txt.get_height()//2))

        # Draw toasts
        self.draw_toasts()

        # Draw settings and quit buttons during gameplay
        self.buttons['settings'].draw(self.screen, self.font)
        self.buttons['pause_game'].draw(self.screen, self.font)
        
        if self.settings_menu:
            self.settings_menu.draw(self.screen, self.font)

    def draw_status_bars(self, x, y, width, height, label, value, max_value, color, icon=None):
        """Draw a status bar with label, value, and icon."""
        label_text = self.get_static_text(f"bar_label_{label}", label, self.small_font, WHITE)
        self.screen.blit(label_text, (x, y - 25))

        pygame.draw.rect(self.screen, DARK_GRAY, (x, y, width, height))

        if max_value > 0:
            fill_width = int((value / max_value) * width)
            fill_width = max(0, min(fill_width, width))
        
            # pulsing effect for detection bar when high
            draw_color = color
            if label == "DETECTION":
                ratio = value / max_value if max_value > 0 else 0
                if ratio >= 0.6:
                    period = 0.6
                    pulse = 0.5 * (1.0 + math.sin(2 * math.pi * (self.ui_time / period)))
                    amp = 0.45
                    draw_color = tuple(
                        min(255, int(c + (255 - c) * pulse * amp))
                        for c in color
                    )
            elif label == "TIME":
                ratio = value / max_value if max_value > 0 else 0
                if ratio <= 0.3:
                    period = 0.6
                    pulse = 0.5 * (1.0 + math.sin(2 * math.pi * (self.ui_time / period)))
                    amp = 0.45
                    target = (255, 200, 40)
                    draw_color = tuple(
                        min(255, int(c + (t - c) * pulse * amp))
                        for c, t in zip(color, target)
                    )
            pygame.draw.rect(self.screen, draw_color, (x, y, fill_width, height))

        # Border
        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)

        # Icon
        if icon:
            icon_x = x + 5
            icon_y = y + height//2 - icon.get_height()//2
            self.screen.blit(icon, (icon_x, icon_y))

        if label == 'TIME':
            value_text = self.get_cached_text(f"{int(value)}s", self.small_font, WHITE)
        else:
            value_text = self.get_cached_text(f"{int(value)}%", self.small_font, WHITE)

        text_rect = value_text.get_rect(center=(x + width//2, y + height//2))
        self.screen.blit(value_text, text_rect)

    def draw_mission_progress(self, x, y, width, height):
        """Draw the mission progress bar."""
        # Label
        label = self.get_cached_text("MISSION", self.small_font, WHITE)
        self.screen.blit(label, (x, y - 25))

        # Progress
        progress = self.animated_objectives / self.objectives_needed if self.objectives_needed > 0 else 0

        # Background
        pygame.draw.rect(self.screen, DARK_GRAY, (x, y, width, height))

        # Fill
        fill_width = int(progress * width)
        gradient_color = (
            int(255 * (1 - progress) + 0 * progress),
            int(0 * (1 - progress) + 255 * progress),
            0
        )
        pygame.draw.rect(self.screen, gradient_color, (x, y, fill_width, height))

        # Border
        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)

        # Icon
        icon = self.icons['target']
        icon_x = x + 5
        icon_y = y + height//2 - icon.get_height()//2
        self.screen.blit(icon, (icon_x, icon_y))

        # Percentage
        actual_progress = self.objective_progress / self.objectives_needed if self.objectives_needed > 0 else 0
        percentage = round(actual_progress * 100)
        progress_text = self.font.render(f"{percentage}%", True, WHITE)
        text_rect = progress_text.get_rect(center=(x + width//2, y + height//2))
        self.screen.blit(progress_text, text_rect)

    def draw_toasts(self):
        """Draw toast notifications."""
        toast_x = WIDTH // 2
        toast_y = HEIGHT - 100

        for i, toast in enumerate(self.toasts):
            target_y = toast_y - i * 40

            text_surf = self.font.render(toast['text'], True, toast['color'])
            text_surf.set_alpha(toast.get('alpha', 255))

            padding = 10
            bg_rect = pygame.Rect(
                toast_x - text_surf.get_width() // 2 - padding,
                target_y - padding,
                text_surf.get_width() + 2 * padding,
                text_surf.get_height() + 2 * padding
            )

            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 180))
            self.screen.blit(bg_surf, bg_rect.topleft)
            pygame.draw.rect(self.screen, toast['color'], bg_rect, 2, border_radius=5)

            text_rect = text_surf.get_rect(center=(toast_x, target_y + text_surf.get_height() // 2))
            self.screen.blit(text_surf, text_rect)

    def draw_end_screen(self, message, color):
        """Draw the end screen (success or failure)."""
        text = self.title_font.render(message, True, color)
        text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
        self.screen.blit(text, text_rect)

        stats = [
            f"Objectives Completed: {self.animated_end_objectives}/{self.objectives_needed}",
            f"Final Detection: {self.animated_end_detection}%",
            f"Time Remaining: {int(self.animated_end_time)}s"
        ]

        y = HEIGHT//2
        for stat in stats:
            stat_text = self.font.render(stat, True, WHITE)
            stat_rect = stat_text.get_rect(center=(WIDTH//2, y))
            self.screen.blit(stat_text, stat_rect)
            y += 40
        
        self.buttons['menu'].text = "RETURN TO MENU"
        self.buttons['menu'].draw(self.screen, self.font)
        
        self.buttons['exit'].rect.y = self.buttons['menu'].rect.y + 70
        self.buttons['exit'].draw(self.screen, self.font)

    def draw_upgrade_menu(self):
        """Draw the upgrade/perks shop menu."""
        if not self.upgrade_menu_open:
            return
    
        if not hasattr(self, '_base_costs'):
            self._base_costs = {'cooldown_reduction': 5, 'camera_disable_bonus': 8, 'detection_resistance': 12}
            
        # Background overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Shop panel
        panel_width, panel_height = 500, 400
        panel_x = (WIDTH - panel_width) // 2
        panel_y = (HEIGHT - panel_height) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        
        pygame.draw.rect(self.screen, (40, 40, 60), panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, (120, 120, 120), panel_rect, 3, border_radius=10)
        
        # Title
        title = self.title_font.render("UPGRADE SHOP", True, GREEN)
        title_rect = title.get_rect(center=(panel_x + panel_width//2, panel_y + 30))
        self.screen.blit(title, title_rect)
        
        # Currency display
        currency_text = self.font.render(f"Credits: {self.currency}", True, YELLOW)
        self.screen.blit(currency_text, (panel_x + 20, panel_y + 60))
        
        # Upgrade options
        upgrade_y = panel_y + 100

        if not hasattr(self, 'upgrade_purchase_count'):
            self.upgrade_purchase_count = {'cooldown_reduction': 0, 'camera_disable_bonus': 0, 'detection_resistance': 0}
        
        upgrades = [
            {
                'name': 'Faster Cooldowns',
                'description': 'Reduce all cooldowns by 20%',
                'cost': int(self._base_costs['cooldown_reduction'] * (4 ** self.upgrade_purchase_count['cooldown_reduction'])),
                'key': 'cooldown_reduction',
                'current': f"{int(self.perks.get('cooldown_reduction', 0) * 100)}%"
            },
            {
                'name': 'Extended Camera Disable',
                'description': 'Camera disable lasts 3s longer',
                'cost': int(self._base_costs['camera_disable_bonus'] * (4 ** self.upgrade_purchase_count['camera_disable_bonus'])),
                'key': 'camera_disable_bonus',
                'current': f"+{int(self.perks.get('camera_disable_bonus', 0))}s"
            },
            {
                'name': 'Detection Shield',
                'description': 'Reduce detection gain by 15%',
                'cost': int(self._base_costs['detection_resistance'] * (4 ** self.upgrade_purchase_count['detection_resistance'])),
                'key': 'detection_resistance',
                'current': f"{int(self.perks.get('detection_resistance', 0) * 100)}%"
            }
        ]
        
        for i, upgrade in enumerate(upgrades):
            y_pos = upgrade_y + i * 80
            
            upgrade_rect = pygame.Rect(panel_x + 20, y_pos, panel_width - 40, 70)
            color = (0, 80, 0) if self.currency >= upgrade['cost'] else (80, 40, 40)
            pygame.draw.rect(self.screen, color, upgrade_rect, border_radius=5)
            pygame.draw.rect(self.screen, WHITE, upgrade_rect, 2, border_radius=5)
            
            name_text = self.font.render(upgrade['name'], True, WHITE)
            desc_text = self.small_font.render(upgrade['description'], True, (200, 200, 200))
            cost_text = self.small_font.render(f"Cost: {upgrade['cost']} credits", True, YELLOW)
            current_text = self.small_font.render(f"Current: {upgrade['current']}", True, GREEN)
            
            self.screen.blit(name_text, (upgrade_rect.x + 10, upgrade_rect.y + 5))
            self.screen.blit(desc_text, (upgrade_rect.x + 10, upgrade_rect.y + 25))
            self.screen.blit(cost_text, (upgrade_rect.x + 10, upgrade_rect.y + 45))
            self.screen.blit(current_text, (upgrade_rect.x + 200, upgrade_rect.y + 45))
            
            key_text = self.font.render(f"[{i+1}]", True, WHITE)
            self.screen.blit(key_text, (upgrade_rect.right - 40, upgrade_rect.y + 20))
        
        instructions = [
            "Press 1-3 to purchase upgrades",
            "Press ESC or click Upgrades again to close"
        ]
        
        inst_y = panel_y + panel_height - 50
        for instruction in instructions:
            inst_text = self.small_font.render(instruction, True, (180, 180, 180))
            inst_rect = inst_text.get_rect(center=(panel_x + panel_width//2, inst_y))
            self.screen.blit(inst_text, inst_rect)
            inst_y += 20
    
    def draw_reset_confirmation(self):
        """Draw the reset confirmation dialog."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        dialog_width, dialog_height = 500, 300
        dialog_x = (WIDTH - dialog_width) // 2
        dialog_y = (HEIGHT - dialog_height) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)

        pygame.draw.rect(self.screen, (60, 20, 20), dialog_rect, border_radius=10)
        pygame.draw.rect(self.screen, RED, dialog_rect, 3, border_radius=10)

        title = self.title_font.render("! WARNING !", True, RED)
        title_rect = title.get_rect(center=(dialog_x + dialog_width//2, dialog_y + 40))
        self.screen.blit(title, title_rect)

        messages = [
            "This will permanently reset ALL progress:",
            "• All credits and currency",
            "• All purchased upgrades and perks",
            "• All best scores and achievements",
            "",
            "This action CANNOT be undone."
        ]

        y = dialog_y + 80
        for msg in messages:
            text = self.small_font.render(msg, True, WHITE if msg.startswith("•") or msg == "" else YELLOW)
            text_rect = text.get_rect(center=(dialog_x + dialog_width//2, y))
            self.screen.blit(text, text_rect)
            y += 25
        
        self.reset_yes_btn.draw(self.screen, self.font)
        self.reset_no_btn.draw(self.screen, self.font)
    
    def draw_pause_menu(self):
        """Draw the pause menu overlay."""
        if not self.show_pause_menu:
            return

        if not hasattr(self, '_pause_overlay_cached') or self._pause_overlay_cached is None:
            self._create_pause_overlay()
        
        self.screen.blit(self._pause_overlay, (0, 0))

        pause_text = self.title_font.render("PAUSED", True, YELLOW)
        pause_rect = pause_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
        self.screen.blit(pause_text, pause_rect)

        self.pause_resume_btn.draw(self.screen, self.font)
        self.pause_menu_btn.draw(self.screen, self.font)
    
    def _create_pause_overlay(self):
        """Create and cache the pause menu overlay."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        title_size = 40
        for y in range(0, HEIGHT, title_size):
            for x in range(0, WIDTH, title_size):
                if (x // title_size + y // title_size) % 2 == 0:
                    alpha = 120
                else:
                    alpha = 100
                pygame.draw.rect(overlay, (0, 0, 0, alpha), (x, y, title_size, title_size))
        
        fade_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fade_overlay.fill((0, 0, 0, 180))
        overlay.blit(fade_overlay, (0, 0))

        self._pause_overlay = overlay
        self._pause_overlay_cached = True

    def run(self):
        """Run the main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            self.update_background(dt)

            self.handle_events()
            self.update(dt)
            self.draw()
        
        self.transition_manager.clear()
        
        if self.bg_cap:
            try:
                self.bg_cap.release()
            except Exception:
                pass
        
        pygame.quit()
    
if __name__ == "__main__":
    game = StealthGame()
    game.run()

