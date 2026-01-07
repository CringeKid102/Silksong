import pygame
import os
import json
from typing import Dict, Optional

class AudioManager:
    def __init__(self):
        """Initialize the audio manager."""
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.audio_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "audio"))

        # Volume settings
        self.master_volume = 0.7
        self.music_volume = 0.5
        self.sfx_volume = 0.8

        # Audio channels
        self.sfx_channels = [pygame.mixer.Channel(i) for i in range(8)]
        self.current_channel = 0
        self.sfx_sounds = {}

        self.settings_file = os.path.join(os.path.dirname(__file__), "game_progress.json")
        self.load_settings()
    
    def load_settings(self):
        """Load audio settings from game progress file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    # Audio settings are nested under 'audio_settings' key
                    audio_settings = data.get("audio_settings", {})
                    self.master_volume = audio_settings.get("master", 0.7)
                    self.music_volume = audio_settings.get("music", 0.5)
                    self.sfx_volume = audio_settings.get("sfx", 0.8)
        except Exception as e:
            print(f"Error loading audio settings: {e}")
        
    def save_settings(self):
        """Save audio settings to game progress file."""
        try:
            # Load existing data if file exists
            existing_data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    existing_data = json.load(f)
            
            # Update only the audio_settings section
            existing_data['audio_settings'] = {
                "master": self.master_volume,
                "music": self.music_volume,
                "sfx": self.sfx_volume
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            with open(self.settings_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
        except Exception as e:
            print(f"Error saving audio settings: {e}")

    def load_sounds(self, sounds):
        """Load sound effects from the audio directory."""
        sfx_dir = os.path.join(self.audio_dir, "sfx")
        os.makedirs(sfx_dir, exist_ok=True)

        for sound_name, sound_file in sounds.items():
            sound_loaded = False
            for ext in ['.wav', '.ogg', '.mp3']:
                file_path = os.path.join(sfx_dir, f"{sound_file}{ext}")
                if os.path.exists(file_path):
                    try:
                        self.sfx_sounds[sound_name] = pygame.mixer.Sound(file_path)
                        # Audio loaded successfully
                        sound_loaded = True
                        break
                    except Exception as e:
                        print(f"Error loading sound {sound_name}: {e}")
                        continue
            if not sound_loaded:
                # Only log once during initialization
                pass

    def play_sfx(self, sound_name, volume_override=None):
        """Play a sound effect"""
        if sound_name not in self.sfx_sounds:
            # Silently fail for missing sounds - don't spam console
            return
        
        channel = None
        for ch in self.sfx_channels:
            if not ch.get_busy():
                channel = ch
                break
        
        if not channel:
            channel = self.sfx_channels[self.current_channel]
            self.current_channel = (self.current_channel + 1) % len(self.sfx_channels)
        
        volume = (volume_override or 1.0) * self.sfx_volume * self.master_volume
        channel.set_volume(volume)
        channel.play(self.sfx_sounds[sound_name])
    
    def play_music(self, music_name, loop=True, fade_in=0):
        """Play background music."""
        music_dir = os.path.join(self.audio_dir, "music")
        os.makedirs(music_dir, exist_ok=True)

        for ext in ['.mp3', '.ogg', '.wav']:
            music_path = os.path.join(music_dir, f"{music_name}{ext}")
            if os.path.exists(music_path):
                try:
                    pygame.mixer.music.load(music_path)
                    if fade_in > 0:
                        pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade_in*1000)
                    else:
                        pygame.mixer.music.play(-1 if loop else 0)
                    pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
                    return
                except Exception as e:
                    print(f"Error loading music {music_name}: {e}")
                    continue
    
    def stop_music(self, fade_out: float = 0):
        """Stop background music."""
        if fade_out > 0:
            pygame.mixer.music.fadeout(int(fade_out * 1000))
        else:
            pygame.mixer.music.stop()
    
    def duck_music(self, duck_volume: float = 0.3):
        """Lower music volume temporarily."""
        pygame.mixer.music.set_volume(duck_volume * self.master_volume)
    
    def unduck_music(self):
        """Restore music volume."""
        pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
    
    def set_master_volume(self, volume: float):
        self.master_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
        self.save_settings()
    
    def set_music_volume(self, volume: float):
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
        self.save_settings()
    
    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        self.save_settings()
    
    def get_volumes(self) -> Dict[str, float]:
        return {'master': self.master_volume, 'music': self.music_volume, 'sfx': self.sfx_volume}
    
    def is_music_playing(self) -> bool:
        return pygame.mixer.music.get_busy()