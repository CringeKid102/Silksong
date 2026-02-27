import pygame
import os
from audio import AudioManager
from animation import Animation

class Hornet:
    """Player character class with movement and jumping."""
    
    def __init__(self, x, y, screen_width, screen_height):
        """Initialize Hornet player character.
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
        
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)
        
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
        self.ground_level = screen_height // 2 + self.rect.width  # Ground position
        
        # Facing direction (for future sprite flipping)
        self.facing_right = True
        
        # Audio manager instance
        self.audio_manager = AudioManager()
        
        # Camera velocity cache to avoid tuple creation each frame
        self._camera_velocity = [0, 0]
        
        # Look up/down system
        self.look_hold_timer = 0.0        # How long W/S has been held
        self.look_hold_threshold = 0.25   # Seconds before camera starts panning
        self.camera_look_y = 0.0          # Current look offset
        self.max_look_distance = 300.0    # Maximum pixels the camera can pan
        self.look_speed = 520.0           # Camera pan speed once activated
        self.look_direction = 0           # -1 = up, 1 = down, 0 = none
        
        # Health system
        self.max_health = 5
        self.health = 5
        self.heal_amount = 3  # Amount of health restored per heal
        self.heal_channel_duration = 2.0
        self.heal_channel_timer = 0.0
        self.is_healing = False

        # Silk resource system
        self.max_silk = 99
        self.silk = 0

        # Input cooldowns to prevent SFX spam from held keys
        self.attack_cooldown = 0.18
        self.dash_cooldown = 0.22
        self.special_cooldown = 0.45
        self._attack_timer = 0.0
        self._dash_timer = 0.0
        self._special_timer = 0.0
        self._attack_triggered = False
        self._heal_key_down = False
    
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
        self._attack_triggered = False
        self.velocity_x = 0

        # Heal input (edge-triggered, consume all silk)
        shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if shift_pressed and not self._heal_key_down:
            self.start_heal_channel()
        self._heal_key_down = shift_pressed

        if self.is_healing:
            self.look_direction = 0
            self.look_hold_timer = 0.0
            self._camera_velocity[0] = 0
            self._camera_velocity[1] = 0
            return self._camera_velocity
        
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
        if keys[pygame.K_j] and self._attack_timer <= 0.0:
            self._attack_timer = self.attack_cooldown
            self._attack_triggered = True
            try:
                self.audio_manager.play_sfx("hornet_attack")
            except Exception:
                pass  # Skip if sound doesn't exist

        # Dash
        if keys[pygame.K_k] and self._dash_timer <= 0.0:
            self._dash_timer = self.dash_cooldown
            try:
                self.audio_manager.play_sfx("hornet_dash")
            except Exception:
                pass  # Skip if sound doesn't exist

        # Special
        if keys[pygame.K_h] and self._special_timer <= 0.0:
            self._special_timer = self.special_cooldown
            try:
                self.audio_manager.play_sfx("hornet_special")
            except Exception:
                pass  # Skip if sound doesn't exist
        
        # Look up/down
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

    def consume_attack_trigger(self):
        """Return whether attack was pressed this frame, then clear the flag."""
        attack_pressed = self._attack_triggered
        self._attack_triggered = False
        return attack_pressed

    def gain_silk(self, amount):
        """Gain silk up to max_silk."""
        if amount <= 0:
            return
        self.silk = min(self.max_silk, self.silk + amount)

    def start_heal_channel(self):
        """Start 2-second healing channel and consume all silk immediately."""
        if self.is_healing:
            return False
        if self.silk <= 0:
            return False
        if self.health >= self.max_health:
            return False

        self.silk = 0
        self.is_healing = True
        self.heal_channel_timer = self.heal_channel_duration
        return True

    def cancel_heal_channel(self):
        """Cancel active heal channel."""
        self.is_healing = False
        self.heal_channel_timer = 0.0
    
    def heal(self):
        """Apply healing immediately."""
        if self.health < self.max_health:
            self.health = min(self.health + self.heal_amount, self.max_health)
            try:
                self.audio_manager.play_sfx("hornet_heal")
            except Exception:
                pass  # Skip if sound doesn't exist
            
    def draw_silk_bar(self):
        """
        Displays amount of silk player has available for healing. 
        Args: 
            
        """
        silk_bar = os.path.join(os.path.dirname(__file__), "../assets/images/palceholder")

    def take_damage(self, damage):
        """
        Apply damage to the player.
        Args:
            damage (int): Amount of damage to take
        """
        if damage <= 0:
            return
        if self.is_healing:
            self.cancel_heal_channel()
        self.health = max(0, self.health - damage)
    
    def update(self, dt):
        """Update player position and physics.
        Args:
            dt (float): Delta time in seconds
        """
        if self._attack_timer > 0.0:
            self._attack_timer = max(0.0, self._attack_timer - dt)
        if self._dash_timer > 0.0:
            self._dash_timer = max(0.0, self._dash_timer - dt)
        if self._special_timer > 0.0:
            self._special_timer = max(0.0, self._special_timer - dt)

        # Complete channel heal after 2 seconds if uninterrupted
        if self.is_healing:
            self.heal_channel_timer -= dt
            if self.heal_channel_timer <= 0.0:
                self.heal_channel_timer = 0.0
                self.is_healing = False
                self.heal()
        
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
            screen.blit(self.image_flipped, draw_rect)
        else:
            screen.blit(self.image, draw_rect)

        # Draw UI
        healthbar = os.path.join(os.path.dirname(__file__), "../assets/images/healthbar.webp")

        # Simple heal-channel visual effect
        if self.is_healing:
            center = draw_rect.center
    
    def reset_position(self, x, y):
        """Reset player to a specific position.
        Args:
            x (float): New x position (sprite bottom-center X)
            y (float): New y position (sprite bottom-center Y)
        """
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
