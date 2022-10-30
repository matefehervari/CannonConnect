import Constants
import csv
import Assets
import UI
import pygame as pg
import Classes as C
import Sprites as S
from random import random, choice
from Functions import draw_text
from math import sin, pi
from numpy import argmax
from numpy.random import multinomial


class Splash:
    def __init__(self, main):  # defines splash assets
        self.main = main
        self.image = Assets.assets['Splash']
        self.rect = self.image.get_rect

    def loop(self, screen):  # checks for keyboard or mouse presses
        self.theta = 0  # parameter for hovering
        while True:
            self.main.clock.tick(Constants.FPS)
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    self.main.mainloop = False  # quits game in the mainloop
                    return
                elif e.type in (pg.KEYUP, pg.MOUSEBUTTONUP):
                    self.main.game_state = 'main'  # switches to main menu game state in mainloop
                    return

            self.draw(screen)
            self.theta += 1  # parameter incremented for animation

    def draw(self, screen):
        screen.blit(self.image, (0, 0))  # draws splash background
        draw_text(screen, 'Cannon Connect', 172, Constants.WHITE, Constants.WIDTH//2,
                  50+15*sin(2*pi*self.theta/Constants.FPS), Constants.FONT_MOON)  # draws hovering text at correct dimensions
        pg.display.flip()


class MainMenu:
    def __init__(self, main):  # defines main menu assets and buttons
        self.main = main
        self.image = Assets.assets['Main']
        self.highscore_b = UI.Button(Assets.assets['High Score Button'], 697, 519)
        self.play_b = UI.Button(Assets.assets['Play Button'], 697, 759)

    def loop(self, screen):  # checks for button clicks
        while True:
            self.draw(screen)
            e = pg.event.wait()  # blocks loop until an event is received in queue
            if e.type == pg.QUIT:
                self.main.mainloop = False
                return
            elif e.type == pg.MOUSEBUTTONUP:  # checks if any button was clicked and updates game states
                mouse_pos = pg.mouse.get_pos()
                if self.play_b.check_clicked(mouse_pos):
                    self.main.game_state = 'inst'
                    return

                elif self.highscore_b.check_clicked(mouse_pos):
                    self.main.game_state = 'high'
                    return

    def draw(self, screen):
        screen.blit(self.image, (0, 0))  # draws main menu background
        self.play_b.draw(screen)  # draws button images
        self.highscore_b.draw(screen)
        pg.display.flip()


class Highscore:
    def __init__(self, main):  # defines highscore assets, buttons and highscore file path
        self.main = main
        self.image = Assets.assets['High']
        self.main_b = UI.Button(Assets.assets['High Main Button'], 697, 822)
        self.path = Constants.HIGHSCORES_FILE

    def loop(self, screen):  # checks for button clicks to return to main menu
        self.draw(screen)
        while True:
            e = pg.event.wait()
            if e.type == pg.QUIT:
                self.main.mainloop = False
                return
            elif e.type == pg.MOUSEBUTTONUP:  # checks if any button was clicked and updates game states
                mouse_pos = pg.mouse.get_pos()
                if self.main_b.check_clicked(mouse_pos):
                    self.main.game_state = 'main'
                    return

    def draw(self, screen):  # draws background, headings and highscore entries
        screen.blit(self.image, (0, 0))
        self.main_b.draw(screen)
        highscores = self.read_scores()

        draw_text(screen, 'Score', 48, Constants.WHITE, 312, 272, Constants.FONT_MOON, True)  # draws score column
        for i, score in enumerate(highscores['Score']):
            draw_text(screen, score, 48, Constants.WHITE, 312, 359+79*i, Constants.FONT_MOON_LIGHT, True)  # draws data at regular intervals

        draw_text(screen, 'Play Time', 48, Constants.WHITE, 760, 272, Constants.FONT_MOON, True)  # draws play time column
        for i, score in enumerate(highscores['Play Time']):
            draw_text(screen, score, 48, Constants.WHITE, 760, 359+79*i, Constants.FONT_MOON_LIGHT, True)

        draw_text(screen, 'Date', 48, Constants.WHITE, 1245, 272, Constants.FONT_MOON, True)  # draws date column
        for i, score in enumerate(highscores['Date']):
            draw_text(screen, score, 48, Constants.WHITE, 1245, 359+79*i, Constants.FONT_MOON_LIGHT, True)
        pg.display.flip()

    def read_scores(self):  # returns a dictionary of headings as keys and list of data as values
        with open(self.path) as f:
            reader = csv.reader(f)  # reads rows from csv file

            headings = next(reader)  # first row is headings
            values = list(zip(*reader))  # joins columns into separate entries
            values = values if len(values) > 0 else [[]]*len(headings)
        return dict(zip(headings, values))

    def write_score(self, data):  # writes new entry if score is in top 5
        '''data - Tuple(score, play time, date)'''

        highscores = self.read_scores()
        entries = list(zip(*highscores.values()))  # list of entries
        lowest = int(entries[-1][0]) if entries else 0
        entries.append(data)
        entries.sort(key=lambda x: int(x[0]), reverse=True)  # sorts entries after adding new entry
        length = len(entries)

        with open(self.path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(highscores.keys())  # writes the headings row
            writer.writerows(entries[:min(length, 5)])  # write the first 5 entries as subsequent row

        return data[0] >= lowest  # now returns if the new score is higher than the lowest know until now


class Instructions:
    def __init__(self, main):  # defines instruction assets
        self.main = main
        self.image = Assets.assets['Inst']

    def loop(self, screen):  # checks for key presses
        self.draw(screen)
        while True:
            e = pg.event.wait()
            if e.type == pg.QUIT:
                self.main.mainloop = False
                return
            elif e.type == pg.KEYUP or e.type == pg.MOUSEBUTTONUP:
                self.main.game_state = 'game'  # invokes Game gamestate
                return

    def draw(self, screen):
        screen.blit(self.image, (0, 0))
        pg.display.flip()


class Game:
    def __init__(self, main):  # defines game assets and Menu button
        self.main = main
        self.image = Assets.assets['Game']
        self.game_loop = True
        self.menu_b = UI.Button(Assets.assets['Menu Button'], 1659, 0)
        self.sounds = self.main.sounds

        self.sprites = pg.sprite.LayeredUpdates()  # defines sprite groups storing associated sprite
        self.projectiles = pg.sprite.Group()
        self.cannonballs = pg.sprite.Group()
        self.coins = pg.sprite.Group()

        self.game_map = C.Map()
        self.path = C.Path(self.game_map.get_path_points(), self)

        self.cannon = S.Cannon(self, self.game_map.get_cannon_pos())

        self.start = pg.time.get_ticks()
        self.distribution = [0.25] * 4  # default uniform distribution of colours
        self.lives = 3
        self.score = C.Score(self, 1498, 9, 1726, 122, 84)
        pos = choice(self.game_map.coin_points)

    def loop(self, screen):
        while self.game_loop:
            self.dt = self.main.clock.tick(Constants.FPS)/1000
            for e in pg.event.get():
                if e.type == pg.QUIT:  # checks if window is closed
                    self.main.mainloop = False
                    return
                elif e.type == pg.MOUSEBUTTONUP:
                    mouse_pos = pg.mouse.get_pos()
                    if self.menu_b.check_clicked(mouse_pos):  # checks if menu button is clicked
                        self.main.game_state = 'pause'
                        return
                    elif e.button == pg.BUTTON_RIGHT:  # events for cannon controls
                        self.cannon.swap_colours()

                    elif e.button == pg.BUTTON_LEFT:
                        self.cannon.shoot()

                elif e.type == pg.KEYUP:  # checks for menu and instruction key binds
                    if e.key == pg.K_ESCAPE:
                        self.main.game_state = 'pause'
                        return
                    elif e.key == pg.K_i:
                        self.main.game_state = 'inst'
                        return
            self.update()
            self.draw(screen)

    def update(self):  # updates sprites and cannon
        # checks for collisions between projectiles and cannonballs using circular hitboxes
        for projectile, cannonballs in pg.sprite.groupcollide(self.projectiles, self.cannonballs,
                                                              False, False, pg.sprite.collide_circle).items():
            if projectile.target is None:
                pg.mixer.find_channel().play(self.sounds['Collide'])
                cannonball = cannonballs[0]
                cannonball.chunk.insert(cannonball, projectile)  # inserts placeholder at projectile collision

        for coin in pg.sprite.groupcollide(self.coins, self.projectiles, False, False):  # checks for projectile and coin collision
            coin.collect()

        if random() < Constants.POWERUP_PROBABILITY:  # upgrade cannon balls at a small probability
            self.path.upgrade_random()

        if random() < Constants.COIN_PROBABILITY and not self.coins:  # spawn coin at small probability
            pos = choice(self.game_map.coin_points)
            S.Coin(self, pos)

        self.path.update()
        self.sprites.update()
        self.cannon.update()

    def draw(self, screen):
        screen.blit(self.image, (0, 0))  # draws BG, button and score
        self.menu_b.draw(screen)
        self.score.draw(screen)

        for i in range(self.lives):  # draws lives at regular intervals
            screen.blit(Assets.assets['Life'], (1128+72*i, 15))

        self.cannon.draw(screen)  # draws sprites and cannon
        self.sprites.draw(screen)

        pg.display.flip()

    def get_colour(self):  # selects a colour from the stored distribution
        col = argmax(multinomial(1, self.distribution))
        return col

    def lose(self):  # subtracts a life or invokes the gameover screen
        if not self.path.reversing:  # uses reverse timer as timer for immunity
            if not self.lives:
                self.time_played = int((pg.time.get_ticks()-self.start)/1000)
                self.main.game_state = 'gameover'
                self.game_loop = False
            else:
                self.lives -= 1


class Pause:
    def __init__(self, main):  # defines Pause screen assets and UI objects
        self.main = main
        self.image = Assets.assets['Pause']
        self.fog = Assets.assets['Fog']

        self.main_b = UI.Button(Assets.assets['Pause Main Button'], 950, 643)
        self.game_b = UI.Button(Assets.assets['Resume Button'], 442, 643)
        self.music_check = UI.CheckBox(875, 561)
        self.vol_slider = UI.Slider(442, 441)

        self.slider_held = False  # dictates if slider was clicked and not yet released

    def loop(self, screen):
        screen.blit(self.fog, (0, 0))

        while True:
            self.main.clock.tick(Constants.FPS)
            mouse_pos = pg.mouse.get_pos()  # stores mouse position (x, y)
            buttons = pg.mouse.get_pressed()  # stores mouse button states

            if self.slider_held and buttons[0]:  # the slider is currently being held and dragged
                self.vol_slider.drag(mouse_pos)

            for e in pg.event.get():
                match e.type:  # checks if window is closed
                    case pg.QUIT:
                        self.main.mainloop = False
                        return
                    case pg.MOUSEBUTTONDOWN:  # checks if slider bar was clicked
                        mouse_pos = pg.mouse.get_pos()
                        if self.vol_slider.check_clicked(mouse_pos):
                            self.slider_held = True  # activates dragging

                    case pg.MOUSEBUTTONUP:
                        mouse_pos = pg.mouse.get_pos()

                        if self.slider_held:  # slider was released
                            self.slider_held = False
                            for sound in self.main.sounds.values():  # updates sounds volumes
                                sound.set_volume(self.vol_slider.value)
                            self.main.sounds['BG'].set_volume(self.music_check.value*self.vol_slider.value)  # sets volume to 0 if music was off
                        else:
                            if self.game_b.check_clicked(mouse_pos):  # Resume Game button pressed
                                self.main.game_state = 'game'
                                return
                            elif self.main_b.check_clicked(mouse_pos):  # Main Menu button pressed
                                # reset game
                                self.main.game_state = 'main'
                                return
                            elif self.music_check.check_clicked(mouse_pos):  # check box clicked
                                self.main.sounds['BG'].set_volume(self.music_check.value*self.vol_slider.value)

                    case pg.KEYUP:  # Escapes hides pause screen
                        if e.key == pg.K_ESCAPE:
                            self.main.game_state = 'game'
                            return

            self.draw(screen)

    def draw(self, screen):  # draws each element of the pause screen
        screen.blit(self.image, (0, 0))
        self.main_b.draw(screen)
        self.game_b.draw(screen)
        self.music_check.draw(screen)
        self.vol_slider.draw(screen)
        pg.display.flip()


class GameOver:
    def __init__(self, main):  # defines gameover assets and buttons
        self.main = main
        self.image = Assets.assets['GameOver']
        self.main_b = UI.Button(Assets.assets['High Main Button'], 399, 782)
        self.play_b = UI.Button(Assets.assets['Play Again Button'], 955, 782)

    def loop(self, screen, score, play_time, new_high):  # checks for button clicks and defines data to be drawn on screen
        self.score = score
        self.play_time = play_time
        self.new_high = new_high

        while True:
            self.draw(screen)
            e = pg.event.wait()  # blocks loop until an event is received in queue
            if e.type == pg.QUIT:
                self.main.mainloop = False
                return
            elif e.type == pg.MOUSEBUTTONUP:  # checks if any button was clicked and updates game states
                mouse_pos = pg.mouse.get_pos()
                if self.play_b.check_clicked(mouse_pos):
                    self.main.game_state = 'game'
                    return

                elif self.main_b.check_clicked(mouse_pos):
                    self.main.game_state = 'main'
                    return

    def draw(self, screen):
        screen.blit(self.image, (0, 0))  # draws main gameover background
        self.play_b.draw(screen)  # draws button images
        self.main_b.draw(screen)
        draw_text(screen, str(self.score), 48, Constants.WHITE, 990, 477, Constants.FONT_MOON_LIGHT, topleft=True)  # draws points and text
        draw_text(screen, self.play_time, 48, Constants.WHITE, 990, 629, Constants.FONT_MOON_LIGHT, topleft=True)

        if self.new_high:  # draws New High Score text if score is in top 5
            draw_text(screen, 'New High Score Achieved', 48, Constants.WHITE, 555, 331, Constants.FONT_MOON, topleft=True)
        pg.display.flip()
