import pygame
from asset_paths import resolve_image_path

class Tutorial:
    """Tutorial overlay shown once after the intro cutscene for new saves."""
    # slides
    SLIDES = [
        {
            "label": "Movement & Exploration",
            "image": resolve_image_path("tutorial_move.png"),
            "hint": (
                "Use Arrow Keys or A / D to run\n"
                "Press Space to jump  —  hold longer for a higher jump\n"
                "Follow the signs and explore the world to find secrets and upgrades"
            ),
        },
        {
            "label": "Combat Basics",
            "image": resolve_image_path("tutorial_combat.png"),
            "hint": (
                "Press J to attack with your needle\n"
                "Attack from above using W + J to bounce off enemies\n"
                "Attack from below using S + J to attack upward\n"
                "Time your strikes carefully to avoid taking damage"
            ),
        },
        {
            "label": "Silk Mechanics",
            "image": resolve_image_path("tutorial_silk.png"),
            "hint": (
                "Hit enemies to fill your Silk gauge\n"
                "Fill your Silk gauge to heal by pressing L SHIFT\n"
                "Keep your gauge full to stay at full strength"
            ),
        },
        {
            "label": "Survival Tips",
            "image": resolve_image_path("tutorial_survival.png"),
            "hint": (
                "Rest at benches to restore your health\n"
                "You respawn at your last bench if you fall\n"
                "Dodge enemy attacks and use the environment to your advantage\n"
            ),
        },
    ]

    # transition speed (fraction of screen width per second)
    TRANSITION_SPEED = 3.5   # fraction of screen per second (full slide ≈ 0.29 s)

    # colors and styling
    _OVERLAY_ALPHA    = 210
    _PANEL_COLOR      = (35,  33,  38 )
    _PLACEHOLDER_COLOR= (55,  52,  58 )
    _BORDER_COLOR     = (140, 125, 105)
    _TEXT_COLOR       = (235, 225, 210)
    _HINT_COLOR       = (175, 165, 150)
    _DOT_ACTIVE_COLOR = (220, 195, 160)
    _DOT_IDLE_COLOR   = (80,  76,  72 )
    _NEXT_IDLE_COLOR  = (210, 185, 150)
    _NEXT_HOVER_COLOR = (255, 235, 195)
    _NEXT_BG_COLOR    = (55,  50,  45 )

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize the tutorial overlay.
        Args:
            screen_width (int): Logical screen width in pixels.
            screen_height (int): Logical screen height in pixels.
        """
        self.w = screen_width
        self.h = screen_height

        self.current_slide = 0
        self.on_complete = None   # callable – set by the owner

        # Transition state
        self._transitioning   = False
        self._transition_t    = 0.0   # 0.0 → 1.0
        self._next_slide_idx  = 0
        self._next_hovered    = False

        # Full-screen translucent overlay (built once)
        self._overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        self._overlay.fill((20, 20, 25, self._OVERLAY_ALPHA))

        # Panel geometry
        panel_w = int(screen_width  * 0.72)
        panel_h = int(screen_height * 0.78)
        self._panel_rect = pygame.Rect(
            (screen_width  - panel_w) // 2,
            (screen_height - panel_h) // 2,
            panel_w,
            panel_h,
        )

        # Image placeholder area (local coords, relative to panel top-left)
        img_margin = 30
        img_h      = int(panel_h * 0.58)
        self._img_local = pygame.Rect(img_margin, img_margin,
                                      panel_w - img_margin * 2, img_h)

        # "Next >" button – fixed screen position (bottom-right of panel)
        btn_w, btn_h = 190, 54
        self._next_btn_rect = pygame.Rect(
            self._panel_rect.right  - btn_w - 24,
            self._panel_rect.bottom - btn_h - 22,
            btn_w,
            btn_h,
        )

        # Dot progress indicators (y inside panel, centered horizontally)
        self._dot_panel_y = panel_h - (btn_h + 22 + 18)   # just above button

        # Lazy font references (populated on first draw via config cache)
        self._font_label = None
        self._font_hint  = None
        self._font_ph    = None

        # Pre-load slide images (None where image key is missing or file not found)
        self._slide_images = []
        for slide in self.SLIDES:
            img_surf = None
            img_file = slide.get("image")
            if img_file:
                try:
                    raw = pygame.image.load(resolve_image_path(img_file)).convert_alpha()
                    # Scale to fit the placeholder box while preserving aspect ratio
                    box_w = self._img_local.width
                    box_h = self._img_local.height
                    src_w, src_h = raw.get_size()
                    scale = min(box_w / src_w, box_h / src_h)
                    img_surf = pygame.transform.smoothscale(
                        raw, (int(src_w * scale), int(src_h * scale))
                    )
                except (FileNotFoundError, pygame.error):
                    img_surf = None
            self._slide_images.append(img_surf)

    # font loading helper (called on first draw to populate font references from config)
    def _ensure_fonts(self):
        """Populate font references from config if not already done."""
        if self._font_label is not None:
            return
        import config
        self._font_label = config.get_title_font(32)
        self._font_hint  = config.get_font(26)
        self._font_ph    = config.get_font(22)

    # slide rendering helper (draws slide *idx* with panel shifted by *x_offset* pixels for transition animation)
    def _draw_slide(self, surface: pygame.Surface, idx: int, x_offset: int):
        """
        Render slide *idx* with its panel shifted by *x_offset* pixels.
        Args:
            surface (pygame.Surface): Target surface to render onto.
            idx (int): Index of the slide to render.
            x_offset (int): Horizontal offset in pixels for transition animation.
        """
        if not (0 <= idx < len(self.SLIDES)):
            return

        slide = self.SLIDES[idx]
        pw    = self._panel_rect.width
        ph    = self._panel_rect.height
        px    = self._panel_rect.x + x_offset
        py    = self._panel_rect.y

        # panel background with border
        panel_r = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(surface, self._PANEL_COLOR,   panel_r, border_radius=14)
        pygame.draw.rect(surface, self._BORDER_COLOR,  panel_r, width=2, border_radius=14)

        #
        img_r = pygame.Rect(
            px + self._img_local.x,
            py + self._img_local.y,
            self._img_local.width,
            self._img_local.height,
        )
        img_surf = self._slide_images[idx] if idx < len(self._slide_images) else None
        if img_surf is not None:
            blit_rect = img_surf.get_rect(center=img_r.center)
            surface.blit(img_surf, blit_rect)

        #  slide title
        text_x  = px + 30
        title_y = py + self._img_local.bottom + 26
        title_s = self._font_label.render(slide["label"], True, self._TEXT_COLOR)
        surface.blit(title_s, (text_x, title_y))

        # hint text (multi-line)
        hint_y = title_y + title_s.get_height() + 14
        for line in slide["hint"].split("\n"):
            ls = self._font_hint.render(line, True, self._HINT_COLOR)
            surface.blit(ls, (text_x, hint_y))
            hint_y += ls.get_height() + 6

        # dot indicators (centered horizontally below the panel, above the button)
        n        = len(self.SLIDES)
        dot_r    = 6
        gap      = 22
        dot_y    = py + self._dot_panel_y
        dot_cx   = px + pw // 2
        start_dx = dot_cx - (n - 1) * gap // 2
        for i in range(n):
            color = self._DOT_ACTIVE_COLOR if i == idx else self._DOT_IDLE_COLOR
            radius = dot_r if i == idx else 5
            pygame.draw.circle(surface, color, (int(start_dx + i * gap), dot_y), radius)

    # interaction and state update methods
    def update(self, dt: float, mouse_pos: tuple):
        """
        Advance transition animation and track button hover.
        Args:
            dt (float): Time elapsed in seconds since the last update.
            mouse_pos (tuple): Current mouse position in screen coordinates.
        """
        if self._transitioning:
            self._transition_t = min(1.0, self._transition_t + dt * self.TRANSITION_SPEED)
            if self._transition_t >= 1.0:
                self.current_slide  = self._next_slide_idx
                self._transitioning = False
                self._transition_t  = 0.0
        else:
            self._next_hovered = self._next_btn_rect.collidepoint(mouse_pos)

    def draw(self, surface: pygame.Surface):
        """
        Render the tutorial overlay onto *surface*.
        Args:
            surface (pygame.Surface): Target surface (usually the main screen) to render onto.
        """
        self._ensure_fonts()

        # Semi-transparent dark backdrop
        surface.blit(self._overlay, (0, 0))

        if self._transitioning:
            t       = self._transition_t
            out_off = -int(t * self.w)               # current exits left
            in_off  = int((1.0 - t) * self.w)        # next enters from right
            self._draw_slide(surface, self.current_slide, out_off)
            self._draw_slide(surface, self._next_slide_idx, in_off)
        else:
            self._draw_slide(surface, self.current_slide, 0)

            # "Next >" button (changes to "Done >" on last slide)
            is_last   = self.current_slide == len(self.SLIDES) - 1
            btn_label = "Done  >" if is_last else "Next  >"
            btn_color = self._NEXT_HOVER_COLOR if self._next_hovered else self._NEXT_IDLE_COLOR

            pygame.draw.rect(surface, self._NEXT_BG_COLOR,  self._next_btn_rect, border_radius=8)
            pygame.draw.rect(surface, btn_color,             self._next_btn_rect, width=2, border_radius=8)

            btn_s    = self._font_label.render(btn_label, True, btn_color)
            btn_rect = btn_s.get_rect(center=self._next_btn_rect.center)
            surface.blit(btn_s, btn_rect)

    def handle_click(self, pos: tuple) -> bool:
        """
        Handle a left-click at *pos*.
        Args:
            pos (tuple): Mouse position in screen coordinates.
        Returns:
            bool: True if the click triggers tutorial completion (i.e. advancing past the last slide).
        """
        if self._transitioning:
            return False
        if not self._next_btn_rect.collidepoint(pos):
            return False

        next_i = self.current_slide + 1
        if next_i >= len(self.SLIDES):
            if self.on_complete:
                self.on_complete()
            return True

        # Kick off the right-to-left slide transition
        self._next_slide_idx = next_i
        self._transitioning  = True
        self._transition_t   = 0.0
        return False

    def reset(self):
        """Return the tutorial to slide 0 (for reuse without re-construction)."""
        self.current_slide  = 0
        self._transitioning = False
        self._transition_t  = 0.0
        self._next_slide_idx = 0
        self._next_hovered   = False
