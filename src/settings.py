import pygame
import os
import json
from slider import Slider

class SettingsMenu:
    def __init__(self, width, height, audio_manager, button_class):
        self.width = width
        self.height = height
        self.audio_manager = audio_manager
        self.button_class = button_class
        self.visible = False
        
        # Menu state
        self.current_menu = "options"  # options, game, audio, video, controller
        
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

        # Initialize menu buttons
        self._init_options_menu()
        self._init_game_menu()
        self._init_audio_menu()
        self._init_video_menu()
        self._init_controller_menu()
        
        # Save file path
        self.save_path = os.path.join(os.path.dirname(__file__), "game_progress.json")
        
        # Reference to main game (will be set from outside)
        self.game = None
        
    def _init_options_menu(self):
        """Initialize the main options menu."""
        button_width, button_height = 150, 40
        start_y = self.panel_y + 80
        spacing = 60
        
        self.options_buttons = {
            'game': self.button_class(self.panel_x + 175, start_y, button_width, button_height,
                                     "GAME", (70, 130, 180), (100, 160, 210)),
            'audio': self.button_class(self.panel_x + 175, start_y + spacing, button_width, button_height,
                                      "AUDIO", (70, 130, 180), (100, 160, 210)),
            'video': self.button_class(self.panel_x + 175, start_y + spacing * 2, button_width, button_height,
                                      "VIDEO", (70, 130, 180), (100, 160, 210)),
            'controller': self.button_class(self.panel_x + 175, start_y + spacing * 3, button_width, button_height,
                                           "CONTROLLER", (70, 130, 180), (100, 160, 210)),
        }
        self.close_button = self.button_class(self.panel_x + self.panel_width - 80, self.panel_y + self.panel_height - 50,
                                             60, 30, "CLOSE", (100, 100, 100), (150, 150, 150))
    
    def _init_game_menu(self):
        """Initialize game settings menu.""" 
        button_width, button_height = 200, 30
        start_y = self.panel_y + 80
        spacing = 50
        
        self.game_buttons = {
            'language': self.button_class(self.panel_x + 150, start_y, button_width, button_height,
                                         "Language: English", (70, 130, 180), (100, 160, 210)),
            'camera_shake': self.button_class(self.panel_x + 150, start_y + spacing, button_width, button_height,
                                             "Camera Shake: ON", (70, 130, 180), (100, 160, 210)),
        }
        self.game_back_button = self.button_class(self.panel_x + 20, self.panel_y + self.panel_height - 50,
                                                 60, 30, "BACK", (100, 100, 100), (150, 150, 150))
    
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
        self.audio_back_button = self.button_class(self.panel_x + 20, self.panel_y + self.panel_height - 50,
                                                  60, 30, "BACK", (100, 100, 100), (150, 150, 150))
    
    def _init_video_menu(self):
        """Initialize video settings menu."""
        slider_x = self.panel_x + 50
        
        self.video_sliders = {
            'brightness': Slider(slider_x, self.panel_y + 100, 350, 20, 0.0, 1.0,
                                 self.settings_data['brightness'], "Brightness", self._set_brightness),
        }
        self.video_back_button = self.button_class(self.panel_x + 20, self.panel_y + self.panel_height - 50,
                                                  60, 30, "BACK", (100, 100, 100), (150, 150, 150))
    
    def _init_controller_menu(self):
        """Initialize controller settings menu."""
        self.controller_back_button = self.button_class(self.panel_x + 20, self.panel_y + self.panel_height - 50,
                                                       60, 30, "BACK", (100, 100, 100), (150, 150, 150))
    
    def _set_brightness(self, value):
        """Set brightness value."""
        self.settings_data['brightness'] = value
    
    def _toggle_camera_shake(self):
        """Toggle camera shake setting."""
        self.settings_data['camera_shake'] = not self.settings_data['camera_shake']
    
    def _toggle_language(self):
        """Toggle language setting."""
        languages = ['english']  # Add more languages as needed
        current_index = languages.index(self.settings_data['language'])
        self.settings_data['language'] = languages[(current_index + 1) % len(languages)]
    
    def save_progress(self):
        """Save game progress including audio settings and game data."""
        if not self.game:
            return False
        
        try:
            # Ensure directory exists
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
                slider.update_handle_pos()
            
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
                slider.update_handle_pos()
            
            return True
        except Exception as e:
            print(f"Load failed: {e}")
            return False
    
    def show(self):
        self.visible = True
        self.current_menu = "options"
        volumes = self.audio_manager.get_volumes()
        for key, slider in self.audio_sliders.items():
            slider.value = volumes[key]
            slider.update_handle_pos()
    
    def hide(self):
        self.visible = False
    
    def handle_event(self, event):
        if not self.visible:
            return False
        
        if self.current_menu == "options":
            return self._handle_options_menu(event)
        elif self.current_menu == "game":
            return self._handle_game_menu(event)
        elif self.current_menu == "audio":
            return self._handle_audio_menu(event)
        elif self.current_menu == "video":
            return self._handle_video_menu(event)
        elif self.current_menu == "controller":
            return self._handle_controller_menu(event)
        
        return False
    
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
                self.current_menu = "game"
                return True
            elif self.options_buttons['audio'].is_clicked(event.pos):
                self.options_buttons['audio'].press()
                self.audio_manager.play_sfx("button_click")
                self.current_menu = "audio"
                return True
            elif self.options_buttons['video'].is_clicked(event.pos):
                self.options_buttons['video'].press()
                self.audio_manager.play_sfx("button_click")
                self.current_menu = "video"
                return True
            elif self.options_buttons['controller'].is_clicked(event.pos):
                self.options_buttons['controller'].press()
                self.audio_manager.play_sfx("button_click")
                self.current_menu = "controller"
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
                self.current_menu = "options"
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
            self.current_menu = "options"
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
                self.current_menu = "options"
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.current_menu = "options"
            return True
        
        return self.visible
    
    def _handle_video_menu(self, event):
        """Handle events for the video menu."""
        self.video_sliders['brightness'].handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.video_back_button.is_clicked(event.pos):
                self.video_back_button.press()
                self.audio_manager.play_sfx("button_click")
                self.current_menu = "options"
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.current_menu = "options"
            return True
        
        return self.visible
    
    def _handle_controller_menu(self, event):
        """Handle events for the controller menu."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.controller_back_button.is_clicked(event.pos):
                self.controller_back_button.press()
                self.audio_manager.play_sfx("button_click")
                self.current_menu = "options"
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.current_menu = "options"
            return True
        
        return self.visible
    
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
            elif self.current_menu == "controller":
                self.controller_back_button.update(dt)
        
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
        title = font.render("SETTINGS", True, (255, 255, 255))
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
        elif self.current_menu == "controller":
            self._draw_controller_menu(screen, font)
    
    def _draw_options_menu(self, screen, font):
        """Draw the options menu."""
        menu_label = font.render("Options", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        for button in self.options_buttons.values():
            button.draw(screen, font)
        
        self.close_button.draw(screen, font)
    
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
            button.draw(screen, font)
        
        self.game_back_button.draw(screen, font)
    
    def _draw_audio_menu(self, screen, font):
        """Draw the audio menu."""
        menu_label = font.render("Audio Settings", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        for slider in self.audio_sliders.values():
            slider.draw(screen, font)
        
        self.audio_back_button.draw(screen, font)
    
    def _draw_video_menu(self, screen, font):
        """Draw the video menu."""
        menu_label = font.render("Video Settings", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        for slider in self.video_sliders.values():
            slider.draw(screen, font)
        
        self.video_back_button.draw(screen, font)
    
    def _draw_controller_menu(self, screen, font):
        """Draw the controller menu."""
        menu_label = font.render("Controller", True, (200, 200, 200))
        screen.blit(menu_label, (self.panel_x + 20, self.panel_y + 50))
        
        # Placeholder text for keyboard functions
        placeholder_text = font.render("[Keyboard Functions Image]", True, (150, 150, 150))
        placeholder_rect = placeholder_text.get_rect(center=(self.panel_rect.centerx, self.panel_y + 150))
        screen.blit(placeholder_text, placeholder_rect)
        
        self.controller_back_button.draw(screen, font)