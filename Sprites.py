import Assets
import random
import numpy as np
import pygame as pg
import Constants as C
from pygame.math import Vector2
from math import sin, cos, atan2, pi
from Functions import get_text_image


class Cannon(pg.sprite.Sprite):
    def __init__(self, game, pos):
        self.game = game
        super().__init__()  # initialises Sprite() methods and attributes

        self.current_col = random.randrange(4)  # stores colour encodings for of cannonballs
        self.next_col = random.randrange(4)

        self.rad = pi  # rotation of cannon in radians
        self.pos = np.array(pos)  # center position
        self.original_image = self.make_image()
        self.image = self.original_image.copy()  # copy of original image for rotation

        self.rect = self.image.get_rect()
        self.rect.center = self.get_center()
        self.proj_offset = self.rect.width*C.PROJECTILE_OFFSET_RATIO  # position to spawn projectiles from

        self.shadow = Assets.assets['Cannon Shadow']  # shadow assets under cannon
        self.shadow_rect = self.shadow.get_rect()
        self.shadow_rect.center = pos

        self.last_shot = 0  # time frame in milliseconds of last shot

    def swap_colours(self):  # swaps colours and updates image
        if self.current_col is not None:
            self.current_col, self.next_col = self.next_col, self.current_col
            self.original_image = self.make_image()

    def shoot(self):
        if self.current_col is not None:  # checks if cannon is loaded
            self.game.sounds['Shoot'].play()
            direction = np.array((cos(self.rad), -sin(self.rad)))  # unit vector of direction of cannon
            velocity = C.PROJECTILE_VELOCITY*direction
            position = self.pos+(self.proj_offset)*direction  # offsets spawn position in direction of vector

            Projectile(self.current_col, position, velocity, self.game)  # spawns projectile and plays animation
            Animation(Assets.assets['Flash'], position, self.game)

            self.current_col = None  # updates cannon to its emptied state
            self.original_image = self.make_image()
            self.last_shot = pg.time.get_ticks()

    def update(self):  # updates cannon each tick
        self.point_to_cursor()

        # progresses colour and reloads cannon if enough time has passed
        if self.current_col is None and pg.time.get_ticks() > self.last_shot+C.SHOOT_DELAY:
            self.game.sounds['Reload'].play()
            self.current_col = self.next_col
            self.next_col = random.randrange(4)
            self.original_image = self.make_image()

    def point_to_cursor(self):  # rotates cannon original image towards cursor
        self.image = self.original_image.copy()

        mouse_pos = pg.mouse.get_pos()
        self.rad = atan2((self.pos[1]-mouse_pos[1]), (mouse_pos[0]-self.pos[0]))  # angle from cannon center to mouse

        self.image = pg.transform.rotate(self.image, (pi+self.rad)*(180/pi))  # rotation by angle
        self.rect = self.image.get_rect()
        self.rect.center = self.get_center()  # recenters changed cannon image

    def make_image(self):  # renders cannonballs on cannon image (including none if cannon is empty)
        image = Assets.assets['Cannon'].copy()
        image.blit(Assets.assets['Secondary'][self.next_col], (0, 0))

        if self.current_col is not None:
            image.blit(Assets.assets['Primary'][self.current_col], (0, 0))
        return image

    def get_center(self):  # gets offset from position to center cannon on correct axis
        offset = 20*np.array((cos(self.rad), -sin(self.rad)))
        return self.pos+offset

    def draw(self, surface):  # draws cannon and shadow
        surface.blit(self.shadow, self.shadow_rect)
        surface.blit(self.image, self.rect)


# Animation sprite which plays given frame iterable
class Animation(pg.sprite.Sprite):
    def __init__(self, frames, center, game):
        self.game = game
        self.groups = self.game.sprites
        super().__init__(self.groups)

        self.frames = frames
        self.count = len(self.frames)
        self.frame = 0  # index of current frame

        self.image = self.frames[self.frame]
        self.rect = self.image.get_rect()
        self.rect.center = center

    def update(self):
        if self.frame == self.count:  # deletes sprite if no frames remain
            self.kill()
        else:
            self.image = self.frames[self.frame]  # updates and recenters frame image
            old_center = self.rect.center
            self.rect = self.image.get_rect()
            self.rect.center = old_center
            self.frame += 1  # prepares next frame index


class Projectile(pg.sprite.Sprite):
    def __init__(self, colour, pos, velocity, game):
        self.game = game
        self.groups = self.game.sprites, self.game.projectiles
        super().__init__(self.groups)
        self._layer = C.PROJECTILE_LAYER  # draws Projectile on specified layer

        self.radius = C.CANNONBALL_DIM//2
        self.pos = pos
        self.velocity = velocity

        self.colour = colour
        self.image = Assets.assets['Default_C'][self.colour].copy()  # loads and centers image at end of cannon
        self.rect = self.image.get_rect()
        self.rect.center = self.pos

        self.target = None  # the target parameter when integrating into stream

    def update(self):  # updates position and rect center with velocity
        if self.target is not None:  # follows the direction of the target
            diff = Vector2(self.target.rect.center) - self.pos
            self.velocity = C.PROJECTILE_INSERT_VEL*diff.normalize()
            self.pos += self.velocity*self.game.dt
            new_diff = Vector2(self.target.rect.center) - self.pos  # difference between target and potential position

            if new_diff.length() > diff.length():  # if the new position would be further than the current, replace the target
                self.replace_target()

        else:  # updates position in direction of shooting
            self.pos += self.velocity*self.game.dt
            if self.pos[0] < 0 or self.pos[0] > C.WIDTH or self.pos[1] < 0 or self.pos[1] > C.HEIGHT:  # deletes cannonball if it goes off screen
                self.game.score.reset_streak()
                self.kill()
        self.rect.center = self.pos  # updates position on screen

    def replace_target(self):  # updates the image, colour, and checks if a clsuter has been formed
        self.target.image = self.image
        self.target.colour = self.colour
        self.target.placeholder = False
        self.target.chunk.check_cluster(self.target)

        self.kill()


class Cannonball(pg.sprite.Sprite):
    velocity = C.CANNONBALL_VEL

    def __init__(self, chunk, game, colour=-1, parameter=0, placeholder=False):
        self.game = game
        self.groups = self.game.cannonballs, self.game.sprites
        super().__init__(self.groups)

        self.chunk = chunk
        self.parameter = parameter
        self.placeholder = placeholder

        self.radius = C.CANNONBALL_DIM//2
        self.colour = colour
        self.load_image(placeholder)

    def __repr__(self):
        return f'colour {self.colour} parameter {self.parameter}'

    def load_image(self, placeholder):
        if placeholder:  # transparent image is loaded for placeholder for drawing
            self.image = pg.Surface((C.CANNONBALL_DIM, C.CANNONBALL_DIM), pg.SRCALPHA)
        else:  # associated fdefault colour is loaded for actual cannonballs
            self.image = Assets.assets['Default_C'][self.colour].copy()
        self.rect = self.image.get_rect()
        self.rect.center = self.chunk.path.get_pos(self.parameter)

    def destroy(self):  # plays destruction animation
        self.kill()
        Animation(Assets.assets['Destroy'][self.colour], self.rect.center, self.game)

    @classmethod
    def set_velocity(cls, velocity):
        cls.velocity = velocity

    @classmethod
    def get_velocity(cls):
        return cls.velocity


class Points(pg.sprite.Sprite):
    def __init__(self, game, value, colour, pos):
        self.game = game
        super().__init__(self.game.sprites)

        self.value = value
        self.colour = colour
        self.text = get_text_image(str(self.value), 30, self.colour, C.FONT_MOON)

        self.pos = Vector2(pos)
        # random direction vector of magnitude POINT_VELOCITY
        self.velocity = Vector2(random.uniform(-1, 1), random.uniform(0, 1)).normalize()*C.POINT_VELOCITY
        self.alpha = 255

        self.image = self.text
        self.rect = self.image.get_rect()
        self.rect.center = self.pos

    def update(self):
        self.pos += self.velocity*self.game.dt  # postion and transparency updated
        self.rect.center = self.pos
        self.alpha -= C.POINT_FADE*self.game.dt

        new_surface = pg.Surface(self.rect.size, pg.SRCALPHA)  # new image is created
        new_surface.blit(self.text, (0, 0))
        new_surface.set_alpha(self.alpha)
        self.image = new_surface

        if self.alpha <= 0:
            self.kill()


class Coin(pg.sprite.Sprite):
    delay = 0.3  # delay between frames

    def __init__(self, game, pos):
        self.game = game
        self.groups = self.game.sprites, self.game.coins
        super().__init__(self.groups)

        self.frames = Assets.assets['Coin']
        self.length = len(self.frames)
        self.frame = 0  # index of frame for the image
        self.last_frame = pg.time.get_ticks()  # last time stamp of frame update

        self.pos = pos  # position on screen
        self.image = self.frames[self.frame]
        self.rect = self.image.get_rect()
        self.rect.center = self.pos  # centers sprite on the position

    def update(self):
        if (now := pg.time.get_ticks()) - self.last_frame > self.delay:  # if the delay has passed
            self.image = self.frames[self.frame]  # update the image and rect
            self.rect = self.image.get_rect()
            self.rect.center = self.pos  # reposition at the center
            self.frame = (self.frame+1) % self.length  # increment frame and wrap around with modulo
            self.last_frame = now

    def collect(self):  # add points and kill the sprite
        pg.mixer.find_channel().play(self.game.sounds['Coin'])
        self.game.score.points_from_coin(C.COIN_BONUS, self.pos)
        self.kill()
