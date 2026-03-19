import pygame
import os
import math
from audio import AudioManager


class MossMother:
    """Boss enemy implementing flying pursuit, curve attack, and stagger behavior."""

    def __init__(self, x, y, screen_width, screen_height):
        """Initialize Moss Mother. """
        image_path = os.path.join(os.path.dirname(__file__), "../assets/images/moss_mother.png")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.25
        self.image = pygame.transform.scale(self.image, (int(source_width * scale_factor), int(source_height * scale_factor)))
        self.image_flipped = pygame.transform.flip(self.image, True, False)

        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)

        self.screen_width = screen_width
        self.screen_height = screen_height

        # Movement state
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.speed = 180.0
        self.gravity = 1800.0
        self.on_ground = False
        self.facing_right = True

        # Flight / gravity control
        self.is_staggered = False
        self.use_gravity = False

        # Attack control
        self.attack_range_x = 260
        self.attack_range_y = 190
        self.attack_cooldown = 1.2
        self.attack_timer = 0.0
        self.is_attacking = False
        self.attack_elapsed = 0.0
        self.attack_duration = 0.85
        self.attack_start = (0.0, 0.0)
        self.attack_target = (0.0, 0.0)
        self.attack_curve_depth = 200.0

        self.attack_burst_count = 0
        self.attack_burst_max = 3
        self.attack_long_cooldown = 30.0
        self.attack_long_cooldown_timer = 0.0

        self.attack_contact_registered = False
        self.phase_through = False
        self.attack_approach_side = 1

        # Multi-phase attack timing
        self.attack_step = 0
        self.attack_phase_time = 0.0
        self.attack_dive_duration = 0.25
        self.attack_vertical_duration = 0.25
        self.attack_ascent_duration = 0.25
        self.attack_mid = (0.0, 0.0)
        self.attack_impact_end = (0.0, 0.0)
        self.attack_reposition_target = (0.0, 0.0)

        # Reposition after each attack
        self.is_repositioning = False
        self.reposition_duration = 0.15
        self.reposition_timer = 0.0
        self.reposition_origin = (0.0, 0.0)
        self.reposition_target = (0.0, 0.0)

        # Stagger / health
        self.max_health = 3000
        self.health = 3000
        self.stagger_count = 0
        self.max_staggers = 2
        self.stagger_thresholds = [int(self.max_health * 0.66), int(self.max_health * 0.33)]
        self.next_stagger_idx = 0
        self.stagger_recovery_time = 0.6
        self.stagger_recovery_timer = 0.0

        # Knockback (same behavior as MossGrub/Hornet)
        self.knockback_velocity_x = 0.0
        self.knockback_strength = 520.0
        self.knockback_decay = 1600.0

        # Constant for pathfinding
        self.cell_size = 64
        self.path_search_radius = 18

        # Camera velocity cache
        self._camera_velocity = [0, 0]

    def _world_position(self, camera_x=0, camera_y=0):
        world_x = self.rect.centerx + int(camera_x)
        world_y = self.rect.centery + int(camera_y)
        return world_x, world_y

    def _find_bfs_next_point(self, start_world, target_world, collision_rects):
        if collision_rects is None:
            return target_world

        def is_point_blocked(px, py):
            # Use the boss collision box for checking.
            candidate = pygame.Rect(0, 0, self.rect.width * 0.8, self.rect.height * 0.8)
            candidate.center = (px, py)
            for cr in collision_rects:
                if candidate.colliderect(cr):
                    return True
            return False

        sx, sy = start_world
        tx, ty = target_world

        start_cell = (int(sx // self.cell_size), int(sy // self.cell_size))
        target_cell = (int(tx // self.cell_size), int(ty // self.cell_size))

        if start_cell == target_cell:
            return target_world

        visited = set([start_cell])
        queue = [start_cell]
        parent = {start_cell: None}

        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

        while queue:
            cx, cy = queue.pop(0)
            if (cx, cy) == target_cell:
                break

            if abs(cx - start_cell[0]) > self.path_search_radius or abs(cy - start_cell[1]) > self.path_search_radius:
                continue

            for nx, ny in [(cx + dx, cy + dy) for dx, dy in neighbors]:
                if (nx, ny) in visited:
                    continue
                visited.add((nx, ny))

                world_x = (nx + 0.5) * self.cell_size
                world_y = (ny + 0.5) * self.cell_size

                if is_point_blocked(world_x, world_y):
                    continue

                parent[(nx, ny)] = (cx, cy)
                queue.append((nx, ny))

                if (nx, ny) == target_cell:
                    queue = []
                    break

        if target_cell not in parent:
            # path not found: aim directly toward player
            return target_world

        # Reconstruct path to first step
        path_node = target_cell
        while parent[path_node] is not None and parent[path_node] != start_cell:
            path_node = parent[path_node]

        next_world = ((path_node[0] + 0.5) * self.cell_size, (path_node[1] + 0.5) * self.cell_size)
        return next_world

    def _start_curve_attack(self, player_world_rect, camera_x=0, camera_y=0):
        self.is_attacking = True
        self.attack_timer = self.attack_cooldown
        self.attack_step = 0
        self.attack_phase_time = 0.0
        self.attack_contact_registered = False

        self.attack_start = self._world_position(camera_x=camera_x, camera_y=camera_y)
        player_x = player_world_rect.centerx
        player_y = player_world_rect.centery

        # side offset relative to player horizontally
        side_offset = self.attack_start[0] - player_x
        if abs(side_offset) < 40:
            side_offset = 140 if self.attack_approach_side >= 0 else -140

        self.attack_approach_side = -1 if side_offset < 0 else 1

        # Dive: same x as start, down toward near player height
        dive_y = min(player_y - 40, self.attack_start[1] + 120)
        self.attack_mid = (self.attack_start[0], dive_y)

        # Vertical path through Hornet to opponent side x (mirror relative to player)
        target_x = player_x - side_offset
        self.attack_impact_end = (target_x, self.attack_start[1])

        # Ascend path, just above the opponent side for next attack
        self.attack_reposition_target = (target_x, player_y - 220)

        self.attack_burst_count += 1
        if self.attack_burst_count >= self.attack_burst_max:
            self.attack_long_cooldown_timer = self.attack_long_cooldown
            self.attack_burst_count = 0
    def _end_attack(self, player_world_rect):
        self.is_attacking = False
        self.attack_elapsed = 0.0
        self.attack_timer = 0.0

        self.phase_through = self.attack_contact_registered

        # set up smooth reposition for next attack
        self.is_repositioning = True
        self.reposition_timer = self.reposition_duration
        self.reposition_origin = (self.rect.centerx, self.rect.centery)

        if player_world_rect is not None:
            # reposition to the opposite side of the direction we came from.
            opposite_side = -self.attack_approach_side
            self.reposition_target = (player_world_rect.centerx + opposite_side * 220,
                                      player_world_rect.centery - 220)
        else:
            self.reposition_target = self.reposition_origin

        self.attack_contact_registered = False

    def _update_curve_attack(self, dt, player_world_rect=None, camera_x=0, camera_y=0):
        self.attack_phase_time += dt

        if self.attack_step == 0:
            # Dive from start to mid.
            t = min(1.0, self.attack_phase_time / self.attack_dive_duration)
            sx, sy = self.attack_start
            mx, my = self.attack_mid
            x = sx + (mx - sx) * t
            y = sy + (my - sy) * t + (self.attack_curve_depth * (t ** 2) * (1 - t))
            self.rect.centerx = int(x - camera_x)
            self.rect.centery = int(y - camera_y)
            if t >= 1.0:
                self.attack_step = 1
                self.attack_phase_time = 0.0

        elif self.attack_step == 1:
            # Straight attack to mirrored side (through Hornet)
            t = min(1.0, self.attack_phase_time / self.attack_vertical_duration)
            mx, my = self.attack_mid
            ix, iy = self.attack_impact_end
            x = mx + (ix - mx) * t
            y = my + (iy - my) * t
            self.rect.centerx = int(x - camera_x)
            self.rect.centery = int(y - camera_y)

            if player_world_rect and not self.attack_contact_registered:
                world_hitbox = self.rect.copy()
                world_hitbox.x += int(camera_x)
                world_hitbox.y += int(camera_y)
                if world_hitbox.colliderect(player_world_rect):
                    self.attack_contact_registered = True
                    self.phase_through = True

            if t >= 1.0:
                self.attack_step = 2
                self.attack_phase_time = 0.0

        elif self.attack_step == 2:
            # Ascent diagonally to next attack starting point on other side.
            t = min(1.0, self.attack_phase_time / self.attack_ascent_duration)
            ix, iy = self.attack_impact_end
            tx, ty = self.attack_reposition_target
            x = ix + (tx - ix) * t
            y = iy + (ty - iy) * t - (self.attack_curve_depth / 2.0 * (1 - (2 * (t - 0.5)) ** 2))
            self.rect.centerx = int(x - camera_x)
            self.rect.centery = int(y - camera_y)

            if t >= 1.0:
                self.attack_step = 0
                self.attack_phase_time = 0.0
                self.is_attacking = False
                self.attack_timer = 0.0


    def _update_reposition(self, dt):
        if not self.is_repositioning:
            return

        self.reposition_timer -= dt
        t = 1.0 - max(0.0, self.reposition_timer) / self.reposition_duration

        ox, oy = self.reposition_origin
        tx, ty = self.reposition_target

        self.rect.centerx = int(ox + (tx - ox) * t)
        self.rect.centery = int(oy + (ty - oy) * t)

        if self.reposition_timer <= 0.0:
            self.is_repositioning = False
            self.rect.centerx = int(tx)
            self.rect.centery = int(ty)

    def _update_flight_path(self, dt, player_world_rect, collision_rects, camera_x=0, camera_y=0, min_x=0, max_x=None):
        if player_world_rect is None:
            return

        world_x, world_y = self._world_position(camera_x=camera_x, camera_y=camera_y)

        # Pathfind toward player position
        target_world = self._find_bfs_next_point((world_x, world_y), (player_world_rect.centerx, player_world_rect.centery), collision_rects)

        dx = target_world[0] - world_x
        dy = target_world[1] - world_y
        dist = math.hypot(dx, dy)
        if dist > 1e-3:
            norm_x = dx / dist
            norm_y = dy / dist
        else:
            norm_x = 0.0
            norm_y = 0.0

        self.velocity_x = norm_x * self.speed
        self.velocity_y = norm_y * self.speed

        self.rect.x += int(self.velocity_x * dt)
        self.rect.y += int(self.velocity_y * dt)

        if self.velocity_x > 0:
            self.facing_right = True
        elif self.velocity_x < 0:
            self.facing_right = False

        if max_x is not None:
            if self.rect.centerx >= max_x:
                self.facing_right = False
            elif self.rect.centerx <= min_x:
                self.facing_right = True

    def _apply_gravity_and_collision(self, dt, collision_rects, camera_x=0, camera_y=0):
        # Falling behavior during stagger state.
        self.velocity_y += self.gravity * dt
        self.rect.y += int(self.velocity_y * dt)

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
                landed = True

        if not landed:
            self.on_ground = False

        # Prevent flying above top of screen
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity_y = 0

        # Ground collision clamp bottom far off-screen
        if self.rect.bottom > self.screen_height + 400:
            self.rect.bottom = self.screen_height + 400
            self.velocity_y = 0
            self.on_ground = True

        return landed

    def take_damage(self, damage, knockback_direction=0):
        if damage <= 0:
            return

        self.health = max(0, self.health - damage)

        if knockback_direction < 0:
            self.knockback_velocity_x = -self.knockback_strength
        elif knockback_direction > 0:
            self.knockback_velocity_x = self.knockback_strength

        if self.next_stagger_idx < len(self.stagger_thresholds) and self.health <= self.stagger_thresholds[self.next_stagger_idx]:
            self.next_stagger_idx += 1
            self.is_staggered = True
            self.use_gravity = True
            self.stagger_recovery_timer = self.stagger_recovery_time
            self.stagger_count += 1

    def reset_position(self, x, y):
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.is_staggered = False
        self.use_gravity = False
        self.is_attacking = False
        self.attack_timer = 0.0
        self.attack_elapsed = 0.0
        self.attack_burst_count = 0
        self.attack_long_cooldown_timer = 0.0
        self.next_stagger_idx = 0
        self.stagger_count = 0
        self.health = self.max_health

    def update(self, min_x, max_x, dt, collision_rects=None, camera_x=0, camera_y=0, camera_dx=0, camera_dy=0, player_world_rect=None):
        self.rect.x -= int(camera_dx)
        self.rect.y -= int(camera_dy)

        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

        if self.attack_timer > 0.0:
            self.attack_timer = max(0.0, self.attack_timer - dt)

        if self.is_staggered:
            landed = self._apply_gravity_and_collision(dt, collision_rects, camera_x=camera_x, camera_y=camera_y)
            if landed:
                self.stagger_recovery_timer -= dt
                if self.stagger_recovery_timer <= 0.0:
                    self.is_staggered = False
                    self.use_gravity = False
                    self.on_ground = False
            return

        # Decrement long cooldown timer each frame
        if self.attack_long_cooldown_timer > 0.0:
            self.attack_long_cooldown_timer = max(0.0, self.attack_long_cooldown_timer - dt)

        # Forced gravity flag may be enabled during stagger only.
        if not self.use_gravity:
            # Flying behavior
            if self.is_attacking:
                self._update_curve_attack(dt, player_world_rect=player_world_rect, camera_x=camera_x, camera_y=camera_y)
                return

            if player_world_rect is not None:
                world_x = self.rect.centerx + int(camera_x)
                world_y = self.rect.centery + int(camera_y)
                diff_x = player_world_rect.centerx - world_x
                diff_y = player_world_rect.centery - world_y

                can_attack = (self.attack_timer <= 0.0 and self.attack_long_cooldown_timer <= 0.0)
                if abs(diff_x) <= self.attack_range_x and abs(diff_y) <= self.attack_range_y and can_attack:
                    self._start_curve_attack(player_world_rect, camera_x=camera_x, camera_y=camera_y)
                    return

            self._update_flight_path(dt, player_world_rect, collision_rects, camera_x=camera_x, camera_y=camera_y, min_x=min_x, max_x=max_x)

            # add knockback to flight.
            self.rect.x += int(self.knockback_velocity_x * dt)

            # Keep the boss in patrol bounds like MossGrub
            if self.rect.centerx >= max_x:
                self.facing_right = False
            elif self.rect.centerx <= min_x:
                self.facing_right = True

        else:
            # Should not happen outside stagger state, but keep safe fallback.
            self._apply_gravity_and_collision(dt, collision_rects, camera_x=camera_x, camera_y=camera_y)

    def draw(self, screen, look_y_offset=0):
        draw_rect = self.rect.copy()
        draw_rect.y += look_y_offset

        if self.facing_right:
            screen.blit(self.image, draw_rect)
        else:
            screen.blit(self.image_flipped, draw_rect)
