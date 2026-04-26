import pygame
from animation import Animation
from audio import AudioManager
from asset_paths import resolve_image_path
import config


def _apply_white_overlay(surface, intensity):
    """Return a copy of surface blended with white at the given intensity (0-255)."""
    result = surface.copy()
    white_layer = pygame.Surface(surface.get_size())
    white_layer.fill((intensity, intensity, intensity))
    result.blit(white_layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return result


class MossGrub:
    """Basic patrol enemy that walks back and forth."""
    
    def __init__(self, x, y, screen_width, screen_height):
        """Create a MossGrub at the given position."""
        image_path = resolve_image_path("spritesheet/enemy/mossgrub.png")
        frame_width = 128
        frame_height = 101
        anim_scale = 0.45 * config.scale_y * config.ENEMY_SCALE_MULTIPLIER
        self.animation = Animation(
            image_path,
            frame_width=frame_width,
            frame_height=frame_height,
            scale=anim_scale,
        )
        self._load_mossgrub_animation()
        self.animations = self.animation.animations
        self.display_facing_right = False
        self.turn_target_facing_right = False
        self.current_animation_name = "move_left"
        self.animation.set_animation(self.current_animation_name)
        self.image = self.animation.get_current_frame()
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
        self.is_dying = False
        self.death_landed = False
        self.death_finished = False
        self.death_launch_velocity_y = -620.0
        
        # Audio manager instance
        self.audio_manager = AudioManager()
        
        # Camera velocity cache to avoid tuple creation each frame
        self._camera_velocity = [0, 0]
        
        # Health system
        self.max_health = 2
        self.health = 2

        # Per-animation draw offsets for easy visual tuning.
        self.animation_draw_offsets = {
            "default": (0, 0),
            "turn_right": (0, 0),
            "turn_left": (0, 0),
            "move_right": (0, 0),
            "move_left": (0, 0),
            "death_air_right": (0, 0),
            "death_air_left": (0, 0),
            "death_land_right": (0, 0),
            "death_land_left": (0, 0),
        }

        # Sub-pixel accumulator for horizontal movement precision.
        self._frac_x = 0.0
        self.hit_white_timer = 0.0
    
    def _load_mossgrub_animation(self):
        """Load mossgrub animations from spritesheet."""
        self.animation.add_animation("turn_right", row=0, start_col=0, num_frames=3, speed=0.08, loop=False)
        self.animation.add_animation("turn_left", row=0, start_col=0, num_frames=3, flip_x=True, speed=0.08, loop=False)
        self.animation.add_animation("move_right", row=0, start_col=3, num_frames=5, speed=0.1, loop=True)
        self.animation.add_animation("move_left", row=0, start_col=3, num_frames=5, flip_x=True, speed=0.1, loop=True)
        self.animation.add_animation("death_air_right", row=1, start_col=0, num_frames=4, speed=0.09, loop=False)
        self.animation.add_animation("death_air_left", row=1, start_col=0, num_frames=4, flip_x=True, speed=0.09, loop=False)
        self.animation.add_animation("death_land_right", row=1, start_col=4, num_frames=3, speed=0.1, loop=False)
        self.animation.add_animation("death_land_left", row=1, start_col=4, num_frames=3, flip_x=True, speed=0.1, loop=False)

    def _set_animation(self, name, reset=False):
        """Switch to the named animation only if it differs from the current one."""
        if self.current_animation_name != name or reset:
            self.current_animation_name = name
            self.animation.set_animation(name, reset=True)
            self.image = self.animation.get_current_frame()

    def _advance_animation(self, dt):
        """
        Tick the animation and update the display image.

        Args:
            dt (float): Elapsed time in seconds since the last frame.

        Returns:
            bool: True if the current animation has finished.
        """
        self.animation.update(dt)
        current_frame = self.animation.get_current_frame()
        if current_frame is not None:
            self.image = current_frame
        return self.animation.is_finished()

    def _update_animation(self, dt):
        """
        Run the full animation state machine for movement, turns, and death.

        Args:
            dt (float): Elapsed time in seconds since the last frame.
        """
        if self.is_dying:
            if self.facing_right == 1:
                self.display_facing_right = True
            elif self.facing_right == -1:
                self.display_facing_right = False

            facing_suffix = "right" if self.display_facing_right else "left"
            death_air_name = f"death_air_{facing_suffix}"
            death_land_name = f"death_land_{facing_suffix}"

            if self.death_finished:
                self._set_animation(death_land_name)
                self.animation.current_frame = self.animation.get_animation_frame_count(death_land_name) - 1
                self.image = self.animation.get_current_frame()
                return

            if self.death_landed:
                if self.current_animation_name != death_land_name:
                    self._set_animation(death_land_name, reset=True)
                if self._advance_animation(dt):
                    self.death_finished = True
                    self.animation.current_frame = self.animation.get_animation_frame_count(death_land_name) - 1
                    self.image = self.animation.get_current_frame()
                return

            if self.current_animation_name != death_air_name:
                self._set_animation(death_air_name, reset=True)
            self._advance_animation(dt)
            return

        desired_display_facing_right = self.facing_right == 1
        if desired_display_facing_right != self.display_facing_right:
            self.turn_target_facing_right = desired_display_facing_right
            turn_name = "turn_right" if self.turn_target_facing_right else "turn_left"
            if self.current_animation_name != turn_name:
                self._set_animation(turn_name, reset=True)
            if self._advance_animation(dt):
                self.display_facing_right = self.turn_target_facing_right
                move_name = "move_right" if self.display_facing_right else "move_left"
                self._set_animation(move_name, reset=True)
            return

        move_name = "move_right" if self.display_facing_right else "move_left"
        self._set_animation(move_name)
        self._advance_animation(dt)

    def take_damage(self, damage, knockback_direction=0):
        """Apply damage and knockback to the mossgrub."""
        if damage <= 0:
            return
        else:
            self.hit_white_timer = 0.12
            self.health = max(0, self.health - damage)
            if knockback_direction < 0:
                self.knockback_velocity_x = -self.knockback_strength
            elif knockback_direction > 0:
                self.knockback_velocity_x = self.knockback_strength

            if self.health <= 0 and not self.is_dying:
                self.is_dying = True
                self.death_landed = False
                self.death_finished = False
                self.on_ground = False
                self.velocity_y = self.death_launch_velocity_y
                if knockback_direction < 0:
                    self.facing_right = -1
                elif knockback_direction > 0:
                    self.facing_right = 1

    def update(self, min_x, max_x, dt, collision_rects=None, camera_x=0, camera_y=0, camera_dx=0, camera_dy=0):
        """Update position, physics, and patrol movement."""
        # Compensate for camera movement so mossgrub stays at its world position.
        self.rect.x -= int(camera_dx)
        self.rect.y -= int(camera_dy)
        if self.hit_white_timer > 0.0:
            self.hit_white_timer = max(0.0, self.hit_white_timer - dt)

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
        patrol_speed = 0.0 if self.is_dying else self.speed * self.facing_right
        horizontal_move = (patrol_speed + self.knockback_velocity_x) * dt
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
                    if not self.is_dying:
                        self.facing_right = -1
                else:
                    world_rect.left = cr.right
                    if not self.is_dying:
                        self.facing_right = 1

                self.rect.x = int(world_rect.x - camera_x)

        # Check for boundaries and reverse direction.
        if not self.is_dying:
            if self.rect.centerx >= max_x:
                self.facing_right = -1
            elif self.rect.centerx <= min_x:
                self.facing_right = 1
        
        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

        if self.is_dying and landed:
            self.death_landed = True
            self.knockback_velocity_x = 0.0
            self._frac_x = 0.0

        self._update_animation(dt)

    def _get_animation_draw_offset(self):
        """Return the configured draw offset for the current animation."""
        return self.animation_draw_offsets.get(self.current_animation_name, self.animation_draw_offsets.get("default", (0, 0)))

    def get_draw_rect(self, look_y_offset=0, screen_offset=(0, 0)):
        """Return the final draw rect after camera/look/screen offset tuning."""
        draw_rect = self.rect.copy()
        draw_rect.x += int(screen_offset[0])
        draw_rect.y += int(look_y_offset + screen_offset[1])
        offset_x, offset_y = self._get_animation_draw_offset()
        draw_rect.x += int(offset_x)
        draw_rect.y += int(offset_y)
        return draw_rect

    def draw(self, screen, look_y_offset=0, screen_offset=(0, 0)):
        """Draw the mossgrub on screen."""
        draw_surf = _apply_white_overlay(self.image, int(255 * self.hit_white_timer / 0.12)) if self.hit_white_timer > 0.0 else self.image
        screen.blit(draw_surf, self.get_draw_rect(look_y_offset=look_y_offset, screen_offset=screen_offset))
    
    def reset_position(self, x, y):
        """Reset the mossgrub to the given spawn position."""
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.is_dying = False
        self.death_landed = False
        self.death_finished = False
        self.facing_right = -1
        self.display_facing_right = False
        self.turn_target_facing_right = False
        self.knockback_velocity_x = 0.0
        self._frac_x = 0.0
        self.health = self.max_health
        self._set_animation("move_left", reset=True)