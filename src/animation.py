import os
import pygame
from typing import List, Optional, Tuple, Dict

class Animation:
    def __init__(
            self, 
            sprite_sheet_path: str, 
            frame_width: int, 
            frame_height: int, 
            scale: float = 1.0,
            margin: int = 0,
            spacing: int = 0
        ):
        """
        Initialize the animation handler with a spritesheet.
        Args:
            sprite_sheet_path (str): Path to the spritesheet image
            frame_width (int): Width of each frame in pixels
            frame_height (int): Height of each frame in pixels
            scale (float): Scale factor for the sprites (default: 1.0)
            margin (int): Pixel margin around the sheet (default: 0)
            spacing (int): Pixel spacing between frames (default: 0)
        """
        if not os.path.exists(sprite_sheet_path):
            raise FileNotFoundError(f"Sprite sheet not found: {sprite_sheet_path}")
        self.sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
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

    def _extract_frame_surface(self, col: int, row: int, flip_x: bool) -> pygame.Surface:
        """
        Extract a single frame surface from the spritesheet.
        Args:
            col (int): Column number (0-based index)
            row (int): Row number (0-based index)
            flip_x (bool): Whether to flip the frame horizontally
        Returns:
            pygame.Surface: The extracted frame surface
        """
        key = (col, row, flip_x, self.scale)
        if key in self._frame_cache:
            return self._frame_cache[key]
        
        x = self.margin + col * (self.frame_width + self.spacing)
        y = self.margin + row * (self.frame_height + self.spacing)
        rect = pygame.Rect(x, y, self.frame_width, self.frame_height)
        
        # Validate rectangle is within sprite sheet bounds
        sheet_width = self.sprite_sheet.get_width()
        sheet_height = self.sprite_sheet.get_height()
        if rect.right > sheet_width or rect.bottom > sheet_height:
            raise ValueError(
                f"Frame at row={row}, col={col} is outside sprite sheet bounds. "
                f"Frame rect: {rect}, Sheet size: {sheet_width}x{sheet_height}. "
                f"Frame size: {self.frame_width}x{self.frame_height}, "
                f"Margin: {self.margin}, Spacing: {self.spacing}"
            )
        
        frame_surf = self.sprite_sheet.subsurface(rect).copy()
        if self.scale != 1.0:
            new_size = (int(self.frame_width * self.scale), int(self.frame_height * self.scale))
            frame_surf = pygame.transform.smoothscale(frame_surf, new_size)
        if flip_x:
            frame_surf = pygame.transform.flip(frame_surf, True, False)
        self._frame_cache[key] = frame_surf
        return frame_surf

    def extract_frames(self, row: int, start_col: int, num_frames: int, flip_x: bool = False) -> List[pygame.Surface]:
        """
        Extract frames from a specific row in the spritesheet.
        Args:
            row (int): Row number (0-based index)
            start_col (int): Starting column number (0-based index)
            num_frames (int): Number of frames to extract
            flip_x (bool): Whether to flip frames horizontally
        Returns:
            list: List of pygame.Surface objects representing the frames
        """
        frames: List[pygame.Surface] = []
        for i in range(num_frames):
            col = start_col + i
            frames.append(self._extract_frame_surface(col, row, flip_x))
        return frames
    
    def add_animation(
            self, 
            name: str, 
            frames: Optional[List[pygame.Surface]] = None, 
            *,
            row: Optional[int] = None,
            start_col: int = 0,
            num_frames: int = 0,
            flip_x: bool = False,
            speed: float = 0.1,
            durations: Optional[List[float]] = None,
            loop: bool = True,
            pingpong: bool = False
        ):
        """
        Add an animation to the animation dictionary.
        Args:
            name (str): Name of the animation (e.g., "walk", "attack")
            frames (list): List of frames for the animation
            row (int): Row number in the spritesheet to extract frames from
            start_col (int): Starting column number in the spritesheet
            num_frames (int): Number of frames to extract from the spritesheet
            flip_x (bool): Whether to flip frames horizontally
            speed (float): default seconds per frame (used if durations is None)
            durations (list): Optional list of durations for each frame
            loop (bool): Whether the animation should loop
            pingpong (bool): Whether the animation should pingpong
        """
        if frames is None:
            if row is None or num_frames <= 0:
                raise ValueError("Either frames must be provided or row and num_frames must be specified.")
            frames = self.extract_frames(row, start_col, num_frames, flip_x=flip_x)
        
        if durations is not None and len(durations) != len(frames):
            raise ValueError("Length of durations must match number of frames.")
        
        # Normalize durations list
        if durations is None:
            durations = [speed] * len(frames)

        self.animations[name] = {
            'frames': frames,
            'durations': durations,
            'loop': loop,
            'pingpong': pingpong
        }
        
    def set_animation(self, name: str, reset: bool = True, reverse: bool = False):
        """
        Set the current animation if it's different from the current one.
        Args:
            name (str): Name of the animation to set
            reset (bool): Whether to reset to the first frame
            reverse (bool): Whether to play the animation in reverse
        """
        if name not in self.animations:
            raise KeyError(f"Animation not found: {name}")
        if name != self.current_animation or reset:
            self.current_animation = name
            self.current_frame = 0 if not reverse else len(self.animations[name]['frames']) - 1
            self.elapsed = 0.0
            self.playing = True
            self.finished = False
            self.reverse = reverse
            self.pingpong = self.animations[name].get('pingpong', False)

    def update(self, dt: float):
        """
        Advance animation by dt seconds. Call from your main loop with delta-time.
        Args:
            dt (float): Delta time since last update.
        """
        if not self.playing or self.current_animation is None or self.finished:
            return

        anim = self.animations[self.current_animation]
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
        """
        Return the current frame surface (or None if no animation set).
        """
        if self.current_animation is None:
            return None
        anim = self.animations[self.current_animation]
        if len(anim['frames']) == 0:
            return None
        idx = max(0, min(self.current_frame, len(anim['frames']) - 1))
        return anim['frames'][idx]
    
    def draw(self, surface: pygame.Surface, x: int, y: int, anchor: str = 'topleft'):
        """
        Draw the current frame at the specified position on the given surface.
        Args:
            surface (pygame.Surface): Surface to draw on
            x (int): X coordinate
            y (int): Y coordinate
            anchor (str): Anchor point for positioning ('topleft', 'center', etc.)
        """
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
        """
        Pause the current animation.
        """
        self.playing = False
    
    def resume(self):
        """
        Resume the current animation.
        """
        if not self.finished:
            self.playing = True
    
    def reset(self):
        """
        Reset the current animation to the first frame.
        """
        self.current_frame = 0
        self.elapsed = 0.0
        self.finished = False
        self.playing = True
    
    def is_finished(self) -> bool:
        """
        Return True if the current animation has finished playing (non-looping).
        """
        return self.finished

    def set_scale(self, scale: float):
        """
        Set a new scale for the animation frames.
        Args:
            scale (float): New scale factor
        """
        if scale <= 0:
            raise ValueError("Scale must be a positive number.")
        if scale != self.scale:
            self.scale = float(scale)
            self._frame_cache.clear()  # Clear cache to re-extract frames with new scale