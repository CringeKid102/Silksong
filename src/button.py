import pygame
import os
from typing import Tuple, Optional
from animation import Animation

class Button:
    def __init__(self, x: int, y: int, text: str, color: Tuple[int,int,int], font_path: Optional[str] = None, font_size: int = 32):
        """
        Initialize a button with pointer animations.
        Args:
            x (int): X position of the button center.
            y (int): Y position of the button center.
            text (str): Text to display on the button.
            color (Tuple[int,int,int]): Color of the text.
            font_path (Optional[str]): Path to custom font file. If None, uses default system font.
            font_size (int): Size of the font (default: 32).
            pointer_sheet (str): Path to the pointer spritesheet (42x48, 10 sprites).
        """
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
        pointer_sheet = os.path.join(os.path.dirname(__file__), "../assets/images/pointer.png")
        self.pointer_anim = Animation(pointer_sheet, frame_width=36, frame_height=44)
        self._load_pointer_animations()
        
        # Start with normal state
        self.current_state = "normal"
    
    def _update_text_cache(self):
        """Update cached text surface and rect."""
        self._text_surface = self.font.render(self.text, True, self.color)
        self._text_rect = self._text_surface.get_rect(center=(self.x, self.y))
        # Cache collision rect
        collision_rect = self._text_rect.copy()
        collision_rect.height -= 10
        self._cached_rect = collision_rect
    
    def _load_pointer_animations(self):
        """Load pointer animations from the spritesheet."""
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
        """
        Draw the button with static text and animated pointers on both sides.
        Args:
            screen (pygame.Surface): The surface to draw on.
        """
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
        """
        Update the button's state and pointer animation.
        Args:
            dt (float): Delta time since last update.
        """
        
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
        """Get the button's collision rect from cache."""
        return self._cached_rect

    def is_clicked(self, pos):
        """
        Check if the button is currently clicked.
        Args:
            pos (Tuple[int,int]): Position to check.
        Returns:
            bool: True if clicked, False otherwise.
        """
        return self._cached_rect.collidepoint(pos) and self.active
    
    def is_hovered(self):
        """
        Check if the button is currently hovered.
        Returns:
            bool: True if hovered, False otherwise.
        """
        mouse_pos = pygame.mouse.get_pos()
        return self._cached_rect.collidepoint(mouse_pos)
    
    def press(self):
        """Trigger the button press animation."""
        self.press_timer = self.press_duration
    
    def set_cooldown(self, cooldown_time: float):
        """
        Set the button's cooldown.
        Args:
            cooldown_time (float): Cooldown time in seconds.
        """
        self.cooldown = cooldown_time
        self.max_cooldown = cooldown_time
    
    @property
    def text(self) -> str:
        """Get the button text."""
        return self._text
    
    @text.setter
    def text(self, value: str):
        """Set the button text and update cache."""
        if self._text != value:
            self._text = value
            self._update_text_cache()