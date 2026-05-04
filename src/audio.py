import pygame
import os
import json
import random
from typing import Dict, List, Optional

from runtime_paths import assets_path, user_data_file

class AudioManager:
    """Singleton audio manager for music playback, sound effects, and volume control."""

    _instance = None
    _initialized = False

    def stop_all_sfx(self):
        """Immediately stop all SFX channels (not music or atmosphere)."""
        if not self._audio_available:
            return
        for ch in self.sfx_channels:
            ch.stop()
    
    def __new__(cls):
        """Singleton pattern so only one AudioManager ever exists."""
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Set up the mixer, channels, and load saved volume settings."""
        # Only initialize once
        if AudioManager._initialized:
            return
        AudioManager._initialized = True
        
        self._audio_available = True
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(32)
        except Exception as e:
            self._audio_available = False
            print(f"Warning: Audio disabled ({e})")

        self.audio_dir = os.path.normpath(assets_path("audio"))

        # Volume settings
        self.master_volume = 0.7
        self.music_volume = 0.5
        self.sfx_volume = 0.8

        # Audio channels (0-29 for sfx, 30 for atmosphere)
        self.sfx_channels = [pygame.mixer.Channel(i) for i in range(30)] if self._audio_available else []
        self._atmos_channel = pygame.mixer.Channel(30) if self._audio_available else None
        self.current_channel = 0
        self.sfx_sounds = {}
        self._current_music_name = None

        self.settings_file = user_data_file("game_progress.json")
        self.load_settings()
    
    def load_settings(self):
        """Load volume settings from the game progress file."""
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
        """Persist volume settings to the game progress file."""
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
        """
        Load sound effects from the audio directory by name.
        Args:
            sounds (dict): Mapping of sound key to filename (without extension).
        """
        sfx_dir = self.audio_dir
        if not os.path.exists(sfx_dir):
            print(f"Warning: Audio directory not found: {sfx_dir}")
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
        """
        Play a loaded sound effect on the next available channel.
        Args:
            sound_name (str): Key of the loaded sound to play.
            volume_override (float | None): Optional 0–1 override; multiplied with sfx and master volume.
        """
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

    def stop_sfx(self, sound_name):
        """Stop all channels currently playing the named sound effect."""
        if not self._audio_available:
            return
        sound = self.sfx_sounds.get(sound_name)
        if sound:
            sound.stop()

    def play_music(self, music_name, loop=True, fade_in=0):
        """
        Play background music from the audio directory.
        Args:
            music_name (str): Filename without extension to search for.
            loop (bool): Whether the music should loop.
            fade_in (float): Fade-in duration in seconds (0 = instant).
        """
        if not self._audio_available:
            return
        if music_name == self._current_music_name and self.is_music_playing():
            return
        self._current_music_name = music_name
        music_dir = self.audio_dir

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
        """
        Stop background music, optionally fading out first.
        Args:
            fade_out (float): Fade-out duration in seconds (0 = instant).
        """
        if not self._audio_available:
            return
        self._current_music_name = None
        if fade_out > 0:
            pygame.mixer.music.fadeout(int(fade_out * 1000))
        else:
            pygame.mixer.music.stop()

    def play_atmosphere(self, sound_name, volume_override=None):
        """
        Play a looping atmosphere sound on the dedicated atmosphere channel.
        Args:
            sound_name (str): Key of the loaded sound to loop.
            volume_override (float | None): Optional base volume (default 0.6); multiplied with sfx and master.
        """
        if not self._audio_available or self._atmos_channel is None:
            return
        if sound_name not in self.sfx_sounds:
            return
        volume = (volume_override if volume_override is not None else 0.6) * self.sfx_volume * self.master_volume
        self._atmos_channel.set_volume(volume)
        self._atmos_channel.play(self.sfx_sounds[sound_name], loops=-1)

    def stop_atmosphere(self):
        """Stop the looping atmosphere channel."""
        if not self._audio_available or self._atmos_channel is None:
            return
        self._atmos_channel.stop()

    def play_sfx_random(self, sound_names: List[str], volume_override=None):
        """
        Play a random sound from the provided list of sound-name keys.
        Args:
            sound_names (List[str]): Pool of sound keys to choose from.
            volume_override (float | None): Optional volume override passed to play_sfx.
        """
        available = [name for name in sound_names if name in self.sfx_sounds]
        if not available:
            return
        self.play_sfx(random.choice(available), volume_override=volume_override)
    
    def set_master_volume(self, volume: float):
        """
        Set the master volume, clamped to [0, 1], and save settings.
        Args:
            volume (float): New master volume (0.0–1.0).
        """
        self.master_volume = max(0.0, min(1.0, volume))
        if self._audio_available:
            pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
            self._refresh_sfx_channel_volumes()
        self.save_settings()
    
    def set_music_volume(self, volume: float):
        """
        Set the music volume, clamped to [0, 1], and save settings.
        Args:
            volume (float): New music volume (0.0–1.0).
        """
        self.music_volume = max(0.0, min(1.0, volume))
        if self._audio_available:
            pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
        self.save_settings()
    
    def set_sfx_volume(self, volume: float):
        """
        Set the sound-effects volume, clamped to [0, 1], and save settings.
        Args:
            volume (float): New sfx volume (0.0–1.0).
        """
        self.sfx_volume = max(0.0, min(1.0, volume))
        if self._audio_available:
            self._refresh_sfx_channel_volumes()
        self.save_settings()

    def _refresh_sfx_channel_volumes(self):
        """Apply current master and sfx volume to all mixer channels."""
        channel_volume = self.sfx_volume * self.master_volume
        for channel in self.sfx_channels:
            channel.set_volume(channel_volume)
        if self._atmos_channel is not None:
            self._atmos_channel.set_volume(self.sfx_volume * self.master_volume * 0.6)
    
    def get_volumes(self) -> Dict[str, float]:
        """Return a dict with current master, music, and sfx volume levels."""
        return {'master': self.master_volume, 'music': self.music_volume, 'sfx': self.sfx_volume}
    
    def is_music_playing(self) -> bool:
        """
        Return True if background music is currently playing.
        Returns:
            bool: True when mixer music is active.
        """
        if not self._audio_available:
            return False
        return pygame.mixer.music.get_busy()