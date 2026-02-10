import pygame
import os
from audio import AudioManager
from animation import Animation

class Hornet:
    """Player character class with movement and jumping."""
    
    def __init__(self, x, y, screen_width, screen_height):
        """Initialize Hornet player character.
        Args:
            x (float): Initial x position
            y (float): Initial y position
            screen_width (int): Width of the game screen
            screen_height (int): Height of the game screen
        """
        # Load and scale player image
        image_path = os.path.join(os.path.dirname(__file__), "../assets/images/hornet.webp")
        self.image = pygame.image.load(image_path)
        self.image = pygame.transform.scale(self.image, (80, 80))  # Scale to reasonable size
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        # Movement attributes
        self.velocity_x = 0
        self.velocity_y = 0
        self.speed = 300  # Horizontal movement speed (pixels per second)
        self.jump_power = -600  # Jump velocity (negative is up)
        self.gravity = 1800  # Gravity acceleration (pixels per second squared)
        self.on_ground = False
        
        # Screen boundaries
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.ground_level = screen_height - 100  # Ground position
        
        # Facing direction (for future sprite flipping)
        self.facing_right = True
        
        # Audio manager instance
        self.audio_manager = AudioManager()
        
        # Camera velocity cache to avoid tuple creation each frame
        self._camera_velocity = [0, 0]
    
    def _load_hornet_animation(self):
        """Load Hornet animations from spritesheet."""
        # Placeholder for future animation loading
        pass
    
    def handle_input(self, keys):
        """Handle keyboard input for movement.
        Args:
            keys: pygame key state dictionary
        Returns:
            tuple: (velocity_x, velocity_y) for camera movement
        """
        # Horizontal movement (returns velocity for camera)
        self.velocity_x = 0
        
        if keys[pygame.K_a]:
            self.velocity_x = -self.speed
            self.facing_right = False
        if keys[pygame.K_d]:
            self.velocity_x = self.speed
            self.facing_right = True
        
        # Jumping
        if keys[pygame.K_SPACE] and self.on_ground:
            self.velocity_y = self.jump_power
            self.on_ground = False
            try:
                self.audio_manager.play_sfx("hornet_jump")
            except Exception:
                pass  # Skip if sound doesn't exist

        # Attack
        if keys[pygame.K_j]:
            try:
                self.audio_manager.play_sfx("hornet_attack")
            except Exception:
                pass  # Skip if sound doesn't exist

        if keys[pygame.K_k]:
            try:
                self.audio_manager.play_sfx("hornet_dash")
            except Exception:
                pass  # Skip if sound doesn't exist

        if keys[pygame.K_h]:
            AudioManager.play_sfx("hornet_special")
        
        if keys[pygame.K_LSHIFT]:
            AudioManager.play_sfx("hornet_heal")

        if keys[pygame.K_w]:
            # look up
            pass
        if keys[pygame.K_s]:
            # look down
            pass
            
        
        # Return camera movement (reuse cached list)
        self._camera_velocity[0] = self.velocity_x
        self._camera_velocity[1] = 0
        return self._camera_velocity
    
    def update(self, dt):
        """Update player position and physics.
        Args:
            dt (float): Delta time in seconds
        """
        # Don't move horizontally - camera handles that
        # Only apply vertical movement (jumping/gravity)
        
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
    
    def draw(self, screen):
        """Draw the player character.
        Args:
            screen: pygame display surface
        """
        # Flip image based on facing direction
        if self.facing_right:
            flipped_image = pygame.transform.flip(self.image, True, False)
            screen.blit(flipped_image, self.rect)
        else:
            screen.blit(self.image, self.rect)
    
    def reset_position(self, x, y):
        """Reset player to a specific position.
        Args:
            x (float): New x position
            y (float): New y position
        """
        self.rect.x = x
        self.rect.y = y
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
