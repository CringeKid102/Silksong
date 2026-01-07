import pygame
from typing import Optional, Callable

class Slider:
    """
    Slider control for adjusting numeric values.
    """

    def __init__(self, x: int, y: int, width: int, height: int, min_val: float, max_val: float,
                 initial_val: float, label: str = "", callback: Optional[Callable] = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.label = label
        self.callback = callback
        self.dragging = False
        self.handle_width = 20
        self.update_handle_pos()
    
    def update_handle_pos(self):
        """Update the handle position based on the current value."""
        progress = (self.value - self.min_val) / (self.max_val - self.min_val)
        handle_x = self.rect.x + progress * (self.rect.width - self.handle_width)
        self.handle_rect = pygame.Rect(handle_x, self.rect.y - 5, self.handle_width, self.rect.height + 10)

    def handle_event(self, event):
        """Handle mouse events for the slider."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.handle_rect.collidepoint(event.pos):
                self.dragging = True
            elif self.rect.collidepoint(event.pos):
                rel_x = event.pos[0] - self.rect.x
                progress = rel_x / self.rect.width
                self.value = self.min_val + progress * (self.max_val - self.min_val)
                self.value = max(self.min_val, min(self.value, self.max_val))
                self.update_handle_pos()
                if self.callback:
                    self.callback(self.value)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                rel_x = event.pos[0] - self.rect.x
                progress = rel_x / self.rect.width
                self.value = self.min_val + progress * (self.max_val - self.min_val)
                self.value = max(self.min_val, min(self.value, self.max_val))
                self.update_handle_pos()
                if self.callback:
                    self.callback(self.value)
        
    def draw(self, surface, font=None):
        """Draw the slider on the given surface."""
        pygame.draw.rect(surface, (100, 100, 100), self.rect, border_radius=self.rect.height//2)
        fill_width = int((self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(surface, (0, 150, 255), fill_rect, border_radius=self.rect.height//2)
        handle_color = (255, 255, 255) if not self.dragging else (200, 200, 200)
        pygame.draw.rect(surface, handle_color, self.handle_rect, border_radius=5)
        if self.label and font:
            text = font.render(f"{self.label}: {int(self.value * 100)}%", True, (255, 255, 255))
            surface.blit(text, (self.rect.x, self.rect.y - 25))