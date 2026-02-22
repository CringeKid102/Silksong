import pygame
import os
import json
from typing import Dict, Optional

class AudioManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one AudioManager instance exists."""
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the audio manager."""
        # Only initialize once
        if AudioManager._initialized:
            return
        AudioManager._initialized = True
        
        self._audio_available = True
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            self._audio_available = False
            print(f"Warning: Audio disabled ({e})")

        self.audio_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "audio"))

        # Volume settings
        self.master_volume = 0.7
        self.music_volume = 0.5
        self.sfx_volume = 0.8

        # Audio channels
        self.sfx_channels = [pygame.mixer.Channel(i) for i in range(8)] if self._audio_available else []
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
        try:
            os.makedirs(sfx_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating sfx directory: {e}")
            return

        for sound_name, sound_file in sounds.items():
            sound_loaded = False
            for ext in ['.wav', '.ogg', '.mp3']:
                file_path = os.path.join(sfx_dir, f"{sound_file}{ext}")
                try:
                    if os.path.exists(file_path):
                        self.sfx_sounds[sound_name] = pygame.mixer.Sound(file_path)
                        sound_loaded = True
                        break
                except FileNotFoundError:
                    # File doesn't exist, try next extension
                    continue
                except Exception as e:
                    print(f"Error loading sound '{sound_name}' from {file_path}: {e}")
                    continue
            
            if not sound_loaded:
                print(f"Warning: Sound file '{sound_file}' not found in {sfx_dir}")

    def play_sfx(self, sound_name, volume_override=None):
        """Play a sound effect"""
        if not self._audio_available:
            return
        if sound_name not in self.sfx_sounds:
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
        if not self._audio_available:
            return
        music_dir = os.path.join(self.audio_dir, "music")
        try:
            os.makedirs(music_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating music directory: {e}")
            return

        music_loaded = False
        for ext in ['.mp3', '.ogg', '.wav']:
            music_path = os.path.join(music_dir, f"{music_name}{ext}")
            try:
                if os.path.exists(music_path):
                    pygame.mixer.music.load(music_path)
                    if fade_in > 0:
                        pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade_in*1000)
                    else:
                        pygame.mixer.music.play(-1 if loop else 0)
                    pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
                    music_loaded = True
                    return
            except FileNotFoundError:
                # File doesn't exist, try next extension
                continue
            except Exception as e:
                print(f"Error loading music '{music_name}' from {music_path}: {e}")
                continue
        
        if not music_loaded:
            print(f"Warning: Music file '{music_name}' not found in {music_dir}")
    
    def stop_music(self, fade_out: float = 0):
        """Stop background music."""
        if not self._audio_available:
            return
        if fade_out > 0:
            pygame.mixer.music.fadeout(int(fade_out * 1000))
        else:
            pygame.mixer.music.stop()
    
    def set_master_volume(self, volume: float):
        self.master_volume = max(0.0, min(1.0, volume))
        if self._audio_available:
            pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
            self._refresh_sfx_channel_volumes()
        self.save_settings()
    
    def set_music_volume(self, volume: float):
        self.music_volume = max(0.0, min(1.0, volume))
        if self._audio_available:
            pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
        self.save_settings()
    
    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        if self._audio_available:
            self._refresh_sfx_channel_volumes()
        self.save_settings()

    def _refresh_sfx_channel_volumes(self):
        """Apply current master/sfx volume to all mixer channels."""
        channel_volume = self.sfx_volume * self.master_volume
        for channel in self.sfx_channels:
            channel.set_volume(channel_volume)
    
    def get_volumes(self) -> Dict[str, float]:
        return {'master': self.master_volume, 'music': self.music_volume, 'sfx': self.sfx_volume}
    
    def is_music_playing(self) -> bool:
        if not self._audio_available:
            return False
        return pygame.mixer.music.get_busy()