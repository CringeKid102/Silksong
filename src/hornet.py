import pygame
import os
from audio import AudioManager
from animation import Animation
from bench import Bench

class Hornet:
    """Player character with movement, combat, and platforming."""
    
    def __init__(self, x, y, screen_width, screen_height):
        """Create Hornet at the given position on a screen of the given size."""
        # Load and scale player image
        image_path = os.path.join(os.path.dirname(__file__), "../assets/images/hornet.webp")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.3
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
        self.jump_initial_impulse = -800  # Small upward kick on first frame
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
        self.attack_recoil_velocity_x = 0.0
        self.attack_recoil_strength = 320.0
        self.attack_recoil_decay = 1800.0

        # Wall jump / wall slide
        self.touching_wall_left = False
        self.touching_wall_right = False
        self.wall_jump_power_x = 450.0
        # Use full jump lift so repeated wall jumps climb quickly.
        self.wall_jump_power_y = self.jump_power
        self.wall_slide_speed = 120.0
        self._wall_jump_timer = 0.0
        self._wall_jump_cooldown = 0.08

        # Ledge climb
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self.ledge_climb_duration = 0.3
        self._ledge_target_world_x = None
        self._ledge_target_world_y = 0
        self._ledge_wall_direction = 0
        self._pressing_down = False

        # Camera correction for wall collisions
        self.camera_x_correction = 0.0

        # Diagonal down-attack charge
        self.down_attack_charge_speed = 900.0  # Horizontal burst speed
        self.down_attack_dive_speed = 600.0    # Extra downward speed added
        self.down_attack_rebound_horizontal_scale = 0.2
        
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

        # Crowd control
        self.stun_timer = 0.0
        
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
        self._attack_key_down = False
        self._heal_key_down = False

        # Dedicated attack hitbox state
        self.attack_range = 70
        self.attack_height_padding = 25
        self.attack_hitbox_duration = 0.12
        self.down_attack_hitbox_duration = 0.20
        self.attack_hitbox_timer = 0.0
        self.attack_hitbox = None
        self.attack_hitbox_facing_right = True
        self.attack_hitbox_direction = "forward"
        self.attack_hit_mossgrub = False
        self.attack_hit_mossmother = False
        self.attack_recoil_applied = False
        self.is_down_attacking = False
        self.down_attack_momentum_active = False
        self.down_attack_rebound_timer = 0.0
        self.down_attack_jump_lock_duration = 0.3
        self.down_attack_jump_lock_timer = 0.0

        #Respawn point
        self.respawn_x = x
        self.respawn_y = y
    
    def _load_hornet_animation(self):
        """Load Hornet animations from spritesheet. Placeholder for future use."""
        pass
    
    def handle_input(self, keys, dt=0.016):
        """Handle keyboard input for movement and return camera velocity."""
        # Horizontal movement (returns velocity for camera)
        self._attack_triggered = False
        self._pressing_down = keys[pygame.K_s]
        self.velocity_x = 0
        attack_pressed = keys[pygame.K_j]

        # Heal input (edge-triggered, consume all silk)
        shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if shift_pressed and not self._heal_key_down:
            self.start_heal_channel()
        self._heal_key_down = shift_pressed

        if self.is_healing or self.is_resting or self.is_climbing_ledge or self.stun_timer > 0.0:
            self.look_direction = 0
            self.look_hold_timer = 0.0
            self.velocity_x = 0
            self._attack_key_down = attack_pressed
            self._camera_velocity[0] = self.knockback_velocity_x + self.attack_recoil_velocity_x
            self._camera_velocity[1] = 0
            return self._camera_velocity
        
        if keys[pygame.K_a]:
            self.velocity_x = -self.speed
            self.facing_right = False
        if keys[pygame.K_d]:
            self.velocity_x = self.speed
            self.facing_right = True
        
        # Jumping
        jump_pressed = keys[pygame.K_SPACE]
        jump_locked = self.down_attack_jump_lock_timer > 0.0

        if jump_pressed and self.on_ground and not jump_locked:
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
        if jump_pressed and not self._jump_held and not self.on_ground and self._wall_jump_timer <= 0.0 and not jump_locked:
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
        if self._jumping and not jump_pressed and self.velocity_y < 0 and self.down_attack_rebound_timer <= 0.0:
            self.velocity_y = 0
            self._jumping = False

        # Stop variable-jump tracking once falling
        if self._jumping and self.velocity_y >= 0:
            self._jumping = False

        self._jump_held = jump_pressed

        # Attack
        fresh_attack_press = attack_pressed and not self._attack_key_down
        if fresh_attack_press and self._attack_timer <= 0.0:
            self._attack_timer = self.attack_cooldown
            self._attack_triggered = True
            if keys[pygame.K_w]:
                self.attack_hitbox_direction = "up"
            elif keys[pygame.K_s] and not self.on_ground:
                self.attack_hitbox_direction = "down"
                self.is_down_attacking = True
                self.down_attack_momentum_active = True
                # Fast diagonal charge in facing direction + downward
                direction = 1 if self.facing_right else -1
                self.knockback_velocity_x = direction * self.down_attack_charge_speed
                self.velocity_y = self.down_attack_dive_speed
            else:
                self.attack_hitbox_direction = "forward"
                self.is_down_attacking = False
            try:
                self.audio_manager.play_sfx("hornet_attack")
            except Exception:
                pass  # Skip if sound doesn't exist
        self._attack_key_down = attack_pressed

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
        self._camera_velocity[0] = self.velocity_x + self.knockback_velocity_x + self.attack_recoil_velocity_x
        self._camera_velocity[1] = 0
        return self._camera_velocity

    def consume_attack_trigger(self):
        """Return True if attack was triggered this frame, then reset."""
        attack_pressed = self._attack_triggered
        self._attack_triggered = False
        return attack_pressed

    def _build_attack_hitbox(self, world_rect):
        """Build an attack hitbox based on direction and world-space position."""
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
        """Activate the attack hitbox in world coordinates."""
        world_rect = self.rect.copy()
        world_rect.x += int(camera_x)
        world_rect.y += int(camera_y)
        self.attack_hitbox_facing_right = self.facing_right
        self.attack_recoil_applied = False
        self.attack_hitbox = self._build_attack_hitbox(world_rect)
        self.attack_hit_mossgrub = False
        self.attack_hit_mossmother = False
        if self.attack_hitbox_direction == "down":
            self.attack_hitbox_timer = self.down_attack_hitbox_duration
        else:
            self.attack_hitbox_timer = self.attack_hitbox_duration
        return self.attack_hitbox.copy()

    def apply_attack_recoil_on_hit(self):
        """Apply recoil knockback once per swing when hitting an enemy."""
        if self.attack_recoil_applied:
            return
        facing_direction = 1 if self.attack_hitbox_facing_right else -1
        self.attack_recoil_velocity_x = -facing_direction * self.attack_recoil_strength
        self.attack_recoil_applied = True

    def gain_silk(self, amount):
        """Add silk, clamped to the maximum."""
        if amount <= 0:
            return
        self.silk = min(self.max_silk, self.silk + amount)

    def start_heal_channel(self):
        """Begin the heal channel, consuming all silk upfront."""
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
        """Cancel the current heal channel if active."""
        self.is_healing = False
        self.heal_channel_timer = 0.0

    def start_rest(self):
        """Sit on a bench, fully heal, and pause movement."""
        self.cancel_heal_channel()
        self.is_resting = True
        self.rest_timer = self.rest_duration
        self.health = self.max_health
        self.velocity_x = 0
        self.velocity_y = 0

    def start_stun(self, duration=2.0):
        """Temporarily prevent Hornet from moving or attacking."""
        if duration <= 0:
            return
        self.cancel_heal_channel()
        self.is_resting = False
        self.rest_timer = 0.0
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self.stun_timer = max(self.stun_timer, duration)
        self.velocity_x = 0
        self.velocity_y = max(0, self.velocity_y)
        self.look_direction = 0
        self.look_hold_timer = 0.0

    def heal(self):
        """Restore health when the heal channel completes."""
        if self.health < self.max_health:
            self.health = min(self.health + self.heal_amount, self.max_health)
            try:
                self.audio_manager.play_sfx("hornet_heal")
            except Exception:
                pass  # Skip if sound doesn't exist
            
    def draw_silk_bar(self):
        """Draw the silk resource bar on screen. Placeholder for future use."""
        pass

    def take_damage(self, damage, knockback_direction=0):
        """Apply damage and knockback to the player."""
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
        """Bounce Hornet upward after a successful down-attack hit."""
        if self.attack_hitbox_direction != "down" or self.on_ground:
            return False

        if enemy_rect is not None:
            desired_world_bottom = int(enemy_rect.top - 6)
            current_world_bottom = int(self.rect.bottom + camera_y)
            if current_world_bottom > desired_world_bottom:
                self.rect.bottom = int(desired_world_bottom - camera_y)

        self.velocity_y = self.jump_initial_impulse
        self.knockback_velocity_x *= self.down_attack_rebound_horizontal_scale
        self.on_ground = False
        self._rebound_available = False
        self._jumping = True
        self._jump_hold_timer = 0.0
        self.is_down_attacking = False
        self.down_attack_rebound_timer = max(self.down_attack_rebound_timer, self.attack_hitbox_timer)
        return True
    
    def update(self, dt, collision_rects=None, camera_x=0, camera_y=0, move_horizontally=False):
        """Update player physics, collisions, and timers."""
        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

        if self.attack_recoil_velocity_x > 0.0:
            self.attack_recoil_velocity_x = max(0.0, self.attack_recoil_velocity_x - self.attack_recoil_decay * dt)
        elif self.attack_recoil_velocity_x < 0.0:
            self.attack_recoil_velocity_x = min(0.0, self.attack_recoil_velocity_x + self.attack_recoil_decay * dt)

        if self._attack_timer > 0.0:
            self._attack_timer = max(0.0, self._attack_timer - dt)
        if self._dash_timer > 0.0:
            self._dash_timer = max(0.0, self._dash_timer - dt)
        if self._special_timer > 0.0:
            self._special_timer = max(0.0, self._special_timer - dt)
        if self._wall_jump_timer > 0.0:
            self._wall_jump_timer = max(0.0, self._wall_jump_timer - dt)
        if self.down_attack_rebound_timer > 0.0:
            self.down_attack_rebound_timer = max(0.0, self.down_attack_rebound_timer - dt)
        if self.down_attack_jump_lock_timer > 0.0:
            self.down_attack_jump_lock_timer = max(0.0, self.down_attack_jump_lock_timer - dt)
        if self.stun_timer > 0.0:
            self.stun_timer = max(0.0, self.stun_timer - dt)

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
            # Ledge climb animation: move toward the cached landing point.
            self.ledge_climb_timer -= dt
            target_world_bottom = self._ledge_target_world_y
            target_world_x = self._ledge_target_world_x
            current_world_bottom = self.rect.bottom + camera_y
            climb_speed = 500.0
            if current_world_bottom > target_world_bottom:
                move = min(climb_speed * dt, current_world_bottom - target_world_bottom)
                self.rect.y -= int(move)
            if self.ledge_climb_timer <= 0.0 or self.rect.bottom + camera_y <= target_world_bottom + 2:
                self.rect.bottom = int(target_world_bottom - camera_y)
                if target_world_x is not None:
                    current_world_x = self.rect.x + camera_x
                    self.camera_x_correction = float(target_world_x - current_world_x)
                self.is_climbing_ledge = False
                self.ledge_climb_timer = 0.0
                self._ledge_target_world_x = None
                self.velocity_y = 0
                self.on_ground = True
        else:
            # Apply gravity
            self.velocity_y += self.gravity * dt

            if self.down_attack_rebound_timer > 0.0:
                self.velocity_y = self.jump_initial_impulse
                self.on_ground = False
                self._jumping = True

            # Wall slide: always engage on wall contact in air (outside immediate wall-jump impulse).
            # This prevents jump-hold from creating upward wall-glide.
            if not self.on_ground and (self.touching_wall_left or self.touching_wall_right) and self._wall_jump_timer <= 0.0 and self.down_attack_rebound_timer <= 0.0:
                self.velocity_y = self.wall_slide_speed

            if move_horizontally:
                horizontal_velocity = self.velocity_x + self.knockback_velocity_x + self.attack_recoil_velocity_x
                self.rect.x += horizontal_velocity * dt

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
                    if self.down_attack_momentum_active:
                        self.knockback_velocity_x = 0.0
                        self.down_attack_momentum_active = False
                    self._rebound_available = False
                    self.down_attack_rebound_timer = 0.0
                    if self.is_down_attacking:
                        self.down_attack_jump_lock_timer = self.down_attack_jump_lock_duration
                        self.is_down_attacking = False
                    landed = True

            if not landed:
                if collision_rects:
                    self.on_ground = False
                else:
                    self.on_ground = False

            # Horizontal (wall) collision detection
            self.touching_wall_left = False
            self.touching_wall_right = False
            resolved_world_rect = None

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

                    correction_x = 0
                    if overlap_right < overlap_left:
                        correction_x = -overlap_right
                        self.touching_wall_right = True
                    else:
                        correction_x = overlap_left
                        self.touching_wall_left = True

                    self.camera_x_correction += correction_x
                    world_rect.x += int(correction_x)

                    if self.is_down_attacking:
                        self.down_attack_jump_lock_timer = self.down_attack_jump_lock_duration
                        self.is_down_attacking = False

                resolved_world_rect = world_rect.copy()

            # Ledge detection: auto-grab only when there is actual landing space on top.
            if not self.on_ground and self.velocity_y >= 0 and not self._pressing_down and collision_rects:
                if self.touching_wall_right or self.touching_wall_left:
                    wr = resolved_world_rect.copy() if resolved_world_rect is not None else self.rect.copy()
                    if resolved_world_rect is None:
                        wr.x += int(camera_x)
                        wr.y += int(camera_y)

                    ledge_margin = 8
                    for cr in collision_rects:
                        if cr.width > 5000:
                            continue

                        ledge_top = cr.top
                        if ledge_top < wr.top - 10 or ledge_top > wr.centery:
                            continue

                        climbing_right = self.touching_wall_right and wr.right >= cr.left - 5 and wr.left < cr.right
                        climbing_left = self.touching_wall_left and wr.left <= cr.right + 5 and wr.right > cr.left
                        if not (climbing_right or climbing_left):
                            continue

                        landing_rect = wr.copy()
                        landing_rect.bottom = int(ledge_top)
                        if climbing_right:
                            landing_rect.left = int(cr.left + ledge_margin)
                            ledge_direction = 1
                        else:
                            landing_rect.right = int(cr.right - ledge_margin)
                            ledge_direction = -1

                        blocked = False
                        for blocking_rect in collision_rects:
                            if blocking_rect.width > 5000 or blocking_rect is cr:
                                continue
                            if landing_rect.colliderect(blocking_rect):
                                blocked = True
                                break

                        if blocked:
                            continue

                        self.is_climbing_ledge = True
                        self.ledge_climb_timer = self.ledge_climb_duration
                        self._ledge_target_world_x = int(landing_rect.x)
                        self._ledge_target_world_y = int(ledge_top)
                        self._ledge_wall_direction = ledge_direction
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
                self.attack_hit_mossgrub = False
                self.attack_hit_mossmother = False
        
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
    
    def draw(self, screen, look_y_offset=0, screen_offset=(0, 0)):
        """Draw Hornet on screen with the given vertical look offset."""
        draw_rect = self.rect.copy()
        draw_rect.x += int(screen_offset[0])
        draw_rect.y += int(look_y_offset + screen_offset[1])
        
        if self.facing_right:
            screen.blit(self.image_flipped, draw_rect)
        else:
            screen.blit(self.image, draw_rect)      
    
    def reset_position(self, x, y):
        """Reset Hornet to the given position and clear all movement/combat state."""
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.knockback_velocity_x = 0.0
        self.attack_recoil_velocity_x = 0.0
        self.on_ground = False
        self.is_resting = False
        self.rest_timer = 0.0
        self.is_healing = False
        self.heal_channel_timer = 0.0
        self.stun_timer = 0.0
        self._jump_hold_timer = 0.0
        self._jump_held = False
        self._jumping = False
        self._rebound_available = False
        self._wall_jump_timer = 0.0
        self._pressing_down = False
        self.look_hold_timer = 0.0
        self.camera_look_y = 0.0
        self.look_direction = 0
        self.attack_hitbox = None
        self.attack_hitbox_timer = 0.0
        self.attack_hitbox_facing_right = self.facing_right
        self.attack_hitbox_direction = "forward"
        self.attack_hit_mossgrub = False
        self.attack_hit_mossmother = False
        self.attack_recoil_applied = False
        self.is_down_attacking = False
        self.down_attack_momentum_active = False
        self.down_attack_rebound_timer = 0.0
        self.down_attack_jump_lock_timer = 0.0
        self._attack_timer = 0.0
        self._dash_timer = 0.0
        self._special_timer = 0.0
        self._attack_triggered = False
        self._attack_key_down = False
        self._heal_key_down = False
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self._ledge_target_world_x = None
        self.touching_wall_left = False
        self.touching_wall_right = False
        self.camera_x_correction = 0.0