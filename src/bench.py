import pygame
import os


class Bench:
    """Bench class for the game."""
    
    def __init__(self, x, y):
        """
        Initialize the bench
        Args:
            x (float): Initial x position (sprite bottom-center X)
            y (float): Initial y position (sprite bottom-center Y)
        """
        image_path = os.path.join(os.path.dirname(__file__), "../assets/images/bench.png")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.25
        scaled_size = (int(source_width * scale_factor), int(source_height * scale_factor))
        self.image = pygame.transform.scale(self.image, scaled_size)
        
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)

    def draw(self, screen, camera_x=0, camera_y=0, look_y_offset=0):
        draw_rect = self.rect.copy()
        draw_rect.x -= int(camera_x)
        draw_rect.y -= int(camera_y + look_y_offset)
        screen.blit(self.image, draw_rect)