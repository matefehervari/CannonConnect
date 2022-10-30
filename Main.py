import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame as pg
import os
from win32api import GetSystemMetrics
from Constants import WIDTH, HEIGHT, FPS, TITLE
import GameStates as G
import Assets
from datetime import datetime

pg.mixer.pre_init(44100, -16, 30, 8192)
pg.mixer.init(channels=30, buffer=8192)
pg.mixer.set_num_channels(30)
pg.display.init()
screen_x = (GetSystemMetrics(0)-WIDTH)//2  # positions window at the centre of the screen
screen_y = (GetSystemMetrics(1)-HEIGHT)
os.environ['SDL_VIDEO_WINDOW_POS'] = f'{screen_x},{screen_y}'
screen = pg.display.set_mode((WIDTH, HEIGHT), )  # pygame screen game will be drawn to
pg.display.set_caption(TITLE)  # sets title of window


class Main:
    def __init__(self):
        self.sounds = Assets.sounds
        self.sounds['BG'].play(-1)

        self.clock = pg.time.Clock()  # main control attributes
        self.game_state = 'splash'
        self.mainloop = True

        self.splash = G.Splash(self)  # game state classes
        self.main = G.MainMenu(self)
        self.highscore = G.Highscore(self)
        self.inst = G.Instructions(self)
        self.game = G.Game(self)
        self.menu = G.Pause(self)
        self.gameover = G.GameOver(self)

    def loop(self):  # mainloop
        while self.mainloop:
            for e in pg.event.get():  # checks for quit events
                if e.type == pg.QUIT:
                    return

            self.clock.tick(FPS)
            match self.game_state:  # invokes the relevent gamestate
                case 'splash': self.splash.loop(screen)
                case 'main': self.main.loop(screen)
                case 'high': self.highscore.loop(screen)
                case 'inst': self.inst.loop(screen)
                case 'game': self.game.loop(screen)
                case 'pause': self.menu.loop(screen)
                case 'gameover':
                    points = self.game.score.points  # stores points and time
                    time = self.game.time_played
                    date = datetime.now().strftime('%d.%m.%Y')  # stores date in correct format
                    self.game = G.Game(self)  # resets game
                    new_high = self.highscore.write_score((points, str(time)+' s', date))  # writes scores
                    self.gameover.loop(screen, str(points), str(time)+' s', new_high)  # invoeks GameOver screen


if __name__ == '__main__':
    main = Main()
    main.loop()
    pg.quit()
