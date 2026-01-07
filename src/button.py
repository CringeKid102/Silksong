import pygame
import math
from typing import Tuple, Optional

class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, color: Tuple[int,int,int], hover_color: Tuple[int,int,int],
                 tooltip: str = "", icon: Optional[pygame.Surface] = None, hotkey: str = ""):
        """
        Initialize a button.
        Args:
            x (int): X position of the button.
            y (int): Y position of the button.
            width (int): Width of the button.
            height (int): Height of the button.
            text (str): Text to display on the button.
            color (Tuple[int,int,int]): Normal color of the button.
            hover_color (Tuple[int,int,int]): Color of the button when hovered.
            tooltip (str, optional): Tooltip text to display on hover.
            icon (Optional[pygame.Surface], optional): Icon to display on the button.
            hotkey (str, optional): Hotkey text to display on the button.
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.tooltip = tooltip
        self.icon = icon
        self.hotkey = hotkey
        self.active = True
        self.cooldown = 0.0
        self.max_cooldown = 0.0
        self.hover_t = 0.0
        self.scale_t = 1.0
        self.press_timer = 0.0
        self.press_duration = 0.12

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, show_tooltip: bool = False):
        """
        Draw the button on the screen.
        Args:
            screen (pygame.Surface): The surface to draw on.
            font (pygame.font.Font): The font to use for text.
            show_tooltip (bool): Whether to show the tooltip.
        """
        draw_color = (100,100,100) if not self.active else tuple(
            int(self.color[i] + (self.hover_color[i] - self.color[i]) * self.hover_t) for i in range(3))

        w = int(self.rect.width * self.scale_t)
        h = int(self.rect.height * self.scale_t)
        scaled_rect = pygame.Rect(0, 0, w, h)
        scaled_rect.center = self.rect.center

        pygame.draw.rect(screen, draw_color, scaled_rect, border_radius=6)
        pygame.draw.rect(screen, (255,255,255), scaled_rect, 2, border_radius=6)

        if self.cooldown > 0 and self.max_cooldown > 0:
            self._draw_radial_cooldown(screen, scaled_rect)
        
        if self.icon:
            icon_rect = self.icon.get_rect(center=(scaled_rect.left + 20, scaled_rect.centery))
            screen.blit(self.icon, icon_rect)

        text_surf = font.render(self.text, True, (255,255,255))
        if self.icon:
            text_rect = text_surf.get_rect(center=(scaled_rect.centerx + 10, scaled_rect.centery))
        else:
            text_rect = text_surf.get_rect(center=scaled_rect.center)
        screen.blit(text_surf, text_rect)

        if self.hotkey:
            small_font = pygame.font.Font(None, 18)
            key_surf = small_font.render(self.hotkey, True, (200,200,200))
            screen.blit(key_surf, (scaled_rect.left + 4, scaled_rect.top + 4))
        
        if show_tooltip and self.tooltip:
            self._draw_tooltip(screen, font)
    
    def _draw_radial_cooldown(self, screen: pygame.Surface, rect: pygame.Rect):
        """
        Draw radial cooldown indicator overlay
        Args:
            screen (pygame.Surface): The surface to draw on.
            rect (pygame.Rect): The rectangle area of the button.
        """
        progress = 1.0 - (self.cooldown / self.max_cooldown)
        center = rect.center
        radius = min(rect.width, rect.height) // 2 - 4
        
        # Create overlay surface
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay_center = (rect.width // 2, rect.height // 2)
        
        # Draw the "empty" part (what remains on cooldown) as a pie slice
        if progress < 1.0:
            # Create points for the unfilled arc (cooldown remaining)
            points = [overlay_center]
            start_angle = -math.pi / 2  # Start at top (12 o'clock)
            end_angle = start_angle + (2 * math.pi * (1.0 - progress))  # Sweep clockwise for remaining time
            
            # Generate arc points with more steps for smoother circle
            steps = 64
            for i in range(steps + 1):
                angle = start_angle + (end_angle - start_angle) * (i / steps)
                x = overlay_center[0] + radius * math.cos(angle)
                y = overlay_center[1] + radius * math.sin(angle)
                points.append((x, y))
            
            # Draw the darkened wedge showing time remaining
            if len(points) > 2:
                pygame.draw.polygon(overlay, (0, 0, 0, 180), points)
                # Draw outline for the arc
                if len(points) > 3:
                    pygame.draw.lines(overlay, (100, 100, 100, 200), False, points[1:], 2)
        
        screen.blit(overlay, rect.topleft)
         
        # Draw cooldown text in center
        cooldown_font = pygame.font.Font(None, 24)
        cd_text = cooldown_font.render(f"{math.ceil(self.cooldown)}s", True, (255,255,0))
        cd_rect = cd_text.get_rect(center=center)
        screen.blit(cd_text, cd_rect)

    def _draw_tooltip(self, screen: pygame.Surface, font: pygame.font.Font):
        """
        Draw the tooltip near the button.
        Args:
            screen (pygame.Surface): The surface to draw on.
            font (pygame.font.Font): The font to use for the tooltip text.
        """
        tooltip_font = pygame.font.Font(None, 20)
        tooltip_text = self.tooltip
        if self.cooldown > 0:
            tooltip_text += f"\n[Cooldown: {math.ceil(self.cooldown)}s remaining]"
        lines = tooltip_text.split('\n')

        max_width = max(tooltip_font.size(line)[0] for line in lines)
        line_height = tooltip_font.get_linesize()
        padding = 8

        tooltip_rect = pygame.Rect(
            self.rect.centerx - max_width // 2 - padding,
            self.rect.bottom + 10,
            max_width + padding * 2,
            line_height * len(lines) + padding * 2
        )

        bg_color = (60, 40, 40) if self.cooldown > 0 else (40, 40, 40)
        border_color = (255, 100, 100) if self.cooldown > 0 else (200, 200, 200)
        pygame.draw.rect(screen, bg_color, tooltip_rect, border_radius=4)
        pygame.draw.rect(screen, border_color, tooltip_rect, 1, border_radius=4)

        y = tooltip_rect.top + padding
        for line in lines:
            color = (255, 255, 100) if line.startswith("[Cooldown:") else (255,255,255)
            text_surf = tooltip_font.render(line, True, color)
            screen.blit(text_surf, (tooltip_rect.left + padding, y))
            y += line_height

    def update(self, dt: float):
        """
        Update the button's state.
        Args:
            dt (float): Delta time since last update.
        """
        if self.cooldown > 0:
            self.cooldown -= dt
            self.active = False
            if self.cooldown <= 0:
                self.cooldown = 0.0
                self.max_cooldown = 0.0
                self.active = True
        else:
            self.active = True

        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos) and self.active
        target = 1.0 if is_hover else 0.0
        lerp_speed = dt / 0.13 if 0.13 > 0 else 1.0
        self.hover_t += (target - self.hover_t) * min(1.0, lerp_speed)

        if self.press_timer > 0:
            self.press_timer = max(0.0, self.press_timer - dt)

        hover_scale = 1.0 + 0.05 * self.hover_t
        target_scale = hover_scale * (0.92 if self.press_timer > 0 else 1.0)
        self.scale_t += (target_scale - self.scale_t) * min(1.0, dt / 0.08)

    def is_clicked(self, pos):
        """
        Check if the button is currently clicked.
        Args:
            pos (Tuple[int,int]): Position to check.
        """
        return self.rect.collidepoint(pos) and self.active
    
    def is_hovered(self):
        """
        Check if the button is currently hovered.
        """
        mouse_pos = pygame.mouse.get_pos()
        return self.rect.collidepoint(mouse_pos)

    def press(self):
        """
        Trigger the button press animation.
        """
        self.press_timer = self.press_duration
        self.scale_t = max(0.0, self.scale_t * 0.92)
    
    def set_cooldown(self, cooldown_time: float):
        """
        Set the button's cooldown.
        Args:
            cooldown_time (float): Cooldown time in seconds.
        """
        self.cooldown = cooldown_time
        self.max_cooldown = cooldown_time