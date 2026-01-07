import pygame
import random
import math
from typing import List, Dict, Tuple

class ParticleSystem:
    def __init__(self):
        """
        Initialize the particle system.
        """
        self.particles: List[Dict] = []
        self.float_texts: List[Dict] = []
        # Screen shake
        self.shake_amount = 0.0
        self.shake_time = 0.0
        self.shake_duration = 0.0

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
        for p in list(self.particles):
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += p.get('gravity', 0) * dt
            p['life'] -= dt
            if p['life'] <= 0:
                self.particles.remove(p)

        for ft in list(self.float_texts):
            ft['y'] += ft['vy'] * dt
            ft['time'] -= dt
            ft['alpha'] = max(0, int(255 * (ft['time'] / max(0.01, ft.get('duration', 1.0)))))
            if ft['time'] <= 0:
                self.float_texts.remove(ft)
        
        # decay screen shake
        if self.shake_time > 0:
            self.shake_time -= dt
            if self.shake_time <= 0:
                self.shake_amount = 0.0
                self.shake_time = 0.0
                self.shake_duration = 0.0
        else:
            self.shake_amount = max(0.0, self.shake_amount - 8.0 * dt)

    def draw_particles(self, surface: pygame.Surface):
        """
        Draw the particles on the given surface.
        Args:
            surface (pygame.Surface): The surface to draw on.
        """
        for p in self.particles:
            life_frac = max(0.0, min(1.0, p['life'] / max(0.001, p.get('initial_life', p['life']))))
            alpha = int(255 * life_frac)
            if p['type'] == 'spark':
                r = max(1, int(p['size']))
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                col = p['color'] + (alpha,)
                pygame.draw.circle(s, col, (r, r), r)
                surface.blit(s, (int(p['x'])-r, int(p['y'])-r))
            else:
                r = max(1, int(p['size']))
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                sc = p['color'] + (max(20, int(150 * life_frac)),)
                pygame.draw.circle(s, sc, (r, r), r)
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