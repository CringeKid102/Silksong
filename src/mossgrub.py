import pygame
import os
from audio import AudioManager

class MossGrub:
    """Type 1 Enemy movement"""
    
    def __init__(self, x, y, screen_width, screen_height):
        """Initialize MossGrub enemy character.
        Args:
            x (float): Initial x position (sprite bottom-center X)
            y (float): Initial y position (sprite bottom-center Y)
            screen_width (int): Width of the game screen
            screen_height (int): Height of the game screen
        """
        # Load and scale player image
        image_path = os.path.join(os.path.dirname(__file__), "../assets/images/hornet.webp")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.25
        scaled_size = (int(source_width * scale_factor), int(source_height * scale_factor))
        self.image = pygame.transform.scale(self.image, scaled_size)
        self.image_flipped = pygame.transform.flip(self.image, True, False)
        self.rect.x = x
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)
        
        # Movement attributes
        self.velocity_x = 0
        self.velocity_y = 0
        self.speed = 150  # Horizontal movement speed (pixels per second)
        self.gravity = 1800  # Gravity acceleration (pixels per second squared)
        self.on_ground = False
        
        # Screen boundaries
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.ground_level = screen_height // 2 + self.rect.width  # Ground position
        
        # Facing direction (for future sprite flipping)
        self.facing_right = 1
        
        # Audio manager instance
        self.audio_manager = AudioManager()
        
        # Camera velocity cache to avoid tuple creation each frame
        self._camera_velocity = [0, 0]
        
        
        # Health system
        self.max_health = 2
        self.health = 2
    
    def _load_mossgrub_animation(self):
        """Load Hornet animations from spritesheet."""
        # Placeholder for future animation loading
        pass
    
    
    def take_damage(self, damage):
        """Apply damage to the player.
        Args:
            damage (int): Amount of damage to take
        """
        self.health = max(0, self.health - damage)
    
    def update(self, max_x, min_x, dt):
        """Update mossgrub position and physics.
        Args:
            dt (float): Delta time in seconds
            max_x (int): right boundary
            min_x (int): left boundary
        """
        # Apply gravity
        self.velocity_y += self.gravity * dt
        self.rect.y += self.velocity_y * dt
        
        # Ground collision
        if self.rect.bottom >= self.ground_level:
            self.rect.bottom = self.ground_level
            self.velocity_y = 0
            self.on_ground = True
        
        # Prevent falling off screen top
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity_y = 0

        # Check for boundaries and reverse direction
        if self.rect.x >= max_x or self.rect.x <= min_x:
            self.facing_right *= -1

        #Constantly move moss grub
        self.rect.x += self.speed * self.facing_right * dt

    def draw(self, screen, look_y_offset=0):
        """Draw the player character.
        Args:
            screen: pygame display surface
            look_y_offset (float): Vertical offset for camera look panning
        """
        # Calculate draw position with look offset
        draw_rect = self.rect.copy()
        draw_rect.y += look_y_offset
        
        # Flip image based on facing direction
        if self.facing_right == 1:
            screen.blit(self.image, draw_rect)
        else:
            screen.blit(self.image_flipped, draw_rect)
    
    def reset_position(self, x, y):
        """Reset mossgrub to its spawn position.
        Args:
            x (float): New x position (sprite bottom-center X)
            y (float): New y position (sprite bottom-center Y)
        """
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
