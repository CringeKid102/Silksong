import pygame
import os
from audio import AudioManager
from animation import Animation
from bench import Bench

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
        self.jump_power = -750  # Max jump velocity (negative is up)
        self.jump_initial_impulse = -280  # Small upward kick on first frame
        self.jump_sustain_accel = -2800  # Upward acceleration while SPACE held
        self.jump_max_hold_time = 0.18  # Max seconds SPACE adds upward force
        self._jump_hold_timer = 0.0
        self.jump_cut_multiplier = 0.05  # Velocity multiplied when jump released early
        self.gravity = 1800  # Gravity acceleration (pixels per second squared)
        self.on_ground = False
        self._jump_held = False  # Whether jump key is currently held
        self._jumping = False  # True while in a jump that can still be cut short
        self._rebound_available = False  # Set when a down-attack hits; cleared on landing or release
        self.knockback_velocity_x = 0.0
        self.knockback_strength = 520.0
        self.knockback_decay = 1600.0

        # Wall jump / wall slide
        self.touching_wall_left = False
        self.touching_wall_right = False
        self.wall_jump_power_x = 450.0
        self.wall_jump_power_y = -680.0
        self.wall_slide_speed = 120.0
        self._wall_jump_timer = 0.0
        self._wall_jump_cooldown = 0.15

        # Ledge climb
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self.ledge_climb_duration = 0.3
        self._ledge_target_world_y = 0
        self._ledge_wall_direction = 0
        self._pressing_down = False

        # Camera correction for wall collisions
        self.camera_x_correction = 0.0

        # Diagonal down-attack charge
        self.down_attack_charge_speed = 900.0  # Horizontal burst speed
        self.down_attack_dive_speed = 600.0    # Extra downward speed added
        
        # Screen boundaries
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Facing direction (for future sprite flipping)
        self.facing_right = True
        
        # Audio manager instance
        self.audio_manager = AudioManager()

        # Initialize bench (main.py anchors it to world ground collider)
        self.bench = Bench(screen_width // 2, y)

        # Bench rest state
        self.is_resting = False
        self.rest_timer = 0.0
        self.rest_duration = 0.45
        
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
        self.heal_channel_duration = 1.0
        self.heal_channel_timer = 0.0
        self.is_healing = False

        # Silk resource system
        self.max_silk = 9
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

        # Dedicated attack hitbox state (world-space rect, short visual lifetime)
        self.attack_range = 70
        self.attack_height_padding = 25
        self.attack_hitbox_duration = 0.12
        self.attack_hitbox_timer = 0.0
        self.attack_hitbox = None
        self.attack_hitbox_facing_right = True
        self.attack_hitbox_direction = "forward"

        #Respawn point
        self.respawn_x = x
        self.respawn_y = y
    
    def _load_hornet_animation(self):
        """Load Hornet animations from spritesheet."""
        # Placeholder for future animation loading
        pass
    
    def handle_input(self, keys, dt=0.016):
        """Handle keyboard input for movement.
        Args:
            keys: pygame key state dictionary
            dt: delta time in seconds
        Returns:
            tuple: (velocity_x, velocity_y) for camera movement
        """
        # Horizontal movement (returns velocity for camera)
        self._attack_triggered = False
        self._pressing_down = keys[pygame.K_s]
        self.velocity_x = 0

        # Heal input (edge-triggered, consume all silk)
        shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if shift_pressed and not self._heal_key_down:
            self.start_heal_channel()
        self._heal_key_down = shift_pressed

        if self.is_healing or self.is_resting or self.is_climbing_ledge:
            self.look_direction = 0
            self.look_hold_timer = 0.0
            self._camera_velocity[0] = self.knockback_velocity_x
            self._camera_velocity[1] = 0
            return self._camera_velocity
        
        if keys[pygame.K_a]:
            self.velocity_x = -self.speed
            self.facing_right = False
        if keys[pygame.K_d]:
            self.velocity_x = self.speed
            self.facing_right = True
        
        # Jumping (variable height: hold SPACE for higher jump)
        jump_pressed = keys[pygame.K_SPACE]

        if jump_pressed and self.on_ground:
            self.velocity_y = self.jump_initial_impulse
            self.on_ground = False
            self._jumping = True
            self._jump_hold_timer = 0.0
            try:
                self.audio_manager.play_sfx("hornet_jump")
            except Exception:
                pass  # Skip if sound doesn't exist

        # Auto-rebound from down-attack: variable height via jump hold
        if self._rebound_available:
            self._rebound_available = False
            self._jumping = True
            self._jump_hold_timer = 0.0

        # Wall jump (edge-triggered: fresh SPACE press while touching wall in air)
        if jump_pressed and not self._jump_held and not self.on_ground and self._wall_jump_timer <= 0.0:
            if self.touching_wall_left:
                self.velocity_y = self.wall_jump_power_y
                self.knockback_velocity_x = self.wall_jump_power_x
                self._wall_jump_timer = self._wall_jump_cooldown
                self._jumping = True
                self._jump_hold_timer = 0.0
                self.facing_right = True
                try:
                    self.audio_manager.play_sfx("hornet_jump")
                except Exception:
                    pass
            elif self.touching_wall_right:
                self.velocity_y = self.wall_jump_power_y
                self.knockback_velocity_x = -self.wall_jump_power_x
                self._wall_jump_timer = self._wall_jump_cooldown
                self._jumping = True
                self._jump_hold_timer = 0.0
                self.facing_right = False
                try:
                    self.audio_manager.play_sfx("hornet_jump")
                except Exception:
                    pass

        # While holding SPACE during a jump, keep adding upward force
        if self._jumping and jump_pressed and self._jump_hold_timer < self.jump_max_hold_time:
            self._jump_hold_timer += dt
            self.velocity_y += self.jump_sustain_accel * dt
            # Clamp to max jump velocity
            if self.velocity_y < self.jump_power:
                self.velocity_y = self.jump_power

        # Cut jump short when SPACE released while still rising
        if self._jumping and not jump_pressed and self.velocity_y < 0:
            self.velocity_y = 0
            self._jumping = False

        # Stop variable-jump tracking once falling
        if self._jumping and self.velocity_y >= 0:
            self._jumping = False

        self._jump_held = jump_pressed

        # Attack
        if keys[pygame.K_j] and self._attack_timer <= 0.0:
            self._attack_timer = self.attack_cooldown
            self._attack_triggered = True
            if keys[pygame.K_w]:
                self.attack_hitbox_direction = "up"
            elif keys[pygame.K_s]:
                self.attack_hitbox_direction = "down"
                # Fast diagonal charge in facing direction + downward
                direction = 1 if self.facing_right else -1
                self.knockback_velocity_x = direction * self.down_attack_charge_speed
                self.velocity_y = self.down_attack_dive_speed
            else:
                self.attack_hitbox_direction = "forward"
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
        
        # Do not let vertical attack inputs, horizontal movement, or jumping drive camera panning.
        directional_attack_active = self._attack_timer > 0.0 and self.attack_hitbox_direction in ("up", "down")
        moving_horizontally = self.velocity_x != 0
        in_air = not self.on_ground

        # Look up/down
        if directional_attack_active or moving_horizontally or in_air:
            self.look_direction = 0
            self.look_hold_timer = 0.0
        elif keys[pygame.K_w]:
            if self.look_direction != -1:
                # Started pressing up, reset timer
                self.look_hold_timer = 0.0
                self.look_direction = -1
        elif keys[pygame.K_s]:
            if self.look_direction != 1:
                # Started pressing down, reset timer
                self.look_hold_timer = 0.0
                self.look_direction = 1
        else:
            self.look_direction = 0
            self.look_hold_timer = 0.0
        
        # Return camera movement (reuse cached list)
        self._camera_velocity[0] = self.velocity_x + self.knockback_velocity_x
        self._camera_velocity[1] = 0
        return self._camera_velocity

    def consume_attack_trigger(self):
        """Return whether attack was pressed this frame, then clear the flag."""
        attack_pressed = self._attack_triggered
        self._attack_triggered = False
        return attack_pressed

    def _build_attack_hitbox(self, world_rect):
        """Build attack hitbox from the current world-space Hornet rect."""
        base_height = max(10, world_rect.height - self.attack_height_padding * 2)

        if self.attack_hitbox_direction == "up":
            hitbox_width = max(26, int(world_rect.width * 0.9))
            hitbox_height = int(self.attack_range)
            facing_bias = 12 if self.attack_hitbox_facing_right else -12
            hitbox_left = world_rect.centerx - hitbox_width // 2 + facing_bias
            hitbox_top = world_rect.top - hitbox_height
            return pygame.Rect(int(hitbox_left), int(hitbox_top), int(hitbox_width), int(hitbox_height))

        if self.attack_hitbox_direction == "down":
            hitbox_width = int(self.attack_range)
            hitbox_height = max(base_height, int(self.attack_range * 0.7))
            hitbox_top = world_rect.bottom - int(hitbox_height * 0.35)
            if self.attack_hitbox_facing_right:
                hitbox_left = world_rect.right
            else:
                hitbox_left = world_rect.left - hitbox_width
            return pygame.Rect(int(hitbox_left), int(hitbox_top), int(hitbox_width), int(hitbox_height))

        hitbox_top = world_rect.top + self.attack_height_padding
        if self.attack_hitbox_facing_right:
            hitbox_left = world_rect.right
        else:
            hitbox_left = world_rect.left - self.attack_range
        return pygame.Rect(int(hitbox_left), int(hitbox_top), int(self.attack_range), int(base_height))

    def start_attack_hitbox(self, camera_x=0, camera_y=0):
        """Create and activate Hornet's attack hitbox in world coordinates."""
        world_rect = self.rect.copy()
        world_rect.x += int(camera_x)
        world_rect.y += int(camera_y)
        self.attack_hitbox_facing_right = self.facing_right
        self.attack_hitbox = self._build_attack_hitbox(world_rect)
        self.attack_hitbox_timer = self.attack_hitbox_duration
        return self.attack_hitbox.copy()

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

    def start_rest(self):
        """Start a short bench rest and fully heal."""
        self.cancel_heal_channel()
        self.is_resting = True
        self.rest_timer = self.rest_duration
        self.health = self.max_health
        self.velocity_x = 0
        self.velocity_y = 0
    
    def heal(self):
        """Apply healing immediately."""
        # Silk is consumed when channel starts, so completion should only check HP.
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

    def take_damage(self, damage, knockback_direction=0):
        """
        Apply damage to the player.
        Args:
            damage (int): Amount of damage to take
            knockback_direction (int): Horizontal knockback direction (-1 or 1)
        """
        if damage <= 0:
            return
        if self.is_healing:
            self.cancel_heal_channel()
        if self.is_resting:
            self.is_resting = False
            self.rest_timer = 0.0
        if self.is_climbing_ledge:
            self.is_climbing_ledge = False
            self.ledge_climb_timer = 0.0
        self.health = max(0, self.health - damage)

        if knockback_direction < 0:
            self.knockback_velocity_x = -self.knockback_strength
        elif knockback_direction > 0:
            self.knockback_velocity_x = self.knockback_strength

    def rebound_from_down_attack(self, enemy_rect=None, camera_y=0):
        """Launch Hornet upward after a successful downward strike.

        The rebound uses the same variable-height jump: hold SPACE to
        rise higher, release early for a short bounce.
        """
        if self.attack_hitbox_direction != "down" or self.on_ground:
            return False

        if enemy_rect is not None:
            desired_world_bottom = int(enemy_rect.top - 6)
            current_world_bottom = int(self.rect.bottom + camera_y)
            if current_world_bottom > desired_world_bottom:
                self.rect.bottom = int(desired_world_bottom - camera_y)

        self.velocity_y = self.jump_power
        self.on_ground = False
        self._rebound_available = True
        self._jumping = False
        return True
    
    def update(self, dt, collision_rects=None, camera_x=0, camera_y=0):
        """Update player position and physics.
        Args:
            dt (float): Delta time in seconds
        """
        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

        if self._attack_timer > 0.0:
            self._attack_timer = max(0.0, self._attack_timer - dt)
        if self._dash_timer > 0.0:
            self._dash_timer = max(0.0, self._dash_timer - dt)
        if self._special_timer > 0.0:
            self._special_timer = max(0.0, self._special_timer - dt)
        if self._wall_jump_timer > 0.0:
            self._wall_jump_timer = max(0.0, self._wall_jump_timer - dt)

        if self.is_resting:
            self.rest_timer = max(0.0, self.rest_timer - dt)
            if self.rest_timer <= 0.0:
                self.is_resting = False

        # Complete channel heal after 1 seconds if uninterrupted
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
        
        # Reset per-frame wall correction
        self.camera_x_correction = 0.0

        if self.is_climbing_ledge:
            # Ledge climb animation: move upward toward ledge top
            self.ledge_climb_timer -= dt
            target_world_bottom = self._ledge_target_world_y
            current_world_bottom = self.rect.bottom + camera_y
            climb_speed = 500.0
            if current_world_bottom > target_world_bottom:
                move = min(climb_speed * dt, current_world_bottom - target_world_bottom)
                self.rect.y -= int(move)
            if self.ledge_climb_timer <= 0.0 or self.rect.bottom + camera_y <= target_world_bottom + 2:
                self.rect.bottom = int(target_world_bottom - camera_y)
                push_distance = self.rect.width // 2 + 5
                if self._ledge_wall_direction == 1:
                    self.camera_x_correction = push_distance
                else:
                    self.camera_x_correction = -push_distance
                self.is_climbing_ledge = False
                self.ledge_climb_timer = 0.0
                self.velocity_y = 0
                self.on_ground = True
        else:
            # Apply gravity
            self.velocity_y += self.gravity * dt

            # Wall slide: limit fall speed when touching a wall in the air
            if not self.on_ground and self.velocity_y > 0 and (self.touching_wall_left or self.touching_wall_right):
                if self.velocity_y > self.wall_slide_speed:
                    self.velocity_y = self.wall_slide_speed

            self.rect.y += self.velocity_y * dt

            landed = False
            if collision_rects:
                world_rect = self.rect.copy()
                world_rect.x += int(camera_x)
                world_rect.y += int(camera_y)
                previous_bottom = world_rect.bottom - (self.velocity_y * dt)

                # Ceiling collision (elevated platforms only)
                if self.velocity_y < 0:
                    previous_top = world_rect.top - (self.velocity_y * dt)
                    for cr in collision_rects:
                        if cr.width > 5000:
                            continue
                        if world_rect.right <= cr.left or world_rect.left >= cr.right:
                            continue
                        if previous_top >= cr.bottom and world_rect.top <= cr.bottom:
                            world_rect.top = cr.bottom
                            self.rect.y = int(world_rect.y - camera_y)
                            self.velocity_y = 0
                            break

                # Landing collision
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
                else:
                    self.on_ground = False

            # Horizontal (wall) collision detection
            self.touching_wall_left = False
            self.touching_wall_right = False

            if collision_rects:
                world_rect = self.rect.copy()
                world_rect.x += int(camera_x)
                world_rect.y += int(camera_y)

                for cr in collision_rects:
                    if cr.width > 5000:
                        continue
                    if not world_rect.colliderect(cr):
                        continue
                    if world_rect.bottom <= cr.top + 4:
                        continue

                    overlap_right = world_rect.right - cr.left
                    overlap_left = cr.right - world_rect.left
                    overlap_bottom = world_rect.bottom - cr.top
                    overlap_top = cr.bottom - world_rect.top

                    min_h = min(overlap_right, overlap_left)
                    min_v = min(overlap_bottom, overlap_top)

                    if min_h >= min_v:
                        continue

                    if overlap_right < overlap_left:
                        self.camera_x_correction -= overlap_right
                        self.touching_wall_right = True
                    else:
                        self.camera_x_correction += overlap_left
                        self.touching_wall_left = True

            # Ledge detection: auto-grab when falling against a wall
            if not self.on_ground and self.velocity_y >= 0 and not self._pressing_down:
                if self.touching_wall_right or self.touching_wall_left:
                    wr = self.rect.copy()
                    wr.x += int(camera_x)
                    wr.y += int(camera_y)

                    for cr in collision_rects or []:
                        if cr.width > 5000:
                            continue
                        ledge_top = cr.top
                        if ledge_top < wr.top - 10 or ledge_top > wr.centery:
                            continue
                        if self.touching_wall_right and wr.right >= cr.left - 5 and wr.left < cr.right:
                            self.is_climbing_ledge = True
                            self.ledge_climb_timer = self.ledge_climb_duration
                            self._ledge_target_world_y = ledge_top
                            self._ledge_wall_direction = 1
                            self.velocity_y = 0
                            self.knockback_velocity_x = 0
                            break
                        elif self.touching_wall_left and wr.left <= cr.right + 5 and wr.right > cr.left:
                            self.is_climbing_ledge = True
                            self.ledge_climb_timer = self.ledge_climb_duration
                            self._ledge_target_world_y = ledge_top
                            self._ledge_wall_direction = -1
                            self.velocity_y = 0
                            self.knockback_velocity_x = 0
                            break

        if self.attack_hitbox_timer > 0.0:
            # Keep active attack hitbox attached to Hornet in world-space.
            world_rect = self.rect.copy()
            world_rect.x += int(camera_x)
            world_rect.y += int(camera_y)
            self.attack_hitbox = self._build_attack_hitbox(world_rect)

            self.attack_hitbox_timer = max(0.0, self.attack_hitbox_timer - dt)
            if self.attack_hitbox_timer <= 0.0:
                self.attack_hitbox = None
        
        # Prevent falling off screen top
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity_y = 0

        if self.health <= 0:
            self.health = 0
            try:
                self.audio_manager.play_sfx("hornet_death")
            except Exception:
                pass  # Skip if sound doesn't exist
    
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
        self.is_resting = False
        self.rest_timer = 0.0
        self.attack_hitbox = None
        self.attack_hitbox_timer = 0.0
        self.attack_hitbox_facing_right = self.facing_right
        self.attack_hitbox_direction = "forward"
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self.touching_wall_left = False
        self.touching_wall_right = False
        self.camera_x_correction = 0.0