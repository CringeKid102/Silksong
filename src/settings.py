import pygame
import os
import json
from slider import Slider

class SettingsMenu:
    def __init__(self, width, height, audio_manager, button_class):
        self.width = width
        self.height = height
        self.audio_manager = audio_manager
        self.visible = False

        # Panel
        panel_width, panel_height = 400, 300
        panel_x = (width - panel_width) // 2
        panel_y = (height - panel_height) // 2
        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # Sliders
        slider_x = panel_x + 50
        volumes = self.audio_manager.get_volumes()

        self.sliders = {
            'master': Slider(slider_x, panel_y + 80, 300, 20, 0.0, 1.0, 
                             volumes['master'], "Master Volume", self.audio_manager.set_master_volume),
            'music': Slider(slider_x, panel_y + 130, 300, 20, 0.0, 1.0, 
                            volumes['music'], "Music Volume", self.audio_manager.set_music_volume),
            'sfx': Slider(slider_x, panel_y + 180, 300, 20, 0.0, 1.0, 
                          volumes['sfx'], "SFX Volume", self.audio_manager.set_sfx_volume),
        }

        self.close_button = button_class(panel_x + panel_width - 80, panel_y + panel_height - 50,
                                         60, 30, "CLOSE", (100, 100, 100), (150, 150, 150))
    
        # Add save/load buttons
        self.save_button = button_class(panel_x + 20, panel_y + panel_height - 50,
                                       60, 30, "SAVE", (0, 100, 0), (0, 150, 0))
        self.load_button = button_class(panel_x + 90, panel_y + panel_height - 50,
                                       60, 30, "LOAD", (0, 0, 100), (0, 0, 150))
        
        # Save file path
        self.save_path = os.path.join(os.path.dirname(__file__), "game_progress.json")
        
        # Reference to main game (will be set from outside)
        self.game = None
    
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
            
            # Restore game progress
            self.game.currency = save_data.get('currency', 0)
            self.game.perks = save_data.get('perks', {})
            self.game.unlocked_perks = set(save_data.get('unlocked_perks', []))
            self.game.best_objectives = save_data.get('best_objectives', 0)
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
        volumes = self.audio_manager.get_volumes()
        for key, slider in self.sliders.items():
            slider.value = volumes[key]
            slider.update_handle_pos()
    
    def hide(self):
        self.visible = False
    
    def handle_event(self, event):
        if not self.visible:
            return False
        
        for slider in self.sliders.values():
            slider.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.is_clicked(event.pos):
                self.close_button.press()
                self.audio_manager.play_sfx("button_click")
                self.hide()
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.hide()
            return True
        
        return self.visible
    
    def update(self, dt):
        if self.visible:
            mouse_pos = pygame.mouse.get_pos()
            self.close_button.update(dt)
            self.save_button.update(dt)
            self.load_button.update(dt)
        
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
        title_rect = title.get_rect(center=(self.panel_rect.centerx, self.panel_rect.y + 40))
        screen.blit(title, title_rect)

        # Draw sliders
        for slider in self.sliders.values():
            slider.draw(screen, font)

        # Draw close button
        self.close_button.draw(screen, font)
        
        # Draw save/load buttons
        self.save_button.draw(screen, font)
        self.load_button.draw(screen, font)
        
        # Draw progress info if game reference exists
        if self.game:
            info_y = self.panel_rect.y + 220
            currency_text = font.render(f"Currency: {getattr(self.game, 'currency', 0)}", True, (255, 255, 255))
            screen.blit(currency_text, (self.panel_rect.x + 20, info_y))
            
            best_text = font.render(f"Best: {getattr(self.game, 'best_objectives', 0)} objectives", True, (255, 255, 255))
            screen.blit(best_text, (self.panel_rect.x + 180, info_y))