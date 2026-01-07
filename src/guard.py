import pygame
import math
from typing import Optional, Dict
from animation import Animation

class Guard:
    def __init__(self, patrol_id: int, patrol_time: float, animation_set: Dict[str, Animation] = None, default_anim: str = "idle"):
        """
        Initialize a guard with patrol parameters.
        Args:
            patrol_id (int): Unique identifier for the guard.
            patrol_time (float): Time taken to complete one patrol cycle.
            animation_set (Dict[str, Animation], optional): Set of animations for the guard.
            default_anim (str): Default animation name.
        """
        self.id = patrol_id
        self.patrol_time = patrol_time
        
        self.view_distance = 220
        self.view_angle = 60
        self.facing_angle = 0.0
        
        self.alert = False
        self._alert_sound_played = False

        self.current_time = 0.0
        self.position = 0.0
        self.alert = False
        self.alert_time = 0.0
        self.alert_flash = False

        self.animation_set = animation_set or {}
        self.current_anim_name = default_anim if default_anim in self.animation_set else None
        self.anim_offset_x = 0
        self.anim_offset_y = 0

    def update(self, dt: float):
        """
        Update the guard's state.
        Args:
            dt (float): Delta time since last update.
        """
        self.current_time += dt
        self.position = (self.current_time % self.patrol_time) / self.patrol_time

        if self.alert:
            self.alert_time += dt
            self.alert_flash = (int(self.alert_time / 0.3) % 2) == 0

        anim = self.animation_set.get(self.current_anim_name) if self.current_anim_name else None
        if anim:
            if self.alert and "alert" in self.animation_set and self.current_anim_name != "alert":
                anim = self.animation_set["alert"]
                self.current_anim_name = "alert"
            elif not self.alert and self.current_anim_name == "alert" and "idle" in self.animation_set:
                self.current_anim_name = "idle"
                self.alert_time = 0.0
                anim = self.animation_set["idle"]
            anim.update(dt)

    def draw(self, screen: pygame.Surface, x: int, y: int, width: int, height: int):
        """
        Draw the guard on the screen.
        Args:
            screen (pygame.Surface): The surface to draw on.
            x (int): X position of the patrol route.
            y (int): Y position of the patrol route.
            width (int): Width of the patrol route.
            height (int): Height of the patrol route.
        """
        route_rect = pygame.Rect(x, y, width, height)

        bg_color = (50, 50, 50) if self.alert and self.alert_flash else (100, 50, 50)
        pygame.draw.rect(screen, bg_color, route_rect)
        pygame.draw.rect(screen, (255,255,255), route_rect, 1)

        guard_x = x + int(self.position * width)
        anim = self.animation_set.get(self.current_anim_name) if self.current_anim_name else None
        if anim:
            anim.draw(screen, guard_x + self.anim_offset_x, y + height//2 + self.anim_offset_y, anchor="center")
        else:
            guard_color = (255,0,0) if self.alert else (0,0,255)
            pygame.draw.circle(screen, guard_color, (guard_x, y + height//2), 8)

        if self.alert and self.alert_flash:
            font = pygame.font.Font(None, 28)
            exclaim = font.render("!", True, (255,255,0))
            screen.blit(exclaim, (guard_x - exclaim.get_width()//2, y - 25))   

        font = pygame.font.Font(None, 20)
        label = font.render(f"Guard {self.id}", True, (255,255,255))
        screen.blit(label, (x, y - 20))

        if hasattr(self, 'game') and getattr(self.game, 'debug_draw', False):
            self.draw_fov(screen, (x + width//2, y + height//2))
        
    def is_in_sight(self, point):
        """Return True if the given point is within the guard's field of view."""
        gx, gy = self.position
        dx = point[0] - gx
        dy = point[1] - gy
        dist = math.hypot(dx, dy)
        if dist > self.view_distance:
            return False
        angle_to_point = math.degrees(math.atan2(dy, dx))
        diff = (angle_to_point - self.facing_angle + 360) % 360 - 180
        return abs(diff) <= self.view_angle / 2

    def draw_fov(self, screen, origin):
        """Draw the guard's field of view for debugging."""
        ox, oy = origin
        start_angle = math.radians(self.facing_angle - self.view_angle / 2)
        end_angle = math.radians(self.facing_angle + self.view_angle / 2)
        points = [(ox, oy)]
        steps = 12
        for i in range(steps + 1):
            a = start_angle + (end_angle - start_angle) * (i / steps)
            x = ox + self.view_distance * math.cos(a)
            y = oy + self.view_distance * math.sin(a)
            points.append((x, y))
        s = pygame.Surface(screen.get_width(), screen.get_height(), pygame.SRCALPHA)
        pygame.draw.polygon(s, (255, 255, 0, 40), points)
        screen.blit(s, (0, 0))