import pygame
import random
import sys
from src.constants import *
from src.sprites import Wagon, Button, Slot, RoboticArm, SpeakerButton
from src.tts import TTSManager

# Level Definitions
LEVELS = [
    {
        "id": 1,
        "target_word": "CASĂ",
        "phonemes": ["C", "A", "S", "Ă"],
        "distractors": ["M", "R"], # Reduced distractors to fit screen
        "spawn_mode": "conveyor", # classic
        "pre_filled": [],
        "image_key": "casa"
    },
    {
        "id": 2,
        "target_word": "ALBINĂ",
        "phonemes": ["A", "L", "B", "I", "N", "Ă"],
        "distractors": ["T", "S", "M", "P"],
        "spawn_mode": "conveyor",
        "pre_filled": [0, 2, 4], # A, B, N are pre-filled
        "image_key": "albina"
    },
    {
        "id": 3,
        "target_word": "PISICĂ",
        "phonemes": ["P", "I", "S", "I", "C", "Ă"],
        "distractors": ["A", "L", "R", "E"],
        "spawn_mode": "raining",
        "pre_filled": [],
        "image_key": "pisica"
    }
]

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "INTRO" # INTRO, PLAYING, SUCCESS
        self.intro_audio_played = False
        self.success_audio_played = False
        
        try:
            self.font = pygame.font.SysFont('Comic Sans MS', 42, bold=True)
            self.story_font = pygame.font.SysFont('Comic Sans MS', 28)
        except:
            self.font = pygame.font.Font(None, 48)
            self.story_font = pygame.font.Font(None, 32)
        
        # Text-to-Speech Manager
        self.tts = TTSManager()
        
        # Preload Audio
        print("Preloading game audio...") 
        preload_list = []
        # General messages
        preload_list.extend([
            "Literă greșită, mai încearcă",
            "Literă greșită! Mai încearcă!", 
            "Felicitări! Nivel Complet!",
            "Cuvântul nu este complet, mai încearcă"
        ])
        
        # Intro and Outro text
        self.intro_text = "Salutare, micule constructor! Bine ai venit pe Șantierul Cuvintelor. Aici, literele sunt ca niște cărămizi, iar noi avem nevoie de ajutorul tău pentru a construi cuvinte puternice. Ești gata să pornim macaraua și să asamblăm cuvinte? Haide să începem!"
        self.outro_text = "Felicitări, Maestre Constructor! Ai terminat toate nivelurile cu succes. Șantierul Cuvintelor arată minunat datorită ție. Ești un adevărat campion al literelor!"
        
        preload_list.append(self.intro_text)
        preload_list.append(self.outro_text)
        
        # Level specific content
        for level in LEVELS:
            word = level["target_word"]
            # Instruction
            if level["id"] == 1:
                preload_list.append(f"Da click pe litere in ordine si construieste cuvantul {word}")
            else:
                preload_list.append(f"Nivelul {level['id']}. Construiește cuvântul {word}")
            
            # Completion
            preload_list.append(f"Felicitări! Cuvântul {word} este complet!")
            preload_list.append(f"Perfect! Cuvântul {word} este corect!")
            preload_list.append(word)
            
            # Letters
            all_letters = level["phonemes"] + level["distractors"]
            for letter in all_letters:
                preload_list.append(letter)
        
        # Remove duplicates
        preload_list = list(set(preload_list))
        self.tts.preload(preload_list)
        
        # Load background and level images
        self.level_images = {}
        try:
            self.background = pygame.image.load("assets/images/background.png")
            self.background = pygame.transform.scale(self.background, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print("Background image loaded successfully")
        except Exception as e:
            print(f"Failed to load background: {e}")
            self.background = None

        # Load Level Icons
        image_map = {
            "casa": "casa-removebg-preview",
            "albina": "albina-removebg-preview",
            "pisica": "pisica-removebg-preview"
        }
        
        for key, filename in image_map.items():
            try:
                img = pygame.image.load(f"assets/images/{filename}.png").convert_alpha()
                # Scale to reasonable size e.g., 150x150 max keeping aspect ratio
                img = pygame.transform.smoothscale(img, (150, 150))
                self.level_images[key] = img
            except Exception as e:
                 print(f"Failed to load {filename}.png: {e}")
            
        # UI Elements
        self.speaker_btn = SpeakerButton(SCREEN_WIDTH - 320, 500, 60, "speak_word")
        self.next_level_btn = Button("Următorul Nivel", SCREEN_WIDTH - 250, 500, 220, 50, ORANGE, "next_level")
        
        # Intro/Outro Buttons
        self.start_btn = Button("START", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 150, 200, 80, GREEN, "start_game")
        self.quit_btn = Button("IEȘIRE", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 150, 200, 80, RED, "quit_game")

        self.buttons = pygame.sprite.Group(self.speaker_btn, self.next_level_btn)
        
        # Robotic Arm
        self.arm = RoboticArm(ARM_BASE_X, ARM_BASE_Y)
        
        # Level State
        self.current_level_index = 0
        self.setup_level(self.current_level_index)

    def setup_level(self, level_index):
        if level_index >= len(LEVELS):
            print("All levels completed!")
            self.state = "SUCCESS"
            self.success_audio_played = False
            return

        level_config = LEVELS[level_index]
        self.current_level_config = level_config
        self.target_word = level_config["target_word"]
        self.phonemes = level_config["phonemes"]
        
        # Reset Game State
        self.selected_wagon = None
        self.target_slot = None
        self.current_position = 0
        self.completed_letters = []
        self.auto_place = False
        
        # Slots
        self.slots = pygame.sprite.Group()
        self.slot_list = []
        
        total_slots_width = len(self.target_word) * (SLOT_WIDTH + 20) - 20
        start_x_slots = (SCREEN_WIDTH - total_slots_width) // 2
        
        for i in range(len(self.target_word)):
            slot = Slot(start_x_slots + i * (SLOT_WIDTH + 20), SLOT_Y)
            self.slots.add(slot)
            self.slot_list.append(slot)
            
            # Handle pre-filled slots
            if i in level_config["pre_filled"]:
                # Create a "locked" wagon in the correct position (centered in slot)
                letter = self.phonemes[i]
                center_x = slot.rect.centerx
                center_y = slot.rect.centery
                # Start x/y usually topleft, so calculate from center
                start_x = center_x - WAGON_WIDTH // 2
                start_y = center_y - WAGON_HEIGHT // 2
                
                wagon = Wagon(letter, start_x, start_y, start_x)
                wagon.arrived = True
                wagon.current_slot = slot
                slot.occupied_by = wagon
                self.completed_letters.append(letter) # Add to completed
                # Note: current_position logic needs to skip these.
        
        # Initialize current position pointer
        # It should point to the first empty slot
        self.current_position = 0
        while self.current_position in level_config["pre_filled"]:
            self.current_position += 1
            
        # Wagons (Letters to pick)
        self.wagons = pygame.sprite.Group()
        
        # Prepare pool of letters: needed letters (minus pre-filled) + distractors
        needed_indices = [i for i in range(len(self.phonemes)) if i not in level_config["pre_filled"]]
        letters_pool = [self.phonemes[i] for i in needed_indices]
        letters_pool.extend(level_config["distractors"])
        random.shuffle(letters_pool)
        
        start_x = 100
        for i, letter in enumerate(letters_pool):
            is_raining = (level_config["spawn_mode"] == "raining")
            
            if is_raining:
                # Spawn at random X at top
                # Ensure they don't overlap too much if possible, or just random
                # Spread them out across the screen width
                spawn_width = SCREEN_WIDTH - 100
                target_x = 50 + (spawn_width / (len(letters_pool) + 1)) * (i + 1)
                
                # Randomize Y slightly so they don't fall in a perfect line
                start_y = -WAGON_HEIGHT - random.randint(0, 300)
                
                # Target Y is the conveyor belt level (so they land there)
                # Or maybe they float? Let's land them on the conveyor Y
                target_y = CONVEYOR_Y
                
                # Initial X is same as target X
                wagon = Wagon(letter, target_x, target_y, target_x, is_raining=True)
                # Override initial Y position
                wagon.rect.y = start_y
                self.wagons.add(wagon)
                
            else:
                # Classic Conveyor
                target_x = start_x + i * (WAGON_WIDTH + 20)
                initial_x = -WAGON_WIDTH - i * (WAGON_WIDTH + 20)
                wagon = Wagon(letter, target_x, CONVEYOR_Y, initial_x)
                self.wagons.add(wagon)
        
        # Reset Buttons
        # Always add next_level_btn but disabled
        self.next_level_btn.set_enabled(False)
        self.buttons = pygame.sprite.Group(self.speaker_btn, self.next_level_btn)
        
        self.message = "Nivelul " + str(level_config['id']) + ": " + get_level_description(level_config)
        self.message_color = (50, 100, 200)
        
        # Reset Arm
        self.arm.move_to_rest()
        self.arm.release_wagon()
        
        # Initial instruction
        if not self.state == "INTRO":
            pygame.time.set_timer(pygame.USEREVENT + 1, 1000, 1)
        
        # Randomize Level Image Position
        # Safe zones: Left (150, 315), Center (400, 315), Right (650, 315)
        safe_positions = [(150, 315), (400, 315), (650, 315)]
        self.current_image_pos = random.choice(safe_positions)

    def handle_events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            
            if self.state == "INTRO":
                self.handle_intro_events(event)
            elif self.state == "SUCCESS":
                self.handle_success_events(event)
            elif self.state == "PLAYING":
                self.handle_game_event(event)
                
        if self.state == "PLAYING":
            self.wagons.update(events)
            self.update_arm_state()
            self.arm.update() 
    
    # ... rest of file logic implies start_wagon_pickup is next ...

    def start_wagon_pickup(self, wagon):
        self.selected_wagon = wagon
        self.arm.state = "moving_to_pickup"
        self.arm.target_pos = wagon.rect.center
        self.auto_place = True
    
    def move_to_current_slot(self):
        if self.current_position < len(self.slot_list):
            self.target_slot = self.slot_list[self.current_position]
            self.arm.state = "moving_to_slot"
            center_x = self.target_slot.rect.centerx
            center_y = self.target_slot.rect.centery
            self.arm.target_pos = (center_x, center_y)
    
    def update_arm_state(self):
        if self.arm.state == "moving_to_pickup":
            if self.arm.is_at_target():
                # Pick it up
                if self.selected_wagon is None:
                    self.arm.state = "idle"
                    return
                
                self.arm.pick_wagon(self.selected_wagon)
                self.selected_wagon.being_held = True
                self.selected_wagon = None
                
                if self.auto_place:
                    self.move_to_current_slot()
                    self.auto_place = False
                else:
                    self.arm.state = "holding"
        
        elif self.arm.state == "moving_to_slot":
            if self.arm.is_at_target():
                # Place wagon
                wagon = self.arm.held_wagon
                wagon.being_held = False
                
                wagon.rect.centerx = self.target_slot.rect.centerx
                wagon.rect.centery = self.target_slot.rect.centery
                
                wagon.current_slot = self.target_slot
                self.target_slot.occupied_by = wagon
                
                # Check correctness
                slot_index = self.slot_list.index(self.target_slot)
                expected_letter = self.phonemes[slot_index]
                
                if wagon.letter == expected_letter:
                    # Correct
                    # We can't just append to completed_letters blindly because of pre-filled slots
                    # We need to insert it correctly or just rely on current_position
                    
                    # Update completed letters representation (optional, mostly for logic)
                    # self.completed_letters.append(wagon.letter) 
                    
                    # Advance current position
                    self.current_position += 1
                    # Skip any subsequent pre-filled slots
                    while self.current_position in self.current_level_config["pre_filled"]:
                        self.current_position += 1
                    
                    # Construct partial word for TTS
                    # We need to reconstruct the word from the slots
                    current_word_state = ""
                    for i, phoneme in enumerate(self.phonemes):
                        if i < self.current_position:
                             current_word_state += phoneme
                        elif i in self.current_level_config["pre_filled"]:
                             current_word_state += phoneme
                        # else: break? No, we want to speak what is there.
                    
                    # Actually, let's just speak the letter or the target word if done?
                    # The original logic spoke the partial word.
                    
                    # Let's count how many slots are filled
                    filled_count = 0
                    for slot in self.slot_list:
                        if slot.occupied_by is not None:
                            filled_count += 1
                            
                    if filled_count == len(self.phonemes):
                         # Level Complete
                        self.message = f"Felicitări! Nivel Complet!"
                        self.message_color = (255, 165, 0)
                        self.tts.speak(f"Felicitări! Cuvântul {self.target_word} este complet!")
                        
                        # Show Next Level Button
                        self.next_level_btn.set_enabled(True)
                            
                        # self.buttons.remove(self.assemble_btn) # Removed
                    else:
                        self.message = f"Bravo! {wagon.letter}"
                        self.message_color = (34, 200, 34)
                        self.tts.speak_word(wagon.letter)

                else:
                    # Wrong letter
                    self.target_slot.occupied_by = None
                    wagon.current_slot = None
                    
                    # Reset wagon position
                    if self.current_level_config["spawn_mode"] == "raining":
                         # Respawn at top? Or return to where it fell?
                         # Let's return it to where it landed (its target_y)
                         wagon.rect.x = wagon.target_x
                         wagon.rect.y = wagon.target_y
                    else:
                        wagon.rect.x = wagon.target_x
                        wagon.rect.y = CONVEYOR_Y
                    
                    self.message = "Literă greșită! Mai încearcă!"
                    self.message_color = (220, 50, 50)
                    self.tts.speak("Literă greșită, mai încearcă")
                
                self.arm.release_wagon()
                self.arm.move_to_rest()
                self.target_slot = None

    def check_solution(self):
        # Count filled slots
        filled_count = 0
        correct_count = 0
        for i, slot in enumerate(self.slot_list):
            if slot.occupied_by:
                filled_count += 1
                if slot.occupied_by.letter == self.phonemes[i]:
                    correct_count += 1
        
        if correct_count == len(self.phonemes):
            self.message = f"Perfect! Cuvântul {self.target_word} este corect!"
            self.message_color = (255, 165, 0)
            self.tts.speak(f"Perfect! Cuvântul {self.target_word} este corect!")
            self.buttons.add(self.next_level_btn)
            self.buttons.remove(self.assemble_btn)
        else:
            remaining = len(self.phonemes) - filled_count
            if remaining > 0:
                self.message = f"Mai lipsesc {remaining} {'literă' if remaining == 1 else 'litere'}!"
            else:
                 self.message = "Ceva nu este corect. Verifică literele!"
            self.message_color = (50, 150, 255)
            self.tts.speak(self.message)

    def draw(self):
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(WHITE)
            
        if self.state == "INTRO":
            self.draw_intro()
        elif self.state == "SUCCESS":
            self.draw_success()
        elif self.state == "PLAYING":
            self.draw_game()
            
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(FPS)

    def handle_intro_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                action = self.start_btn.check_click(event.pos)
                if action == "start_game":
                    self.state = "PLAYING"
                    self.tts.speak_instruction(f"Da click pe litere in ordine si construieste cuvantul {self.target_word}")
    
    def handle_success_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                action = self.quit_btn.check_click(event.pos)
                if action == "quit_game":
                    self.running = False

    def handle_game_event(self, event):
        if event.type == pygame.USEREVENT + 1:
            # Initial instruction
            if self.current_level_index == 0:
                    self.tts.speak_instruction(f"Da click pe litere in ordine si construieste cuvantul {self.target_word}")
            else:
                self.tts.speak_instruction(f"Nivelul {self.current_level_index + 1}. Construiește cuvântul {self.target_word}")
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Check button clicks
                button_clicked = False
                for btn in self.buttons:
                    action = btn.check_click(event.pos)
                    if action == "next_level":
                        if self.next_level_btn.enabled:
                            self.current_level_index += 1
                            self.setup_level(self.current_level_index)
                        else:
                            print("Next level button disabled clicked")
                            self.message = "Cuvântul nu este complet!"
                            self.message_color = RED
                            self.tts.speak("Cuvântul nu este complet, mai încearcă")

                        button_clicked = True
                        break
                    elif action == "speak_word":
                        print(f"Speaker button clicked! Speaking: {self.target_word}")
                        self.message = f"Ascultă: {self.target_word}"
                        self.message_color = (100, 150, 255)
                        self.tts.speak_word(self.target_word)
                        button_clicked = True
                        break
                
                if button_clicked:
                    return
                
                # Check if clicking on a wagon
                if self.arm.state == "idle" and not self.arm.held_wagon:
                    for wagon in self.wagons:
                        # Allow picking up if arrived (or close enough for raining?)
                        # For raining, let's say they can be picked up if they are visible
                        if wagon.rect.collidepoint(event.pos) and (wagon.arrived or self.current_level_config["spawn_mode"] == "raining") and wagon.current_slot is None:
                            self.start_wagon_pickup(wagon)
                            self.tts.speak_letter(wagon.letter)
                            break

    def draw_intro(self):
        if not self.intro_audio_played:
            self.tts.speak(self.intro_text)
            self.intro_audio_played = True
            
        # Background fallback if needed but main draw handles clear
        
        # Draw Title
        title_surf = self.font.render("Șantierul Cuvintelor", True, BLUE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_surf, title_rect)
        
        # Draw Story
        self.draw_multiline_text(self.intro_text, SCREEN_WIDTH // 2, 200, SCREEN_WIDTH - 100, self.story_font, BLACK)
        
        # Draw Button
        self.screen.blit(self.start_btn.image, self.start_btn.rect)
        
    def draw_success(self):
        if not self.success_audio_played:
            self.tts.speak(self.outro_text)
            self.success_audio_played = True
            
        title_surf = self.font.render("Felicitări!", True, ORANGE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_surf, title_rect)
        
        self.draw_multiline_text(self.outro_text, SCREEN_WIDTH // 2, 250, SCREEN_WIDTH - 100, self.story_font, BLACK)
        
        self.screen.blit(self.quit_btn.image, self.quit_btn.rect)

    def draw_game(self):
        if self.current_level_config["spawn_mode"] == "conveyor":
             pygame.draw.rect(self.screen, GRAY, (0, CONVEYOR_Y + WAGON_HEIGHT, SCREEN_WIDTH, 20))
        else:
             pygame.draw.rect(self.screen, (100, 200, 100), (0, CONVEYOR_Y + WAGON_HEIGHT, SCREEN_WIDTH, 20))
        
        self.slots.draw(self.screen)
        
        for slot in self.slot_list:
            if slot.occupied_by and slot.occupied_by not in self.wagons and slot.occupied_by != self.arm.held_wagon:
                 self.screen.blit(slot.occupied_by.image, slot.occupied_by.rect)

        for wagon in self.wagons:
            if wagon != self.arm.held_wagon:
                self.screen.blit(wagon.image, wagon.rect)
        
        self.arm.draw(self.screen)
        
        if self.arm.held_wagon:
            self.screen.blit(self.arm.held_wagon.image, self.arm.held_wagon.rect)
        
        self.buttons.draw(self.screen)
        
        try:
            msg_font = pygame.font.SysFont('Comic Sans MS', 38, bold=True)
        except:
            msg_font = pygame.font.Font(None, 44)
        
        msg_surf_temp = msg_font.render(self.message, True, self.message_color)
        msg_width = msg_surf_temp.get_width()
        if msg_width > SCREEN_WIDTH - 40:
            try:
                msg_font = pygame.font.SysFont('Comic Sans MS', 32, bold=True)
            except:
                msg_font = pygame.font.Font(None, 38)
        
        if self.message:
            font = pygame.font.SysFont('Comic Sans MS', 48, bold=True)
            shadow_text = font.render(self.message, True, (0, 0, 0))
            shadow_rect = shadow_text.get_rect(center=(SCREEN_WIDTH // 2 + 2, 72))
            self.screen.blit(shadow_text, shadow_rect)
            
            text_surface = font.render(self.message, True, self.message_color)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 70))
            self.screen.blit(text_surface, text_rect)
            
        if self.current_level_config and "image_key" in self.current_level_config:
            key = self.current_level_config["image_key"]
            if key in self.level_images:
                img = self.level_images[key]
                img_rect = img.get_rect(center=self.current_image_pos)
                self.screen.blit(img, img_rect)
        
        try:
            inst_font = pygame.font.SysFont('Arial', 18, italic=True)
        except:
            inst_font = pygame.font.Font(None, 22)
            
        if not self.arm.held_wagon:
             inst_text = "Nivel " + str(self.current_level_index + 1) + "/" + str(len(LEVELS))
        else:
             inst_text = f"Plasare litera..."
             
        inst_surf = inst_font.render(inst_text, True, (50, 50, 50))
        inst_rect = inst_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 25))
        self.screen.blit(inst_surf, inst_rect)
        
        try:
            num_font = pygame.font.SysFont('Arial', 36, bold=True)
        except:
            num_font = pygame.font.Font(None, 42)
            
        for i, slot in enumerate(self.slot_list):
            slot.set_current(i == self.current_position)
            
            num_text = ""
            bg_color = None
            text_color = WHITE
            
            if i in self.current_level_config["pre_filled"]:
                 pass
            elif i < self.current_position:
                 num_text = str(i + 1)
                 bg_color = (34, 200, 34) # Green
            elif i == self.current_position:
                 num_text = str(i + 1)
                 bg_color = (255, 200, 0) # Gold
            else:
                 num_text = str(i + 1)
                 bg_color = WHITE
                 text_color = (100, 100, 100)
            
            if num_text:
                center_x = slot.rect.centerx
                center_y = slot.rect.top - 25
                
                if bg_color == WHITE:
                    pygame.draw.circle(self.screen, (200, 200, 200), (center_x, center_y), 18)
                    pygame.draw.circle(self.screen, bg_color, (center_x, center_y), 16)
                else:
                    pygame.draw.circle(self.screen, bg_color, (center_x, center_y), 18)
                
                num_surf = num_font.render(num_text, True, text_color)
                num_rect = num_surf.get_rect(center=(center_x, center_y))
                self.screen.blit(num_surf, num_rect)

    def draw_multiline_text(self, text, x, y, max_width, font, color=(0,0,0)):
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            text_surf = font.render(' '.join(current_line), True, color)
            if text_surf.get_width() > max_width:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
            
        for i, line in enumerate(lines):
            text_surf = font.render(line, True, color)
            rect = text_surf.get_rect(center=(x, y + i * 40))
            self.screen.blit(text_surf, rect)

def get_level_description(config):
    if config["spawn_mode"] == "raining":
        return "Prinde literele!"
    elif len(config["pre_filled"]) > 0:
        return "Completează literele lipsă!"
    else:
        return "Construiește cuvântul!"
