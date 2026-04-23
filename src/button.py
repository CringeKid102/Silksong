import pygame
from typing import Tuple, Optional
from asset_paths import resolve_image_path
from animation import Animation

class Button:
    """Animated menu button with hover and press pointer animations."""

    def __init__(self, x: int, y: int, text: str, color: Tuple[int,int,int], font_path: Optional[str] = None, font_size: int = 32):
        """Create a button with animated pointer indicators."""
        self.x = x
        self.y = y
        self._text = text
        self.color = color
        
        # Load font
        self.font = pygame.font.Font(font_path, font_size)
        
        # Cache rendered text surface and rect
        self._text_surface = None
        self._text_rect = None
        self._cached_rect = None
        self._update_text_cache()
        
        # Interaction state
        self.active = True
        self.press_timer = 0.0
        self.press_duration = 0.12
        self.was_hovering = False  # Track if we were hovering in previous frame

        # Pointer animation
        pointer_sheet = resolve_image_path("pointer.png")
        self.pointer_anim = Animation(pointer_sheet, frame_width=36, frame_height=44)
        self._load_pointer_animations()
        
        # Start with normal state
        self.current_state = "normal"
    
    def _update_text_cache(self):
        """Rebuild the cached text surface and collision rect."""
        self._text_surface = self.font.render(self.text, True, self.color)
        self._text_rect = self._text_surface.get_rect(center=(self.x, self.y))
        # Cache collision rect
        collision_rect = self._text_rect.copy()
        collision_rect.height -= 10
        self._cached_rect = collision_rect
    
    def _load_pointer_animations(self):
        """Set up hover, pressed, and release animations from the spritesheet."""
        # Hover state
        self.pointer_anim.add_animation(
            "hover",
            row=0,
            start_col=0,
            num_frames=10,
            speed=0.01,
            loop=False
        )
        
        # Pressed state
        self.pointer_anim.add_animation(
            "pressed",
            row=1,
            start_col=0,
            num_frames=10,
            speed=0.01,
            loop=False
        )
        
        # Release state
        self.pointer_anim.add_animation(
            "release",
            row=1,
            start_col=0,
            num_frames=10,
            speed=0.01,
            loop=False
        )
    
    def draw(self, screen: pygame.Surface):
        """Draw the button text with animated pointers on both sides."""
        # Get current pointer frame based on state
        if self.current_state == "normal":
            # Normal state
            pointer_frame = self.pointer_anim.extract_frames(0, 0, 1)[0]
        else:
            # All other states (hover, pressed, release)
            pointer_frame = self.pointer_anim.get_current_frame()
        
        # Draw text in the center (use cached surface)
        screen.blit(self._text_surface, self._text_rect)
        
        # Draw left pointer
        left_rect = pointer_frame.get_rect(right=self._text_rect.left - 10, centery=self.y-7)
        screen.blit(pointer_frame, left_rect)
        
        # Draw right pointer
        right_pointer = pygame.transform.flip(pointer_frame, True, False)
        right_rect = right_pointer.get_rect(left=self._text_rect.right + 10, centery=self.y-7)
        screen.blit(right_pointer, right_rect)
    
    def update(self, dt: float):
        """Update hover state and pointer animation."""
        
        # Update pointer animation based on state (use cached rect)
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self._cached_rect.collidepoint(mouse_pos) and self.active
        
        if self.press_timer > 0:
            self.press_timer = max(0.0, self.press_timer - dt)
            new_state = "pressed"
        elif is_hover:
            new_state = "hover"
        else:
            # Determine if we should play release animation or go to normal
            if self.was_hovering:
                new_state = "release"
            else:
                new_state = "normal"
        
        # Change animation if state changed
        if new_state != self.current_state:
            self.current_state = new_state
            if new_state in ("pressed", "release", "hover"):
                # Play animation forward
                self.pointer_anim.set_animation(new_state, reset=True, reverse=False)
            # Normal state has no animation, just static frame
        
        # Update tracking for hover state
        if is_hover and not self.was_hovering:
            self.was_hovering = True
        elif not is_hover and self.was_hovering and self.current_state == "normal":
            self.was_hovering = False
        
        # Update animation
        if self.current_state != "normal":
            self.pointer_anim.update(dt)

    
    @property
    def _rect(self) -> pygame.Rect:
        """Return the cached collision rect."""
        return self._cached_rect

    def is_clicked(self, pos):
        """Return True if the button is active and the position is inside it."""
        return self._cached_rect.collidepoint(pos) and self.active
    
    def is_hovered(self):
        """Return True if the mouse is over the button."""
        mouse_pos = pygame.mouse.get_pos()
        return self._cached_rect.collidepoint(mouse_pos)
    
    def press(self):
        """Start the button press animation."""
        self.press_timer = self.press_duration
    
    def set_cooldown(self, cooldown_time: float):
        """Set the button cooldown duration in seconds."""
        self.cooldown = cooldown_time
        self.max_cooldown = cooldown_time
    
    @property
    def text(self) -> str:
        """Get the button label text."""
        return self._text
    
    @text.setter
    def text(self, value: str):
        """Set the button label text and refresh the cached surface."""
        if self._text != value:
            self._text = value
            self._update_text_cache()