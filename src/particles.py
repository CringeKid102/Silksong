import pygame
import random
import math
import os
from typing import List, Dict, Tuple

class ParticleSystem:
    def __init__(self, screen_width=None, screen_height=None):
        """
        Initialize the particle system.
        Args:
            screen_width: Width of the screen for ember spawning
            screen_height: Height of the screen for ember spawning
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
        
    def load_ember_image(self, image_path):
        """Load the ember particle image."""
        self.ember_image = pygame.image.load(image_path).convert_alpha()

    def load_ember_round_image(self, image_path):
        """Load the round ember particle image."""
        self.ember_round_image = pygame.image.load(image_path).convert_alpha()
        
    def enable_ember_spawning(self, enabled=True):
        """Enable or disable automatic ember spawning."""
        self.ember_enabled = enabled

    def _trim_surface_cache(self):
        """Bound cache growth to prevent memory and CPU spikes."""
        if len(self._surface_cache) > self.max_cache_entries:
            drop_count = max(1, self.max_cache_entries // 4)
            for _ in range(drop_count):
                self._surface_cache.pop(next(iter(self._surface_cache)), None)

    def _get_cached_ember_surface(self, img, size, angle, alpha):
        """Fetch a cached transformed ember image with quantized buckets."""
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
        Spawn spark particles.
        Args:
            x (float): X position to spawn sparks.
            y (float): Y position to spawn sparks.
            count (int): Number of sparks to spawn.
            color (Tuple[int,int,int]): Color of the sparks.
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
        Spawn smoke particles.
        Args:
            x (float): X position to spawn smoke.
            y (float): Y position to spawn smoke.
            count (int): Number of smoke particles to spawn.
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

    def spawn_embers(self, x: float, y: float, count: int = 1, image=None):
        """
        Spawn ember particles that float from bottom left to top right.
        Args:
            x (float): X position to spawn embers.
            y (float): Y position to spawn embers.
            count (int): Number of embers to spawn.
            image: Pygame surface to use as ember image.
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
        Spawn round background ember particles with depth-based velocity and sin sway.
        No size change over lifetime. Biased toward small sizes to stay in the background.
        Args:
            x (float): X position to spawn embers.
            y (float): Y position to spawn embers.
            count (int): Number of embers to spawn.
            image: Pygame surface to use as ember image (falls back to ember_round_image).
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
        Add a floating text popup for damage or healing.
        Args:
            delta (int): Amount of damage (negative) or healing (positive).
            x (float): X position for the popup.
            y (float): Y position for the popup.
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
        Update the particle system.
        Args:
            dt (float): Delta time since last update.
        """
        # Update particles
        alive_particles = []
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
            
            if p['life'] > 0:
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
        Draw the particles on the given surface.
        Args:
            surface (pygame.Surface): The surface to draw on.
            size_min (float): Minimum size to draw (inclusive).
            size_max (float): Maximum size to draw (inclusive).
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
        Draw the floating text popups on the given surface.
        Args:
            surface (pygame.Surface): The surface to draw on.
            font (pygame.font.Font): The font to use for the text.
        """
        for ft in self.float_texts:
            txt_surf = font.render(ft['text'], True, ft['color'])
            txt_surf.set_alpha(ft.get('alpha', 255))
            surface.blit(txt_surf, (int(ft['x']), int(ft['y'])))

    def clear(self):
        """
        Clear all particles and floating texts.
        """
        self.particles.clear()
        self.float_texts.clear()
        self.shake_amount = 0.0
        self.shake_time = 0.0
        self.shake_duration = 0.0
        self._surface_cache.clear()
    
    def start_shake(self, amount: float, duration: float):
        """
        Start or boost a screen shake effect
        """
        self.shake_amount = max(self.shake_amount, float(amount))
        self.shake_time = self.shake_duration = float(duration)
    
    def get_shake_offset(self):
        """
        Return an (x,y) random offset based on current shake state
        """
        if self.shake_amount <= 0:
            return 0, 0
        frac = (self.shake_time / max(0.0001, self.shake_duration)) if self.shake_duration > 0 else 0
        cur_amp = self.shake_amount * (frac if frac > 0 else 1.0)
        ox = int(random.uniform(-cur_amp, cur_amp))
        oy = int(random.uniform(-cur_amp, cur_amp))
        return ox, oy