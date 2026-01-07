import pygame
import random
import math
import time

class Minigame:
    def __init__(self, width, height, difficulty='normal'):
        self.width = width
        self.height = height
        self.difficulty = difficulty
        self.active = False
        self.complete = False
        self.success_count = 0
        self.fail_count = 0
        self.round_num = 0
    
    def start(self):
        self.active = True
        self.complete = False
        self.success_count = 0
        self.fail_count = 0
        self.round_num = 0
    
    def update(self, dt):
        pass

    def draw(self, surface):
        pass

    def handle_input(self, event):
        pass

    def is_complete(self):
        return self.complete
    
    def get_result(self):
        total = self.success_count + self.fail_count
        if total == 0:
            return (False, 20)
        success_rate = self.success_count / total
        if success_rate >= 0.7:
            return (True, -int(success_rate * 15))
        else:
            return (False, int((1 - success_rate) * 20))

def KeyboardMinigame(Minigame):
    """A minigame where players must press specific keys in sequence."""
    def __init__(self, width, height, difficulty='normal'):
        super().__init__(width, height, difficulty)
        self.letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.max_rounds = {'easy': 4, 'normal': 6, 'hard': 8}[difficulty]
        self.speed = {'easy': 1.0, 'normal': 1.5, 'hard': 2.0}[difficulty]
        self.current_letter = ''
        self.circle_radius = 0.0
        self.target_radius = 50
        self.tolerance = 20
        self.state = 'waiting'
        self.state_timer = 0.0
    
    def start(self):
        super().start()
        self.next_round()
    
    def next_round(self):
        self.round_num += 1
        if self.round_num > self.max_rounds:
            self.complete = True
            return
        self.current_letter = random.choice(self.letters)
        self.circle_radius = 200
        self.state = 'shrinking'
        self.current_speed = self.speed * (1 + self.round_num * 0.1)
    
    def update(self, dt):
        if not self.active or self.complete:
            return
        
        if self.state == 'shrinking':
            self.circle_radius -= self.current_speed * dt * 100
            if self.circle_radius <= self.target_radius - self.tolerance:
                self.fail_count += 1
                self.state = 'fail'
                self.state_timer = 1.0
        elif self.state in ['success', 'fail']:
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.next_round()
    
    def draw(self, surface):
        if not self.active:
            return
        
        center_x, center_y = self.width // 2, self.height // 2

        if self.state == 'shrinking':
            pygame.draw.circle(surface, (255, 0, 0), (center_x, center_y), int(self.circle_radius), 3)
        
        pygame.draw.circle(surface, (255, 255, 0), (center_x, center_y), self.target_radius + self.tolerance, 2)
        pygame.draw.circle(surface, (0, 255, 0), (center_x, center_y), self.target_radius - self.tolerance, 2)

        pygame.draw.circle(surface, (100, 100, 255), (center_x, center_y), self.target_radius)
        font = pygame.font.Font(None, 48)
        text = font.render(self.current_letter, True, (255, 255, 255))
        text_rect = text.get_rect(center=(center_x, center_y))
        surface.blit(text, text_rect)

        if self.state == 'success':
            status = font.render("SUCCESS!", True, (0, 255, 0))
        elif self.state == 'fail':
            status = font.render("MISSED!", True, (255, 0, 0))
        else:
            status = None
        
        if status:
            status_rect= status.get_rect(center=(center_x, center_y - 100))
            surface.blit(status, status_rect)
        
        small_font = pygame.font.Font(None, 24)
        round_text = small_font.render(f"Round {self.success_count}/{self.round_num - 1 if self.round_num > 1 else 0}", True, (255, 255, 255))
        surface.blit(round_text, (center_x - 50, center_y + 130))

    def handle_input(self, event):
        if not self.active or self.complete:
            return
        
        if event.type == pygame.KEYDOWN and self.state == 'shrinking':
            pressed_key = pygame.key.name(event.key).upper()
            if pressed_key == self.current_letter:
                if abs(self.circle_radius - self.target_radius) <= self.tolerance:
                    self.success_count += 1
                    self.state = 'success'
                else:
                    self.fail_count += 1
                    self.state = 'fail'
                self.state_timer = 0.5