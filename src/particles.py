import pygame
import random
import math
import os
from typing import List, Dict, Tuple

class ParticleSystem:
    """Particle system managing embers, sparks, smoke, gameplay world particles, and screen shake."""
    def __init__(self, screen_width=None, screen_height=None):
        """
        Create the particle system for the given screen dimensions.
        Args:
            screen_width (int | None): Logical screen width in pixels.
            screen_height (int | None): Logical screen height in pixels.
        """
        self.particles: List[Dict] = []
        self.float_texts: List[Dict] = []
        # Screen shake
        self.shake_amount = 0.0
        self.shake_time = 0.0
        self.shake_duration = 0.0
        # Ember settings
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.ember_image = None
        self.ember_round_image = None
        self.ember_spawn_timer = 0.0
        self.ember_round_spawn_timer = 0.0
        self.ember_enabled = False
        self.ember_base_spawn_interval = 0.05
        self.max_particles = 1000
        self.max_cache_entries = 240
        
        # Surface cache for particle rendering
        self._surface_cache = {}

        # Gameplay/world particle effects
        self.gameplay_particles: List[Dict] = []
        self.fung_mote_image = None
        self.mossbone_small_frames: List[pygame.Surface] = []
        self.coral_particle_image = None
        self.aspid_particle_image = None
        self.mossbone_spawn_timer = 0.0
        self.mossbone_spawn_interval = 0.35
        self.coral_aspid_spawn_timer = 0.0
        self.coral_aspid_spawn_interval = 0.22
        self.max_gameplay_particles = 300
        self.immediate_offscreen_cull = True  # [21] github copilot
        
    def load_ember_image(self, image_path):
        """
        Load the standard ember particle image.
        Args:
            image_path (str): Filesystem path to the ember image.
        """
        self.ember_image = pygame.image.load(image_path).convert_alpha()

    def load_ember_round_image(self, image_path):
        """
        Load the round background ember particle image.
        Args:
            image_path (str): Filesystem path to the round ember image.
        """
        self.ember_round_image = pygame.image.load(image_path).convert_alpha()

    def load_gameplay_particle_images(self, fung_mote_path, mossbone_small_path, coral_particle_path, aspid_particle_path):
        """
        Load sprite assets used by gameplay world particles.
        Args:
            fung_mote_path (str): Path to the fung mote particle image.
            mossbone_small_path (str): Path to the mossbone insect spritesheet.
            coral_particle_path (str): Path to the coral particle image.
            aspid_particle_path (str): Path to the aspid particle image.
        """
        self.fung_mote_image = pygame.image.load(fung_mote_path).convert_alpha()
        self.coral_particle_image = pygame.image.load(coral_particle_path).convert_alpha()
        self.aspid_particle_image = pygame.image.load(aspid_particle_path).convert_alpha()

        mossbone_sheet = pygame.image.load(mossbone_small_path).convert_alpha()
        frame_w, frame_h = 89, 78
        cols = max(1, mossbone_sheet.get_width() // frame_w)
        rows = max(1, mossbone_sheet.get_height() // frame_h)
        self.mossbone_small_frames = []
        for row in range(rows):
            for col in range(cols):
                frame_rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                if frame_rect.right > mossbone_sheet.get_width() or frame_rect.bottom > mossbone_sheet.get_height():
                    continue
                self.mossbone_small_frames.append(mossbone_sheet.subsurface(frame_rect).copy())

    def _can_spawn_gameplay_particle(self):
        """Return True if there is room for one more gameplay particle."""
        return len(self.gameplay_particles) < self.max_gameplay_particles

    def spawn_fung_mote_death_burst(self, world_x, world_y, ground_y, count=None):
        """
        Spawn a one-shot burst of fung motes that arc, fall, and disappear on ground hit.
        Args:
            world_x (float): World x-coordinate of the burst origin.
            world_y (float): World y-coordinate of the burst origin.
            ground_y (float): World y-coordinate of the floor where motes vanish.
            count (int | None): Number of motes to spawn; random if None.
        """
        if self.fung_mote_image is None:
            return

        burst_count = random.randint(15, 20) if count is None else max(1, int(count))
        for _ in range(burst_count):
            if not self._can_spawn_gameplay_particle():
                break

            self.gameplay_particles.append({
                'type': 'fung_mote',
                'x': float(world_x) + random.uniform(-14.0, 14.0),
                'y': float(world_y) + random.uniform(-10.0, 8.0),
                'vx': random.uniform(-240.0, 240.0),
                'vy': random.uniform(-820.0, -420.0),
                'gravity': random.uniform(1700.0, 2100.0),
                'ground_y': float(ground_y),
                'image': self.fung_mote_image,
                'scale': random.uniform(0.55, 0.95),
                'rotation': random.uniform(0.0, 360.0),
                'rot_speed': random.uniform(-220.0, 220.0),
                'life': random.uniform(1.8, 2.5),
            })

    def _spawn_mossbone_insect(self, camera_world_rect):
        """Spawn one animated mossbone insect around the current camera view."""
        if not self.mossbone_small_frames or not self._can_spawn_gameplay_particle():
            return

        margin = 260
        spawn_x = random.uniform(camera_world_rect.left - margin, camera_world_rect.right + margin)
        spawn_y = random.uniform(camera_world_rect.top - margin, camera_world_rect.bottom + margin)
        scale = random.uniform(0.35, 0.65)
        self.gameplay_particles.append({
            'type': 'mossbone_insect',
            'x': spawn_x,
            'y': spawn_y,
            'base_vx': random.uniform(-55.0, 90.0),
            'base_vy': random.uniform(-45.0, 45.0),
            'wander_phase': random.uniform(0.0, math.pi * 2.0),
            'wander_speed': random.uniform(0.9, 1.8),
            'wander_amp_x': random.uniform(25.0, 65.0),
            'wander_amp_y': random.uniform(18.0, 55.0),
            'anim_time': 0.0,
            'anim_fps': random.uniform(8.0, 13.0),
            'anim_index': random.randrange(len(self.mossbone_small_frames)),
            'scale': scale,
            'life': random.uniform(18.0, 32.0),
        })

    def _spawn_coral_or_aspid_particle(self, camera_world_rect):
        """Spawn one drifting particle that generally moves bottom-left to top-right."""
        if not self._can_spawn_gameplay_particle():
            return

        image = self.coral_particle_image if random.random() < 0.5 else self.aspid_particle_image
        if image is None:
            return

        spawn_x = random.uniform(camera_world_rect.left - 80, camera_world_rect.right - 20)
        spawn_y = random.uniform(camera_world_rect.bottom - 80, camera_world_rect.bottom + 160)
        self.gameplay_particles.append({
            'type': 'coral_aspid',
            'x': spawn_x,
            'y': spawn_y,
            'vx': random.uniform(45.0, 110.0),
            'vy': random.uniform(-165.0, -90.0),
            'jitter_timer': random.uniform(0.08, 0.22),
            'image': image,
            'scale': random.uniform(0.45, 0.95),
            'rotation': random.uniform(-35.0, 35.0),
            'rot_speed': random.uniform(-48.0, 48.0),
            'life': random.uniform(8.0, 15.0),
        })

    def update_gameplay_particles(self, dt, camera_world_rect, ground_colliders=None):
        """
        Advance world-space gameplay particles and maintain ambient spawners.
        Args:
            dt (float): Elapsed time in seconds since the last frame.
            camera_world_rect (pygame.Rect): Visible world area; used for cull and spawn bounds.
            ground_colliders (list | None): Collision rects used for ground-landing logic.
        """
        if camera_world_rect is None:
            return

        self.mossbone_spawn_timer += dt
        while self.mossbone_spawn_timer >= self.mossbone_spawn_interval:
            self.mossbone_spawn_timer -= self.mossbone_spawn_interval
            mossbone_count = sum(1 for p in self.gameplay_particles if p['type'] == 'mossbone_insect')
            if mossbone_count < 22:
                self._spawn_mossbone_insect(camera_world_rect)

        self.coral_aspid_spawn_timer += dt
        while self.coral_aspid_spawn_timer >= self.coral_aspid_spawn_interval:
            self.coral_aspid_spawn_timer -= self.coral_aspid_spawn_interval
            drift_count = sum(1 for p in self.gameplay_particles if p['type'] == 'coral_aspid')
            if drift_count < 46:
                self._spawn_coral_or_aspid_particle(camera_world_rect)

        alive_particles = []
        min_x = float(camera_world_rect.left)
        max_x = float(camera_world_rect.right)
        min_y = float(camera_world_rect.top)
        max_y = float(camera_world_rect.bottom)

        for p in self.gameplay_particles:
            p['life'] -= dt
            if p['life'] <= 0.0:
                continue

            particle_type = p.get('type')
            if particle_type == 'fung_mote':
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += p['gravity'] * dt
                p['rotation'] += p.get('rot_speed', 0.0) * dt
                if p['y'] >= p.get('ground_y', max_y):
                    continue
            elif particle_type == 'mossbone_insect':
                p['wander_phase'] += p['wander_speed'] * dt
                drift_x = math.sin(p['wander_phase']) * p['wander_amp_x']
                drift_y = math.cos(p['wander_phase'] * 1.23) * p['wander_amp_y']
                p['x'] += (p['base_vx'] + drift_x) * dt
                p['y'] += (p['base_vy'] + drift_y) * dt
                p['anim_time'] += dt
                frame_count = max(1, len(self.mossbone_small_frames))
                p['anim_index'] = int(p['anim_time'] * p['anim_fps']) % frame_count
            elif particle_type == 'coral_aspid':
                p['jitter_timer'] -= dt
                if p['jitter_timer'] <= 0.0:
                    p['jitter_timer'] = random.uniform(0.08, 0.24)
                    p['vx'] += random.uniform(-30.0, 34.0)
                    p['vy'] += random.uniform(-36.0, 18.0)
                    p['vx'] = max(20.0, min(140.0, p['vx']))
                    p['vy'] = max(-220.0, min(-35.0, p['vy']))
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['rotation'] += p.get('rot_speed', 0.0) * dt

            image = p.get('image')
            if particle_type == 'mossbone_insect' and self.mossbone_small_frames:
                frame_index = int(p.get('anim_index', 0)) % len(self.mossbone_small_frames)
                image = self.mossbone_small_frames[frame_index]

            if image is not None:
                base_w, base_h = image.get_size()
                scale = max(0.1, float(p.get('scale', 1.0)))
                half_w = max(1.0, (base_w * scale) * 0.5)
                half_h = max(1.0, (base_h * scale) * 0.5)
            else:
                half_w = 2.0
                half_h = 2.0

            if (
                p['x'] + half_w < min_x
                or p['x'] - half_w > max_x
                or p['y'] + half_h < min_y
                or p['y'] - half_h > max_y
            ):
                continue

            alive_particles.append(p)

        self.gameplay_particles = alive_particles

    def draw_gameplay_particles(self, surface: pygame.Surface, camera_x=0, camera_y=0, look_y_offset=0, screen_offset=(0, 0)):
        """
        Draw world-space gameplay particles transformed into screen space.
        Args:
            surface (pygame.Surface): Target surface.
            camera_x (float): Horizontal camera offset in pixels.
            camera_y (float): Vertical camera offset in pixels.
            look_y_offset (float): Additional vertical look-ahead offset.
            screen_offset (tuple[float, float]): Screen shake (x, y) offset.
        """
        if not self.gameplay_particles:
            return

        shake_x = int(screen_offset[0])
        shake_y = int(screen_offset[1])

        for p in self.gameplay_particles:
            image = p.get('image')
            if p.get('type') == 'mossbone_insect':
                if not self.mossbone_small_frames:
                    continue
                frame_index = int(p.get('anim_index', 0)) % len(self.mossbone_small_frames)
                image = self.mossbone_small_frames[frame_index]

            if image is None:
                continue

            base_w, base_h = image.get_size()
            scale = max(0.1, float(p.get('scale', 1.0)))
            draw_w = max(1, int(base_w * scale))
            draw_h = max(1, int(base_h * scale))
            scaled = pygame.transform.smoothscale(image, (draw_w, draw_h))

            rotation = float(p.get('rotation', 0.0))
            if abs(rotation) > 0.01:
                scaled = pygame.transform.rotate(scaled, rotation)

            screen_x = int(p['x'] - camera_x + shake_x)
            screen_y = int(p['y'] - camera_y - look_y_offset + shake_y)
            draw_rect = scaled.get_rect(center=(screen_x, screen_y))
            surface.blit(scaled, draw_rect)
        
    def enable_ember_spawning(self, enabled=True):
        """Toggle automatic ember particle spawning."""
        self.ember_enabled = enabled

    def _trim_surface_cache(self):
        """Evict old entries when the surface cache grows too large."""
        if len(self._surface_cache) > self.max_cache_entries:
            drop_count = max(1, self.max_cache_entries // 4)
            for _ in range(drop_count):
                self._surface_cache.pop(next(iter(self._surface_cache)), None)

    # [11] github copilot
    def _get_cached_ember_surface(self, img, size, angle, alpha):
        """
        Return a cached, transformed ember image using quantized buckets to limit cache entries.
        Args:
            img (pygame.Surface): Source ember image.
            size (float): Desired display size in pixels.
            angle (float): Rotation angle in degrees.
            alpha (int): Opacity (0–255).
        Returns:
            pygame.Surface: Scaled, rotated, and alpha-set surface.
        """
        scale_factor = max(0.2, size / 3.0)
        scale_bucket = round(scale_factor * 4) / 4.0
        angle_bucket = int(round(angle / 5.0) * 5)
        alpha_bucket = max(0, min(255, int(round(alpha / 24.0) * 24)))

        cache_key = (id(img), scale_bucket, angle_bucket, alpha_bucket)
        cached = self._surface_cache.get(cache_key)
        if cached is not None:
            return cached

        w = max(1, int(img.get_width() * scale_bucket))
        h = max(1, int(img.get_height() * scale_bucket))
        scaled_img = pygame.transform.smoothscale(img, (w, h))
        rotated_img = pygame.transform.rotate(scaled_img, angle_bucket)
        rotated_img.set_alpha(alpha_bucket)
        self._surface_cache[cache_key] = rotated_img
        self._trim_surface_cache()
        return rotated_img

    def spawn_sparks(self, x: float, y: float, count: int = 12, color: Tuple[int,int,int]=(255,200,100)):
        """
        Spawn burst spark particles at the given position.
        Args:
            x (float): Horizontal spawn position in screen pixels.
            y (float): Vertical spawn position in screen pixels.
            count (int): Number of sparks to emit.
            color (tuple[int, int, int]): RGB color of the sparks.
        """
        MAX = 500
        available = max(0, MAX - len(self.particles))
        to_spawn = min(count, available)
        for _ in range(to_spawn):
            ang = random.uniform(0, math.pi*2)
            spd = random.uniform(40, 220)
            life = random.uniform(0.35, 0.9)
            self.particles.append({
                'x': x + random.uniform(-8, 8),
                'y': y + random.uniform(-8, 8),
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd * 0.6 - random.uniform(10, 60),
                'life': life,
                'initial_life': life,
                'size': random.uniform(2, 4),
                'color': color,
                'gravity': 300,
                'type': 'spark'
            })

    def spawn_smoke(self, x: float, y: float, count: int = 10):
        """
        Spawn rising smoke particles at the given position.
        Args:
            x (float): Horizontal spawn position in screen pixels.
            y (float): Vertical spawn position in screen pixels.
            count (int): Number of smoke puffs to emit.
        """
        MAX = 500
        available = max(0, MAX - len(self.particles))
        to_spawn = min(count, available)
        for _ in range(to_spawn):
            life = random.uniform(0.9, 2.0)
            self.particles.append({
                'x': x + random.uniform(-12, 12),
                'y': y + random.uniform(-6, 6),
                'vx': random.uniform(-20, 20),
                'vy': random.uniform(-40, -10),
                'life': life,
                'initial_life': life,
                'size': random.uniform(8, 18),
                'color': (180, 180, 180),
                'gravity': -20,
                'type': 'smoke'
            })

    # [9] github copilot
    def spawn_embers(self, x: float, y: float, count: int = 1, image=None):
        """
        Spawn ember particles that float diagonally from bottom-left to top-right.
        Args:
            x (float): Horizontal origin in screen pixels.
            y (float): Vertical origin in screen pixels.
            count (int): Number of embers to spawn.
            image (pygame.Surface | None): Custom ember image; falls back to self.ember_image.
        """
        MAX = 1000
        available = max(0, MAX - len(self.particles))
        to_spawn = min(count, available)
        for _ in range(to_spawn):
            life = random.uniform(15.0, 20.0)  # Much longer life to traverse the screen
            # Size with stronger bias towards smaller (farther) particles
            initial_size = 9 * (random.uniform(0, 1) ** 3)
            # Depth factor: larger embers are in front and move faster.
            depth_t = (initial_size - 1.0) / 9.0  # 0 = far/back, 1 = near/front
            speed_scale = 0.45 + 1.05 * depth_t

            # Velocity moves diagonally from bottom-left to top-right.
            base_vx = random.uniform(360, 480)
            base_vy = random.uniform(-480, -360)
            vx = base_vx * speed_scale
            vy = base_vy * speed_scale
            # Random size change behavior
            size_change_rate = random.uniform(-0.5, 0.5)  # Can grow or shrink
            self.particles.append({
                'x': x + random.uniform(-self.screen_width, self.screen_width),
                'y': y + random.uniform(self.screen_height, 0),
                'vx': vx,
                'vy': vy,
                'life': life,
                'initial_life': life,
                'size': initial_size,
                'initial_size': initial_size,
                'size_change_rate': size_change_rate,
                'min_size': 3.0,
                'max_size': 10.0,
                'color': None,
                'gravity': 0,  # No gravity for floating embers
                'type': 'ember',
                'image': image,
                'angle': random.uniform(-20, 20),  # Random rotation angle ±25 degrees
                'time': 0,  # For sin wave movement
                'sin_freq': random.uniform(1, 5),  # Frequency for sin wave
                'sin_amp': (1.5 + 8.5 * depth_t)  # Foreground embers sway more
            })

    def spawn_round_embers(self, x: float, y: float, count: int = 1, image=None):
        """
        Spawn round background embers with depth-based velocity and sway.
        Args:
            x (float): Horizontal origin in screen pixels.
            y (float): Vertical origin in screen pixels.
            count (int): Number of round embers to spawn.
            image (pygame.Surface | None): Custom image; falls back to self.ember_round_image.
        """
        img = image or self.ember_round_image
        MAX = 1000
        available = max(0, MAX - len(self.particles))
        to_spawn = min(count, available)
        for _ in range(to_spawn):
            life = random.uniform(15.0, 20.0)
            # Background bias: strong cubic bias keeps most particles small/far.
            initial_size = 1.0 + 3.0 * (random.uniform(0, 1) ** 3)
            # Depth factor: 0 = far/back, 1 = near/front.
            depth_t = (initial_size - 1.0) / 3.0
            speed_scale = 0.45 + 1.05 * depth_t

            base_vx = random.uniform(360, 480)
            base_vy = random.uniform(-480, -360)
            vx = base_vx * speed_scale
            vy = base_vy * speed_scale

            self.particles.append({
                'x': x + random.uniform(-self.screen_width, self.screen_width),
                'y': y + random.uniform(self.screen_height, 0),
                'vx': vx,
                'vy': vy,
                'life': life,
                'initial_life': life,
                'size': initial_size,
                'initial_size': initial_size,
                'color': None,
                'gravity': 0,
                'type': 'ember',
                'image': img,
                'angle': random.uniform(-20, 20),
                'time': 0,
                'sin_freq': random.uniform(1, 5),
                'sin_amp': 1.5 + 8.5 * depth_t,
            })

    def add_detection_popup(self, delta: int, x: float, y: float):
        """
        Add a floating damage or healing number popup.
        Args:
            delta (int): Value to display; positive for healing, negative for damage.
            x (float): Horizontal spawn position in screen pixels.
            y (float): Vertical spawn position in screen pixels.
        """
        txt = f"{'+' if delta>0 else ''}{int(delta)}"
        col = (0,255,0) if delta > 0 else (255,0,0)
        self.float_texts.append({
            'text': txt,
            'x': x + random.uniform(-12, 12),
            'y': y + random.uniform(-6, 6),
            'vy': -40 - random.uniform(0, 40),
            'time': 1.0,
            'duration': 1.0,
            'color': col,
            'alpha': 255,
        })

    def update(self, dt: float):
        """
        Advance all particles, floating texts, screen shake, and auto-spawning.
        Args:
            dt (float): Elapsed time in seconds since the last frame.
        """
        # Update particles
        alive_particles = []
        screen_w = self.screen_width or 0
        screen_h = self.screen_height or 0
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += p.get('gravity', 0) * dt
            p['life'] -= dt
            
            # Update size for particles that have size_change_rate
            if 'size_change_rate' in p:
                p['size'] += p['size_change_rate'] * dt
                # Clamp size within bounds
                p['size'] = max(p.get('min_size', 0.5), min(p.get('max_size', 10.0), p['size']))
            
            # Sin wave movement for embers
            if p['type'] == 'ember':
                p['time'] += dt
                p['x'] += math.sin(p['time'] * p['sin_freq']) * p['sin_amp']

            if p['life'] <= 0:
                continue

            if self.immediate_offscreen_cull and screen_w > 0 and screen_h > 0:
                if p['type'] == 'ember' and p.get('image'):
                    img = p['image']
                    radius = max(1, int(max(img.get_width(), img.get_height()) * p.get('size', 1.0) * 0.5 / 3.0))
                else:
                    radius = max(1, int(p.get('size', 2)))

                if (
                    p['x'] + radius < 0
                    or p['x'] - radius > screen_w
                    or p['y'] + radius < 0
                    or p['y'] - radius > screen_h
                ):
                    continue

            alive_particles.append(p)
        self.particles = alive_particles

        # Update floating texts
        alive_texts = []
        for ft in self.float_texts:
            ft['y'] += ft['vy'] * dt
            ft['time'] -= dt
            ft['alpha'] = max(0, int(255 * (ft['time'] / max(0.01, ft.get('duration', 1.0)))))
            if ft['time'] > 0:
                alive_texts.append(ft)
        self.float_texts = alive_texts
        
        # Decay screen shake
        if self.shake_time > 0:
            self.shake_time -= dt
            if self.shake_time <= 0:
                self.shake_amount = 0.0
                self.shake_time = 0.0
                self.shake_duration = 0.0
        else:
            self.shake_amount = max(0.0, self.shake_amount - 8.0 * dt)
        
        # Handle automatic ember spawning
        if self.ember_enabled and self.ember_image and self.screen_width and self.screen_height:
            self.ember_spawn_timer += dt
            load_t = min(1.0, len(self.particles) / max(1, self.max_particles))
            spawn_interval = self.ember_base_spawn_interval + (0.09 * load_t)
            if self.ember_spawn_timer >= spawn_interval:
                self.ember_spawn_timer = 0.0
                # Randomly choose to spawn from bottom edge or left edge
                if random.choice([True, False]):
                    # Spawn from bottom edge (anywhere along the bottom)
                    spawn_x = random.uniform(0, self.screen_width)
                    spawn_y = random.uniform(self.screen_height * 0.95, self.screen_height)
                else:
                    # Spawn from left edge (anywhere along the left side)
                    spawn_x = random.uniform(0, self.screen_width * 0.05)
                    spawn_y = random.uniform(0, self.screen_height)
                spawn_count = 1 if load_t > 0.6 else random.randint(1, 3)
                self.spawn_embers(spawn_x, spawn_y, count=spawn_count, image=self.ember_image)

        # Handle automatic round ember spawning
        if self.ember_enabled and self.ember_round_image and self.screen_width and self.screen_height:
            self.ember_round_spawn_timer += dt
            load_t = min(1.0, len(self.particles) / max(1, self.max_particles))
            spawn_interval = self.ember_base_spawn_interval + (0.11 * load_t)
            if self.ember_round_spawn_timer >= spawn_interval:
                self.ember_round_spawn_timer = 0.0
                if random.choice([True, False]):
                    spawn_x = random.uniform(0, self.screen_width)
                    spawn_y = random.uniform(self.screen_height * 0.95, self.screen_height)
                else:
                    spawn_x = random.uniform(0, self.screen_width * 0.05)
                    spawn_y = random.uniform(0, self.screen_height)
                spawn_count = 1 if load_t > 0.5 else random.randint(1, 2)
                self.spawn_round_embers(spawn_x, spawn_y, count=spawn_count, image=self.ember_round_image)

    def draw_particles(self, surface: pygame.Surface, size_min=None, size_max=None):
        """
        Draw particles to the surface, optionally filtered by size range.
        Args:
            surface (pygame.Surface): Target surface.
            size_min (float | None): Skip particles smaller than this size.
            size_max (float | None): Skip particles larger than this size.
        """
        # Sort particles by size for depth effect (smaller = farther = behind, larger = closer = in front)
        self.particles.sort(key=lambda p: p.get('size', 0))
        
        for p in self.particles:
            if size_min is not None and p.get('size', 0) < size_min:
                continue
            if size_max is not None and p.get('size', 0) > size_max:
                continue
            life_frac = max(0.0, min(1.0, p['life'] / max(0.001, p.get('initial_life', p['life']))))
            alpha = int(255 * life_frac)
            
            if p['type'] == 'ember' and p.get('image'):
                # Use image for ember particles
                img = p['image']
                angle = p.get('angle', 0)
                rotated_img = self._get_cached_ember_surface(img, p['size'], angle, alpha)
                
                # Draw centered on particle position
                surface.blit(rotated_img, (int(p['x']) - rotated_img.get_width()//2, int(p['y']) - rotated_img.get_height()//2))
            elif p['type'] == 'spark':
                r = max(1, int(p['size']))
                cache_key = ('spark', r, p['color'], alpha)
                
                if cache_key not in self._surface_cache:
                    s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                    col = p['color'] + (alpha,)
                    pygame.draw.circle(s, col, (r, r), r)
                    self._surface_cache[cache_key] = s
                    self._trim_surface_cache()
                else:
                    s = self._surface_cache[cache_key]
                
                surface.blit(s, (int(p['x'])-r, int(p['y'])-r))
            else:
                r = max(1, int(p['size']))
                smoke_alpha = max(20, int(150 * life_frac))
                cache_key = ('smoke', r, p['color'], smoke_alpha)
                
                if cache_key not in self._surface_cache:
                    s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                    sc = p['color'] + (smoke_alpha,)
                    pygame.draw.circle(s, sc, (r, r), r)
                    self._surface_cache[cache_key] = s
                    self._trim_surface_cache()
                else:
                    s = self._surface_cache[cache_key]
                
                surface.blit(s, (int(p['x'])-r, int(p['y'])-r))

    def draw_float_texts(self, surface: pygame.Surface, font: pygame.font.Font):
        """
        Draw floating text popups on the surface.
        Args:
            surface (pygame.Surface): Target surface.
            font (pygame.font.Font): Font used to render popup text.
        """
        for ft in self.float_texts:
            txt_surf = font.render(ft['text'], True, ft['color'])
            txt_surf.set_alpha(ft.get('alpha', 255))
            surface.blit(txt_surf, (int(ft['x']), int(ft['y'])))

    def clear(self):
        """Remove all particles and reset screen shake."""
        self.particles.clear()
        self.float_texts.clear()
        self.shake_amount = 0.0
        self.shake_time = 0.0
        self.shake_duration = 0.0
        self._surface_cache.clear()
    
    def start_shake(self, amount: float, duration: float):
        """
        Start or boost a screen shake effect.
        Args:
            amount (float): Maximum shake displacement in pixels.
            duration (float): Shake duration in seconds.
        """
        self.shake_amount = max(self.shake_amount, float(amount))
        self.shake_time = self.shake_duration = float(duration)
    
    def get_shake_offset(self):
        """
        Return a random x, y offset based on the current shake intensity.
        Returns:
            tuple[int, int]: Pixel offsets (ox, oy) to apply to the camera.
        """
        if self.shake_amount <= 0:
            return 0, 0
        frac = (self.shake_time / max(0.0001, self.shake_duration)) if self.shake_duration > 0 else 0
        cur_amp = self.shake_amount * (frac if frac > 0 else 1.0)
        ox = int(random.uniform(-cur_amp, cur_amp))
        oy = int(random.uniform(-cur_amp, cur_amp))
        return ox, oy