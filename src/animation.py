import os
import pygame
from typing import Callable, List, Optional, Tuple, Dict

class Animation:
    _sprite_sheet_cache: Dict[str, pygame.Surface] = {}

    def __init__(
            self, 
            sprite_sheet_path: str, 
            frame_width: int, 
            frame_height: int, 
            scale: float = 1.0,
            margin: int = 0,
            spacing: int = 0
        ):
        """Initialize the animation handler with a spritesheet."""
        if not os.path.exists(sprite_sheet_path):
            raise FileNotFoundError(f"Sprite sheet not found: {sprite_sheet_path}")
        self.sprite_sheet_path = os.path.normpath(sprite_sheet_path)
        self.sprite_sheet: Optional[pygame.Surface] = None
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.scale = float(scale)
        self.margin = int(margin)
        self.spacing = int(spacing)

        self.animations: Dict[str, Dict] = {}
        self.current_animation: Optional[str] = None

        # Playback state
        self.elapsed = 0.0
        self.current_frame = 0
        self.playing = True
        self.finished = False
        self.pingpong = False
        self.reverse = False
        
        # Cache for extracted frames to avoid re-blitting repeatedly
        self._frame_cache: Dict[Tuple[int, int, bool, float], pygame.Surface] = {}

    def _get_sprite_sheet(self) -> pygame.Surface:
        cached_sheet = self._sprite_sheet_cache.get(self.sprite_sheet_path)
        if cached_sheet is None:
            cached_sheet = pygame.image.load(self.sprite_sheet_path).convert_alpha()
            self._sprite_sheet_cache[self.sprite_sheet_path] = cached_sheet
        self.sprite_sheet = cached_sheet
        return cached_sheet

    def _extract_frame_surface(self, col: int, row: int, flip_x: bool) -> pygame.Surface:
        """Extract and cache a single frame surface from the spritesheet."""
        key = (col, row, flip_x, self.scale)
        if key in self._frame_cache:
            return self._frame_cache[key]

        sprite_sheet = self.sprite_sheet if self.sprite_sheet is not None else self._get_sprite_sheet()
        
        x = self.margin + col * (self.frame_width + self.spacing)
        y = self.margin + row * (self.frame_height + self.spacing)
        rect = pygame.Rect(x, y, self.frame_width, self.frame_height)
        
        # Validate rectangle is within sprite sheet bounds
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()
        if rect.right > sheet_width or rect.bottom > sheet_height:
            raise ValueError(
                f"Frame at row={row}, col={col} is outside sprite sheet bounds. "
                f"Frame rect: {rect}, Sheet size: {sheet_width}x{sheet_height}. "
                f"Frame size: {self.frame_width}x{self.frame_height}, "
                f"Margin: {self.margin}, Spacing: {self.spacing}"
            )
        
        frame_surf = sprite_sheet.subsurface(rect).copy()
        if self.scale != 1.0:
            new_size = (int(self.frame_width * self.scale), int(self.frame_height * self.scale))
            frame_surf = pygame.transform.smoothscale(frame_surf, new_size)
        if flip_x:
            frame_surf = pygame.transform.flip(frame_surf, True, False)
        self._frame_cache[key] = frame_surf
        return frame_surf

    def extract_frames(self, row: int, start_col: int, num_frames: int, flip_x: bool = False) -> List[pygame.Surface]:
        """Extract a sequence of frames from a row in the spritesheet."""
        frames: List[pygame.Surface] = []
        for i in range(num_frames):
            col = start_col + i
            frames.append(self._extract_frame_surface(col, row, flip_x))
        return frames
    
    def add_animation(
            self, 
            name: str, 
            frames: Optional[List[pygame.Surface] | Callable[[], List[pygame.Surface]]] = None, 
            *,
            row: Optional[int] = None,
            start_col: int = 0,
            num_frames: int = 0,
            flip_x: bool = False,
            speed: float = 0.1,
            durations: Optional[List[float]] = None,
            frame_count: Optional[int] = None,
            loop: bool = True,
            pingpong: bool = False
        ):
        """Register a named animation from frames or spritesheet coordinates."""
        frames_factory = None
        resolved_frames = None

        if frames is None:
            if row is None or num_frames <= 0:
                raise ValueError("Either frames must be provided or row and num_frames must be specified.")
            frame_count = num_frames
            frames_factory = lambda: self.extract_frames(row, start_col, num_frames, flip_x=flip_x)
        elif callable(frames):
            if frame_count is None and durations is None:
                raise ValueError("Callable frame providers require frame_count or durations.")
            frames_factory = frames
        else:
            resolved_frames = frames
            frame_count = len(resolved_frames)

        if frame_count is None:
            frame_count = len(durations) if durations is not None else 0

        if durations is not None and len(durations) != frame_count:
            raise ValueError("Length of durations must match number of frames.")

        self.animations[name] = {
            'frames': resolved_frames,
            'durations': durations,
            'speed': speed,
            'frame_count': frame_count,
            'frames_factory': frames_factory,
            'loop': loop,
            'pingpong': pingpong
        }

    def _ensure_animation_loaded(self, name: str):
        anim = self.animations[name]
        if anim['frames'] is not None:
            return anim

        frames_factory = anim.get('frames_factory')
        if frames_factory is None:
            anim['frames'] = []
        else:
            anim['frames'] = frames_factory()

        if anim['durations'] is None:
            anim['durations'] = [anim['speed']] * len(anim['frames'])

        anim['frame_count'] = len(anim['frames'])
        return anim

    def get_animation_frame_count(self, name: str) -> int:
        anim = self._ensure_animation_loaded(name)
        return len(anim['frames'])
        
    def set_animation(self, name: str, reset: bool = True, reverse: bool = False):
        """Switch to a named animation, optionally resetting playback."""
        if name not in self.animations:
            raise KeyError(f"Animation not found: {name}")
        if name != self.current_animation or reset:
            anim = self._ensure_animation_loaded(name)
            self.current_animation = name
            self.current_frame = 0 if not reverse else len(anim['frames']) - 1
            self.elapsed = 0.0
            self.playing = True
            self.finished = False
            self.reverse = reverse
            self.pingpong = anim.get('pingpong', False)

    def update(self, dt: float):
        """Advance animation playback by dt seconds."""
        if not self.playing or self.current_animation is None or self.finished:
            return

        anim = self._ensure_animation_loaded(self.current_animation)
        durations = anim['durations']
        frame_count = len(durations)

        if frame_count == 0:
            return
        
        # Cache loop and pingpong flags to avoid dict lookups
        loop = anim['loop']
        pingpong = anim['pingpong']
        
        self.elapsed += dt
        # Use while to support large dt values
        while self.elapsed >= durations[self.current_frame]:
            self.elapsed -= durations[self.current_frame]
            if not self.reverse:
                self.current_frame += 1
            else:
                self.current_frame -= 1

            # Handle bounds
            if 0 <= self.current_frame < frame_count:
                continue

            # out of bounds handling
            if pingpong:
                # Reverse direction
                self.reverse = not self.reverse
                if self.reverse:
                    self.current_frame = frame_count - 2 if frame_count > 1 else 0
                else:
                    self.current_frame = 1 if frame_count > 1 else 0
                continue

            if loop:
                # wrap
                if self.current_frame >= frame_count:
                    self.current_frame = 0
                elif self.current_frame < 0:
                    self.current_frame = frame_count - 1
                continue

            # Non-looping animation finished
            if self.current_frame >= frame_count:
                self.current_frame = frame_count - 1
            elif self.current_frame < 0:
                self.current_frame = 0
            self.playing = False
            self.finished = True
            break

    def get_current_frame(self) -> Optional[pygame.Surface]:
        """Return the current frame surface, or None if no animation is set."""
        if self.current_animation is None:
            return None
        anim = self._ensure_animation_loaded(self.current_animation)
        if len(anim['frames']) == 0:
            return None
        idx = max(0, min(self.current_frame, len(anim['frames']) - 1))
        return anim['frames'][idx]
    
    def draw(self, surface: pygame.Surface, x: int, y: int, anchor: str = 'topleft'):
        """Draw the current frame at the given position on the surface."""
        frame = self.get_current_frame()
        if frame is None:
            return

        rect = frame.get_rect()
        if anchor == "center":
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        surface.blit(frame, rect)
    
    def pause(self):
        """Pause the current animation."""
        self.playing = False
    
    def resume(self):
        """Resume the current animation."""
        if not self.finished:
            self.playing = True
    
    def reset(self):
        """Reset the current animation to the first frame."""
        self.current_frame = 0
        self.elapsed = 0.0
        self.finished = False
        self.playing = True
    
    def is_finished(self) -> bool:
        """Return True if the current non-looping animation has finished."""
        return self.finished

    def set_scale(self, scale: float):
        """Set a new scale factor, clearing the frame cache."""
        if scale <= 0:
            raise ValueError("Scale must be a positive number.")
        if scale != self.scale:
            self.scale = float(scale)
            self._frame_cache.clear()  # Clear cache to re-extract frames with new scale