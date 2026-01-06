import pygame
import math
from src.constants import *

class RoboticArm:
    def __init__(self, base_x, base_y):
        self.base_pos = (base_x, base_y)
        self.l1 = SEGMENT_LENGTH
        self.l2 = SEGMENT_LENGTH
        self.angle1 = 0
        self.angle2 = 0
        self.rest_pos = (base_x + 100, base_y - 100)
        self.target_pos = self.rest_pos
        self.current_pos = self.rest_pos
        self.held_wagon = None
        self.state = "idle"  # States: idle, moving_to_pickup, picking, holding, moving_to_slot, placing
        self.animation_speed = 5  # pixels per frame
        
    def update(self, target_pos=None):
        if target_pos:
            self.target_pos = target_pos
        
        # Smoothly interpolate current position to target position
        dx = self.target_pos[0] - self.current_pos[0]
        dy = self.target_pos[1] - self.current_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > self.animation_speed:
            # Move towards target
            ratio = self.animation_speed / distance
            self.current_pos = (
                self.current_pos[0] + dx * ratio,
                self.current_pos[1] + dy * ratio
            )
        else:
            # Reached target
            self.current_pos = self.target_pos
        
        self.solve_ik(self.current_pos[0], self.current_pos[1])
        
        # Update held wagon position if holding one
        if self.held_wagon:
            end_pos = self.get_end_position()
            self.held_wagon.rect.center = (int(end_pos[0]), int(end_pos[1]))

    def solve_ik(self, x, y):
        # Inverse Kinematics for 2-segment arm
        dx = x - self.base_pos[0]
        dy = y - self.base_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Clamp distance
        if dist > self.l1 + self.l2:
            dist = self.l1 + self.l2
            # Re-calculate x, y based on clamped distance
            angle = math.atan2(dy, dx)
            x = self.base_pos[0] + dist * math.cos(angle)
            y = self.base_pos[1] + dist * math.sin(angle)
            dx = x - self.base_pos[0]
            dy = y - self.base_pos[1]

        # Law of Cosines
        # c^2 = a^2 + b^2 - 2ab cos(C)
        # dist^2 = l1^2 + l2^2 - 2*l1*l2 * cos(angle2_internal)
        
        try:
            cos_angle2 = (dist*dist - self.l1*self.l1 - self.l2*self.l2) / (2 * self.l1 * self.l2)
            # Clamp for floating point errors
            cos_angle2 = max(-1.0, min(1.0, cos_angle2))
            angle2_internal = math.acos(cos_angle2)
            
            # Angle 2 (relative to first segment)
            self.angle2 = angle2_internal
            
            # Angle 1 (shoulder)
            # angle1 = atan2(dy, dx) - atan2(l2 * sin(angle2), l1 + l2 * cos(angle2))
            # Note: using -angle2 because usually "elbow up" or "elbow down" configuration
            # Let's try "elbow up" (negative angle2 relative to straight line?)
            # Actually, let's just use the standard formula
            
            phi = math.atan2(dy, dx)
            psi = math.atan2(self.l2 * math.sin(angle2_internal), self.l1 + self.l2 * math.cos(angle2_internal))
            
            self.angle1 = phi - psi
            
        except ValueError:
            pass

    def get_end_position(self):
        """Get the position of the arm's end effector (claw)"""
        x1 = self.base_pos[0] + self.l1 * math.cos(self.angle1)
        y1 = self.base_pos[1] + self.l1 * math.sin(self.angle1)
        x2 = x1 + self.l2 * math.cos(self.angle1 + self.angle2)
        y2 = y1 + self.l2 * math.sin(self.angle1 + self.angle2)
        return (x2, y2)
    
    def pick_wagon(self, wagon):
        """Pick up a wagon"""
        self.held_wagon = wagon
        wagon.dragging = False
        if wagon.current_slot:
            wagon.current_slot.occupied_by = None
            wagon.current_slot = None
    
    def release_wagon(self):
        """Release the held wagon"""
        self.held_wagon = None
    
    def is_at_target(self):
        """Check if arm has reached target position"""
        dx = self.target_pos[0] - self.current_pos[0]
        dy = self.target_pos[1] - self.current_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < self.animation_speed
    
    def move_to_rest(self):
        """Move arm back to rest position"""
        self.target_pos = self.rest_pos
        self.state = "idle"

    def draw(self, surface):
        # Calculate joint positions
        x1 = self.base_pos[0] + self.l1 * math.cos(self.angle1)
        y1 = self.base_pos[1] + self.l1 * math.sin(self.angle1)
        
        x2 = x1 + self.l2 * math.cos(self.angle1 + self.angle2)
        y2 = y1 + self.l2 * math.sin(self.angle1 + self.angle2)
        
        # Draw segments
        pygame.draw.line(surface, ARM_COLOR, self.base_pos, (x1, y1), 20)
        pygame.draw.line(surface, ARM_COLOR, (x1, y1), (x2, y2), 15)
        
        # Draw joints
        pygame.draw.circle(surface, JOINT_COLOR, self.base_pos, 15)
        pygame.draw.circle(surface, JOINT_COLOR, (int(x1), int(y1)), 12)
        
        # Draw claw - open or closed based on whether holding wagon
        if self.held_wagon:
            pygame.draw.circle(surface, CLAW_COLOR, (int(x2), int(y2)), 12)
        else:
            pygame.draw.circle(surface, CLAW_COLOR, (int(x2), int(y2)), 10)

class Wagon(pygame.sprite.Sprite):
    def __init__(self, letter, target_x, y, start_x, is_raining=False):
        super().__init__()
        self.letter = letter
        
        # Generate the main tile image
        self.base_image = self.generate_tile_image()
        self.image = self.base_image.copy()
        
        self.rect = self.image.get_rect()
        self.rect.topleft = (start_x, y)
        
        self.target_x = target_x
        self.target_y = y 
        self.is_raining = is_raining
        
        self.arrived = False
        self.dragging = False # Legacy
        self.being_held = False 
        self.current_slot = None
        
        # Animation state
        self.scale = 1.0
        self.target_scale = 1.0

    def generate_tile_image(self):
        """Generate a consistent wood-style tile"""
        surf = pygame.Surface((WAGON_WIDTH, WAGON_HEIGHT), pygame.SRCALPHA)
        
        # Rounded Rect Body
        pygame.draw.rect(surf, TILE_COLOR, (0, 0, WAGON_WIDTH, WAGON_HEIGHT), border_radius=12)
        
        # Inner 'Bevel' highlight (top/left)
        pygame.draw.rect(surf, (255, 248, 220), (5, 5, WAGON_WIDTH-10, WAGON_HEIGHT-10), border_radius=8, width=2)
        
        # Border
        pygame.draw.rect(surf, TILE_BORDER_COLOR, (0, 0, WAGON_WIDTH, WAGON_HEIGHT), 4, border_radius=12)
        
        # Text
        try:
            font = pygame.font.SysFont('Comic Sans MS', 48, bold=True)
        except:
            font = pygame.font.Font(None, 56)
        
        # Shadow for text
        text_shadow = font.render(self.letter, True, (200, 150, 100))
        shadow_rect = text_shadow.get_rect(center=(WAGON_WIDTH//2 + 2, WAGON_HEIGHT//2 + 2))
        surf.blit(text_shadow, shadow_rect)
        
        # Main Text
        text_surf = font.render(self.letter, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=(WAGON_WIDTH//2, WAGON_HEIGHT//2))
        surf.blit(text_surf, text_rect)
        
        return surf

    def update(self, event_list):
        # 1. Animation: Hover Scale
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos) and not self.being_held and (self.arrived or self.is_raining):
            self.target_scale = 1.15
        else:
            self.target_scale = 1.0
            
        # Smooth scale interpolation
        if abs(self.scale - self.target_scale) > 0.01:
            self.scale += (self.target_scale - self.scale) * 0.2
            
            # Apply scale
            center = self.rect.center
            new_size = (int(WAGON_WIDTH * self.scale), int(WAGON_HEIGHT * self.scale))
            self.image = pygame.transform.scale(self.base_image, new_size)
            self.rect = self.image.get_rect(center=center)
            
        # 2. Movement Logic
        if not self.arrived and not self.being_held and self.current_slot is None:
            if self.is_raining:
                if self.rect.y < self.target_y:
                    self.rect.y += WAGON_SPEED
                else:
                    self.rect.y = self.target_y
                    self.arrived = True
            else:
                if self.rect.x < self.target_x:
                    self.rect.x += WAGON_SPEED
                else:
                    self.rect.x = self.target_x
                    self.arrived = True

class Slot(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.base_image = pygame.Surface((SLOT_WIDTH, SLOT_HEIGHT), pygame.SRCALPHA)
        # Background for slot
        pygame.draw.rect(self.base_image, (255, 255, 255, 150), (0, 0, SLOT_WIDTH, SLOT_HEIGHT), border_radius=10)
        # Dashed border simulation or solid
        pygame.draw.rect(self.base_image, SLOT_BORDER_COLOR, (0, 0, SLOT_WIDTH, SLOT_HEIGHT), 3, border_radius=10)
        
        self.highlighted_image = self.base_image.copy()
        pygame.draw.rect(self.highlighted_image, (255, 215, 0), (0, 0, SLOT_WIDTH, SLOT_HEIGHT), 5, border_radius=10)
        
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.occupied_by = None
        self.is_current = False
    
    def set_current(self, is_current):
        self.is_current = is_current
        if is_current:
            self.image = self.highlighted_image.copy()
        else:
            self.image = self.base_image.copy()

class Button(pygame.sprite.Sprite):
    def __init__(self, text, x, y, width, height, color, action):
        super().__init__()
        self.width = width
        self.height = height
        self.base_color = color # Store the original color
        self.color = color
        self.enabled = True # Default enabled
        
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.text = text
        self.action = action
        self._draw_button()
        
    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.color = self.base_color
        else:
            self.color = (150, 150, 150) # Gray
        self._draw_button()

    def _draw_button(self):
        """Draw button with rounded corners and gradient"""
        # Draw rounded rectangle background
        pygame.draw.rect(self.image, self.color, (0, 0, self.width, self.height), border_radius=15)
        
        # Add lighter top for 3D effect
        lighter_color = tuple(min(c + 40, 255) for c in self.color)
        pygame.draw.rect(self.image, lighter_color, (0, 0, self.width, self.height // 3), border_radius=15)
        
        # Add border
        darker_color = tuple(max(c - 40, 0) for c in self.color)
        pygame.draw.rect(self.image, darker_color, (0, 0, self.width, self.height), 3, border_radius=15)
        
        # Render text with shadow - adjusted font size based on text length
        try:
            if len(self.text) > 10:
                font = pygame.font.SysFont('Comic Sans MS', 24, bold=True)
            else:
                font = pygame.font.SysFont('Comic Sans MS', 28, bold=True)
        except:
            font = pygame.font.Font(None, 32)
        
        # Shadow
        shadow_surf = font.render(self.text, True, (0, 0, 0, 128))
        shadow_rect = shadow_surf.get_rect(center=(self.width // 2 + 2, self.height // 2 + 2))
        self.image.blit(shadow_surf, shadow_rect)
        
        # Main text
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=(self.width // 2, self.height // 2))
        self.image.blit(text_surf, text_rect)

    def check_click(self, pos):
        if self.rect.collidepoint(pos):
            return self.action
        return None

class SpeakerButton(pygame.sprite.Sprite):
    """Button with speaker icon for TTS"""
    def __init__(self, x, y, size, action):
        super().__init__()
        self.size = size
        self.action = action
        self.rect = pygame.Rect(x, y, size, size)
        
        # Create image 
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
            
        # Draw rounded rectangle background with 3D effect (BLUE)
        # Main body
        pygame.draw.rect(self.image, BLUE, (0, 0, size, size), border_radius=12)
        # Highlight (top)
        lighter_blue = (100, 180, 255)
        pygame.draw.rect(self.image, lighter_blue, (0, 0, size, size // 2), border_radius=12)
        # Border/Shadow (bottom)
        darker_blue = (0, 50, 150)
        pygame.draw.rect(self.image, darker_blue, (0, 0, size, size), 3, border_radius=12)
        
        # Draw Icon
        self.draw_speaker_icon()
    
    def draw_speaker_icon(self):
        """Draw a speaker icon on the button"""
        center_x = self.size // 2
        center_y = self.size // 2
        icon_color = WHITE
        
        # Speaker Cone points
        # Main body
        pygame.draw.rect(self.image, icon_color, (center_x - 12, center_y - 6, 8, 12))
        
        # Cone
        cone_points = [
            (center_x - 4, center_y - 6),
            (center_x - 4, center_y + 6),
            (center_x + 8, center_y + 12),
            (center_x + 8, center_y - 12)
        ]
        pygame.draw.polygon(self.image, icon_color, cone_points)
        
        # Waves
        for i in range(2):
            pygame.draw.arc(self.image, icon_color, 
                          (center_x - 5, center_y - 8 - i*5, 20 + i*8, 16 + i*10), 
                          -0.8, 0.8, 2)
    
    def check_click(self, pos):
        if self.rect.collidepoint(pos):
            return self.action
        return None
