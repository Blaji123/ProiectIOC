import pygame
import sys
from src.constants import *
from src.game import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Șantierul Cuvintelor")
    
    game = Game(screen)
    game.run()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
