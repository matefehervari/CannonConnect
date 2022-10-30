import pygame as pg
from Constants import FONT, ARC_SCALE, TILESIZE
from math import sin, cos
from pygame.math import Vector2

pg.font.init()


def get_text_image(text, size, colour, font=FONT):
    f = pg.font.Font(font, size)
    text_image = f.render(text, True, colour)  # text image is rendered of given font
    return text_image


# draws text on screen of given size and position
def draw_text(surf, text, size, colour, x, y, font=FONT, topleft=False):
    text_image = get_text_image(text, size, colour, font)
    text_rect = text_image.get_rect()
    if topleft:  # allows for text to be aligned from top left corner rather than top middle
        text_rect.topleft = (x, y)
    else:
        text_rect.midtop = (x, y)
    surf.blit(text_image, text_rect)  # text is drawn to screen


def straight_piece(prev_param, prev_point, diff):  # returns piece functions for straight
    def piece(t):
        return prev_point + diff.normalize()*(t-prev_param)  # offset in direction of difference and magnitude of parameter
    return piece


def arc_piece(prev_param, prev_point, diff, previous_straight):
    x_sign = diff.x/abs(diff.x)  # signs to rotate arcs
    y_sign = diff.y/abs(diff.y)

    def vert_piece(t):  # piece when turning from verticle
        x_offset = x_sign*(1-cos(2*ARC_SCALE*(t-prev_param)/TILESIZE))
        y_offset = y_sign*(sin(2*ARC_SCALE*(t-prev_param)/TILESIZE))
        return prev_point + Vector2(x_offset, y_offset)*TILESIZE/2

    def hz_piece(t):  # piece when turning from horizontal
        x_offset = x_sign*(sin(2*ARC_SCALE*(t-prev_param)/TILESIZE))
        y_offset = y_sign*(1-cos(2*ARC_SCALE*(t-prev_param)/TILESIZE))
        return prev_point + Vector2(x_offset, y_offset)*TILESIZE/2

    if previous_straight:  # returns correct arc piece
        return hz_piece
    return vert_piece
