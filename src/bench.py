import pygame
from asset_paths import resolve_image_path


class Bench:
    """Bench save point for resting and healing."""
    
    def __init__(self, x, y):
        """Create a bench at the given bottom-center position."""
        image_path = resolve_image_path("bench.png")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.25
        scaled_size = (int(source_width * scale_factor), int(source_height * scale_factor))
        self.image = pygame.transform.scale(self.image, scaled_size)
        
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)

    def draw(self, screen, camera_x=0, camera_y=0, look_y_offset=0, screen_offset=(0, 0)):
        draw_rect = self.rect.copy()
        draw_rect.x -= int(camera_x)
        draw_rect.y -= int(camera_y + look_y_offset)
        draw_rect.x += int(screen_offset[0])
        draw_rect.y += int(screen_offset[1])
        screen.blit(self.image, draw_rect)