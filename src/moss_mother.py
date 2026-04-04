import pygame
import os
import math
from audio import AudioManager
import config


class MossMother:
    """Flying boss enemy with pursuit, curve attacks, and stagger phases."""

    def __init__(self, x, y, screen_width, screen_height):
        """Create the Moss Mother boss at the given position."""
        image_path = os.path.join(os.path.dirname(__file__), "../assets/images/moss_mother.png")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.45
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

        # Arena encounter state
        self.is_engaged = False
        self.spawn_top_padding = 48
        self.attack_lane_margin = 72
        self.spawn_delay = 3.0
        self.spawn_delay_timer = 0.0
        self.has_spawned_in_arena = False

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

        self.attack_start = (float(self.rect.centerx), float(self.rect.centery))
        self.attack_entry_origin = (float(self.rect.centerx), float(self.rect.centery))
        self.attack_target = (0.0, 0.0)
        self.attack_curve_depth = 180.0
        self.attack_burst_count = 0
        self.attack_burst_max = 3
        self.attack_long_cooldown = 30.0
        self.attack_long_cooldown_timer = 0.0
        self.attack_contact_registered = False
        self.phase_through = False
        self.attack_approach_side = 1

        # Secondary cry attack
        self.is_crying = False
        self.cry_duration = 1.0
        self.cry_timer = 0.0
        self.cry_cooldown = 60.0
        self.cry_cooldown_timer = 0.0
        self._cry_attack_triggered = False
        self.attack_type_separation = 10.0
        self.curve_attack_lockout_timer = 0.0
        self.cry_attack_lockout_timer = 0.0

        # Multi-phase attack timing
        self.attack_step = 0
        self.attack_phase_time = 0.0
        self.attack_dive_duration = 0.3
        self.attack_vertical_duration = 0.55
        self.attack_ascent_duration = 0.25
        self.attack_mid = (0.0, 0.0)
        self.attack_impact_end = (0.0, 0.0)
        self.attack_reposition_target = (float(self.rect.centerx), float(self.rect.centery))

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

        # Knockback
        self.knockback_velocity_x = 0.0
        self.knockback_strength = 560.0
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

    def _get_arena_spawn_point(self, arena_rect):
        """Return the idle spawn position at the top-middle of the arena."""
        return (
            int(arena_rect.centerx),
            int(arena_rect.top + self.rect.height // 2 + self.spawn_top_padding),
        )

    def _get_attack_lane_points(self, arena_rect):
        """Return the side and floor lane positions used for the arena sweep attack."""
        edge_padding = max(self.rect.width // 2 + 24, self.attack_lane_margin)
        left_x = int(arena_rect.left + edge_padding)
        right_x = int(arena_rect.right - edge_padding)
        middle_y = int(arena_rect.centery)
        floor_y = int(arena_rect.bottom - self.rect.height // 2 - 28)
        return left_x, right_x, middle_y, floor_y

    def _set_world_center(self, world_x, world_y, camera_x=0, camera_y=0):
        """Place the boss using world coordinates while keeping its rect in screen space."""
        self.rect.centerx = int(world_x - camera_x)
        self.rect.centery = int(world_y - camera_y)

    def start_cry_attack(self):
        """Begin the cry attack and emit a one-shot trigger for the game to handle hazards."""
        if self.is_attacking or self.is_crying:
            return False
        self.is_crying = True
        self.cry_timer = self.cry_duration
        self.cry_cooldown_timer = self.cry_cooldown
        self._cry_attack_triggered = True
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.attack_contact_registered = False
        self.phase_through = False
        return True

    def consume_cry_attack_trigger(self):
        """Return True once when the cry attack begins."""
        triggered = self._cry_attack_triggered
        self._cry_attack_triggered = False
        return triggered

    def _resolve_horizontal_collisions(self, collision_rects, camera_x=0, camera_y=0):
        if not collision_rects:
            return

        world_rect = self.rect.copy()
        world_rect.x += int(camera_x)
        world_rect.y += int(camera_y)

        for cr in collision_rects:
            # Match Hornet/MossGrub wall behavior; the huge ground rect is floor-only.
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
                world_rect.right = cr.left
                self.facing_right = False
            else:
                world_rect.left = cr.right
                self.facing_right = True

            self.rect.x = int(world_rect.x - camera_x)

    def _resolve_vertical_collisions(self, collision_rects, camera_x=0, camera_y=0):
        if not collision_rects:
            return

        world_rect = self.rect.copy()
        world_rect.x += int(camera_x)
        world_rect.y += int(camera_y)

        landed = False
        for cr in collision_rects:
            if not world_rect.colliderect(cr):
                continue

            overlap_bottom = world_rect.bottom - cr.top
            overlap_top = cr.bottom - world_rect.top

            if overlap_bottom <= overlap_top:
                world_rect.bottom = cr.top
                landed = True
            else:
                world_rect.top = cr.bottom

            self.rect.y = int(world_rect.y - camera_y)
            self.velocity_y = 0.0

        self.on_ground = landed

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

    def _start_curve_attack(self, player_world_rect, arena_rect, camera_x=0, camera_y=0):
        """Start a three-part arena sweep: half-parabola down, floor dash, then vertical rise."""
        if arena_rect is None:
            return

        self.is_attacking = True
        self.attack_timer = self.attack_cooldown
        self.attack_step = 0
        self.attack_phase_time = 0.0
        self.attack_contact_registered = False
        self.phase_through = False
        self.attack_burst_count = 0

        current_world_x, current_world_y = self._world_position(camera_x=camera_x, camera_y=camera_y)
        left_x, right_x, middle_y, floor_y = self._get_attack_lane_points(arena_rect)

        if abs(current_world_x - left_x) <= abs(current_world_x - right_x):
            start_edge_x, end_edge_x = left_x, right_x
            self.attack_approach_side = -1
            self.facing_right = True
        else:
            start_edge_x, end_edge_x = right_x, left_x
            self.attack_approach_side = 1
            self.facing_right = False

        self.attack_entry_origin = (current_world_x, current_world_y)
        self.attack_start = (start_edge_x, middle_y)
        self.attack_mid = ((left_x + right_x) / 2.0, floor_y)
        self.attack_impact_end = (end_edge_x, floor_y)
        self.attack_reposition_target = (end_edge_x, middle_y)
        self.attack_curve_depth = max(0.0, floor_y - middle_y)

        # Begin the attack already aligned at the nearest edge-middle point.
        self._set_world_center(self.attack_start[0], self.attack_start[1], camera_x=camera_x, camera_y=camera_y)
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

    def _update_curve_attack(self, dt, player_world_rect=None, camera_x=0, camera_y=0, collision_rects=None, arena_rect=None):
        """Advance the three-part sweep: half-parabola down, horizontal floor run, then vertical rise."""
        if arena_rect is None:
            self.is_attacking = False
            return

        self.attack_phase_time += dt

        def register_contact_once():
            if player_world_rect and not self.attack_contact_registered:
                world_hitbox = self.rect.copy()
                world_hitbox.x += int(camera_x)
                world_hitbox.y += int(camera_y)
                if world_hitbox.colliderect(player_world_rect):
                    self.attack_contact_registered = True
                    self.phase_through = True

        if self.attack_step == 0:
            # Part 1: half open-up parabola from edge-middle down to the arena floor lane.
            t = min(1.0, self.attack_phase_time / self.attack_dive_duration)
            sx, sy = self.attack_start
            mx, my = self.attack_mid
            x = sx + (mx - sx) * t
            y = my - (my - sy) * ((1.0 - t) ** 2)
            self._set_world_center(x, y, camera_x=camera_x, camera_y=camera_y)
            self.facing_right = mx >= sx
            register_contact_once()

            if t >= 1.0:
                self.attack_step = 1
                self.attack_phase_time = 0.0
                self.attack_contact_registered = False
                self.phase_through = False

        elif self.attack_step == 1:
            # Part 2: move straight horizontally near the arena floor.
            t = min(1.0, self.attack_phase_time / self.attack_vertical_duration)
            mx, my = self.attack_mid
            ex, ey = self.attack_impact_end
            x = mx + (ex - mx) * t
            y = my
            self._set_world_center(x, y, camera_x=camera_x, camera_y=camera_y)
            self.facing_right = ex >= mx
            register_contact_once()

            if t >= 1.0:
                self.attack_step = 2
                self.attack_phase_time = 0.0
                self.attack_contact_registered = False
                self.phase_through = False

        elif self.attack_step == 2:
            # Part 3: move vertically up to the opposite edge-middle point.
            t = min(1.0, self.attack_phase_time / self.attack_ascent_duration)
            ex, ey = self.attack_impact_end
            rx, ry = self.attack_reposition_target
            x = ex
            y = ey + (ry - ey) * t
            self._set_world_center(x, y, camera_x=camera_x, camera_y=camera_y)
            self.facing_right = rx >= self.attack_start[0]
            register_contact_once()

            if t >= 1.0:
                self.attack_burst_count += 1
                if self.attack_burst_count >= self.attack_burst_max:
                    self.attack_step = 0
                    self.attack_phase_time = 0.0
                    self.is_attacking = False
                    self.attack_timer = 0.0
                    self.attack_long_cooldown_timer = self.attack_long_cooldown
                    self.cry_attack_lockout_timer = max(self.cry_attack_lockout_timer, self.attack_type_separation)
                    self.attack_contact_registered = False
                    self.phase_through = False
                else:
                    previous_start_x = self.attack_start[0]
                    next_start_x = self.attack_reposition_target[0]
                    middle_y = self.attack_reposition_target[1]
                    floor_y = self.attack_impact_end[1]
                    self.attack_start = (next_start_x, middle_y)
                    self.attack_mid = ((next_start_x + previous_start_x) / 2.0, floor_y)
                    self.attack_impact_end = (previous_start_x, floor_y)
                    self.attack_reposition_target = (previous_start_x, middle_y)
                    self.attack_phase_time = 0.0
                    self.attack_step = 0
                    self.attack_contact_registered = False
                    self.phase_through = False
            

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
        self._resolve_horizontal_collisions(collision_rects, camera_x=camera_x, camera_y=camera_y)

        self.rect.y += int(self.velocity_y * dt)
        self._resolve_vertical_collisions(collision_rects, camera_x=camera_x, camera_y=camera_y)

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

    def take_damage(self, damage, knockback_direction=0, apply_knockback=True):
        if damage <= 0:
            return

        self.health = max(0, self.health - damage)

        if apply_knockback and not self.is_attacking:
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
        self.attack_step = 0
        self.attack_phase_time = 0.0
        self.attack_contact_registered = False
        self.phase_through = False
        self.is_repositioning = False
        self.is_engaged = False
        self.spawn_delay_timer = 0.0
        self.has_spawned_in_arena = False
        self.is_crying = False
        self.cry_timer = 0.0
        self.cry_cooldown_timer = 0.0
        self._cry_attack_triggered = False
        self.curve_attack_lockout_timer = 0.0
        self.cry_attack_lockout_timer = 0.0
        self.next_stagger_idx = 0
        self.stagger_count = 0
        self.health = self.max_health

    def update(self, min_x, max_x, dt, collision_rects=None, camera_x=0, camera_y=0, camera_dx=0, camera_dy=0, player_world_rect=None, arena_rect=None):
        self.rect.x -= int(camera_dx)
        self.rect.y -= int(camera_dy)

        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

        if self.attack_timer > 0.0:
            self.attack_timer = max(0.0, self.attack_timer - dt)
        if self.cry_cooldown_timer > 0.0:
            self.cry_cooldown_timer = max(0.0, self.cry_cooldown_timer - dt)
        if self.curve_attack_lockout_timer > 0.0:
            self.curve_attack_lockout_timer = max(0.0, self.curve_attack_lockout_timer - dt)
        if self.cry_attack_lockout_timer > 0.0:
            self.cry_attack_lockout_timer = max(0.0, self.cry_attack_lockout_timer - dt)

        player_in_arena = bool(arena_rect and player_world_rect and arena_rect.colliderect(player_world_rect))

        if arena_rect is not None and not self.is_engaged:
            if player_in_arena and not self.has_spawned_in_arena:
                self.spawn_delay_timer += dt
            elif not player_in_arena and not self.has_spawned_in_arena:
                self.spawn_delay_timer = 0.0

            if not self.has_spawned_in_arena:
                if self.spawn_delay_timer < self.spawn_delay:
                    return
                spawn_x, spawn_y = self._get_arena_spawn_point(arena_rect)
                self._set_world_center(spawn_x, spawn_y, camera_x=camera_x, camera_y=camera_y)
                self.velocity_x = 0.0
                self.velocity_y = 0.0
                self.on_ground = False
                self.has_spawned_in_arena = True

            if not player_in_arena:
                return

            self.is_engaged = True
            self.attack_timer = min(self.attack_timer, 0.35)

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

        if self.is_crying:
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            self.cry_timer = max(0.0, self.cry_timer - dt)
            if self.cry_timer <= 0.0:
                self.is_crying = False
                self.curve_attack_lockout_timer = max(self.curve_attack_lockout_timer, self.attack_type_separation)
            return

        # Forced gravity flag may be enabled during stagger only.
        if not self.use_gravity:
            if (
                player_world_rect is not None
                and player_in_arena
                and self.cry_cooldown_timer <= 0.0
                and self.cry_attack_lockout_timer <= 0.0
                and not self.is_attacking
            ):
                if self.start_cry_attack():
                    return

            if self.is_attacking:
                self._update_curve_attack(
                    dt,
                    player_world_rect=player_world_rect,
                    camera_x=camera_x,
                    camera_y=camera_y,
                    collision_rects=collision_rects,
                    arena_rect=arena_rect,
                )
                return

            if player_world_rect is not None and player_in_arena:
                can_attack = (
                    self.attack_timer <= 0.0
                    and self.attack_long_cooldown_timer <= 0.0
                    and self.curve_attack_lockout_timer <= 0.0
                    and not self.is_crying
                )
                if can_attack:
                    self._start_curve_attack(player_world_rect, arena_rect, camera_x=camera_x, camera_y=camera_y)
                    return

                self._update_flight_path(dt, player_world_rect, collision_rects, camera_x=camera_x, camera_y=camera_y, min_x=min_x, max_x=max_x)

                # Add knockback to flight.
                self.rect.x += int(self.knockback_velocity_x * dt)
                self._resolve_horizontal_collisions(collision_rects, camera_x=camera_x, camera_y=camera_y)

                if arena_rect is not None:
                    world_x, world_y = self._world_position(camera_x=camera_x, camera_y=camera_y)
                    left_x, right_x, _, _ = self._get_attack_lane_points(arena_rect)
                    clamped_x = max(left_x, min(right_x, world_x))
                    clamped_y = max(arena_rect.top + self.rect.height // 2, min(arena_rect.bottom - self.rect.height // 2, world_y))
                    self._set_world_center(clamped_x, clamped_y, camera_x=camera_x, camera_y=camera_y)

                if self.rect.centerx >= max_x:
                    self.facing_right = False
                elif self.rect.centerx <= min_x:
                    self.facing_right = True
            elif arena_rect is not None:
                spawn_x, spawn_y = self._get_arena_spawn_point(arena_rect)
                self._set_world_center(spawn_x, spawn_y, camera_x=camera_x, camera_y=camera_y)
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
