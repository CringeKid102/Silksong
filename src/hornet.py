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
        
        # Look up/down system
        self.look_hold_timer = 0.0        # How long W/S has been held
        self.look_hold_threshold = 1.0    # Seconds before camera starts panning
        self.camera_look_y = 0.0          # Current look offset
        self.max_look_distance = 300.0    # Maximum pixels the camera can pan
        self.look_speed = 250.0           # Camera pan speed once activated
        self.look_direction = 0           # -1 = up, 1 = down, 0 = none
        
        # Health system
        self.max_health = 4
        self.health = 4
        self.heal_amount = 3  # Amount of health restored per heal
        self.max_silk = 9 # Seconds between heals
        self.silk = 9
    
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
        
        # Healing with left shift
        if keys[pygame.K_LSHIFT]:
            self.try_heal()

        # Look up/down — requires holding key for 1 second before camera pans
        looking = False
        if keys[pygame.K_w]:
            looking = True
            if self.look_direction != -1:
                # Started pressing up, reset timer
                self.look_hold_timer = 0.0
                self.look_direction = -1
        elif keys[pygame.K_s]:
            looking = True
            if self.look_direction != 1:
                # Started pressing down, reset timer
                self.look_hold_timer = 0.0
                self.look_direction = 1
        else:
            self.look_direction = 0
            self.look_hold_timer = 0.0
        
        # Return camera movement (reuse cached list)
        self._camera_velocity[0] = self.velocity_x
        self._camera_velocity[1] = 0
        return self._camera_velocity
    
    def try_heal(self):
        """Attempt to heal the player if cooldown has elapsed."""
        if self.heal_timer <= 0 and self.health < self.max_health:
            # Heal the player
            self.health = min(self.health + self.heal_amount, self.max_health)
            self.heal_timer = self.heal_cooldown
            # Play heal sound
            try:
                AudioManager.play_sfx("hornet_heal")
            except Exception:
                pass  # Skip if sound doesn't exist
    
    def take_damage(self, damage):
        """Apply damage to the player.
        Args:
            damage (int): Amount of damage to take
        """
        self.health = max(0, self.health - damage)
    
    def update(self, dt):
        """Update player position and physics.
        Args:
            dt (float): Delta time in seconds
        """
        # Update heal cooldown timer
        if self.heal_timer > 0:
            self.heal_timer -= dt
        
        # Update look hold timer and camera look offset
        if self.look_direction != 0:
            self.look_hold_timer += dt
            if self.look_hold_timer >= self.look_hold_threshold:
                # Pan the camera in the look direction
                self.camera_look_y += self.look_direction * self.look_speed * dt
                # Clamp to max distance
                self.camera_look_y = max(-self.max_look_distance, min(self.max_look_distance, self.camera_look_y))
        else:
            # Smoothly return camera to center when not looking
            if abs(self.camera_look_y) > 1.0:
                self.camera_look_y *= 0.85  # Ease back to center
            else:
                self.camera_look_y = 0.0
        
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
        if self.facing_right:
            flipped_image = pygame.transform.flip(self.image, True, False)
            screen.blit(flipped_image, draw_rect)
        else:
            screen.blit(self.image, draw_rect)
    
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
