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
        self.ember_spawn_timer = 0.0
        self.ember_enabled = False
        
        # Surface cache for particle rendering
        self._surface_cache = {}
        
    def load_ember_image(self, image_path):
        """Load the ember particle image."""
        self.ember_image = pygame.image.load(image_path).convert_alpha()
        
    def enable_ember_spawning(self, enabled=True):
        """Enable or disable automatic ember spawning."""
        self.ember_enabled = enabled

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
            # Velocity moves diagonally from bottom-left to top-right
            vx = random.uniform(80, 120)  # Move right faster
            vy = random.uniform(-120, -90)  # Move up faster
            initial_size = random.uniform(2, 5)
            # Random size change behavior
            size_change_rate = random.uniform(-0.5, 0.5)  # Can grow or shrink
            self.particles.append({
                'x': x + random.uniform(-self.screen_width, 10),
                'y': y + random.uniform(-self.screen_height, self.screen_height),
                'vx': vx,
                'vy': vy,
                'life': life,
                'initial_life': life,
                'size': initial_size,
                'initial_size': initial_size,
                'size_change_rate': size_change_rate,
                'min_size': 1.0,
                'max_size': 8.0,
                'color': None,
                'gravity': 0,  # No gravity for floating embers
                'type': 'ember',
                'image': image,
                'angle': random.uniform(-20, 20)  # Random rotation angle ±25 degrees
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
        col = (255,0,0) if delta > 0 else (0,255,0)
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
            if self.ember_spawn_timer >= 0.1:  # Spawn every 0.1 seconds
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
                self.spawn_embers(spawn_x, spawn_y, count=1, image=self.ember_image)

    def draw_particles(self, surface: pygame.Surface):
        """
        Draw the particles on the given surface.
        Args:
            surface (pygame.Surface): The surface to draw on.
        """
        for p in self.particles:
            life_frac = max(0.0, min(1.0, p['life'] / max(0.001, p.get('initial_life', p['life']))))
            alpha = int(255 * life_frac)
            
            if p['type'] == 'ember' and p.get('image'):
                # Use image for ember particles
                img = p['image']
                # Scale image based on particle size
                scale_factor = p['size'] / 3.0  # Adjust base scale as needed
                angle = p.get('angle', 0)
                cache_key = (id(img), round(scale_factor, 2), alpha // 8, int(angle))
                
                if cache_key not in self._surface_cache:
                    scaled_img = pygame.transform.scale(img, (int(img.get_width() * scale_factor), int(img.get_height() * scale_factor)))
                    # Rotate the image
                    rotated_img = pygame.transform.rotate(scaled_img, angle)
                    rotated_img.set_alpha(alpha)
                    self._surface_cache[cache_key] = rotated_img
                    # Limit cache size
                    if len(self._surface_cache) > 100:
                        # Remove oldest entries (first 20)
                        for _ in range(20):
                            self._surface_cache.pop(next(iter(self._surface_cache)))
                else:
                    rotated_img = self._surface_cache[cache_key]
                
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
                    if len(self._surface_cache) > 100:
                        for _ in range(20):
                            self._surface_cache.pop(next(iter(self._surface_cache)))
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
                    if len(self._surface_cache) > 100:
                        for _ in range(20):
                            self._surface_cache.pop(next(iter(self._surface_cache)))
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