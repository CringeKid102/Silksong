import pygame
import os
import json
import config
from slider import Slider
from transition import TransitionType

class SettingsMenu:
    """
    Settings menu for the game.
    Attributes:
        width (int): Width of the game screen.
        height (int): Height of the game screen.
        audio_manager (AudioManager): Reference to the game's audio manager.
        button_class (class): Reference to the Button class for creating buttons.
    """

    def __init__(self, width, height, audio_manager, button_class):
        """
        Initialize the settings menu.
        Args:
            width (int): Width of the game screen.
            height (int): Height of the game screen.
            audio_manager (AudioManager): Reference to the game's audio manager.
            button_class (class): Reference to the Button class for creating buttons.
        """
        self.width = width
        self.height = height
        self.audio_manager = audio_manager
        self.button_class = button_class
        self.visible = False
        
        # Menu state
        self.current_menu = "options"  # options, game, audio, video, keyboard
        
        # Load fonts
        self.font_path = os.path.join(os.path.dirname(__file__), "../assets/fonts/Perpetua Regular.otf")
        self.title_font_path = os.path.join(os.path.dirname(__file__), "../assets/fonts/TrajanPro-Regular.ttf")
        self.font = pygame.font.Font(self.font_path, int(32 * config.scale_y))
        self.title_font = pygame.font.Font(self.title_font_path, int(48 * config.scale_y))

        # Panel
        panel_width, panel_height = 500, 400
        panel_x = (width - panel_width) // 2
        panel_y = (height - panel_height) // 2
        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        self.panel_x = panel_x
        self.panel_y = panel_y
        self.panel_width = panel_width
        self.panel_height = panel_height
        
        # Settings data
        self.settings_data = {
            'language': 'english',
            'camera_shake': True,
            'brightness': 0.8
        }

        # Initialization of menus
        self._init_options_menu()
        self._init_game_menu()
        self._init_audio_menu()
        self._init_video_menu()
        self._init_keyboard_menu()
        
        # Save file path
        self.save_path = os.path.join(os.path.dirname(__file__), "log.json")
        
        # Reference to the main game object
        self.game = None
        
        # Reference to transition manager (will be set by main game)
        self.transition_manager = None
        
        # Track if we're transitioning between menus
        self.pending_menu = None
    
    # TODO: Create one parent function to initialize menus (copilot will do this)

    def _init_options_menu(self):
        """Initialize the main options menu."""
        start_y = self.panel_y + 80
        spacing = 60
        button_font_size = 24
        
        self.options_buttons = {
            'game': self.button_class(self.panel_x + 250, start_y + 25, "Game", config.white, config.title_font_path, button_font_size),
            'audio': self.button_class(self.panel_x + 250, start_y + spacing + 25, "Audio", config.white, config.title_font_path, button_font_size),
            'video': self.button_class(self.panel_x + 250, start_y + spacing * 2 + 25, "Video", config.white, config.title_font_path, button_font_size),
            'keyboard': self.button_class(self.panel_x + 250, start_y + spacing * 3 + 25, "Keyboard", config.white, config.title_font_path, button_font_size),
        }
        self.close_button = self.button_class(self.panel_x + self.panel_width - 80, self.panel_y + self.panel_height - 50,
                                             "Back", config.white, config.title_font_path, 20)

    def _init_game_menu(self):
        """Initialize game settings menu.""" 
        start_y = self.panel_y + 80
        spacing = 30
        button_font_size = 20
        
        self.game_buttons = {
            'language': self.button_class(self.panel_x + 250, start_y + 25, "Language: English", config.white, config.title_font_path, button_font_size),
            'camera_shake': self.button_class(self.panel_x + 250, start_y + spacing + 25, "Camera Shake: ON", config.white, config.title_font_path, button_font_size),
        }
        self.game_back_button = self.button_class(self.panel_x + 75, self.panel_y + self.panel_height - 50,
                                                 "Back", config.white, config.title_font_path, 20)
    
    def _init_audio_menu(self):
        """Initialize audio settings menu."""
        slider_x = self.panel_x + 50
        volumes = self.audio_manager.get_volumes()
        
        self.audio_sliders = {
            'master': Slider(slider_x, self.panel_y + 80, 350, 20, 0.0, 1.0,
                            volumes['master'], "Master Volume", self.audio_manager.set_master_volume),
            'sfx': Slider(slider_x, self.panel_y + 140, 350, 20, 0.0, 1.0,
                           volumes['sfx'], "Sound Volume", self.audio_manager.set_sfx_volume),
            'music': Slider(slider_x, self.panel_y + 200, 350, 20, 0.0, 1.0,
                           volumes['music'], "Music Volume", self.audio_manager.set_music_volume),
        }
        self.audio_back_button = self.button_class(self.panel_x + 75, self.panel_y + self.panel_height - 50,
                                                  "Back", config.white, config.title_font_path, 20)
    
    def _init_video_menu(self):
        """Initialize video settings menu."""
        slider_x = self.panel_x + 50
        
        self.video_sliders = {
            'brightness': Slider(slider_x, self.panel_y + 100, 350, 20, 0.0, 1.0,
                                 self.settings_data['brightness'], "Brightness", self._set_brightness),
        }
        self.video_back_button = self.button_class(self.panel_x + 75, self.panel_y + self.panel_height - 50,
                                                  "Back", config.white, config.title_font_path, 20)
    
    def _init_keyboard_menu(self):
        """Initialize keyboard settings menu."""
        self.keyboard_back_button = self.button_class(self.panel_x + 75, self.panel_y + self.panel_height - 50,
                                                       "Back", config.white, config.title_font_path, 20)
    
    def _set_brightness(self, value):
        """Set brightness value."""
        self.settings_data['brightness'] = value
    
    def _toggle_camera_shake(self):
        """Toggle camera shake setting."""
        self.settings_data['camera_shake'] = not self.settings_data['camera_shake']
    
    def _toggle_language(self):
        """Toggle language setting."""
        languages = ['english', 'french', 'spanish']  # Add more languages as needed
        current_index = languages.index(self.settings_data['language'])
        self.settings_data['language'] = languages[(current_index + 1) % len(languages)]
    
    def save_progress(self):
        """Save game progress including audio settings and game data."""
        if not self.game:
            return False
        
        try:
            # Make sure directory exists
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            
            # Gather all data to save
            save_data = {
                'audio_settings': self.audio_manager.get_volumes(),
                'game_settings': self.settings_data,
                'currency': getattr(self.game, 'currency', 0),
                'perks': getattr(self.game, 'perks', {}),
                'unlocked_perks': list(getattr(self.game, 'unlocked_perks', set())),
                'best_objectives': getattr(self.game, 'best_objectives', 0),
                'best_time': getattr(self.game, 'best_time', 0),
                'difficulty': getattr(self.game, 'difficulty', 'normal')
            }
            
            with open(self.save_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Save failed: {e}")
            return False
    
    def load_progress(self):
        """Load game progress and apply audio settings and game data."""
        if not self.game:
            return False
            
        try:
            if not os.path.exists(self.save_path):
                return False
                
            with open(self.save_path, 'r') as f:
                save_data = json.load(f)
            
            # Restore audio settings
            audio_settings = save_data.get('audio_settings', {})
            if 'master' in audio_settings:
                self.audio_manager.set_master_volume(audio_settings['master'])
            if 'music' in audio_settings:
                self.audio_manager.set_music_volume(audio_settings['music'])
            if 'sfx' in audio_settings:
                self.audio_manager.set_sfx_volume(audio_settings['sfx'])
            
            # Restore game settings
            game_settings = save_data.get('game_settings', {})
            self.settings_data.update(game_settings)
            
            # Restore game progress
            self.game.currency = save_data.get('currency', 0)
            self.game.perks = save_data.get('perks', {})
            self.game.unlocked_perks = set(save_data.get('unlocked_perks', []))
            self.game.best_objectives = save_data.get('best_objectives', 0)
            self.game.best_time = save_data.get('best_time', 0)
            self.game.difficulty = save_data.get('difficulty', 'normal')
            
            # Update slider positions to reflect loaded audio settings
            volumes = self.audio_manager.get_volumes()
            for key, slider in self.audio_sliders.items():
                slider.value = volumes[key]
                slider.update()
            
            return True
        except Exception as e:
            print(f"Load failed: {e}")
            return False
            self.game.best_time = save_data.get('best_time', 0)
            self.game.difficulty = save_data.get('difficulty', 'normal')
            
            # Update slider positions to reflect loaded audio settings
            volumes = self.audio_manager.get_volumes()
            for key, slider in self.sliders.items():
                slider.value = volumes[key]
                slider.update()
            
            return True
        except Exception as e:
            print(f"Load failed: {e}")
            return False
    
    def show(self):
        self.visible = True
        self.current_menu = "options"
        self.pending_menu = None
        volumes = self.audio_manager.get_volumes()
        for key, slider in self.audio_sliders.items():
            slider.value = volumes[key]
            slider.update()
    
    def hide(self):
        self.visible = False
    
    def handle_event(self, event):
        if not self.visible:
            return False
        
        # Skip input handling during transitions
        if self.transition_manager and self.transition_manager.active:
            return True  # Return True to consume the event
        
        if self.current_menu == "options":
            return self._handle_options_menu(event)
        elif self.current_menu == "game":
            return self._handle_game_menu(event)
        elif self.current_menu == "audio":
            return self._handle_audio_menu(event)
        elif self.current_menu == "video":
            return self._handle_video_menu(event)
        elif self.current_menu == "keyboard":
            return self._handle_keyboard_menu(event)
        
        return False
    
    # TODO: Create one parent function to handle menu events (copilot will do this)

    def _handle_options_menu(self, event):
        """Handle events for the options menu."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.is_clicked(event.pos):
                self.close_button.press()
                self.audio_manager.play_sfx("button_click")
                self.hide()
                return True
            elif self.options_buttons['game'].is_clicked(event.pos):
                self.options_buttons['game'].press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("game")
                return True
            elif self.options_buttons['audio'].is_clicked(event.pos):
                self.options_buttons['audio'].press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("audio")
                return True
            elif self.options_buttons['video'].is_clicked(event.pos):
                self.options_buttons['video'].press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("video")
                return True
            elif self.options_buttons['keyboard'].is_clicked(event.pos):
                self.options_buttons['keyboard'].press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("keyboard")
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.hide()
            return True
        
        return self.visible
    
    def _handle_game_menu(self, event):
        """Handle events for the game menu."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.game_back_button.is_clicked(event.pos):
                self.game_back_button.press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("options")
                return True
            elif self.game_buttons['camera_shake'].is_clicked(event.pos):
                self.game_buttons['camera_shake'].press()
                self.audio_manager.play_sfx("button_click")
                self._toggle_camera_shake()
                return True
            elif self.game_buttons['language'].is_clicked(event.pos):
                self.game_buttons['language'].press()
                self.audio_manager.play_sfx("button_click")
                self._toggle_language()
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.change_menu("options")
            return True
        
        return self.visible
    
    def _handle_audio_menu(self, event):
        """Handle events for the audio menu."""
        for slider in self.audio_sliders.values():
            slider.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.audio_back_button.is_clicked(event.pos):
                self.audio_back_button.press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("options")
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.change_menu("options")
            return True
        
        return self.visible
    
    def _handle_video_menu(self, event):
        """Handle events for the video menu."""
        self.video_sliders['brightness'].handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.video_back_button.is_clicked(event.pos):
                self.video_back_button.press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("options")
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.change_menu("options")
            return True
        
        return self.visible
    
    def _handle_keyboard_menu(self, event):
        """Handle events for the keyboard menu."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.keyboard_back_button.is_clicked(event.pos):
                self.keyboard_back_button.press()
                self.audio_manager.play_sfx("button_click")
                self.change_menu("options")
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.change_menu("options")
            return True
        
        return self.visible
    
    def change_menu(self, new_menu):
        """Change menu with black fade transition."""
        if self.transition_manager and self.transition_manager.active:
            return  # Don't start new transition if one is active
            
        def on_menu_change(target_state):
            self.current_menu = target_state
        
        if self.transition_manager:
            self.transition_manager.start_transition(
                target_state=new_menu,
                transition_type=TransitionType.FADE_COLOR,
                speed=3.0,
                state_change_callback=on_menu_change,
                color=(0, 0, 0)
            )
        else:
            # Fallback if no transition manager
            self.current_menu = new_menu
    
    def update(self, dt):
        if self.visible:
            mouse_pos = pygame.mouse.get_pos()
            self.close_button.update(dt)
            
            if self.current_menu == "options":
                for button in self.options_buttons.values():
                    button.update(dt)
            elif self.current_menu == "game":
                for button in self.game_buttons.values():
                    button.update(dt)
                self.game_back_button.update(dt)
            elif self.current_menu == "audio":
                for slider in self.audio_sliders.values():
                    slider.update()
                self.audio_back_button.update(dt)
            elif self.current_menu == "video":
                for slider in self.video_sliders.values():
                    slider.update()
                self.video_back_button.update(dt)
            elif self.current_menu == "keyboard":
                self.keyboard_back_button.update(dt)
        
    def draw(self, screen, font):
        if not self.visible:
            return
        
        # Background
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Draw panel
        pygame.draw.rect(screen, (30, 30, 30), self.panel_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 100), self.panel_rect, 2, border_radius=10)

        # Draw title
        title = font.render("Options", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.panel_rect.centerx, self.panel_rect.y + 30))
        screen.blit(title, title_rect)

        if self.current_menu == "options":
            self._draw_options_menu(screen, font)
        elif self.current_menu == "game":
            self._draw_game_menu(screen, font)
        elif self.current_menu == "audio":
            self._draw_audio_menu(screen, font)
        elif self.current_menu == "video":
            self._draw_video_menu(screen, font)
        elif self.current_menu == "keyboard":
            self._draw_keyboard_menu(screen, font)

# TODO: Create one parent function to draw menus (copilot will do this)

    def _draw_options_menu(self, screen, font):
        """Draw the options menu."""
        menu_label = font.render("Options", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        for button in self.options_buttons.values():
            button.draw(screen)
        
        self.close_button.draw(screen)
    
    def _draw_game_menu(self, screen, font):
        """Draw the game menu."""
        menu_label = font.render("Game Settings", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        # Update button text based on current settings
        shake_text = "Camera Shake: ON" if self.settings_data['camera_shake'] else "Camera Shake: OFF"
        self.game_buttons['camera_shake'].text = shake_text
        
        language_text = f"Language: {self.settings_data['language'].capitalize()}"
        self.game_buttons['language'].text = language_text
        
        for button in self.game_buttons.values():
            button.draw(screen)
        
        self.game_back_button.draw(screen)
    
    def _draw_audio_menu(self, screen, font):
        """Draw the audio menu."""
        menu_label = font.render("Audio Settings", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 30))
        
        for slider in self.audio_sliders.values():
            slider.draw(screen, font)
        
        self.audio_back_button.draw(screen)
    
    def _draw_video_menu(self, screen, font):
        """Draw the video menu."""
        menu_label = font.render("Video Settings", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        for slider in self.video_sliders.values():
            slider.draw(screen, font)
        
        self.video_back_button.draw(screen)
    
    def _draw_keyboard_menu(self, screen, font):
        """Draw the keyboard menu."""
        menu_label = font.render("Keyboard Settings", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        # Placeholder text for keyboard functions
        placeholder_text = font.render("[Keyboard Functions Image]", True, config.white)
        placeholder_rect = placeholder_text.get_rect(center=(self.panel_rect.centerx, self.panel_y + 150))
        screen.blit(placeholder_text, placeholder_rect)
        
        self.keyboard_back_button.draw(screen)