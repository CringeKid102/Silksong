import pygame
import os
from typing import Optional, Callable, Dict, Any
from enum import Enum

class TransitionType(Enum):
    FADE_COLOR = "fade_color"
    FADE_VIDEO = "fade_video"
    FADE_IMAGE = "fade_image"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    CIRCLE_EXPAND = "circle_expand"
    CIRCLE_CONTRACT = "circle_contract"

class TransitionManager:
    def __init__(self, 
                 screen_width: int, 
                 screen_height: int, 
                 default_speed: float, 
                 video_speed_multiplier: float = 1.0, 
                 video_loop: bool = True):
        """
        Transition manager for pygame applications.
        
        Args:
            screen_width (int): Width of the screen.
            screen_height (int): Height of the screen.
            default_speed (float): Speed of the transition.
            video_speed_multiplier (float): Speed multiplier for video transitions.
            video_loop (bool): Whether to loop video transitions.
        """
        self.width = screen_width
        self.height = screen_height
        self.default_speed = default_speed

        # Transition state
        self.active = False
        self.phase = "none"  # "fade_in", "fade_out", "slide_in", "slide_out"
        self.progress = 0.0
        self.speed = default_speed
        self.target_state = None
        self.complete_callback = None
        self.state_change_callback = None
        
        # Content properties
        self.transition_type = TransitionType.FADE_COLOR
        self.fade_color = (0, 0, 0)
        self.video_cap = None
        self.current_frame = None
        self.image_surface = None
        self.slide_offset = 0.0
        self.circle_radius = 0.0

        # Video properties
        self.video_speed_multiplier = video_speed_multiplier
        self.video_loop = video_loop

        # Animation easing
        self.easing_function = self._linear_ease

    def start_transition(self, 
                     target_state: Any = None, 
                     transition_type: TransitionType = TransitionType.FADE_COLOR,
                     speed: Optional[float] = None,
                     completion_callback: Optional[Callable] = None,
                     state_change_callback: Optional[Callable] = None,
                     easing: str = "linear",
                     **kwargs) -> bool:
        """
        Start a transition.

        Args:
            target_state (Any): The state to transition to.
            transition_type (TransitionType): Type of transition.
            speed (Optional[float]): Speed of the transition.
            completion_callback (Optional[Callable]): Callback when transition completes.
            state_change_callback (Optional[Callable]): Callback when state changes.
            easing (str): Easing function name.
            **kwargs: Additional parameters for specific transitions.
        
        Transition-specific kwargs:
            FADE_COLOR: color=(r,g,b)
            FADE_VIDEO: video_path=str, video_loop=bool, video_speed=float
            FADE_IMAGE: image_path=str
            SLIDE_*: color=(r,g,b), surface=pygame.Surface
            CIRCLE_*: color=(r,g,b), center=(x,y)

        Returns:
            bool: True if transition started, False if already active.
        """
        if self.active:
            return False  # Transition already in progress
        
        self.active = True
        self.target_state = target_state
        self.transition_type = transition_type
        self.speed = speed if speed is not None else self.default_speed
        self.complete_callback = completion_callback
        self.state_change_callback = state_change_callback
        self.progress = 0.0
        self.slide_offset = 0.0
        self.circle_radius = 0.0

        # Set easing function
        self.easing_function = getattr(self, f"_{easing}_ease", self._linear_ease)

        # Set initial phase
        if transition_type in [TransitionType.FADE_COLOR, TransitionType.FADE_VIDEO, TransitionType.FADE_IMAGE]:
            self.phase = "in"
        elif "SLIDE" in transition_type.value.upper():
            self.phase = "in"
        elif "CIRCLE" in transition_type.value.upper():
            self.phase = "in"
        else:
            self.phase = "in"
        
        # Configure transition content
        return self._configure_content(**kwargs)
    
    def _configure_content(self, **kwargs) -> bool:
        """
        Configure content based on transition type.
        """
        try:
            if self.transition_type == TransitionType.FADE_COLOR:
                self.fade_color = kwargs.get("color", (0, 0, 0))
            elif self.transition_type == TransitionType.FADE_VIDEO:
                video_path = kwargs.get("video_path")
                if not video_path:
                    print("FADE_VIDEO requires 'video_path' parameter.") 
                    return False
                
                if not os.path.exists(video_path):
                    print(f"Video file not found: {video_path}")
                    return False
                
                try:
                    import cv2
                    self.video_cap = cv2.VideoCapture(video_path)
                    if not self.video_cap.isOpened():
                        print(f"Failed to open video file: {video_path}")
                        return False
                    
                    self.video_speed_multiplier = kwargs.get("video_speed", 2.0)
                    self.video_loop = kwargs.get("video_loop", True)
                    self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
                except ImportError:
                    print("OpenCV is required for video transitions. Please install it via 'pip install opencv-python'.")
                    return False
            
            elif self.transition_type == TransitionType.FADE_IMAGE:
                image_path = kwargs.get("image_path")
                if not image_path:
                    print("FADE_IMAGE requires 'image_path' parameter.")
                    return False
                
                if not os.path.exists(image_path):
                    print(f"Image file not found: {image_path}")
                    return False
                
                self.image_surface = pygame.image.load(image_path).convert()
                self.image_surface = pygame.transform.scale(self.image_surface, (self.width, self.height))
            
            elif "SLIDE" in self.transition_type.value.upper():
                self.fade_color = kwargs.get("color", (0, 0, 0))
                custom_surface = kwargs.get("surface")
                if custom_surface:
                    self.image_surface = pygame.transform.scale(custom_surface, (self.width, self.height))
            
            elif "CIRCLE" in self.transition_type.value.upper():
                self.fade_color = kwargs.get("color", (0, 0, 0))
                self.circle_center = kwargs.get("center", (self.width // 2, self.height // 2))
            
            return True
        
        except Exception as e:
            print(f"Error configuring transition content: {e}")
            return False
    
    def update(self, dt: float):
        """
        Update the transition state.

        Args:
            dt (float): Delta time since last update.

        Returns:
            dict: Status of the transition with keys:
                - active (bool): Whether the transition is active.
                - state_changed (bool): Whether the state has changed during this update.
                - completed (bool): Whether the transition has completed.
                - phase (str): Current phase of the transition.
                - progress (float): Progress of the transition (0.0 to 1.0).
        """
        result = {
            "active": self.active,
            "state_changed": False,
            "completed": False,
            "phase": self.phase,
            "progress": self.progress,
        }
        if not self.active:
            return result

        progress_delta = (self.speed / 255.0) * dt
        self.progress += progress_delta

        if self.phase == 'in':
            if self.progress >= 0.5:
                self.phase = 'out'
                result['state_changed'] = True
                if self.state_change_callback:
                    self.state_change_callback(self.target_state)

        elif self.phase == 'out':
            if self.progress >= 1.0:
                self._complete_transition()
                result['completed'] = True
        
        # Update any dynamic content (e.g., video frames)
        self._update_content()

        result['progress'] = self.progress
        return result

    def _update_content(self):
        """
        Update content based on transition type and progress.
        """
        if self.transition_type == TransitionType.FADE_VIDEO and self.video_cap is not None:
            try:
                import cv2

                steps = max(1, int(self.video_speed_multiplier))
                for _ in range(steps - 1):
                    ret, _ = self.video_cap.read()
                    if not ret:
                        if self.video_loop:
                            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        break
                ret, frame = self.video_cap.read()
                if not ret:
                    if self.video_loop:
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.video_cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Pygame expects (width, height) orientation; swap axes like elsewhere in project
                    surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                    self.current_frame = pygame.transform.scale(surf, (self.width, self.height)).convert()
            except Exception as e:
                print(f"Error updating video frame: {e}")
        
    def _complete_transition(self):
        """
        Complete the transition and reset state.
        """
        self.active = False
        self.phase = "complete"
        self.progress = 1.0

        if self.video_cap:
            try:
                self.video_cap.release()
            except:
                pass
            self.video_cap = None
        
        if self.complete_callback:
            self.complete_callback()
    
    def draw(self, surface: pygame.Surface, alpha_override: Optional[float] = None):
        """
        Draw the transition effect on the given surface.

        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha_override (Optional[float]): Override alpha value for drawing.
        """
        if not self.active:
            return

        if alpha_override is not None:
            alpha = alpha_override * 255
        else:
            eased_progress = self.easing_function(self.progress)

            if self.phase == "in":
                alpha = (eased_progress * 2.0) * 255
            else:
                alpha = (2.0 - eased_progress * 2.0) * 255

            alpha = max(0, min(255, int(alpha)))
        
        self._draw_transition(surface, alpha)
    
    def _draw_transition(self, surface: pygame.Surface, alpha: float):
        """
        Draw the specific transition effect.
        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha (float): Alpha value for the transition.
        """
        if alpha <= 0:
            return

        if self.transition_type == TransitionType.FADE_COLOR:
            self._draw_color_fade(surface, alpha)
        
        elif self.transition_type == TransitionType.FADE_VIDEO:
            self._draw_video_fade(surface, alpha)
        
        elif self.transition_type == TransitionType.FADE_IMAGE:
            self._draw_image_fade(surface, alpha)
        
        elif self.transition_type in [TransitionType.SLIDE_LEFT, TransitionType.SLIDE_RIGHT,
                                      TransitionType.SLIDE_UP, TransitionType.SLIDE_DOWN]:
            self._draw_slide(surface, alpha)
        
        elif self.transition_type in [TransitionType.CIRCLE_EXPAND, TransitionType.CIRCLE_CONTRACT]:
            self._draw_circle(surface, alpha)
        
        elif self.transition_type in [TransitionType.WIPE_LEFT, TransitionType.WIPE_RIGHT]:
            self._draw_wipe(surface, alpha)
        
    def _draw_color_fade(self, surface: pygame.Surface, alpha: float):
        """
        Draw a color fade transition.
        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha (float): Alpha value for the fade.
        """
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill(self.fade_color)
        overlay.set_alpha(alpha)
        surface.blit(overlay, (0, 0))
    
    def _draw_video_fade(self, surface: pygame.Surface, alpha: float):
        """
        Draw a video fade transition.
        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha (float): Alpha value for the fade.
        """
        if self.current_frame:
            video_surface = self.current_frame.copy()
            video_surface.set_alpha(alpha)
            surface.blit(video_surface, (0, 0))
    
    def _draw_image_fade(self, surface: pygame.Surface, alpha: float):
        """
        Draw an image fade transition.
        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha (float): Alpha value for the fade.
        """
        if self.image_surface:
            image_surface = self.image_surface.copy()
            image_surface.set_alpha(alpha)
            surface.blit(image_surface, (0, 0))
    
    def _draw_slide(self, surface: pygame.Surface, alpha: float):
        """
        Draw a slide transition.
        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha (float): Alpha value for the slide.
        """
        slide_progress = self.easing_function(self.progress)

        if self.transition_type == TransitionType.SLIDE_LEFT:
            x = -self.width + (slide_progress * self.width)
            y = 0
        elif self.transition_type == TransitionType.SLIDE_RIGHT:
            x = self.width - (slide_progress * self.width)
            y = 0
        elif self.transition_type == TransitionType.SLIDE_UP:
            x = 0
            y = -self.height + (slide_progress * self.height)
        else: # SLIDE_DOWN
            x = 0
            y = self.height - (slide_progress * self.height)
        
        if self.image_surface:
            surface.blit(self.image_surface, (x, y))
        else:
            overlay = pygame.Surface((self.width, self.height))
            overlay.fill(self.fade_color)
            surface.blit(overlay, (x, y))
    
    def _draw_circle(self, surface: pygame.Surface, alpha: float):
        """
        Draw a circle transition.
        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha (float): Alpha value for the circle.
        """
        circle_progress = self.easing_function(self.progress)

        max_radius = int(((self.width ** 2 + self.height ** 2) ** 0.5) / 2) + 50

        if self.transition_type == TransitionType.CIRCLE_EXPAND:
            radius = int(circle_progress * max_radius)
        else:  # CIRCLE_CONTRACT
            radius = int((1.0 - circle_progress) * max_radius)

        mask = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        mask.fill(self.fade_color)

        if radius > 0:
            circle_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            if self.transition_type == TransitionType.CIRCLE_EXPAND:
                pygame.draw.circle(circle_surface, (0, 0, 0, 0), self.circle_center, radius)
                mask.blit(circle_surface, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            else:  # CIRCLE_CONTRACT
                pygame.draw.circle(mask, (0, 0, 0, 0), self.circle_center, radius)
        
        mask.set_alpha(alpha)
        surface.blit(mask, (0, 0))
    
    def _draw_wipe(self, surface: pygame.Surface, alpha: float):
        """
        Draw a wipe transition.
        Args:
            surface (pygame.Surface): The surface to draw on.
            alpha (float): Alpha value for the wipe.
        """
        wipe_progress = self.easing_function(self.progress)

        if self.transition_type == TransitionType.WIPE_LEFT:
            width = int(self.width * wipe_progress)
            rect = pygame.Rect(0, 0, width, self.height)
        else:  # WIPE_RIGHT
            width = int(self.width * wipe_progress)
            rect = pygame.Rect(self.width - width, 0, width, self.height)

        if rect.width > 0:
            overlay = pygame.Surface((rect.width, rect.height))
            overlay.fill(self.fade_color)
            overlay.set_alpha(alpha)
            surface.blit(overlay, rect.topleft)

    # EASING FUNCTIONS
    def _linear_ease(self, t: float) -> float:
        return max(0.0, min(1.0, t))

    def _ease_in_ease(self, t: float) -> float:
        t = self._linear_ease(t)
        return t * t

    def _ease_out_ease(self, t: float) -> float:
        t = self._linear_ease(t)
        return 1 - (1 - t) * (1 - t)

    def _ease_in_out_ease(self, t: float) -> float:
        t = self._linear_ease(t)
        if t < 0.5:
            return 2 * t * t
        return 1 - pow(-2 * t + 2, 2) / 2
    
    # Utility functions
    def is_active(self) -> bool:
        """
        Check if a transition is currently active.
        Returns:
            bool: True if active, False otherwise.
        """
        return self.active

    def clear(self):
        """
        clear resources used by the transition manager.
        """
        if self.video_cap:
            try:
                self.video_cap.release()
            except:
                pass
            self.video_cap = None
        
        self.current_frame = None
        self.image_surface = None
        self.active = False

