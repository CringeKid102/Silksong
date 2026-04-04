import pygame
import os
from audio import AudioManager

class MossGrub:
    """Basic patrol enemy that walks back and forth."""
    
    def __init__(self, x, y, screen_width, screen_height):
        """Create a MossGrub at the given position."""
        # Load and scale enemy image
        image_path = os.path.join(os.path.dirname(__file__), "../assets/images/mossgrub.png")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.45
        scaled_size = (int(source_width * scale_factor), int(source_height * scale_factor))
        self.image = pygame.transform.scale(self.image, scaled_size)
        self.image_flipped = pygame.transform.flip(self.image, True, False)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.rect.midbottom = (x, y)

        # Knockback
        self.knockback_velocity_x = 0.0
        self.knockback_strength = 560.0
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
        
        # Facing direction (for future sprite flipping)
        self.facing_right = 1
        
        # Audio manager instance
        self.audio_manager = AudioManager()
        
        # Camera velocity cache to avoid tuple creation each frame
        self._camera_velocity = [0, 0]
        
        # Health system
        self.max_health = 1000
        self.health = 1000

        # Sub-pixel accumulator for horizontal movement precision.
        self._frac_x = 0.0
    
    def _load_mossgrub_animation(self):
        """Load mossgrub animations from spritesheet. Placeholder for future use."""
        pass

    def take_damage(self, damage, knockback_direction=0):
        """Apply damage and knockback to the mossgrub."""
        if damage <= 0:
            return
        else:
            self.health = max(0, self.health - damage)
            if knockback_direction < 0:
                self.knockback_velocity_x = -self.knockback_strength
            elif knockback_direction > 0:
                self.knockback_velocity_x = self.knockback_strength

    def update(self, min_x, max_x, dt, collision_rects=None, camera_x=0, camera_y=0, camera_dx=0, camera_dy=0):
        """Update position, physics, and patrol movement."""
        # Compensate for camera movement so mossgrub stays at its world position.
        self.rect.x -= int(camera_dx)
        self.rect.y -= int(camera_dy)

        # Apply gravity
        self.velocity_y += self.gravity * dt
        self.rect.y += self.velocity_y * dt

        landed = False
        if collision_rects:
            world_rect = self.rect.copy()
            world_rect.x += int(camera_x)
            world_rect.y += int(camera_y)
            previous_bottom = world_rect.bottom - (self.velocity_y * dt)

            # Ceiling collision on elevated platforms
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
                    # Only horizontal platforms count as floors.
                    if ground_rect.width < ground_rect.height:
                        continue
                    if world_rect.right <= ground_rect.left or world_rect.left >= ground_rect.right:
                        continue
                    if previous_bottom <= ground_rect.top and world_rect.bottom >= ground_rect.top:
                        if landing_top is None or ground_rect.top < landing_top:
                            landing_top = ground_rect.top

                # Fallback: if already slightly inside/near a platform, snap only to a
                # nearby floor instead of a far-away upper platform.
                if landing_top is None:
                    recovery_top = None
                    recovery_distance = None
                    for ground_rect in collision_rects:
                        if ground_rect.width < ground_rect.height:
                            continue
                        if world_rect.right <= ground_rect.left or world_rect.left >= ground_rect.right:
                            continue

                        distance_to_top = abs(world_rect.bottom - ground_rect.top)
                        if distance_to_top > 24:
                            continue

                        if recovery_distance is None or distance_to_top < recovery_distance or (
                            distance_to_top == recovery_distance and ground_rect.top < recovery_top
                        ):
                            recovery_top = ground_rect.top
                            recovery_distance = distance_to_top

                    if recovery_top is not None:
                        landing_top = recovery_top

            if landing_top is not None:
                world_rect.bottom = int(landing_top)
                self.rect.y = int(world_rect.y - camera_y)
                self.velocity_y = 0
                self.on_ground = True
                landed = True

        if not landed:
            if collision_rects:
                self.on_ground = False
            else:
                self.on_ground = False

        # Do not clamp to the top of the screen here. MossGrub uses screen-space
        # rects derived from world position, so forcing `top = 0` pins it to the
        # camera when it moves above the visible view.

        # Combine patrol motion with temporary knockback push.
        horizontal_move = (self.speed * self.facing_right + self.knockback_velocity_x) * dt
        self._frac_x += horizontal_move
        move_px = int(self._frac_x)
        self._frac_x -= move_px
        self.rect.x += move_px

        # Resolve horizontal collisions against platform side walls.
        if collision_rects:
            world_rect = self.rect.copy()
            world_rect.x += int(camera_x)
            world_rect.y += int(camera_y)

            for cr in collision_rects:
                # Skip the giant infinite ground plane – it has no side walls.
                if cr.width > 5000:
                    continue
                if not world_rect.colliderect(cr):
                    continue
                # Ignore floor contact from above; this is for wall blocking only.
                if world_rect.bottom <= cr.top + 4:
                    continue

                overlap_right = world_rect.right - cr.left
                overlap_left = cr.right - world_rect.left
                overlap_bottom = world_rect.bottom - cr.top
                overlap_top = cr.bottom - world_rect.top

                min_h = min(overlap_right, overlap_left)
                min_v = min(overlap_bottom, overlap_top)

                # Only resolve when horizontal penetration is the limiting axis.
                if min_h >= min_v:
                    continue

                if overlap_right < overlap_left:
                    world_rect.right = cr.left
                    self.facing_right = -1
                else:
                    world_rect.left = cr.right
                    self.facing_right = 1

                self.rect.x = int(world_rect.x - camera_x)

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
        """Draw the mossgrub on screen."""
        # Calculate draw position with look offset
        draw_rect = self.rect.copy()
        draw_rect.y += look_y_offset
        
        # Flip image based on facing direction
        if self.facing_right == 1:
            screen.blit(self.image, draw_rect)
        else:
            screen.blit(self.image_flipped, draw_rect)
    
    def reset_position(self, x, y):
        """Reset the mossgrub to the given spawn position."""
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False