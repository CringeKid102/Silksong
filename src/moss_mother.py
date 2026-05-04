import pygame
import math
import random
from animation import Animation
from audio import AudioManager
from asset_paths import resolve_image_path
import config


_white_overlay_cache: dict = {}

def _apply_white_overlay(surface, intensity):
    """
    Return a copy of surface blended with white at the given intensity.
    Args:
        surface (pygame.Surface): Source surface to blend.
        intensity (int): White blend amount (0–255).
    Returns:
        pygame.Surface: New surface with white overlay applied.
    """
    result = surface.copy()
    size = surface.get_size()
    white_layer = _white_overlay_cache.get(size)
    if white_layer is None:
        white_layer = pygame.Surface(size)
        _white_overlay_cache[size] = white_layer
    white_layer.fill((intensity, intensity, intensity))
    result.blit(white_layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return result


class MossMother:
    """Flying boss enemy with pursuit, curve attacks, and stagger phases."""

    FRAME_WIDTH = 253
    FRAME_HEIGHT = 282
    ANIMATION_SCALE = 0.45

    def __init__(self, x, y, screen_width, screen_height):
        """
        Create the Moss Mother boss at the given position.
        Args:
            x (int): Horizontal spawn position (midbottom x) in screen pixels.
            y (int): Vertical spawn position (midbottom y) in screen pixels.
            screen_width (int): Logical screen width used for boundary checks.
            screen_height (int): Logical screen height used for boundary checks.
        """
        image_path = resolve_image_path("spritesheet/enemy/moss_mother.png")
        self.animation = Animation(
            image_path,
            frame_width=self.FRAME_WIDTH,
            frame_height=self.FRAME_HEIGHT,
            scale=self.ANIMATION_SCALE * config.ENEMY_SCALE_MULTIPLIER,
        )
        self._load_animations()
        self.animations = self.animation.animations
        self.display_facing_right = True
        self.turn_target_facing_right = True
        self.current_animation_name = "idle_right"
        self.animation.set_animation(self.current_animation_name)
        self.image = self.animation.get_current_frame()

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
        self.attack_finish_anim_duration = 0.12
        self.attack_finish_anim_timer = 0.0

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
        self.max_health = 10
        self.health = 10
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
        self.hit_white_timer = 0.0

        # Constant for pathfinding
        self.cell_size = 64
        self.path_search_radius = 18

        # Camera velocity cache
        self._camera_velocity = [0, 0]

        # Death sequence: roar lock phase, then split into 3 falling pieces.
        self.is_dying = False
        self.death_sequence_complete = False
        self.death_roar_active = False
        self.death_roar_duration = 1.0
        self.death_roar_timer = 0.0
        self.death_body_visible = True
        self.death_parts = []
        self.death_part_gravity = 1800.0
        self._death_roar_triggered = False
        self.hitbox_inset_x = 0.22
        self.hitbox_inset_y = 0.18
        self._load_death_part_images()

        # Egg: shown at arena spawn point while waiting to emerge
        self.egg_image = None
        self._load_egg_image()
        self.showing_egg = False
        self._egg_break_triggered = False
        self._egg_spawn_world = (0, 0)

        # Audio
        self.audio_manager = AudioManager()
        self._scream_timer = random.uniform(5.0, 12.0)
        self._death_parts_landed_count = 0

        # Per-animation draw offsets for easy visual tuning.
        self.animation_draw_offsets = {
            "default": (0, 0),
            "turn_right": (0, 0),
            "turn_left": (0, 0),
            "idle_right": (0, 0),
            "idle_left": (0, 0),
            "wall_attack_intro_right": (0, 0),
            "wall_attack_intro_left": (0, 0),
            "wall_attack_loop_right": (0, 0),
            "wall_attack_loop_left": (0, 0),
            "charge_right": (0, 0),
            "charge_left": (0, 0),
            "charge_end_right": (0, 0),
            "charge_end_left": (0, 0),
            "stun_fall_right": (0, 0),
            "stun_fall_left": (0, 0),
            "stun_ground_right": (0, 0),
            "stun_ground_left": (0, 0),
        }

    def _load_animations(self):
        """Register all spritesheet animations for the Moss Mother."""
        self.animation.add_animation("turn_right", row=0, start_col=0, num_frames=5, speed=0.07, loop=False)
        self.animation.add_animation("turn_left", row=0, start_col=0, num_frames=5, flip_x=True, speed=0.07, loop=False)
        self.animation.add_animation("idle_right", row=0, start_col=5, num_frames=5, speed=0.12, loop=True)
        self.animation.add_animation("idle_left", row=0, start_col=5, num_frames=5, flip_x=True, speed=0.12, loop=True)
        self.animation.add_animation("wall_attack_intro_right", row=1, start_col=0, num_frames=3, speed=0.09, loop=False)
        self.animation.add_animation("wall_attack_intro_left", row=1, start_col=0, num_frames=3, flip_x=True, speed=0.09, loop=False)
        self.animation.add_animation("wall_attack_loop_right", row=1, start_col=3, num_frames=2, speed=0.09, loop=True)
        self.animation.add_animation("wall_attack_loop_left", row=1, start_col=3, num_frames=2, flip_x=True, speed=0.09, loop=True)
        self.animation.add_animation("charge_right", row=2, start_col=0, num_frames=3, speed=0.08, loop=True)
        self.animation.add_animation("charge_left", row=2, start_col=0, num_frames=3, flip_x=True, speed=0.08, loop=True)
        self.animation.add_animation("charge_end_right", row=2, start_col=3, num_frames=1, speed=0.1, loop=False)
        self.animation.add_animation("charge_end_left", row=2, start_col=3, num_frames=1, flip_x=True, speed=0.1, loop=False)
        self.animation.add_animation("stun_fall_right", row=3, start_col=0, num_frames=1, speed=0.1, loop=False)
        self.animation.add_animation("stun_fall_left", row=3, start_col=0, num_frames=1, flip_x=True, speed=0.1, loop=False)
        self.animation.add_animation("stun_ground_right", row=3, start_col=1, num_frames=1, speed=0.1, loop=False)
        self.animation.add_animation("stun_ground_left", row=3, start_col=1, num_frames=1, flip_x=True, speed=0.1, loop=False)

    def _load_death_part_images(self):
        """Load and scale the three Moss Mother death piece sprites."""
        death_scale = self.ANIMATION_SCALE * config.ENEMY_SCALE_MULTIPLIER
        self.death_part_images = []
        for idx in (1, 2, 3):
            part_image = pygame.image.load(resolve_image_path(f"sprite/moss_mother_death_{idx}.png")).convert_alpha()
            part_w, part_h = part_image.get_size()
            scaled_size = (
                max(1, int(part_w * death_scale)),
                max(1, int(part_h * death_scale)),
            )
            self.death_part_images.append(pygame.transform.smoothscale(part_image, scaled_size))

    def _load_egg_image(self):
        """Load and scale the moss mother egg sprite."""
        try:
            raw = pygame.image.load(resolve_image_path("sprite/moss_mother_egg.png")).convert_alpha()
            scale = self.ANIMATION_SCALE * config.ENEMY_SCALE_MULTIPLIER
            w, h = raw.get_size()
            self.egg_image = pygame.transform.smoothscale(
                raw, (max(1, int(w * scale)), max(1, int(h * scale)))
            )
        except Exception:
            self.egg_image = None

    def _start_death_sequence(self):
        """Start death roar and prepare split pieces."""
        self.is_dying = True
        self.death_sequence_complete = False
        self.death_roar_active = True
        self.death_roar_timer = self.death_roar_duration
        self.death_body_visible = True
        self.death_parts = []
        self._death_roar_triggered = True
        self._death_parts_landed_count = 0

        # Cancel all active combat states during death sequence.
        self.is_attacking = False
        self.is_crying = False
        self.is_repositioning = False
        self.is_staggered = False
        self.use_gravity = False
        self.attack_contact_registered = False
        self.phase_through = False
        self.attack_timer = 0.0
        self.attack_finish_anim_timer = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        try:
            self.audio_manager.play_sfx("boss_death_1")
        except Exception:
            pass
        try:
            self.audio_manager.play_sfx("enemy_death")
        except Exception:
            pass

    def consume_death_roar_trigger(self):
        """
        Return True once when death roar starts, for the Hornet roar-lock trigger.
        Returns:
            bool: True on the first call after the death roar begins.
        """
        triggered = self._death_roar_triggered
        self._death_roar_triggered = False
        return triggered

    def _spawn_death_parts(self):
        """Create three split parts at the current boss position before falling."""
        if self.death_parts:
            return

        center_x, center_y = self.rect.center
        x_offsets = (-40, 0, 40)
        initial_vy = (-520.0, -640.0, -560.0)
        for idx, image in enumerate(self.death_part_images):
            part_rect = image.get_rect()
            part_rect.center = (int(center_x + x_offsets[idx]), int(center_y))
            base_vx = (-1, 0, 1)[idx] * 280.0
            self.death_parts.append({
                "image": image,
                "rect": part_rect,
                "velocity_x": base_vx + random.uniform(-260.0, 260.0),
                "velocity_y": initial_vy[idx],
                "landed": False,
            })

    def _update_death_parts(self, dt, collision_rects, camera_x=0, camera_y=0):
        """
        Apply gravity and collision to split death parts until all settle on ground.
        Args:
            dt (float): Elapsed time in seconds since the last frame.
            collision_rects (list): World-space collision rects for landing.
            camera_x (float): Horizontal camera offset for world-to-screen conversion.
            camera_y (float): Vertical camera offset for world-to-screen conversion.
        """
        if not self.death_parts:
            return

        for part in self.death_parts:
            if part["landed"]:
                continue

            part["rect"].x += int(part["velocity_x"] * dt)
            part["velocity_y"] += self.death_part_gravity * dt
            part["rect"].y += int(part["velocity_y"] * dt)

            landed = False
            if collision_rects:
                world_rect = part["rect"].copy()
                world_rect.x += int(camera_x)
                world_rect.y += int(camera_y)
                previous_bottom = world_rect.bottom - int(part["velocity_y"] * dt)

                landing_top = None
                if part["velocity_y"] >= 0:
                    for ground_rect in collision_rects:
                        if world_rect.right <= ground_rect.left or world_rect.left >= ground_rect.right:
                            continue
                        if previous_bottom <= ground_rect.top and world_rect.bottom >= ground_rect.top:
                            if landing_top is None or ground_rect.top < landing_top:
                                landing_top = ground_rect.top

                if landing_top is not None:
                    world_rect.bottom = int(landing_top)
                    part["rect"].y = int(world_rect.y - camera_y)
                    part["velocity_x"] = 0.0
                    part["velocity_y"] = 0.0
                    part["landed"] = True
                    landed = True
                    try:
                        self.audio_manager.play_sfx("enemy_corpse_land")
                    except Exception:
                        pass
        self.death_sequence_complete = all(part["landed"] for part in self.death_parts)

    def _set_animation(self, name, reset=False):
        """
        Switch to the named animation only if it differs from the current one.
        Args:
            name (str): Animation key to activate.
            reset (bool): If True, restart from the first frame.
        """
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

    def _get_animation_state_name(self):
        """
        Determine the animation state string from the current behaviour flags.

        Returns:
            str: One of "stun_ground", "stun_fall", "wall_attack", "charge", "charge_end", or "idle".
        """
        if self.is_staggered:
            return "stun_ground" if self.on_ground else "stun_fall"
        if self.death_roar_active:
            return "wall_attack"
        if self.is_crying:
            return "wall_attack"
        if self.is_attacking:
            return "charge"
        if self.attack_finish_anim_timer > 0.0:
            return "charge_end"
        return "idle"

    def _update_animation(self, dt):
        """
        Run the full animation state machine and advance the current animation.

        Args:
            dt (float): Elapsed time in seconds since the last frame.
        """
        animation_state = self._get_animation_state_name()

        if animation_state == "wall_attack":
            self.display_facing_right = self.facing_right
            facing_suffix = "right" if self.display_facing_right else "left"
            intro_name = f"wall_attack_intro_{facing_suffix}"
            loop_name = f"wall_attack_loop_{facing_suffix}"

            if self.current_animation_name not in {intro_name, loop_name}:
                self._set_animation(intro_name, reset=True)
            elif self.current_animation_name == intro_name and self.animation.is_finished():
                self._set_animation(loop_name, reset=True)

            self._advance_animation(dt)

            if self.current_animation_name == intro_name and self.animation.is_finished():
                self._set_animation(loop_name, reset=True)
                self.image = self.animation.get_current_frame()
            return

        if animation_state != "idle":
            self.display_facing_right = self.facing_right
            facing_suffix = "right" if self.display_facing_right else "left"
            self._set_animation(f"{animation_state}_{facing_suffix}")
            self._advance_animation(dt)
            return

        if self.facing_right != self.display_facing_right:
            self.turn_target_facing_right = self.facing_right
            turn_name = "turn_right" if self.turn_target_facing_right else "turn_left"
            if self.current_animation_name != turn_name:
                self._set_animation(turn_name, reset=True)
            if self._advance_animation(dt):
                self.display_facing_right = self.turn_target_facing_right
                facing_suffix = "right" if self.display_facing_right else "left"
                self._set_animation(f"idle_{facing_suffix}", reset=True)
            return

        facing_suffix = "right" if self.display_facing_right else "left"
        self._set_animation(f"idle_{facing_suffix}")
        self._advance_animation(dt)

    def _world_position(self, camera_x=0, camera_y=0):
        """
        Convert the boss screen-space rect to world coordinates.

        Args:
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.

        Returns:
            tuple[int, int]: World (x, y) of the boss center.
        """
        world_x = self.rect.centerx + int(camera_x)
        world_y = self.rect.centery + int(camera_y)
        return world_x, world_y

    def _get_arena_spawn_point(self, arena_rect):
        """
        Return the idle spawn position at the top-middle of the arena.
        Args:
            arena_rect (pygame.Rect): The arena bounding rectangle.
        Returns:
            tuple[int, int]: Screen (x, y) for the boss center.
        """
        return (
            int(arena_rect.centerx),
            int(arena_rect.top + self.rect.height // 2 + self.spawn_top_padding),
        )

    def _get_attack_lane_points(self, arena_rect):
        """
        Return the side and floor lane positions used for the arena sweep attack.
        Args:
            arena_rect (pygame.Rect): The arena bounding rectangle.
        Returns:
            tuple[int, int, int, int]: (left_x, right_x, middle_y, floor_y) in screen pixels.
        """
        edge_padding = max(self.rect.width // 2 + 24, self.attack_lane_margin)
        left_x = int(arena_rect.left + edge_padding)
        right_x = int(arena_rect.right - edge_padding)
        middle_y = int(arena_rect.centery)
        floor_y = int(arena_rect.bottom - self.rect.height // 2 - 28)
        return left_x, right_x, middle_y, floor_y

    def _set_world_center(self, world_x, world_y, camera_x=0, camera_y=0):
        """
        Place the boss using world coordinates while keeping its rect in screen space.
        Args:
            world_x (float): World x-coordinate for the boss center.
            world_y (float): World y-coordinate for the boss center.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
        """
        self.rect.centerx = int(world_x - camera_x)
        self.rect.centery = int(world_y - camera_y)

    def start_cry_attack(self):
        """
        Begin the cry attack and emit a one-shot trigger for the game to handle hazards.
        Returns:
            bool: True if the attack started, False if already attacking or crying.
        """
        if self.is_crying or self.is_attacking:
            return False
        self.is_crying = True
        self.cry_timer = self.cry_duration
        self.cry_cooldown_timer = self.cry_cooldown
        self._cry_attack_triggered = True
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.attack_contact_registered = False
        self.phase_through = False
        try:
            self.audio_manager.play_sfx("moss_mother_scream")
        except Exception:
            pass
        return True

    def consume_cry_attack_trigger(self):
        """
        Return True once when the cry attack begins, then reset.
        Returns:
            bool: True on the first call after a cry attack starts.
        """
        triggered = self._cry_attack_triggered
        self._cry_attack_triggered = False
        return triggered

    def consume_egg_break_trigger(self):
        """
        Return the egg world (x, y) center once when the egg breaks, then reset.
        Returns:
            tuple[int, int] | None: World coordinates of the egg center, or None if not triggered.
        """
        if self._egg_break_triggered:
            self._egg_break_triggered = False
            return self._egg_spawn_world
        return None

    def play_ceiling_dash(self):
        """Play the ceiling dash sound effect."""
        try:
            self.audio_manager.play_sfx("moss_mother_ceiling_dash")
        except Exception:
            pass

    def play_ceiling_hit(self):
        """Play the ceiling impact sound effect."""
        try:
            self.audio_manager.play_sfx("moss_mother_ceiling_hit")
        except Exception:
            pass

    def play_egg_break(self):
        """Play the egg break sound effect."""
        try:
            self.audio_manager.play_sfx("moss_mother_egg_break")
        except Exception:
            pass

    def _resolve_horizontal_collisions(self, collision_rects, camera_x=0, camera_y=0):
        """
        Push the boss out of any wall colliders it overlaps horizontally.
        Args:
            collision_rects (list[pygame.Rect]): Solid collision rectangles.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
        """
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
        """
        Handle floor landing and ceiling collisions for stagger fall physics.
        Args:
            collision_rects (list[pygame.Rect]): Solid collision rectangles.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
        """
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
        """
        Use BFS on a coarse grid to find the next step toward the target.

        Args:
            start_world (tuple[float, float]): Current world position of the boss.
            target_world (tuple[float, float]): Desired world destination.
            collision_rects (list[pygame.Rect]): Solid collision rectangles.

        Returns:
            tuple[float, float]: World position of the next BFS step.
        """
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
        """
        Start a three-part arena sweep: half-parabola down, floor dash, then vertical rise.
        Args:
            player_world_rect (pygame.Rect): Player's world-space rect for targeting.
            arena_rect (pygame.Rect): Boss arena bounds.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
        """
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
        try:
            self.audio_manager.play_sfx("moss_mother_attack")
            self.audio_manager.play_sfx_random(["moss_mother_attack_scream_1", "moss_mother_attack_scream_2"])
        except Exception:
            pass

    def _end_attack(self, player_world_rect):
        """
        End the current attack and set up a smooth reposition toward the opposite side.
        Args:
            player_world_rect (pygame.Rect | None): Player's world-space rect for reposition targeting.
        """
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
        """
        Advance the three-part sweep: half-parabola down, horizontal floor run, then vertical rise.
        Args:
            dt (float): Elapsed time in seconds since the last frame.
            player_world_rect (pygame.Rect | None): Player's world-space rect.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
            collision_rects (list | None): Solid collision rectangles.
            arena_rect (pygame.Rect | None): Boss arena bounds.
        """
        if arena_rect is None:
            self.is_attacking = False
            return

        self.attack_phase_time += dt

        if self.attack_step == 0:
            # Part 1: half open-up parabola from edge-middle down to the arena floor lane.
            t = min(1.0, self.attack_phase_time / self.attack_dive_duration)
            sx, sy = self.attack_start
            mx, my = self.attack_mid
            x = sx + (mx - sx) * t
            y = my - (my - sy) * ((1.0 - t) ** 2)
            self._set_world_center(x, y, camera_x=camera_x, camera_y=camera_y)
            self.facing_right = mx >= sx

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

            if t >= 1.0:
                self.attack_burst_count += 1
                if self.attack_burst_count >= self.attack_burst_max:
                    self.attack_step = 0
                    self.attack_phase_time = 0.0
                    self.is_attacking = False
                    self.attack_finish_anim_timer = self.attack_finish_anim_duration
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
        """
        Lerp the boss toward the reposition target.

        Args:
            dt (float): Elapsed time in seconds since the last frame.
        """
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
        """
        Pathfind toward the player and move the boss, resolving collisions.

        Args:
            dt (float): Elapsed time in seconds since the last frame.
            player_world_rect (pygame.Rect): Player's world-space rect.
            collision_rects (list[pygame.Rect]): Solid collision rectangles.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
            min_x (int): Left arena boundary in screen space.
            max_x (int | None): Right arena boundary in screen space.
        """
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
        """
        Apply gravity and resolve floor collisions during the stagger fall.

        Args:
            dt (float): Elapsed time in seconds since the last frame.
            collision_rects (list[pygame.Rect]): Solid collision rectangles.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.

        Returns:
            bool: True if the boss landed on the floor this frame.
        """
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
        """
        Apply damage and optionally knockback; trigger stagger at health thresholds.

        Args:
            damage (int): Amount of damage to deal.
            knockback_direction (int): -1 for left, 0 for none, 1 for right.
            apply_knockback (bool): Whether to apply horizontal knockback.
        """
        if damage <= 0 or self.is_dying:
            return

        self.hit_white_timer = 0.12
        self.health = max(0, self.health - damage)
        try:
            self.audio_manager.play_sfx("hornet_silkcharge")
        except Exception:
            pass

        if self.health <= 0:
            self._start_death_sequence()
            return

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
            try:
                self.audio_manager.play_sfx("moss_mother_stun")
            except Exception:
                pass

    def reset_position(self, x, y):
        """
        Reset all boss state and place it at the given position.

        Args:
            x (int): Screen X for the bottom-center of the boss.
            y (int): Screen Y for the bottom-center of the boss.
        """
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.is_staggered = False
        self.use_gravity = False
        self.facing_right = True
        self.display_facing_right = True
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
        self.showing_egg = False
        self._egg_break_triggered = False
        self.is_crying = False
        self.cry_timer = 0.0
        self.cry_cooldown_timer = 0.0
        self._cry_attack_triggered = False
        self.curve_attack_lockout_timer = 0.0
        self.cry_attack_lockout_timer = 0.0
        self.attack_finish_anim_timer = 0.0
        self.next_stagger_idx = 0
        self.stagger_count = 0
        self.health = self.max_health
        self.is_dying = False
        self.death_sequence_complete = False
        self.death_roar_active = False
        self.death_roar_timer = 0.0
        self.death_body_visible = True
        self.death_parts = []
        self._death_roar_triggered = False
        self._death_parts_landed_count = 0
        self._scream_timer = random.uniform(5.0, 12.0)
        self._set_animation("idle_right", reset=True)

    def update(self, min_x, max_x, dt, collision_rects=None, camera_x=0, camera_y=0, camera_dx=0, camera_dy=0, player_world_rect=None, arena_rect=None):
        """
        Run the full boss update tick: timers, AI, movement, and animation.

        Args:
            min_x (int): Left boundary in screen space.
            max_x (int): Right boundary in screen space.
            dt (float): Elapsed time in seconds since the last frame.
            collision_rects (list[pygame.Rect] | None): Solid collision rectangles.
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
            camera_dx (float): Camera movement this frame in X.
            camera_dy (float): Camera movement this frame in Y.
            player_world_rect (pygame.Rect | None): Player's world-space rect.
            arena_rect (pygame.Rect | None): Boss arena bounds.
        """
        self.rect.x -= int(camera_dx)
        self.rect.y -= int(camera_dy)
        for part in self.death_parts:
            part["rect"].x -= int(camera_dx)
            part["rect"].y -= int(camera_dy)
        if self.hit_white_timer > 0.0:
            self.hit_white_timer = max(0.0, self.hit_white_timer - dt)

        if self.is_dying:
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            self.knockback_velocity_x = 0.0
            self.attack_contact_registered = False
            self.phase_through = False

            if self.death_roar_active:
                self.death_roar_timer = max(0.0, self.death_roar_timer - dt)
                self._update_animation(dt)
                if self.death_roar_timer <= 0.0:
                    self.death_roar_active = False
                    self.death_body_visible = False
                    self._spawn_death_parts()
                    try:
                        self.audio_manager.play_sfx("boss_death_2")
                    except Exception:
                        pass
            else:
                self._update_death_parts(dt, collision_rects, camera_x=camera_x, camera_y=camera_y)
            return

        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

        # Random mossgrub scream when engaged
        if self.is_engaged and not self.is_dying:
            self._scream_timer -= dt
            if self._scream_timer <= 0.0:
                self._scream_timer = random.uniform(6.0, 14.0)
                try:
                    self.audio_manager.play_sfx("mossgrub_scream")
                except Exception:
                    pass

        if self.attack_timer > 0.0:
            self.attack_timer = max(0.0, self.attack_timer - dt)
        if self.cry_cooldown_timer > 0.0:
            self.cry_cooldown_timer = max(0.0, self.cry_cooldown_timer - dt)
        if self.curve_attack_lockout_timer > 0.0:
            self.curve_attack_lockout_timer = max(0.0, self.curve_attack_lockout_timer - dt)
        if self.cry_attack_lockout_timer > 0.0:
            self.cry_attack_lockout_timer = max(0.0, self.cry_attack_lockout_timer - dt)
        if self.attack_finish_anim_timer > 0.0:
            self.attack_finish_anim_timer = max(0.0, self.attack_finish_anim_timer - dt)

        player_in_arena = bool(arena_rect and player_world_rect and arena_rect.colliderect(player_world_rect))

        if arena_rect is not None and not self.is_engaged:
            if player_in_arena and not self.has_spawned_in_arena:
                # Show egg at the spawn point as soon as Hornet enters
                if not self.showing_egg:
                    egg_x, egg_y = self._get_arena_spawn_point(arena_rect)
                    self._egg_spawn_world = (egg_x, egg_y)
                    self.showing_egg = True
                self.spawn_delay_timer += dt
            elif not player_in_arena and not self.has_spawned_in_arena:
                self.spawn_delay_timer = 0.0
                self.showing_egg = False

            if not self.has_spawned_in_arena:
                if self.spawn_delay_timer < self.spawn_delay:
                    return
                spawn_x, spawn_y = self._get_arena_spawn_point(arena_rect)
                self._set_world_center(spawn_x, spawn_y, camera_x=camera_x, camera_y=camera_y)
                self.velocity_x = 0.0
                self.velocity_y = 0.0
                self.on_ground = False
                # Egg breaks: hide egg, trigger burst effect, play sound
                self.showing_egg = False
                self._egg_break_triggered = True
                self.play_egg_break()
                self.has_spawned_in_arena = True

            if not player_in_arena:
                self._update_animation(dt)
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
            self._update_animation(dt)
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
            self._update_animation(dt)
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
                    self._update_animation(dt)
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
                self._update_animation(dt)
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
                    self._update_animation(dt)
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

        self._update_animation(dt)

    def _get_animation_draw_offset(self):
        """Return the configured draw offset for the current animation."""
        return self.animation_draw_offsets.get(self.current_animation_name, self.animation_draw_offsets.get("default", (0, 0)))

    def get_world_hitbox(self, camera_x=0, camera_y=0):
        """
        Return a reduced world-space hitbox used for combat interactions.
        Args:
            camera_x (float): Horizontal camera offset.
            camera_y (float): Vertical camera offset.
        Returns:
            pygame.Rect: Inset world-space hitbox rectangle.
        """
        world_rect = self.rect.copy()
        world_rect.x += int(camera_x)
        world_rect.y += int(camera_y)
        inset_w = int(world_rect.width * self.hitbox_inset_x)
        inset_h = int(world_rect.height * self.hitbox_inset_y)
        hitbox = world_rect.inflate(-inset_w, -inset_h)
        if hitbox.width < 8:
            hitbox.width = 8
            hitbox.centerx = world_rect.centerx
        if hitbox.height < 8:
            hitbox.height = 8
            hitbox.centery = world_rect.centery
        return hitbox

    def get_draw_rect(self, look_y_offset=0, screen_offset=(0, 0)):
        """
        Return the final draw rect after camera/look/screen offset tuning.
        Args:
            look_y_offset (float): Vertical look-ahead offset in pixels.
            screen_offset (tuple[float, float]): Screen shake (x, y) offset.
        Returns:
            pygame.Rect: Adjusted rect for blitting the sprite.
        """
        draw_rect = self.rect.copy()
        draw_rect.x += int(screen_offset[0])
        draw_rect.y += int(look_y_offset + screen_offset[1])
        offset_x, offset_y = self._get_animation_draw_offset()
        draw_rect.x += int(offset_x)
        draw_rect.y += int(offset_y)
        return draw_rect

    def draw(self, screen, look_y_offset=0, screen_offset=(0, 0)):
        """
        Draw the boss sprite on screen, offset by the vertical look pan.
        Args:
            screen (pygame.Surface): Target surface.
            look_y_offset (float): Vertical look-ahead offset in pixels.
            screen_offset (tuple[float, float]): Screen shake (x, y) offset.
        """
        if self.showing_egg:
            return  # egg is drawn by main.py; mossmother not yet visible

        if self.is_dying and not self.death_body_visible:
            for part in self.death_parts:
                draw_rect = part["rect"].copy()
                draw_rect.x += int(screen_offset[0])
                draw_rect.y += int(look_y_offset + screen_offset[1])
                screen.blit(part["image"], draw_rect)
            return

        draw_surf = _apply_white_overlay(self.image, int(255 * self.hit_white_timer / 0.12)) if self.hit_white_timer > 0.0 else self.image
        screen.blit(draw_surf, self.get_draw_rect(look_y_offset=look_y_offset, screen_offset=screen_offset))
