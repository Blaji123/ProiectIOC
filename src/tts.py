import os
import pygame
from gtts import gTTS
import tempfile
import hashlib

class TTSManager:
    """Text-to-Speech Manager for Romanian language using gTTS"""
    
    def __init__(self):
        self.is_speaking = False
        self.tts_available = True
        
        # Create cache directory for audio files
        self.cache_dir = os.path.join(tempfile.gettempdir(), "santier_cuvinte_tts")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        print("gTTS Romanian TTS Engine initialized successfully")
    
    def _get_cache_path(self, text):
        """Get cached audio file path for given text"""
        # Create hash of text for filename
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.mp3")
    
    def _generate_audio(self, text):
        """Generate audio file from text using gTTS"""
        cache_path = self._get_cache_path(text)
        
        # Check if already cached
        if os.path.exists(cache_path):
            print(f"Using cached audio for: {text}")
            return cache_path
        
        try:
            print(f"Generating audio for: {text}")
            # Generate Romanian speech
            tts = gTTS(text=text, lang='ro', slow=False)
            tts.save(cache_path)
            print(f"Audio saved to: {cache_path}")
            return cache_path
        except Exception as e:
            print(f"gTTS Error: {e}")
            return None
    
    def speak(self, text, wait=False):
        """
        Speak the given text
        
        Args:
            text: Text to speak
            wait: If True, block until speech is complete. If False, speak in background.
        """
        if not self.tts_available:
            print(f"TTS not available. Would speak: {text}")
            return
            
        try:
            # Generate or get cached audio
            audio_path = self._generate_audio(text)
            
            if audio_path and os.path.exists(audio_path):
                # Play audio using pygame mixer
                self.is_speaking = True
                try:
                    pygame.mixer.music.load(audio_path)
                except pygame.error as e:
                    print(f"Corrupt audio detected: {e}. Regenerating...")
                    try:
                        os.remove(audio_path)
                    except:
                        pass
                    # Regenerate
                    audio_path = self._generate_audio(text)
                    if audio_path:
                        try:
                            pygame.mixer.music.load(audio_path)
                        except:
                             print("Failed to recover audio.")
                             self.is_speaking = False
                             return

                pygame.mixer.music.play()
                
                if wait:
                    # Wait for playback to complete
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                    self.is_speaking = False
                    print("Speech completed")
            else:
                print(f"Failed to generate audio for: {text}")
                self.is_speaking = False
                
        except Exception as e:
            print(f"TTS Playback Error: {e}")
            self.is_speaking = False
    
    def stop(self):
        """Stop current speech"""
        try:
            self.engine.stop()
            self.is_speaking = False
        except:
            pass
    
    def speak_letter(self, letter):
        """Speak a single letter"""
        self.speak(letter)
    
    def speak_word(self, word):
        """Speak a complete word"""
        self.speak(word)
    
    def speak_instruction(self, instruction):
        """Speak an instruction"""
        self.speak(instruction)

    def preload(self, text_list):
        """Pre-generate audio for a list of texts"""
        total = len(text_list)
        print(f"Preloading {total} audio clips...")
        for i, text in enumerate(text_list):
            self._generate_audio(text)
            if (i + 1) % 5 == 0:
                print(f"Loaded {i + 1}/{total}...")
        print("Audio preloading complete.")
