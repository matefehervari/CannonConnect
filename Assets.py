import pygame as pg
from pygame.mixer import Sound

pg.mixer.init()


# loads all images used
assets = {
        'Splash': pg.image.load('Assets/UI/Splash.png'),
        'Main': pg.image.load('Assets/UI/Main Menu.png'),
        'High': pg.image.load('Assets/UI/High Scores.png'),
        'Inst': pg.image.load('Assets/UI/Instructions.png'),
        'Game': pg.image.load('Assets/UI/map.png'),
        'Pause': pg.image.load('Assets/UI/Pause.png'),
        'Fog': pg.image.load('Assets/UI/Fog.png'),
        'GameOver': pg.image.load('Assets/UI/Game Over.png'),

        'Play Button': pg.image.load('Assets/UI/Play Button.png'),
        'High Score Button': pg.image.load('Assets/UI/High Score Button.png'),
        'High Main Button': pg.image.load('Assets/UI/Main Menu Button 1.png'),
        'Pause Main Button': pg.image.load('Assets/UI/Main Menu Button.png'),
        'Resume Button': pg.image.load('Assets/UI/Resume Game Button.png'),
        'Play Again Button': pg.image.load('Assets/UI/Play Again Button.png'),
        'Menu Button': pg.image.load('Assets/UI/Menu Button.png'),
        'Check Box 1': pg.image.load('Assets/UI/Check Box 1.png'),
        'Check Box 0': pg.image.load('Assets/UI/Check Box 0.png'),
        'Bar': pg.image.load('Assets/UI/Bar.png'),
        'Slider': pg.image.load('Assets/UI/Slider.png'),

        'Life': pg.image.load('Assets/UI/life.png'),

        'Cannon': pg.image.load('Assets/Cannon/cannon1.png'),
        'Cannon Shadow': pg.image.load('Assets/Decor/shadow-6.png'),
        'Primary': [pg.image.load(f'Assets/Cannon/primary-{i}.png') for i in range(4)],
        'Secondary': [pg.image.load(f'Assets/Cannon/secondary-{i}.png') for i in range(4)],
        'Flash': [pg.image.load(f'Assets/Cannon/flash-{i}.png') for i in range(9)],

        'Default_C': [pg.image.load(f'Assets/Cannonballs/cannonball-{i}.png') for i in range(4)],
        'Bomb_C': [pg.image.load(f'Assets/Cannonballs/bomb-{i}.png') for i in range(4)],
        'Slow_C': [pg.image.load(f'Assets/Cannonballs/pause-{i}.png') for i in range(4)],
        'Reverse_C': [pg.image.load(f'Assets/Cannonballs/reverse-{i}.png') for i in range(4)],

        'Destroy': [[pg.image.load(f'Assets/Cannonballs/destroy_{frame}-{colour}.png')
                     for frame in range(5)] for colour in range(4)],

        'Coin': [pg.image.load(f'Assets/Coin/Coin {frame}.png') for frame in range(15)],
          }

sounds = {
        'BG': Sound('Assets/Sounds/BG.mp3'),
        'Shoot': Sound('Assets/Sounds/Shoot.wav'),
        'Reload': Sound('Assets/Sounds/Reload.wav'),
        'Collide': Sound('Assets/Sounds/Collide.wav'),
        'Cluster': Sound('Assets/Sounds/Cluster.wav'),
        'Reverse': Sound('Assets/Sounds/Reverse.wav'),
        'Slow': Sound('Assets/Sounds/Slow.wav'),
        'Coin': Sound('Assets/Sounds/Coin.wav'),
        }
