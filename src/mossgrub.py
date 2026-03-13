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
        pygame.transform.flip(self.image, True, False)
        source_width, source_height = self.image.get_size()
        scale_factor = 0.25
        scaled_size = (int(source_width * scale_factor), int(source_height * scale_factor))
        self.image = pygame.transform.scale(self.image, scaled_size)
        self.image_flipped = pygame.transform.flip(self.image, True, False)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.rect.midbottom = (x, y)

        self.knockback_velocity_x = 0.0
        self.knockback_strength = 520.0
        self.knockback_decay = 1600.0
        
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
        self.max_health = 1000
        self.health = 1000
    
    def _load_mossgrub_animation(self):
        """Load mossgrub animations from spritesheet."""
        # Placeholder for future animation loading
        pass

    def take_damage(self, damage, knockback_direction=0):
        """
        Apply damage to the mossgrub.
        Args:
            damage (int): Amount of damage to take
            knockback_direction (int): Horizontal knockback direction (-1 or 1)
        """   
        if damage <= 0:
            return
        else:
            self.health = max(0, self.health - damage)
            if knockback_direction < 0:
                self.knockback_velocity_x = -self.knockback_strength
            elif knockback_direction > 0:
                self.knockback_velocity_x = self.knockback_strength
       
    def update(self, min_x, max_x, dt, collision_rects = None, camera_x = 0, camera_y = 0):
        """Update mossgrub position and physics.
        Args:
            dt (float): Delta time in seconds
            min_x (int): left boundary
            max_x (int): right boundary
        """
               # Apply gravity
        self.velocity_y += self.gravity * dt
        self.rect.y += self.velocity_y * dt

        landed = False
        if collision_rects:
            world_rect = self.rect.copy()
            world_rect.x += int(camera_x)
            world_rect.y += int(camera_y)
            previous_bottom = world_rect.bottom - (self.velocity_y * dt)

            landing_top = None
            if self.velocity_y >= 0:
                for ground_rect in collision_rects:
                    if world_rect.right <= ground_rect.left or world_rect.left >= ground_rect.right:
                        continue
                    if previous_bottom <= ground_rect.top and world_rect.bottom >= ground_rect.top:
                        if landing_top is None or ground_rect.top < landing_top:
                            landing_top = ground_rect.top

            if landing_top is not None:
                world_rect.bottom = int(landing_top)
                self.rect.y = int(world_rect.y - camera_y)
                self.velocity_y = 0
                self.on_ground = True
                self._rebound_available = False
                landed = True

        if not landed:
            if collision_rects:
                self.on_ground = False
            elif self.rect.bottom >= self.ground_level:
                self.rect.bottom = self.ground_level
                self.velocity_y = 0
                self.on_ground = True
                self._rebound_available = False
        
        # Ground collision
        if self.rect.bottom >= self.ground_level:
            self.rect.bottom = self.ground_level
            self.velocity_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # Prevent falling off screen top
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity_y = 0

        # Combine patrol motion with temporary knockback push.
        self.rect.x += (self.speed * self.facing_right + self.knockback_velocity_x) * dt

        # Check for boundaries and reverse direction.
        if self.rect.centerx >= max_x:
            self.facing_right = -1
        elif self.rect.centerx <= min_x:
            self.facing_right = 1
        
        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

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