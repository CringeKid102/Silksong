import pygame
from audio import AudioManager
from animation import Animation
from bench import Bench
from asset_paths import resolve_image_path
import config
class Hornet:
    """Player character with movement, combat, and platforming."""
    
    def __init__(self, x, y, screen_width, screen_height):
        """Create Hornet at the given position on a screen of the given size."""
        # Load and scale player image
        image_path = resolve_image_path("hornet.webp")
        self.image = pygame.image.load(image_path).convert_alpha()
        source_width, source_height = self.image.get_size()
        scale_factor = 0.3
        scaled_size = (int(source_width * scale_factor), int(source_height * scale_factor))
        self.image = pygame.transform.scale(self.image, scaled_size)
        self.image_flipped = pygame.transform.flip(self.image, True, False)
        
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)
        
        # Movement attributes
        self.velocity_x = 0
        self.velocity_y = 0
        self.speed = 300  # Horizontal movement speed (pixels per second)
        self.jump_power = -750  # Max jump velocity (negative is up)
        self.jump_initial_impulse = -800  # Small upward kick on first frame
        self.jump_sustain_accel = -2800  # Upward acceleration while SPACE held
        self.jump_max_hold_time = 0.18  # Max seconds SPACE adds upward force
        self._jump_hold_timer = 0.0
        self.jump_cut_multiplier = 0.05  # Velocity multiplied when jump released early
        self.gravity = 1800  # Gravity acceleration (pixels per second squared)
        self.on_ground = False
        self._jump_held = False  # Whether jump key is currently held
        self._jumping = False  # True while in a jump that can still be cut short
        self._rebound_available = False  # Set when a down-attack hits; cleared on landing or release
        self.knockback_velocity_x = 0.0
        self.knockback_strength = 520.0
        self.knockback_decay = 1600.0
        self.attack_recoil_velocity_x = 0.0
        self.attack_recoil_strength = 320.0
        self.attack_recoil_decay = 1800.0

        # Wall jump / wall slide
        self.touching_wall_left = False
        self.touching_wall_right = False
        self.wall_jump_power_x = 450.0
        # Use full jump lift so repeated wall jumps climb quickly.
        self.wall_jump_power_y = self.jump_power
        self.wall_slide_speed = 120.0
        self._wall_jump_timer = 0.0
        self._wall_jump_cooldown = 0.08

        # Ledge climb
        self.is_mantle_clinging = False
        self.is_mantle_canceling = False
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self.ledge_climb_duration = 0.3
        self._ledge_target_world_x = None
        self._ledge_target_world_y = 0
        self._ledge_wall_direction = 0
        self._pressing_down = False

        # Camera correction for wall collisions
        self.camera_x_correction = 0.0

        # Diagonal down-attack charge
        self.down_attack_charge_speed = 900.0  # Horizontal burst speed
        self.down_attack_dive_speed = 600.0    # Extra downward speed added
        self.down_attack_rebound_horizontal_scale = 0.2
        
        # Screen boundaries
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Facing direction (for future sprite flipping)
        self.facing_right = True
        
        # Audio manager instance
        self.audio_manager = AudioManager()

        # Initialize bench (main.py anchors it to world ground collider)
        self.bench = Bench(screen_width // 2, y)

        # Bench rest state
        self.is_resting = False
        self.rest_timer = 0.0
        self.rest_duration = 0.45
        self.is_getting_off_bench = False

        # Crowd control
        self.stun_timer = 0.0
        
        # Camera velocity cache to avoid tuple creation each frame
        self._camera_velocity = [0, 0]
        
        # Look up/down system
        self.look_hold_timer = 0.0        # How long W/S has been held
        self.look_hold_threshold = 0.25   # Seconds before camera starts panning
        self.camera_look_y = 0.0          # Current look offset
        self.max_look_distance = 300.0    # Maximum pixels the camera can pan
        self.look_speed = 520.0           # Camera pan speed once activated
        self.look_direction = 0           # -1 = up, 1 = down, 0 = none
        
        # Health system
        self.max_health = 5
        self.health = 5
        self.heal_amount = 3  # Amount of health restored per heal
        self.heal_channel_duration = 1.0
        self.heal_channel_timer = 0.0
        self.is_healing = False
        self.heal_in_air = False
        self.is_dead = False
        self.death_animation_complete = False

        # Silk resource system
        self.max_silk = 9
        self.silk = 0

        # Input cooldowns to prevent SFX spam from held keys
        self.attack_cooldown = 0.18
        self.dash_cooldown = 0.22
        self.special_cooldown = 0.45
        self._attack_timer = 0.0
        self._dash_timer = 0.0
        self._special_timer = 0.0
        self._attack_triggered = False
        self._attack_key_down = False
        self._heal_key_down = False

        # Dedicated attack hitbox state
        self.attack_range = 70
        self.attack_height_padding = 25
        self.attack_hitbox_duration = 0.12
        self.down_attack_hitbox_duration = 0.20
        self.attack_hitbox_timer = 0.0
        self.attack_hitbox = None
        self.attack_hitbox_facing_right = True
        self.attack_hitbox_direction = "forward"
        self.forward_attack_variant = 1
        self.active_attack_animation = None
        self.active_attack_effect_animation = None
        self.active_attack_visual_key = None
        self.pending_attack_effect_start = False
        self.pending_attack_effect_start_frame = 0
        self.active_pose_animation = None
        self.active_pose_effect_animation = None
        self.active_pose_key = None
        self.was_on_ground = False
        self.landed_this_frame = False
        self.jump_pose_active = False
        self.attack_1_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_1.png"),
            frame_width=256,
            frame_height=181,
            scale=0.3,
        )
        self.attack_2_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_2.png"),
            frame_width=244,
            frame_height=182,
            scale=0.3,
        )
        self.attack_down_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_down.png"),
            frame_width=158,
            frame_height=227,
            scale=0.3,
        )
        self.attack_down_effect_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_down_effect.png"),
            frame_width=251,
            frame_height=256,
            scale=0.3,
        )
        self.attack_effect_1_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_effect_1.png"),
            frame_width=369,
            frame_height=162,
            scale=0.3,
        )
        self.attack_effect_2_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_effect_2.png"),
            frame_width=381,
            frame_height=139,
            scale=0.3,
        )
        self.attack_up_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_up.png"),
            frame_width=165,
            frame_height=235,
            scale=0.3,
        )
        self.attack_up_effect_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_attack_up_effect.png"),
            frame_width=170,
            frame_height=329,
            scale=0.3,
        )
        self.death_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_death.png"),
            frame_width=257,
            frame_height=231,
            scale=0.3,
        )
        self.charged_effect_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_charged_effect.png"),
            frame_width=316,
            frame_height=294,
            scale=0.3,
        )
        self.fall_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_fall.png"),
            frame_width=151,
            frame_height=177,
            scale=0.3,
        )
        self.get_off_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_get_off.png"),
            frame_width=214,
            frame_height=208,
            scale=0.3,
        )
        self.heal_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_heal.png"),
            frame_width=193,
            frame_height=232,
            scale=0.3,
        )
        self.heal_alt_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_heal_alt.png"),
            frame_width=195,
            frame_height=225,
            scale=0.3,
        )
        self.heal_effect_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_heal_effect.png"),
            frame_width=402,
            frame_height=314,
            scale=0.3,
        )
        self.hit_flash_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_hit_flash.png"),
            frame_width=661,
            frame_height=280,
            scale=0.3,
        )
        self.idle_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_idle.png"),
            frame_width=183,
            frame_height=215,
            scale=0.3,
        )
        self.jump_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_jump.png"),
            frame_width=155,
            frame_height=198,
            scale=0.3,
        )
        self.jump_effect_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_jump_effect.png"),
            frame_width=179,
            frame_height=141,
            scale=0.3,
        )
        self.land_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_land.png"),
            frame_width=195,
            frame_height=216,
            scale=0.3,
        )
        self.look_down_better_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_look_down.png"),
            frame_width=183,
            frame_height=223,
            scale=0.3,
        )
        self.look_up_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_look_up.png"),
            frame_width=198,
            frame_height=185,
            scale=0.3,
        )
        self.mantle_cancel_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_mantle_cancel.png"),
            frame_width=222,
            frame_height=192,
            scale=0.3,
        )
        self.mantle_cling_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_mantle_cling.png"),
            frame_width=204,
            frame_height=243,
            scale=0.3,
        )
        self.mantle_vault_anim = Animation(
            resolve_image_path("spritesheet/hornet/hornet_mantle_vault.png"),
            frame_width=196,
            frame_height=250,
            scale=0.3,
        )
        self._load_hornet_animation()
        self.attack_animation_offsets = {
            "forward_1": (0, 0),
            "forward_2": (0, 0),
            "down": (0, 0),
            "up": (0, 0),
        }
        self.attack_effect_offsets = {
            "forward_1": (0, 0),
            "forward_2": (0, 0),
            "down": (0, 0),
            "up": (0, 0),
        }
        self.pose_animation_offsets = {
            "death": (0, 0),
            "heal": (0, 0),
            "heal_air": (0, 0),
            "fall": (0, 0),
            "idle": (0, 0),
            "jump": (0, 0),
            "land": (0, 0),
            "look_down_intro": (0, 0),
            "look_down_loop": (0, 0),
            "look_down_release": (0, 0),
            "look_up_intro": (0, 0),
            "look_up_loop": (0, 0),
            "look_up_release": (0, 0),
            "mantle_cling": (0, 0),
            "mantle_cancel": (0, 0),
            "mantle_vault": (0, 0),
            "get_off": (0, 0),
        }
        self.pose_effect_offsets = {
            "heal": (0, 0),
            "heal_air": (0, 0),
            "charged": (0, 0),
            "jump": (0, 0),
            "hit_flash": (0, 0),
        }
        self.charged_effect_active = False
        self.jump_effect_active = False
        self.hit_flash_active = False
        self.attack_hit_mossgrub = False
        self.attack_hit_mossmother = False
        self.attack_recoil_applied = False
        self.is_down_attacking = False
        self.down_attack_momentum_active = False
        self.down_attack_rebound_timer = 0.0
        self.down_attack_jump_lock_duration = 0.3
        self.down_attack_jump_lock_timer = 0.0

        #Respawn point
        self.respawn_x = x
        self.respawn_y = y
    
    def _repeat_tail_frames(self, animation, base_frame_count, total_frame_count, tail_repeat_count, flip_x=False):
        frames = animation.extract_frames(0, 0, base_frame_count, flip_x=flip_x)
        tail_frames = frames[-tail_repeat_count:]
        while len(frames) < total_frame_count:
            for frame in tail_frames:
                if len(frames) >= total_frame_count:
                    break
                frames.append(frame)
        return frames

    def _combine_rows(self, animation, rows, frame_count_per_row, flip_x=False):
        frames = []
        for row in rows:
            frames.extend(animation.extract_frames(row, 0, frame_count_per_row, flip_x=flip_x))
        return frames

    def _load_hornet_animation(self):
        """Load Hornet combat and state animations from spritesheets."""
        self.attack_1_anim.add_animation("right", row=0, start_col=0, num_frames=5, speed=0.024, loop=False)
        self.attack_1_anim.add_animation("left", row=0, start_col=0, num_frames=5, speed=0.024, flip_x=True, loop=False)
        self.attack_2_anim.add_animation("right", row=0, start_col=0, num_frames=5, speed=0.024, loop=False)
        self.attack_2_anim.add_animation("left", row=0, start_col=0, num_frames=5, speed=0.024, flip_x=True, loop=False)
        self.attack_down_anim.add_animation("right", row=0, start_col=0, num_frames=4, speed=0.03, loop=False)
        self.attack_down_anim.add_animation("left", row=0, start_col=0, num_frames=4, speed=0.03, flip_x=True, loop=False)
        self.attack_down_effect_anim.add_animation("right", row=0, start_col=0, num_frames=4, speed=0.03, loop=False)
        self.attack_down_effect_anim.add_animation("left", row=0, start_col=0, num_frames=4, speed=0.03, flip_x=True, loop=False)
        self.attack_effect_1_anim.add_animation("right", row=0, start_col=0, num_frames=4, speed=0.024, loop=False)
        self.attack_effect_1_anim.add_animation("left", row=0, start_col=0, num_frames=4, speed=0.024, flip_x=True, loop=False)
        self.attack_effect_2_anim.add_animation("right", row=0, start_col=0, num_frames=4, speed=0.024, loop=False)
        self.attack_effect_2_anim.add_animation("left", row=0, start_col=0, num_frames=4, speed=0.024, flip_x=True, loop=False)
        self.attack_up_anim.add_animation("right", row=0, start_col=0, num_frames=6, speed=0.02, loop=False)
        self.attack_up_anim.add_animation("left", row=0, start_col=0, num_frames=6, speed=0.02, flip_x=True, loop=False)
        self.attack_up_effect_anim.add_animation("right", row=0, start_col=0, num_frames=2, speed=0.06, loop=False)
        self.attack_up_effect_anim.add_animation("left", row=0, start_col=0, num_frames=2, speed=0.06, flip_x=True, loop=False)
        self.death_anim.add_animation("right", frames=lambda: self._combine_rows(self.death_anim, [0, 1], 10, flip_x=False), frame_count=20, speed=0.05, loop=False)
        self.death_anim.add_animation("left", frames=lambda: self._combine_rows(self.death_anim, [0, 1], 10, flip_x=True), frame_count=20, speed=0.05, loop=False)
        self.charged_effect_anim.add_animation("right", row=0, start_col=0, num_frames=7, speed=0.03, loop=False)
        self.charged_effect_anim.add_animation("left", row=0, start_col=0, num_frames=7, speed=0.03, flip_x=True, loop=False)
        self.fall_anim.add_animation("right", row=0, start_col=0, num_frames=7, speed=0.05, loop=False)
        self.fall_anim.add_animation("left", row=0, start_col=0, num_frames=7, speed=0.05, flip_x=True, loop=False)
        self.get_off_anim.add_animation("right", row=0, start_col=0, num_frames=2, speed=0.08, loop=False)
        self.get_off_anim.add_animation("left", row=0, start_col=0, num_frames=2, speed=0.08, flip_x=True, loop=False)
        self.heal_anim.add_animation("right", frames=lambda: self._repeat_tail_frames(self.heal_anim, 9, 20, 3, flip_x=False), frame_count=20, speed=0.05, loop=False)
        self.heal_anim.add_animation("left", frames=lambda: self._repeat_tail_frames(self.heal_anim, 9, 20, 3, flip_x=True), frame_count=20, speed=0.05, loop=False)
        self.heal_alt_anim.add_animation("right", frames=lambda: self._repeat_tail_frames(self.heal_alt_anim, 9, 20, 3, flip_x=False), frame_count=20, speed=0.05, loop=False)
        self.heal_alt_anim.add_animation("left", frames=lambda: self._repeat_tail_frames(self.heal_alt_anim, 9, 20, 3, flip_x=True), frame_count=20, speed=0.05, loop=False)
        self.heal_effect_anim.add_animation("right", frames=lambda: self._combine_rows(self.heal_effect_anim, [0, 1], 10, flip_x=False), frame_count=20, speed=0.05, loop=False)
        self.heal_effect_anim.add_animation("left", frames=lambda: self._combine_rows(self.heal_effect_anim, [0, 1], 10, flip_x=True), frame_count=20, speed=0.05, loop=False)
        self.hit_flash_anim.add_animation("right", row=0, start_col=0, num_frames=4, speed=0.02, loop=False)
        self.hit_flash_anim.add_animation("left", row=0, start_col=0, num_frames=4, speed=0.02, flip_x=True, loop=False)
        self.idle_anim.add_animation("right", row=0, start_col=0, num_frames=6, speed=0.07, loop=True)
        self.idle_anim.add_animation("left", row=0, start_col=0, num_frames=6, speed=0.07, flip_x=True, loop=True)
        self.jump_anim.add_animation("right", row=0, start_col=0, num_frames=10, speed=0.04, loop=False)
        self.jump_anim.add_animation("left", row=0, start_col=0, num_frames=10, speed=0.04, flip_x=True, loop=False)
        self.jump_effect_anim.add_animation("right", row=0, start_col=0, num_frames=6, speed=0.03, loop=False)
        self.jump_effect_anim.add_animation("left", row=0, start_col=0, num_frames=6, speed=0.03, flip_x=True, loop=False)
        self.land_anim.add_animation("right", row=0, start_col=0, num_frames=10, speed=0.03, loop=False)
        self.land_anim.add_animation("left", row=0, start_col=0, num_frames=10, speed=0.03, flip_x=True, loop=False)
        self.look_down_better_anim.add_animation("intro_right", row=0, start_col=0, num_frames=2, speed=0.04, loop=False)
        self.look_down_better_anim.add_animation("intro_left", row=0, start_col=0, num_frames=2, speed=0.04, flip_x=True, loop=False)
        self.look_down_better_anim.add_animation("loop_right", row=0, start_col=2, num_frames=6, speed=0.05, loop=True)
        self.look_down_better_anim.add_animation("loop_left", row=0, start_col=2, num_frames=6, speed=0.05, flip_x=True, loop=True)
        self.look_down_better_anim.add_animation("release_right", row=0, start_col=8, num_frames=2, speed=0.05, loop=False)
        self.look_down_better_anim.add_animation("release_left", row=0, start_col=8, num_frames=2, speed=0.05, flip_x=True, loop=False)
        self.look_up_anim.add_animation("intro_right", row=0, start_col=0, num_frames=2, speed=0.04, loop=False)
        self.look_up_anim.add_animation("intro_left", row=0, start_col=0, num_frames=2, speed=0.04, flip_x=True, loop=False)
        self.look_up_anim.add_animation("loop_right", row=0, start_col=2, num_frames=6, speed=0.05, loop=True)
        self.look_up_anim.add_animation("loop_left", row=0, start_col=2, num_frames=6, speed=0.05, flip_x=True, loop=True)
        self.look_up_anim.add_animation("release_right", row=0, start_col=8, num_frames=2, speed=0.05, loop=False)
        self.look_up_anim.add_animation("release_left", row=0, start_col=8, num_frames=2, speed=0.05, flip_x=True, loop=False)
        self.mantle_cancel_anim.add_animation("right", row=0, start_col=0, num_frames=9, speed=0.03, loop=False)
        self.mantle_cancel_anim.add_animation("left", row=0, start_col=0, num_frames=9, speed=0.03, flip_x=True, loop=False)
        self.mantle_cling_anim.add_animation("right", row=0, start_col=0, num_frames=4, speed=0.08, loop=True)
        self.mantle_cling_anim.add_animation("left", row=0, start_col=0, num_frames=4, speed=0.08, flip_x=True, loop=True)
        self.mantle_vault_anim.add_animation("right", row=0, start_col=0, num_frames=4, speed=0.05, loop=False)
        self.mantle_vault_anim.add_animation("left", row=0, start_col=0, num_frames=4, speed=0.05, flip_x=True, loop=False)

    def _animation_name_for_facing(self):
        return "left" if self.facing_right else "right"

    def _update_facing_from_motion(self, horizontal_motion):
        if horizontal_motion > 0.5:
            self.facing_right = True
        elif horizontal_motion < -0.5:
            self.facing_right = False

    def _start_forward_attack_animation(self):
        self.forward_attack_variant = 2 if self.forward_attack_variant == 1 else 1
        if self.forward_attack_variant == 1:
            self.active_attack_animation = self.attack_1_anim
            self.active_attack_effect_animation = self.attack_effect_1_anim
            self.active_attack_visual_key = "forward_1"
        else:
            self.active_attack_animation = self.attack_2_anim
            self.active_attack_effect_animation = self.attack_effect_2_anim
            self.active_attack_visual_key = "forward_2"
        self.pending_attack_effect_start = True
        self.pending_attack_effect_start_frame = 1
        self.active_attack_animation.set_animation(self._animation_name_for_facing(), reset=True)

    def _start_down_attack_animation(self):
        self.active_attack_animation = self.attack_down_anim
        self.active_attack_effect_animation = self.attack_down_effect_anim
        self.active_attack_visual_key = "down"
        self.pending_attack_effect_start = False
        self.pending_attack_effect_start_frame = 0
        anim_name = self._animation_name_for_facing()
        self.active_attack_animation.set_animation(anim_name, reset=True)
        self.active_attack_effect_animation.set_animation(anim_name, reset=True)

    def _start_up_attack_animation(self):
        self.active_attack_animation = self.attack_up_anim
        self.active_attack_effect_animation = self.attack_up_effect_anim
        self.active_attack_visual_key = "up"
        self.pending_attack_effect_start = True
        self.pending_attack_effect_start_frame = 2
        self.active_attack_animation.set_animation(self._animation_name_for_facing(), reset=True)

    def _clear_attack_animations(self):
        self.active_attack_animation = None
        self.active_attack_effect_animation = None
        self.active_attack_visual_key = None
        self.pending_attack_effect_start = False
        self.pending_attack_effect_start_frame = 0

    def _update_attack_animations(self, dt):
        if self.active_attack_animation is None:
            return

        self.active_attack_animation.update(dt)

        if self.pending_attack_effect_start and self.active_attack_animation.current_frame >= self.pending_attack_effect_start_frame:
            self.pending_attack_effect_start = False
            if self.active_attack_effect_animation is not None:
                self.active_attack_effect_animation.set_animation(self._animation_name_for_facing(), reset=True)

        if self.active_attack_effect_animation is not None and not self.pending_attack_effect_start:
            self.active_attack_effect_animation.update(dt)

    def _set_pose_animation(self, pose_key, animation, effect_animation=None, animation_name=None):
        if self.active_pose_key != pose_key:
            self.active_pose_key = pose_key
            self.active_pose_animation = animation
            self.active_pose_effect_animation = effect_animation
            if animation_name is None:
                animation_name = self._animation_name_for_facing()
            self.active_pose_animation.set_animation(animation_name, reset=True)
            if self.active_pose_effect_animation is not None:
                effect_name = self._animation_name_for_facing()
                self.active_pose_effect_animation.set_animation(effect_name, reset=True)

    def _sync_active_pose_direction(self, animation_name=None, effect_animation_name=None):
        if self.active_pose_animation is None:
            return

        if animation_name is None:
            animation_name = self._animation_name_for_facing()

        current_animation_name = self.active_pose_animation.current_animation
        if current_animation_name != animation_name:
            previous_frame = self.active_pose_animation.current_frame
            previous_elapsed = self.active_pose_animation.elapsed
            self.active_pose_animation.set_animation(animation_name, reset=True)
            frame_count = self.active_pose_animation.get_animation_frame_count(animation_name)
            self.active_pose_animation.current_frame = min(previous_frame, max(0, frame_count - 1))
            self.active_pose_animation.elapsed = previous_elapsed

        if self.active_pose_effect_animation is not None:
            if effect_animation_name is None:
                effect_animation_name = self._animation_name_for_facing()
            current_effect_name = self.active_pose_effect_animation.current_animation
            if current_effect_name != effect_animation_name:
                previous_frame = self.active_pose_effect_animation.current_frame
                previous_elapsed = self.active_pose_effect_animation.elapsed
                self.active_pose_effect_animation.set_animation(effect_animation_name, reset=True)
                frame_count = self.active_pose_effect_animation.get_animation_frame_count(effect_animation_name)
                self.active_pose_effect_animation.current_frame = min(previous_frame, max(0, frame_count - 1))
                self.active_pose_effect_animation.elapsed = previous_elapsed

    def _clear_pose_animation(self):
        self.active_pose_key = None
        self.active_pose_animation = None
        self.active_pose_effect_animation = None

    def _start_charged_effect(self):
        self.charged_effect_active = True
        self.charged_effect_anim.set_animation(self._animation_name_for_facing(), reset=True)

    def _start_jump_effect(self):
        self.jump_effect_active = True
        self.jump_effect_anim.set_animation(self._animation_name_for_facing(), reset=True)

    def _start_hit_flash(self):
        self.hit_flash_active = True
        self.hit_flash_anim.set_animation(self._animation_name_for_facing(), reset=True)

    def _start_death_animation(self):
        if self.is_dead:
            return
        self.is_dead = True
        self.death_animation_complete = False
        self.cancel_heal_channel()
        self.is_resting = False
        self.is_getting_off_bench = False
        self.is_mantle_clinging = False
        self.is_mantle_canceling = False
        self.is_climbing_ledge = False
        self.is_down_attacking = False
        self.down_attack_momentum_active = False
        self._clear_attack_animations()
        self._clear_pose_animation()
        self.velocity_x = 0
        self.velocity_y = 0
        try:
            self.audio_manager.play_sfx("hornet_death")
        except Exception:
            pass

    def _start_get_off_bench(self, move_left, move_right):
        self.is_resting = False
        self.rest_timer = 0.0
        self.is_getting_off_bench = True

    def _start_mantle_cling(self, ledge_x, ledge_y, ledge_direction):
        self.is_mantle_clinging = True
        self.is_climbing_ledge = False
        self.is_mantle_canceling = False
        self.ledge_climb_timer = 0.0
        self._ledge_target_world_x = int(ledge_x)
        self._ledge_target_world_y = int(ledge_y)
        self._ledge_wall_direction = ledge_direction
        self.velocity_x = 0
        self.velocity_y = 0
        self.knockback_velocity_x = 0
        self.on_ground = False
        self.facing_right = ledge_direction > 0

    def _start_mantle_vault(self):
        self.is_mantle_clinging = False
        self.is_mantle_canceling = False
        self.is_climbing_ledge = True
        self.ledge_climb_timer = self.ledge_climb_duration
        self.velocity_y = 0
        self.knockback_velocity_x = 0

    def _start_mantle_cancel(self):
        self.is_mantle_clinging = False
        self.is_climbing_ledge = False
        self.is_mantle_canceling = True
        self.velocity_y = self.jump_initial_impulse
        self.knockback_velocity_x = -self._ledge_wall_direction * (self.wall_jump_power_x * 0.5)
        self.on_ground = False
        self._jumping = True
        self.jump_pose_active = True
        self._jump_hold_timer = 0.0

    def _update_pose_animations(self, dt):
        if self.active_attack_animation is not None:
            self._clear_pose_animation()
        else:
            if self.is_dead:
                self._set_pose_animation("death", self.death_anim)
            elif self.is_healing:
                if self.heal_in_air:
                    self._set_pose_animation("heal_air", self.heal_alt_anim, effect_animation=self.heal_effect_anim)
                else:
                    self._set_pose_animation("heal", self.heal_anim, effect_animation=self.heal_effect_anim)
            elif self.is_mantle_canceling:
                self._set_pose_animation("mantle_cancel", self.mantle_cancel_anim)
            elif self.is_mantle_clinging:
                self._set_pose_animation("mantle_cling", self.mantle_cling_anim)
            elif self.is_climbing_ledge:
                self._set_pose_animation("mantle_vault", self.mantle_vault_anim)
            elif self.is_getting_off_bench:
                self._set_pose_animation("get_off", self.get_off_anim)
            elif self.active_pose_key in {"look_down_intro", "look_down_loop", "look_down_release"}:
                pass
            elif self.active_pose_key in {"look_up_intro", "look_up_loop", "look_up_release"}:
                pass
            elif self.on_ground and self.look_direction == 1 and self.velocity_x == 0:
                self._set_pose_animation(
                    "look_down_intro",
                    self.look_down_better_anim,
                    animation_name=f"intro_{self._animation_name_for_facing()}",
                )
            elif self.on_ground and self.look_direction == -1 and self.velocity_x == 0:
                self._set_pose_animation(
                    "look_up_intro",
                    self.look_up_anim,
                    animation_name=f"intro_{self._animation_name_for_facing()}",
                )
            elif self.landed_this_frame:
                self._set_pose_animation("land", self.land_anim)
            elif not self.on_ground and self.jump_pose_active and not self.is_down_attacking:
                self._set_pose_animation("jump", self.jump_anim)
            elif not self.on_ground and not self.jump_pose_active and not self.is_down_attacking:
                self._set_pose_animation("fall", self.fall_anim)
            elif self.on_ground and self.velocity_x == 0:
                self._set_pose_animation("idle", self.idle_anim)
            else:
                self._clear_pose_animation()

        if self.active_pose_animation is not None:
            if self.active_pose_key == "jump":
                self._sync_active_pose_direction()
                self.active_pose_animation.update(dt)
            elif self.active_pose_key in {"look_down_intro", "look_down_loop", "look_down_release"}:
                facing_name = self._animation_name_for_facing()
                look_down_animation_name = {
                    "look_down_intro": f"intro_{facing_name}",
                    "look_down_loop": f"loop_{facing_name}",
                    "look_down_release": f"release_{facing_name}",
                }[self.active_pose_key]
                self._sync_active_pose_direction(animation_name=look_down_animation_name)
                self.active_pose_animation.update(dt)
                if self.active_pose_key == "look_down_intro" and self.look_down_better_anim.is_finished():
                    self.active_pose_key = "look_down_loop"
                    self.look_down_better_anim.set_animation(f"loop_{facing_name}", reset=True)
                elif self.active_pose_key == "look_down_loop" and self.look_direction != 1:
                    self.active_pose_key = "look_down_release"
                    self.look_down_better_anim.set_animation(f"release_{facing_name}", reset=True)
                elif self.active_pose_key == "look_down_release" and self.look_down_better_anim.is_finished():
                    self._clear_pose_animation()
            elif self.active_pose_key in {"look_up_intro", "look_up_loop", "look_up_release"}:
                facing_name = self._animation_name_for_facing()
                look_up_animation_name = {
                    "look_up_intro": f"intro_{facing_name}",
                    "look_up_loop": f"loop_{facing_name}",
                    "look_up_release": f"release_{facing_name}",
                }[self.active_pose_key]
                self._sync_active_pose_direction(animation_name=look_up_animation_name)
                self.active_pose_animation.update(dt)
                if self.active_pose_key == "look_up_intro" and self.look_up_anim.is_finished():
                    self.active_pose_key = "look_up_loop"
                    self.look_up_anim.set_animation(f"loop_{facing_name}", reset=True)
                elif self.active_pose_key == "look_up_loop" and self.look_direction != -1:
                    self.active_pose_key = "look_up_release"
                    self.look_up_anim.set_animation(f"release_{facing_name}", reset=True)
                elif self.active_pose_key == "look_up_release" and self.look_up_anim.is_finished():
                    self._clear_pose_animation()
            else:
                self._sync_active_pose_direction()
                self.active_pose_animation.update(dt)
            if self.active_pose_effect_animation is not None:
                self.active_pose_effect_animation.update(dt)

            if self.active_pose_key == "death" and self.active_pose_animation.is_finished():
                self.death_animation_complete = True
            elif self.active_pose_key == "land" and self.active_pose_animation.is_finished():
                self._clear_pose_animation()
            elif self.active_pose_key == "get_off" and self.active_pose_animation.is_finished():
                self.is_getting_off_bench = False
                self._clear_pose_animation()
            elif self.active_pose_key == "mantle_cancel" and self.active_pose_animation.is_finished():
                self.is_mantle_canceling = False
                self._clear_pose_animation()
            elif self.active_pose_key == "mantle_vault" and self.active_pose_animation.is_finished():
                pass

        if self.charged_effect_active:
            self.charged_effect_anim.update(dt)
            if self.charged_effect_anim.is_finished():
                self.charged_effect_active = False
        if self.jump_effect_active:
            self.jump_effect_anim.update(dt)
            if self.jump_effect_anim.is_finished():
                self.jump_effect_active = False
        if self.hit_flash_active:
            self.hit_flash_anim.update(dt)
            if self.hit_flash_anim.is_finished():
                self.hit_flash_active = False
    
    def handle_input(self, keys, dt=0.016):
        """Handle keyboard input for movement and return camera velocity."""
        # Horizontal movement (returns velocity for camera)
        self._attack_triggered = False
        self._pressing_down = keys[pygame.K_s]
        self.velocity_x = 0
        attack_pressed = keys[pygame.K_j]

        # Heal input (edge-triggered, consume all silk)
        shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if shift_pressed and not self._heal_key_down:
            self.start_heal_channel()
        self._heal_key_down = shift_pressed

        if self.is_dead:
            self.look_direction = 0
            self.look_hold_timer = 0.0
            self.velocity_x = 0
            self._attack_key_down = attack_pressed
            self._camera_velocity[0] = 0
            self._camera_velocity[1] = 0
            return self._camera_velocity

        move_left_pressed = keys[pygame.K_a]
        move_right_pressed = keys[pygame.K_d]
        jump_pressed = keys[pygame.K_SPACE]

        if self.is_mantle_clinging:
            self.look_direction = 0
            self.look_hold_timer = 0.0
            self.velocity_x = 0
            climb_left = self._ledge_wall_direction == -1 and move_left_pressed
            climb_right = self._ledge_wall_direction == 1 and move_right_pressed
            if jump_pressed and not self._jump_held:
                self._start_mantle_cancel()
            elif climb_left or climb_right:
                self._start_mantle_vault()
            self._jump_held = jump_pressed
            self._attack_key_down = attack_pressed
            self._camera_velocity[0] = self.knockback_velocity_x + self.attack_recoil_velocity_x
            self._camera_velocity[1] = 0
            return self._camera_velocity

        if self.is_resting and (move_left_pressed or move_right_pressed):
            self._start_get_off_bench(move_left_pressed, move_right_pressed)

        if self.is_healing or self.is_resting or self.is_climbing_ledge or self.stun_timer > 0.0:
            self.look_direction = 0
            self.look_hold_timer = 0.0
            self.velocity_x = 0
            self._attack_key_down = attack_pressed
            self._camera_velocity[0] = self.knockback_velocity_x + self.attack_recoil_velocity_x
            self._camera_velocity[1] = 0
            return self._camera_velocity
        
        if move_left_pressed:
            self.velocity_x = -self.speed
        if move_right_pressed:
            self.velocity_x = self.speed
        
        # Jumping
        jump_locked = self.down_attack_jump_lock_timer > 0.0

        if jump_pressed and self.on_ground and not jump_locked:
            self.velocity_y = self.jump_initial_impulse
            self.on_ground = False
            self._jumping = True
            self.jump_pose_active = True
            self._jump_hold_timer = 0.0
            self._start_jump_effect()
            try:
                self.audio_manager.play_sfx("hornet_jump")
            except Exception:
                pass  # Skip if sound doesn't exist

        # Auto-rebound from down-attack: variable height via jump hold
        if self._rebound_available:
            self._rebound_available = False
            self._jumping = True
            self.jump_pose_active = True
            self._jump_hold_timer = 0.0

        # Wall jump (edge-triggered: fresh SPACE press while touching wall in air)
        if jump_pressed and not self._jump_held and not self.on_ground and self._wall_jump_timer <= 0.0 and not jump_locked:
            if self.touching_wall_left:
                self.velocity_y = self.wall_jump_power_y
                self.knockback_velocity_x = self.wall_jump_power_x
                self._wall_jump_timer = self._wall_jump_cooldown
                self._jumping = True
                self.jump_pose_active = True
                self._jump_hold_timer = 0.0
                self._start_jump_effect()
                try:
                    self.audio_manager.play_sfx("hornet_jump")
                except Exception:
                    pass
            elif self.touching_wall_right:
                self.velocity_y = self.wall_jump_power_y
                self.knockback_velocity_x = -self.wall_jump_power_x
                self._wall_jump_timer = self._wall_jump_cooldown
                self._jumping = True
                self.jump_pose_active = True
                self._jump_hold_timer = 0.0
                self._start_jump_effect()
                try:
                    self.audio_manager.play_sfx("hornet_jump")
                except Exception:
                    pass

        # While holding SPACE during a jump, keep adding upward force
        if self._jumping and jump_pressed and self._jump_hold_timer < self.jump_max_hold_time:
            self._jump_hold_timer += dt
            self.velocity_y += self.jump_sustain_accel * dt
            # Clamp to max jump velocity
            if self.velocity_y < self.jump_power:
                self.velocity_y = self.jump_power

        # Cut jump short when SPACE released while still rising
        if self._jumping and not jump_pressed and self.velocity_y < 0 and self.down_attack_rebound_timer <= 0.0:
            self.velocity_y = 0
            self._jumping = False

        # Stop variable-jump tracking once falling
        if self._jumping and self.velocity_y >= 0:
            self._jumping = False

        self._update_facing_from_motion(self.velocity_x + self.knockback_velocity_x + self.attack_recoil_velocity_x)

        self._jump_held = jump_pressed

        # Attack
        fresh_attack_press = attack_pressed and not self._attack_key_down
        if fresh_attack_press and self._attack_timer <= 0.0:
            self._attack_timer = self.attack_cooldown
            self._attack_triggered = True
            if keys[pygame.K_w]:
                self.attack_hitbox_direction = "up"
                self._start_up_attack_animation()
            elif keys[pygame.K_s] and not self.on_ground:
                self.attack_hitbox_direction = "down"
                self.is_down_attacking = True
                self.down_attack_momentum_active = True
                self._start_down_attack_animation()
                # Fast diagonal charge in facing direction + downward
                direction = 1 if self.facing_right else -1
                self.knockback_velocity_x = direction * self.down_attack_charge_speed
                self.velocity_y = self.down_attack_dive_speed
            else:
                self.attack_hitbox_direction = "forward"
                self.is_down_attacking = False
                self._start_forward_attack_animation()
            try:
                self.audio_manager.play_sfx("hornet_attack")
            except Exception:
                pass  # Skip if sound doesn't exist
        self._attack_key_down = attack_pressed

        # Dash
        if keys[pygame.K_k] and self._dash_timer <= 0.0:
            self._dash_timer = self.dash_cooldown
            try:
                self.audio_manager.play_sfx("hornet_dash")
            except Exception:
                pass  # Skip if sound doesn't exist

        # Special
        if keys[pygame.K_h] and self._special_timer <= 0.0:
            self._special_timer = self.special_cooldown
            try:
                self.audio_manager.play_sfx("hornet_special")
            except Exception:
                pass  # Skip if sound doesn't exist
        
        # Do not let vertical attack inputs, horizontal movement, or jumping drive camera panning.
        directional_attack_active = self._attack_timer > 0.0 and self.attack_hitbox_direction in ("up", "down")
        moving_horizontally = self.velocity_x != 0
        in_air = not self.on_ground

        # Look up/down
        if directional_attack_active or moving_horizontally or in_air:
            self.look_direction = 0
            self.look_hold_timer = 0.0
        elif keys[pygame.K_w]:
            if self.look_direction != -1:
                # Started pressing up, reset timer
                self.look_hold_timer = 0.0
                self.look_direction = -1
        elif keys[pygame.K_s]:
            if self.look_direction != 1:
                # Started pressing down, reset timer
                self.look_hold_timer = 0.0
                self.look_direction = 1
        else:
            self.look_direction = 0
            self.look_hold_timer = 0.0
        
        # Return camera movement (reuse cached list)
        self._camera_velocity[0] = self.velocity_x + self.knockback_velocity_x + self.attack_recoil_velocity_x
        self._camera_velocity[1] = 0
        return self._camera_velocity

    def consume_attack_trigger(self):
        """Return True if attack was triggered this frame, then reset."""
        attack_pressed = self._attack_triggered
        self._attack_triggered = False
        return attack_pressed

    def _build_attack_hitbox(self, world_rect):
        """Build an attack hitbox based on direction and world-space position."""
        base_height = max(10, world_rect.height - self.attack_height_padding * 2)

        if self.attack_hitbox_direction == "up":
            hitbox_width = max(26, int(world_rect.width * 0.9))
            hitbox_height = int(self.attack_range)
            facing_bias = 12 if self.attack_hitbox_facing_right else -12
            hitbox_left = world_rect.centerx - hitbox_width // 2 + facing_bias
            hitbox_top = world_rect.top - hitbox_height
            return pygame.Rect(int(hitbox_left), int(hitbox_top), int(hitbox_width), int(hitbox_height))

        if self.attack_hitbox_direction == "down":
            hitbox_width = int(self.attack_range)
            hitbox_height = max(base_height, int(self.attack_range * 0.7))
            hitbox_top = world_rect.bottom - int(hitbox_height * 0.35)
            if self.attack_hitbox_facing_right:
                hitbox_left = world_rect.right
            else:
                hitbox_left = world_rect.left - hitbox_width
            return pygame.Rect(int(hitbox_left), int(hitbox_top), int(hitbox_width), int(hitbox_height))

        hitbox_top = world_rect.top + self.attack_height_padding
        if self.attack_hitbox_facing_right:
            hitbox_left = world_rect.right
        else:
            hitbox_left = world_rect.left - self.attack_range
        return pygame.Rect(int(hitbox_left), int(hitbox_top), int(self.attack_range), int(base_height))

    def start_attack_hitbox(self, camera_x=0, camera_y=0):
        """Activate the attack hitbox in world coordinates."""
        world_rect = self.rect.copy()
        world_rect.x += int(camera_x)
        world_rect.y += int(camera_y)
        self.attack_hitbox_facing_right = self.facing_right
        self.attack_recoil_applied = False
        self.attack_hitbox = self._build_attack_hitbox(world_rect)
        self.attack_hit_mossgrub = False
        self.attack_hit_mossmother = False
        if self.attack_hitbox_direction == "down":
            self.attack_hitbox_timer = self.down_attack_hitbox_duration
        else:
            self.attack_hitbox_timer = self.attack_hitbox_duration
        return self.attack_hitbox.copy()

    def apply_attack_recoil_on_hit(self):
        """Apply recoil knockback once per swing when hitting an enemy."""
        if self.attack_recoil_applied:
            return
        facing_direction = 1 if self.attack_hitbox_facing_right else -1
        self.attack_recoil_velocity_x = -facing_direction * self.attack_recoil_strength
        self.attack_recoil_applied = True
        self._start_hit_flash()

    def gain_silk(self, amount):
        """Add silk, clamped to the maximum."""
        if amount <= 0:
            return
        self.silk = min(self.max_silk, self.silk + amount)

    def start_heal_channel(self):
        """Begin the heal channel, consuming all silk upfront."""
        if self.is_healing or self.is_dead:
            return False
        if self.silk <= 0:
            return False
        if self.health >= self.max_health:
            return False

        self.silk = 0
        self.is_healing = True
        self.heal_in_air = not self.on_ground
        self.heal_channel_timer = self.heal_channel_duration
        self._clear_attack_animations()
        return True

    def cancel_heal_channel(self):
        """Cancel the current heal channel if active."""
        self.is_healing = False
        self.heal_in_air = False
        self.heal_channel_timer = 0.0

    def start_rest(self):
        """Sit on a bench, fully heal, and pause movement."""
        self.cancel_heal_channel()
        self.is_resting = True
        self.is_getting_off_bench = False
        self.rest_timer = self.rest_duration
        self.health = self.max_health
        self.velocity_x = 0
        self.velocity_y = 0

    def start_stun(self, duration=2.0):
        """Temporarily prevent Hornet from moving or attacking."""
        if duration <= 0:
            return
        self.cancel_heal_channel()
        self.is_resting = False
        self.rest_timer = 0.0
        self.is_mantle_clinging = False
        self.is_mantle_canceling = False
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self.stun_timer = max(self.stun_timer, duration)
        self.velocity_x = 0
        self.velocity_y = max(0, self.velocity_y)
        self.look_direction = 0
        self.look_hold_timer = 0.0

    def heal(self):
        """Restore health when the heal channel completes."""
        if self.health < self.max_health:
            self.health = min(self.health + self.heal_amount, self.max_health)
            try:
                self.audio_manager.play_sfx("hornet_heal")
            except Exception:
                pass  # Skip if sound doesn't exist
    
    def draw_health_bar(self, screen, x, y):
        """
        Draw the hornet's health bar at the given screen position. 
        It should stay there regardless of the camera position. 
        Each health point (there are 5) is represented by one mask.png icon, and an empty slot is represented by a back square for now as a placeholder.
        
        """

    def draw_silk_bar(self):
        """Draw the silk resource bar on screen. Placeholder for future use."""

        pass



    def take_damage(self, damage, knockback_direction=0):
        """Apply damage and knockback to the player."""
        if damage <= 0 or self.is_dead:
            return
        if self.is_healing:
            self.cancel_heal_channel()
        if self.is_resting:
            self.is_resting = False
            self.rest_timer = 0.0
        if self.is_climbing_ledge:
            self.is_climbing_ledge = False
            self.ledge_climb_timer = 0.0
        if self.is_mantle_clinging:
            self.is_mantle_clinging = False
        if self.is_mantle_canceling:
            self.is_mantle_canceling = False
        self.health = max(0, self.health - damage)

        if self.health <= 0:
            self._start_death_animation()
        else:
            self._start_charged_effect()

        if knockback_direction < 0:
            self.knockback_velocity_x = -self.knockback_strength
        elif knockback_direction > 0:
            self.knockback_velocity_x = self.knockback_strength

    def rebound_from_down_attack(self, enemy_rect=None, camera_y=0):
        """Bounce Hornet upward after a successful down-attack hit."""
        if self.attack_hitbox_direction != "down" or self.on_ground:
            return False

        if enemy_rect is not None:
            desired_world_bottom = int(enemy_rect.top - 6)
            current_world_bottom = int(self.rect.bottom + camera_y)
            if current_world_bottom > desired_world_bottom:
                self.rect.bottom = int(desired_world_bottom - camera_y)

        self.velocity_y = self.jump_initial_impulse
        self.knockback_velocity_x *= self.down_attack_rebound_horizontal_scale
        self.on_ground = False
        self._rebound_available = False
        self._jumping = True
        self._jump_hold_timer = 0.0
        self.is_down_attacking = False
        self.down_attack_rebound_timer = max(self.down_attack_rebound_timer, self.attack_hitbox_timer)
        return True
    
    def update(self, dt, collision_rects=None, camera_x=0, camera_y=0, move_horizontally=False):
        """Update player physics, collisions, and timers."""
        self.landed_this_frame = False
        self.was_on_ground = self.on_ground
        horizontal_displacement = 0.0
        if self.knockback_velocity_x > 0.0:
            self.knockback_velocity_x = max(0.0, self.knockback_velocity_x - self.knockback_decay * dt)
        elif self.knockback_velocity_x < 0.0:
            self.knockback_velocity_x = min(0.0, self.knockback_velocity_x + self.knockback_decay * dt)

        if self.attack_recoil_velocity_x > 0.0:
            self.attack_recoil_velocity_x = max(0.0, self.attack_recoil_velocity_x - self.attack_recoil_decay * dt)
        elif self.attack_recoil_velocity_x < 0.0:
            self.attack_recoil_velocity_x = min(0.0, self.attack_recoil_velocity_x + self.attack_recoil_decay * dt)

        if self._attack_timer > 0.0:
            self._attack_timer = max(0.0, self._attack_timer - dt)
        if self._dash_timer > 0.0:
            self._dash_timer = max(0.0, self._dash_timer - dt)
        if self._special_timer > 0.0:
            self._special_timer = max(0.0, self._special_timer - dt)
        if self._wall_jump_timer > 0.0:
            self._wall_jump_timer = max(0.0, self._wall_jump_timer - dt)
        if self.down_attack_rebound_timer > 0.0:
            self.down_attack_rebound_timer = max(0.0, self.down_attack_rebound_timer - dt)
        if self.down_attack_jump_lock_timer > 0.0:
            self.down_attack_jump_lock_timer = max(0.0, self.down_attack_jump_lock_timer - dt)
        if self.stun_timer > 0.0:
            self.stun_timer = max(0.0, self.stun_timer - dt)

        self._update_attack_animations(dt)

        # Complete channel heal after 1 seconds if uninterrupted
        if self.is_healing:
            self.heal_channel_timer -= dt
            if self.heal_channel_timer <= 0.0:
                self.heal_channel_timer = 0.0
                self.is_healing = False
                self.heal_in_air = False
                self.heal()
        
        # Update look hold timer and camera look offset
        if self.look_direction != 0:
            self.look_hold_timer += dt
            if self.look_hold_timer >= self.look_hold_threshold:
                # Pan the camera in the look direction
                self.camera_look_y += self.look_direction * self.look_speed * dt
                # Clamp to max distance
                self.camera_look_y = max(-self.max_look_distance, min(self.max_look_distance, self.camera_look_y))
        else:
            # Smoothly return camera to center when not looking
            if abs(self.camera_look_y) > 1.0:
                self.camera_look_y *= 0.85  # Ease back to center
            else:
                self.camera_look_y = 0.0
        
        # Reset per-frame wall correction
        self.camera_x_correction = 0.0

        if self.is_climbing_ledge:
            # Ledge climb animation: move toward the cached landing point.
            self.ledge_climb_timer -= dt
            target_world_bottom = self._ledge_target_world_y
            target_world_x = self._ledge_target_world_x
            current_world_bottom = self.rect.bottom + camera_y
            climb_speed = 500.0
            if current_world_bottom > target_world_bottom:
                move = min(climb_speed * dt, current_world_bottom - target_world_bottom)
                self.rect.y -= int(move)
            if self.ledge_climb_timer <= 0.0 or self.rect.bottom + camera_y <= target_world_bottom + 2:
                self.rect.bottom = int(target_world_bottom - camera_y)
                if target_world_x is not None:
                    current_world_x = self.rect.x + camera_x
                    self.camera_x_correction = float(target_world_x - current_world_x)
                    horizontal_displacement += self.camera_x_correction
                self.is_climbing_ledge = False
                self.ledge_climb_timer = 0.0
                self._ledge_target_world_x = None
                self.velocity_y = 0
                self.on_ground = True
                self.landed_this_frame = True
                self.jump_pose_active = False
        elif self.is_mantle_clinging:
            self.velocity_y = 0
            self.on_ground = False
        else:
            # Apply gravity
            if self.is_healing and self.heal_in_air:
                self.velocity_y = 0
            else:
                self.velocity_y += self.gravity * dt

            if self.down_attack_rebound_timer > 0.0:
                self.velocity_y = self.jump_initial_impulse
                self.on_ground = False
                self._jumping = True

            # Wall slide: always engage on wall contact in air (outside immediate wall-jump impulse).
            # This prevents jump-hold from creating upward wall-glide.
            if not self.on_ground and (self.touching_wall_left or self.touching_wall_right) and self._wall_jump_timer <= 0.0 and self.down_attack_rebound_timer <= 0.0:
                self.velocity_y = self.wall_slide_speed

            if move_horizontally:
                horizontal_velocity = self.velocity_x + self.knockback_velocity_x + self.attack_recoil_velocity_x
                frame_horizontal_displacement = horizontal_velocity * dt
                self.rect.x += frame_horizontal_displacement
                horizontal_displacement += frame_horizontal_displacement

            self.rect.y += self.velocity_y * dt

            landed = False
            if collision_rects:
                world_rect = self.rect.copy()
                world_rect.x += int(camera_x)
                world_rect.y += int(camera_y)
                previous_bottom = world_rect.bottom - (self.velocity_y * dt)

                # Ceiling collision (elevated platforms only)
                if self.velocity_y < 0:
                    previous_top = world_rect.top - (self.velocity_y * dt)
                    for cr in collision_rects:
                        if cr.width > 5000:
                            continue
                        if world_rect.right <= cr.left or world_rect.left >= cr.right:
                            continue
                        if previous_top >= cr.bottom and world_rect.top <= cr.bottom:
                            world_rect.top = cr.bottom
                            self.rect.y = int(world_rect.y - camera_y)
                            self.velocity_y = 0
                            break

                # Landing collision
                landing_top = None
                if self.velocity_y >= 0:
                    for ground_rect in collision_rects:
                        if world_rect.right <= ground_rect.left or world_rect.left >= ground_rect.right:
                            continue
                        if previous_bottom <= ground_rect.top and world_rect.bottom >= ground_rect.top:
                            if landing_top is None or ground_rect.top < landing_top:
                                landing_top = ground_rect.top

                if landing_top is not None:
                    world_rect.bottom = int(landing_top)
                    self.rect.y = int(world_rect.y - camera_y)
                    self.velocity_y = 0
                    self.on_ground = True
                    if self.down_attack_momentum_active:
                        self.knockback_velocity_x = 0.0
                        self.down_attack_momentum_active = False
                    self._rebound_available = False
                    self.down_attack_rebound_timer = 0.0
                    if self.is_down_attacking:
                        self.down_attack_jump_lock_timer = self.down_attack_jump_lock_duration
                        self.is_down_attacking = False
                    landed = True
                    self.jump_pose_active = False
                    if not self.was_on_ground:
                        self.landed_this_frame = True

            if not landed:
                if collision_rects:
                    self.on_ground = False
                else:
                    self.on_ground = False

            # Horizontal (wall) collision detection
            self.touching_wall_left = False
            self.touching_wall_right = False
            resolved_world_rect = None

            if collision_rects:
                world_rect = self.rect.copy()
                world_rect.x += int(camera_x)
                world_rect.y += int(camera_y)

                for cr in collision_rects:
                    if cr.width > 5000:
                        continue
                    if not world_rect.colliderect(cr):
                        continue
                    if world_rect.bottom <= cr.top + 4:
                        continue

                    overlap_right = world_rect.right - cr.left
                    overlap_left = cr.right - world_rect.left
                    overlap_bottom = world_rect.bottom - cr.top
                    overlap_top = cr.bottom - world_rect.top

                    min_h = min(overlap_right, overlap_left)
                    min_v = min(overlap_bottom, overlap_top)

                    if min_h >= min_v:
                        continue

                    correction_x = 0
                    if overlap_right < overlap_left:
                        correction_x = -overlap_right
                        self.touching_wall_right = True
                    else:
                        correction_x = overlap_left
                        self.touching_wall_left = True

                    self.camera_x_correction += correction_x
                    world_rect.x += int(correction_x)
                    horizontal_displacement += correction_x

                    if self.is_down_attacking:
                        self.down_attack_jump_lock_timer = self.down_attack_jump_lock_duration
                        self.is_down_attacking = False

                resolved_world_rect = world_rect.copy()

            # Ledge detection: enter cling state until climb or cancel input.
            if not self.on_ground and self.velocity_y >= 0 and not self._pressing_down and collision_rects:
                if self.touching_wall_right or self.touching_wall_left:
                    wr = resolved_world_rect.copy() if resolved_world_rect is not None else self.rect.copy()
                    if resolved_world_rect is None:
                        wr.x += int(camera_x)
                        wr.y += int(camera_y)

                    ledge_margin = 8
                    for cr in collision_rects:
                        if cr.width > 5000:
                            continue

                        ledge_top = cr.top
                        if ledge_top < wr.top - 10 or ledge_top > wr.centery:
                            continue

                        climbing_right = self.touching_wall_right and wr.right >= cr.left - 5 and wr.left < cr.right
                        climbing_left = self.touching_wall_left and wr.left <= cr.right + 5 and wr.right > cr.left
                        if not (climbing_right or climbing_left):
                            continue

                        landing_rect = wr.copy()
                        landing_rect.bottom = int(ledge_top)
                        if climbing_right:
                            landing_rect.left = int(cr.left + ledge_margin)
                            ledge_direction = 1
                        else:
                            landing_rect.right = int(cr.right - ledge_margin)
                            ledge_direction = -1

                        blocked = False
                        for blocking_rect in collision_rects:
                            if blocking_rect.width > 5000 or blocking_rect is cr:
                                continue
                            if landing_rect.colliderect(blocking_rect):
                                blocked = True
                                break

                        if blocked:
                            continue

                        self._start_mantle_cling(landing_rect.x, ledge_top, ledge_direction)
                        break

                self._update_facing_from_motion(horizontal_displacement)
        self._update_pose_animations(dt)

        if self.attack_hitbox_timer > 0.0:
            # Keep active attack hitbox attached to Hornet in world-space.
            world_rect = self.rect.copy()
            world_rect.x += int(camera_x)
            world_rect.y += int(camera_y)
            self.attack_hitbox = self._build_attack_hitbox(world_rect)

            self.attack_hitbox_timer = max(0.0, self.attack_hitbox_timer - dt)
            if self.attack_hitbox_timer <= 0.0:
                self.attack_hitbox = None
                self.attack_hit_mossgrub = False
                self.attack_hit_mossmother = False
                self._clear_attack_animations()
        
        # Prevent falling off screen top
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity_y = 0

        if self.health <= 0:
            self.health = 0
    
    def draw(self, screen, look_y_offset=0, screen_offset=(0, 0)):
        """Draw Hornet on screen with the given vertical look offset."""
        draw_rect = self.rect.copy()
        draw_rect.x += int(screen_offset[0])
        draw_rect.y += int(look_y_offset + screen_offset[1])

        draw_hitbox_rect = None
        if self.attack_hitbox is not None:
            draw_hitbox_rect = self._build_attack_hitbox(draw_rect)

        def apply_facing_offset(offset):
            offset_x, offset_y = offset
            return (offset_x if self.facing_right else -offset_x, offset_y)

        if self.active_attack_animation is not None and self.attack_hitbox_direction in ("forward", "down"):
            attack_frame = self.active_attack_animation.get_current_frame()
            if attack_frame is not None:
                attack_rect = attack_frame.get_rect()
                attack_rect.midbottom = draw_rect.midbottom
                attack_offset = self.attack_animation_offsets.get(self.active_attack_visual_key, (0, 0))
                offset_x, offset_y = apply_facing_offset(attack_offset)
                attack_rect.x += int(offset_x)
                attack_rect.y += int(offset_y)
                screen.blit(attack_frame, attack_rect)
                if draw_hitbox_rect is not None and self.active_attack_effect_animation is not None and not self.pending_attack_effect_start:
                    effect_frame = self.active_attack_effect_animation.get_current_frame()
                    if effect_frame is not None:
                        effect_rect = effect_frame.get_rect()
                        effect_rect.center = draw_hitbox_rect.center
                        effect_offset = self.attack_effect_offsets.get(self.active_attack_visual_key, (0, 0))
                        effect_offset_x, effect_offset_y = apply_facing_offset(effect_offset)
                        effect_rect.x += int(effect_offset_x)
                        effect_rect.y += int(effect_offset_y)
                        screen.blit(effect_frame, effect_rect)
            elif self.facing_right:
                screen.blit(self.image_flipped, draw_rect)
            else:
                screen.blit(self.image, draw_rect)
        elif self.active_attack_animation is not None and self.attack_hitbox_direction == "up":
            attack_frame = self.active_attack_animation.get_current_frame()
            if attack_frame is not None:
                attack_rect = attack_frame.get_rect()
                attack_rect.midbottom = draw_rect.midbottom
                attack_offset = self.attack_animation_offsets.get(self.active_attack_visual_key, (0, 0))
                offset_x, offset_y = apply_facing_offset(attack_offset)
                attack_rect.x += int(offset_x)
                attack_rect.y += int(offset_y)
                screen.blit(attack_frame, attack_rect)
                if draw_hitbox_rect is not None and self.active_attack_effect_animation is not None and not self.pending_attack_effect_start:
                    effect_frame = self.active_attack_effect_animation.get_current_frame()
                    if effect_frame is not None:
                        effect_rect = effect_frame.get_rect()
                        effect_rect.midbottom = draw_hitbox_rect.midbottom
                        effect_offset = self.attack_effect_offsets.get(self.active_attack_visual_key, (0, 0))
                        effect_offset_x, effect_offset_y = apply_facing_offset(effect_offset)
                        effect_rect.x += int(effect_offset_x)
                        effect_rect.y += int(effect_offset_y)
                        screen.blit(effect_frame, effect_rect)
            elif self.facing_right:
                screen.blit(self.image_flipped, draw_rect)
            else:
                screen.blit(self.image, draw_rect)
        elif self.active_pose_animation is not None:
            pose_frame = self.active_pose_animation.get_current_frame()
            if pose_frame is not None:
                pose_rect = pose_frame.get_rect()
                pose_rect.midbottom = draw_rect.midbottom
                pose_offset = self.pose_animation_offsets.get(self.active_pose_key, (0, 0))
                offset_x, offset_y = apply_facing_offset(pose_offset)
                pose_rect.x += int(offset_x)
                pose_rect.y += int(offset_y)
                screen.blit(pose_frame, pose_rect)
                if self.active_pose_effect_animation is not None:
                    effect_frame = self.active_pose_effect_animation.get_current_frame()
                    if effect_frame is not None:
                        effect_rect = effect_frame.get_rect()
                        effect_rect.center = pose_rect.center
                        effect_offset = self.pose_effect_offsets.get(self.active_pose_key, (0, 0))
                        effect_offset_x, effect_offset_y = apply_facing_offset(effect_offset)
                        effect_rect.x += int(effect_offset_x)
                        effect_rect.y += int(effect_offset_y)
                        screen.blit(effect_frame, effect_rect)
            elif self.facing_right:
                screen.blit(self.image_flipped, draw_rect)
            else:
                screen.blit(self.image, draw_rect)
        elif self.facing_right:
            screen.blit(self.image_flipped, draw_rect)
        else:
            screen.blit(self.image, draw_rect)

        if self.charged_effect_active:
            charged_frame = self.charged_effect_anim.get_current_frame()
            if charged_frame is not None:
                charged_rect = charged_frame.get_rect()
                charged_rect.center = draw_rect.center
                effect_offset_x, effect_offset_y = apply_facing_offset(self.pose_effect_offsets.get("charged", (0, 0)))
                charged_rect.x += int(effect_offset_x)
                charged_rect.y += int(effect_offset_y)
                screen.blit(charged_frame, charged_rect)

        if self.jump_effect_active:
            jump_effect_frame = self.jump_effect_anim.get_current_frame()
            if jump_effect_frame is not None:
                jump_effect_rect = jump_effect_frame.get_rect()
                jump_effect_rect.midbottom = draw_rect.midbottom
                effect_offset_x, effect_offset_y = apply_facing_offset(self.pose_effect_offsets.get("jump", (0, 0)))
                jump_effect_rect.x += int(effect_offset_x)
                jump_effect_rect.y += int(effect_offset_y)
                screen.blit(jump_effect_frame, jump_effect_rect)

        if self.hit_flash_active:
            hit_flash_frame = self.hit_flash_anim.get_current_frame()
            if hit_flash_frame is not None:
                hit_flash_rect = hit_flash_frame.get_rect()
                if draw_hitbox_rect is not None:
                    hit_flash_rect.center = draw_hitbox_rect.center
                else:
                    hit_flash_rect.center = draw_rect.center
                effect_offset_x, effect_offset_y = apply_facing_offset(self.pose_effect_offsets.get("hit_flash", (0, 0)))
                hit_flash_rect.x += int(effect_offset_x)
                hit_flash_rect.y += int(effect_offset_y)
                screen.blit(hit_flash_frame, hit_flash_rect)
        
        instructions_draw_x = 10
        instructions_draw_y = config.screen_height - 550
        instructions_text = "Instructions:\nPress D to move right\nPress A to move left\nPress W to look up\nPress S to look down\nPress space to jump\nPress J to attack"
        lines = instructions_text.split('\n')
        for i, line in enumerate(lines):
            line_surface = config.font.render(line, True, config.white)
            line_y = instructions_draw_y + (i * config.font.get_linesize())
            screen.blit(line_surface, (instructions_draw_x, line_y))


    
    def reset_position(self, x, y):
        """Reset Hornet to the given position and clear all movement/combat state."""
        self.rect.midbottom = (x, y)
        self.velocity_x = 0
        self.velocity_y = 0
        self.knockback_velocity_x = 0.0
        self.attack_recoil_velocity_x = 0.0
        self.on_ground = False
        self.is_resting = False
        self.rest_timer = 0.0
        self.is_getting_off_bench = False
        self.is_mantle_clinging = False
        self.is_mantle_canceling = False
        self.is_healing = False
        self.heal_in_air = False
        self.heal_channel_timer = 0.0
        self.stun_timer = 0.0
        self.is_dead = False
        self.death_animation_complete = False
        self.charged_effect_active = False
        self.jump_effect_active = False
        self.hit_flash_active = False
        self._jump_hold_timer = 0.0
        self._jump_held = False
        self._jumping = False
        self._rebound_available = False
        self._wall_jump_timer = 0.0
        self._pressing_down = False
        self.look_hold_timer = 0.0
        self.camera_look_y = 0.0
        self.look_direction = 0
        self.attack_hitbox = None
        self.attack_hitbox_timer = 0.0
        self.attack_hitbox_facing_right = self.facing_right
        self.attack_hitbox_direction = "forward"
        self._clear_attack_animations()
        self._clear_pose_animation()
        self.attack_hit_mossgrub = False
        self.attack_hit_mossmother = False
        self.attack_recoil_applied = False
        self.is_down_attacking = False
        self.down_attack_momentum_active = False
        self.down_attack_rebound_timer = 0.0
        self.down_attack_jump_lock_timer = 0.0
        self.jump_pose_active = False
        self._attack_timer = 0.0
        self._dash_timer = 0.0
        self._special_timer = 0.0
        self._attack_triggered = False
        self._attack_key_down = False
        self._heal_key_down = False
        self.is_climbing_ledge = False
        self.ledge_climb_timer = 0.0
        self._ledge_target_world_x = None
        self.touching_wall_left = False
        self.touching_wall_right = False
        self.camera_x_correction = 0.0