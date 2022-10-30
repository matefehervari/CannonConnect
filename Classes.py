import pytmx
import Assets
import random
import Constants as C
import pygame as pg
import Sprites as S
from types import MethodType
from math import pi, exp
from pygame.math import Vector2
from Functions import draw_text, straight_piece, arc_piece


class Map:
    def __init__(self, path=C.MAP_FILE):
        self.tmxdata = pytmx.load_pygame(path)  # TileMap object storng PYTMX data
        self.make_points()

    def make_points(self):
        path = []
        self.coin_points = []
        for obj in self.tmxdata.objects:  # iterates over all objects
            match obj.name:
                # appends tuple of position and type (point number) for sorting
                case 'Path': path.append(((obj.x, obj.y), obj.type))
                case 'Coin': self.coin_points.append((obj.x, obj.y))
                case 'Cannon': self.cannon_pos = (obj.x, obj.y)

        path.sort(key=lambda x: int(x[1]))  # sorts by path number
        self.path_points = list(map(lambda x: x[0], path))  # removes path number

    def get_path_points(self):  # getters for points
        return self.path_points

    def get_coint_points(self):
        return self.coin_points

    def get_cannon_pos(self):
        return self.cannon_pos


class Path:
    def __init__(self, points, game):
        self.game = game
        self.curve = self.build_curve(points)
        self.end = self.curve[-2][1]  # final parameter (index -1 prevents cannonballs from over shooting end)

        self.head_chunk = Chunk(self, self.game, is_head=True, is_tail=True)  # stores the start of the chunk linked list
        self.tail_chunk = self.head_chunk  # initially the head and tail are the same as there is 1 chunk
        self.chunks = {self.head_chunk: [None, None]}  # doubly linked list
        self.spawn_stack = []

        self.ball_vel = C.CANNONBALL_VEL  # changes cannonball velocity over time

        self.powerup = Powerup()

        self.reversing = False  # reverse motion parameters
        self.reversing_vel = None
        self.reverse_start = None
        self.reverse_length = 0

        self.slowed = False  # slowed motion parameters
        self.slow_start = None
        self.slow_length = 0

        self.colours_to_destroy = []  # must destroy colour after all other updates have been called to avoid conflicts
        self.destroying_colour = False

    def update(self):
        self.head_chunk.spawn(self.game.get_colour())

        if self.reversing and pg.time.get_ticks() > self.reverse_start+self.reverse_length:  # disables reversal if enough time has passed
            self.reversing = False
        if self.slowed and pg.time.get_ticks() > self.slow_start+self.slow_length:  # disables slow if enough time has passed
            self.slowed = False

        # sets velocity depending on state of cannonballs
        if self.reversing:  # reversing
            S.Cannonball.set_velocity(self.reversing_vel)
        elif self.slowed:  # slowed motion
            S.Cannonball.set_velocity(C.POWERUP_SLOW_VELOCITY)
        elif self.end - (t := self.tail_chunk.get_end_param()) < C.SLOW_DIST:  # slowed at end
            S.Cannonball.set_velocity(self.get_decay_vel(t))
        else:  # normal motion
            S.Cannonball.set_velocity(self.ball_vel)

        current = self.head_chunk  # iteration through linked list to update chunks
        while current is not None:
            current.update()
            deleted_fallback = self.check_deleted(current)
            if deleted_fallback == 'STOP ITER':  # avoids bug when deltion of last chunk is detected
                break
            elif deleted_fallback is not None:  # continues to next chunk if current is deleted
                current = deleted_fallback
                continue

            prev, post = self.chunks[current]  # checks for chunks collision backwards (during backwards acceleration)
            if prev is not None and prev.tail_ball is not None and prev.get_end_param()+C.CANNONBALL_DIM > current.get_start_param():
                self.connect(prev, current)
                deleted_fallback = self.check_deleted(current)
                if deleted_fallback == 'STOP ITER':
                    break
                current = deleted_fallback
                continue

            if post is not None:  # checks for forward collision
                if current.get_end_param()+C.CANNONBALL_DIM > post.get_start_param():
                    self.connect(current, post)
                    self.check_deleted(post)

                new_post = self.chunks[current][1]  # creates a new post which points to chunk after current as post may have been deleted during connection
                if new_post is not None and current.tail_ball.colour == new_post.head_ball.colour:  # checks for matching colours with next chunk
                    post.accelerating = True

            current = self.chunks[current][1]

        self.ball_vel += C.DV*self.game.dt  # increases velocity with time
        for colour in self.colours_to_destroy:
            self.destroy_colour(colour)
        self.colours_to_destroy = []

    def build_curve(self, points):  # creates piecewise function
        curve = []  # [(piece, upper parameter bound) ...]
        prev_param = 0
        prev_point = Vector2(*points[0])
        previus_straight = 0  # 1 defines horizontal, 0 defines vertical

        for p in points[1:]:
            point = Vector2(*p)
            diff = point-prev_point

            if point.x != prev_point.x and point.y != prev_point.y:  # arc piece
                upper = ((C.TILESIZE*pi)/(4*C.ARC_SCALE)) + prev_param  # change in difference of parameter is the value required for the input to equal pi/2
                piece = arc_piece(prev_param, prev_point, diff, previus_straight)
                previus_straight = not previus_straight  # the direction of straigh paths is flipped (turning will change from horizontal to vertical)

            else:  # straight piece
                upper = diff.length() + prev_param  # change in parameter due to a straight piece is the difference itself
                piece = straight_piece(prev_param, prev_point, diff)
                previus_straight = bool(diff.x)  # a change in x has boolean value of True

            curve.append((piece, upper))
            prev_param = upper  # updates previous data
            prev_point = point

        return curve

    def get_pos(self, parameter):  # returns cartesian position from parameter
        for piece, upper in self.curve:
            if parameter < upper:  # if parameter is less than upper, the current piece must be used
                if parameter > self.end:  # checks if cannonballs reached end
                    self.game.lose()
                    self.reverse(C.LOSE_REVERSE_DURATION, C.REVERSE_VELOCITY)

                return piece(parameter)

    def draw_curve(self, surface):  # draws red line along path for debugging
        for t in range(int(self.curve[-1][1])):
            pg.draw.circle(surface, C.RED, self.get_pos(t), 2)

    def get_decay_vel(self, t):  # velocity following piecewise decay function
        x = t-self.end+C.SLOW_DIST  # variable for exponential decay (starts at 0 when reaching slow dist) (t-(self.end-C.SLOW_DIST))
        exp_coeff = C.CANNONBALL_VEL-C.MIN_CANNONBALL_VEL
        unscaled = C.MIN_CANNONBALL_VEL + exp_coeff*exp(-x/C.DECAY_DIST)  # exponential decay

        # traces straight line from points (1, min_vel) to (decay_dist, unscaled_value)
        scalar = (((C.MIN_CANNONBALL_VEL+exp_coeff*exp(-1)/C.MIN_CANNONBALL_VEL)-1)/C.DECAY_DIST)*x + 1
        scaled = unscaled/scalar  # smooth curve exponentially decaying from initial velocity to minimum
        return max(scaled, C.MIN_CANNONBALL_VEL)  # takes minimum value after x > decay_dist

    def check_deleted(self, chunk):  # deletes chunk and returns next chunk to progress to
        if chunk.deleted:  # catches chunk deletion preventing further updates
            post = self.chunks[chunk][1]
            del self.chunks[chunk]
            del chunk

            if post is not None:
                return post
            else:
                return 'STOP ITER'

    def remove_start(self, chunk, cluster_tail):  # removes cluster at the start of chunk
        new_head = chunk.cannonballs[cluster_tail][1]
        chunk.cannonballs[new_head][0] = None
        chunk.destroy_cannonballs(chunk.head_ball, cluster_tail)
        chunk.head_ball = new_head

        if chunk == self.head_chunk:  # checks if this is an head chunk
            chunk.is_head = False  # converts chunk into normal chunk
            new_head_chunk = Chunk(self, self.game, is_head=True)  # creates new head chunk
            self.chunks[new_head_chunk] = [None, chunk]
            self.chunks[chunk][0] = new_head_chunk
            self.head_chunk = new_head_chunk

    def remove_chunk(self, chunk):  # removes an isolated chunk of single colour
        if chunk != self.head_chunk:
            prev = self.chunks[chunk][0]  # detatches chunk pointers
            post = self.chunks[chunk][1]
            self.chunks[prev][1] = post

            if post is not None:
                self.chunks[post][0] = prev
            else:
                prev.is_tail = True

            chunk.destroy_cannonballs(chunk.head_ball, chunk.tail_ball)  # destroys cannonballs
            chunk.deleted = True  # sets future deletion which is handled more appropriately elsewhere
        else:  # head chunk is a single colour and must not be deleted
            chunk.destroy_cannonballs(chunk.head_ball, chunk.tail_ball)
            chunk.head_ball = chunk.tail_ball = None

    def remove_slice(self, chunk, cluster_head, cluster_tail):  # removes cluster from middle of chunk, creating 2 new chunks
        cannonballs = chunk.cannonballs

        new_chunk = Chunk(self, self.game)  # creates new chunk (right)
        new_chunk_head = current = cannonballs[cluster_tail][1]  # new head for right chunk
        current.chunk = new_chunk  # initial cannonball chunk must be reassigned
        post = cannonballs[current][1]

        right_cannonballs = {current: [None, None]}
        while post is not None:  # copies all cannonballs after and including new head
            post.chunk = new_chunk
            right_cannonballs[current][1] = post  # sets forwards and backwards pointer
            right_cannonballs[post] = [current, None]

            current, post = post, cannonballs[post][1]  # progresses current and post cannonball

        new_chunk.cannonballs = right_cannonballs  # assigns cannonballs, head and tail to chunks
        new_chunk.head_ball = new_chunk_head
        new_chunk.tail_ball = chunk.tail_ball

        #  old chunk
        chunk.tail_ball = cannonballs[cluster_head][0]  # moves the tail of the left chunk back
        cannonballs[chunk.tail_ball][1] = None  # new tail points to None
        for right_ball in right_cannonballs:  # removes all cannonballs in the right chunk
            del chunk.cannonballs[right_ball]
        chunk.destroy_cannonballs(cluster_head, cluster_tail)  # destroys the cluster

        # inserts new chunk
        next_chunk = self.chunks[chunk][1]  # chunk after the left chunk (new right)
        self.chunks[new_chunk] = [chunk, next_chunk]  # adds new chunk pointing to left and right
        self.chunks[chunk][1] = new_chunk  # left points forwards to new chunk

        if next_chunk is not None:
            self.chunks[next_chunk][0] = new_chunk  # right points back to new chunk

        if self.tail_chunk == chunk:  # updates tail
            self.tail_chunk = new_chunk
            new_chunk.is_tail = True
            chunk.is_tail = False

    def connect(self, left, right):  # connects 2 chunks
        pg.mixer.find_channel().play(self.game.sounds['Collide'])
        connection = left.tail_ball  # stores cannonball of left chunk which meets the right chunk
        accelerating = right.accelerating
        left.cannonballs.update(right.cannonballs)  # adds right cannonballs to left
        left.cannonballs[left.tail_ball][1] = right.head_ball  # forms connection between pointers
        left.cannonballs[right.head_ball][0] = left.tail_ball

        current = right.head_ball  # updates chunks for newly added cannonballs
        while current is not None:
            current.chunk = left

            if accelerating:  # cannonballs must perfectly collide and not overlap if accelerating backwards
                current.parameter = left.cannonballs[current][0].parameter+C.CANNONBALL_DIM
                current.rect.center = self.get_pos(current.parameter)
            current = left.cannonballs[current][1]
        left.tail_ball = right.tail_ball  # tail is moved to the end

        post = self.chunks[right][1]  # detatches pointers from righht chunk which wil lbe deleted
        self.chunks[left][1] = post
        if post is not None:
            self.chunks[post][0] = left

        if self.tail_chunk == right:  # updates tail
            right.is_tail = False
            left.is_tail = True
            self.tail_chunk = left

        right.deleted = True

        if accelerating:  # cluster must only be checked if acceleration occured
            left.check_clusters([connection])
        else:  # shift is applied if not accelerating to avoid snapping when cannonball insertion creates connection
            left.shift_after_connect = connection

    def upgrade_random(self):  # selects random cannonball from a random chunk to upgrade
        cannonball = random.choice(list(self.chunks.keys())).get_random()
        if not hasattr(cannonball, 'powerup'):
            self.powerup.upgrade(cannonball)

    def reverse(self, duration, velocity):  # enables reverse motion
        self.reversing = True
        self.reversing_vel = velocity
        self.reverse_start = pg.time.get_ticks()
        self.reverse_length = duration

    def slow(self, duration):  # enables slowed motion
        self.slowed = True
        self.slow_start = pg.time.get_ticks()
        self.slow_length = duration

    def destroy_colour(self, colour):
        colour_heads = []
        self.destroying_colour = True

        current = self.head_chunk  # gets first cannonball in each coloured cluster
        while current is not None:
            colour_heads += current.get_colour_heads(colour)
            current = self.chunks[current][1]

        for head in colour_heads:  # destroys clusters associated with heads
            head.chunk.check_clusters(check=[head])
        self.destroying_colour = False


class Chunk:
    def __init__(self, path, game, cannonballs={}, head=None, tail=None, is_head=False, is_tail=False):
        self.game = game
        self.path = path
        self.deleted = False  # used by path during updates to delete the chunk when all pointers have been detatched

        self.head_ball = head  # cannonball storage variables
        self.tail_ball = tail
        self.cannonballs = cannonballs

        self.accelerating = False  # variables for motion
        self.accelerating_velocity = 0

        self.shift_after = None
        self.shift_after_connect = None
        self.is_head = is_head  # is used when moving cannonballs to leave isolated chunks stationary
        self.is_tail = is_tail

        self.cluster_buffer = []

    def __repr__(self):  # representation of chunk for debugging
        return 'Chunk: '+' '.join(iter(map(lambda x: str(x.colour), self.cannonballs)))

    def __str__(self):
        return 'Chunk: '+' '.join(iter(map(lambda x: str(x.colour), self.cannonballs)))

    def update(self):  # updates position of all cannonballs and checks for cluster matches
        self.check_clusters()
        if self.deleted:  # update is halted if chunk is deleted
            return

        if self.accelerating:
            self.accelerating_velocity += C.ACCELERATION*self.game.dt  # updates accelerating velocity

        base_velocity = self.accelerating_velocity*self.accelerating  # velocity occuring naturally without projectile insertion
        if S.Cannonball.velocity > 0:  # only head moves forward
            base_velocity += S.Cannonball.velocity*self.is_head
        else:  # only tail reverses
            base_velocity += S.Cannonball.velocity*self.is_tail
        # base_velocity = S.Cannonball.velocity*self.is_head+self.accelerating_velocity*self.acceleratin
        increment = base_velocity  # cannonball parameters wil lbe investigated by base velocity by default
        current = self.head_ball
        while current is not None:
            current.parameter += increment  # updates cannonball positions
            current.rect.center = self.path.get_pos(current.parameter)

            if current == self.shift_after and (post := self.cannonballs[current][1]) is not None:  # starts shifting cannonballs as shift after is no longer None
                next_param = post.parameter  # parameter of next cannonball
                new_param = next_param + C.SHIFT_VELOCITY  # potential parameter of next cannonball
                if new_param > current.parameter+C.CANNONBALL_DIM:  # parameter too large and would disconnect chunk from current
                    increment = current.parameter+C.CANNONBALL_DIM-next_param  # increment shifts cannonballs just enough
                    self.shift_after = None
                else:  # an overlap would exist and the shift velocity must be applied
                    increment = C.SHIFT_VELOCITY

            # a separate check for shifting must be done to prevent shift_After being overwritten during chunk collision and insertion
            if current == self.shift_after_connect and (post := self.cannonballs[current][1]) is not None:  # starts shifting cannonballs due to forwards collision between chunks
                next_param = post.parameter  # parameter of previous cannonball
                new_param = next_param + C.SHIFT_VELOCITY  # potential parameter of next cannonball
                if new_param > current.parameter+C.CANNONBALL_DIM:  # parameter too large and would disconnect chunk from current
                    increment = current.parameter+C.CANNONBALL_DIM-next_param  # increment shifts cannonballs just enough
                    self.shift_after_connect = None
                else:
                    increment = C.SHIFT_VELOCITY

            # self.show_parameter(current)
            post = self.cannonballs[current][1]
            if current.parameter < -C.CANNONBALL_DIM/2:  # removes cannonball from chunk if it goes back off screen
                self.path.spawn_stack.append(current)  # adds cannonball to stack
                self.head_ball = post

                if self.head_ball is not None:  # updates pointers if a head ball exists
                    self.cannonballs[self.head_ball][0] = None
                    del self.cannonballs[current]
                else:  # otherwise stops reversal as there is nothing to reverse
                    self.path.reversing = False

            current = post

    def show_parameter(self, cannonball):  # draws parameter onto cannonballs for debugging
        cannonball.load_image(cannonball.placeholder)
        draw_text(cannonball.image, str(int(cannonball.parameter)), 10, C.WHITE, 45, 45)

    def spawn(self, colour=-1):  # attempts to spawn a cannonball at the start of the chunk
        if self.head_ball is None:  # first cannonball must be spawned in the chunk
            if self.path.spawn_stack:  # if there are cannonballs in the spawn stack, they are prioritised
                new = self.path.spawn_stack.pop()
            else:
                new = S.Cannonball(self, self.game, colour)
            self.cannonballs[new] = [None, None]
            self.tail_ball = new
            self.head_ball = new

        elif self.head_ball.parameter >= C.CANNONBALL_DIM/2:  # cannonball must be inserted at the start of the chunk updating pointers
            if self.path.spawn_stack:
                new = self.path.spawn_stack.pop()
                new.parameter = self.head_ball.parameter - C.CANNONBALL_DIM
            else:
                new = S.Cannonball(self, self.game, colour, self.head_ball.parameter-C.CANNONBALL_DIM)
            self.cannonballs[new] = [None, self.head_ball]
            self.cannonballs[self.head_ball][0] = new
            self.head_ball = new

    def get_start_param(self):  # returns parameter of first cannonball
        return self.head_ball.parameter

    def get_end_param(self):  # returns parameter of last cannonball
        return self.tail_ball.parameter

    def insert(self, cannonball, projectile):  # inserts a placeholder on the nearest side of a cannonball and sets the projectile target
        prev = self.cannonballs[cannonball][0]  # gets positions of cannonballs before and after
        prev_pos = self.path.get_pos(cannonball.parameter-C.CANNONBALL_DIM)

        post = self.cannonballs[cannonball][1]
        post_pos = self.path.get_pos(cannonball.parameter+C.CANNONBALL_DIM)

        if (prev_pos-projectile.pos).length() < (post_pos-projectile.pos).length():  # projectile is closer to the previous cannonball
            if cannonball.chunk.head_ball == cannonball:  # insert onto the start of chunk
                place = S.Cannonball(self, self.game, parameter=cannonball.parameter-C.CANNONBALL_DIM, placeholder=True)
            else:  # insert at the cannonball pushing all cannonballs forward
                place = S.Cannonball(self, self.game, parameter=cannonball.parameter, placeholder=True)
            insert_side = 0  # before
        else:
            place = S.Cannonball(self, self.game, parameter=cannonball.parameter+C.CANNONBALL_DIM, placeholder=True)  # insert at the cannonball after pushing cannonballs forward
            insert_side = 1  # after

        if insert_side:  # insert after cannonball
            self.cannonballs[cannonball][1] = place  # cannonball points forward to place

            if post is not None:  # inserting between 2 cannonballs
                self.cannonballs[post][0] = place  # post points backwards to place
                self.cannonballs[place] = [cannonball, post]  # place points to both directions
                self.shift_after = place
            else:  # inserting at the end of the chunk
                self.cannonballs[place] = [cannonball, None]
                self.tail_ball = place

        else:  # insert before cannonball
            self.cannonballs[cannonball][0] = place

            if prev is not None:  # inserting between 2 cannonballs
                self.cannonballs[prev][1] = place
                self.cannonballs[place] = [prev, cannonball]
                self.shift_after = place
            else:  # inserting at the start of the chunk
                self.cannonballs[place] = [None, cannonball]
                self.head_ball = place

        projectile.target = place  # sets target for projectile

    def check_cluster(self, cannonball):  # adds a cannonball to cluster checking buffer
        self.cluster_buffer.append(cannonball)

    def check_clusters(self, check=[]):
        if self.shift_after is None:  # only check for clusters after projectile has fully been inserted
            for cannonball in self.cluster_buffer+check:
                count = 1
                cluster_head = cluster_tail = cannonball

                while True:  # parses backwards
                    new_head = self.cannonballs[cluster_head][0]
                    if new_head is None or new_head.colour != cannonball.colour:
                        break
                    else:
                        count += 1
                        cluster_head = new_head

                while True:  # parses forwards
                    new_tail = self.cannonballs[cluster_tail][1]
                    if new_tail is None or new_tail.colour != cannonball.colour:
                        break
                    else:
                        count += 1
                        cluster_tail = new_tail

                if count >= 3 or self.path.destroying_colour:  # cluster is destroyed if it has sufficient size or colour bomb is active
                    self.game.score.points_from_cluster(count, cannonball.colour, cannonball.rect.center)  # points are added
                    self.destroy_cluster(cluster_head, cluster_tail)

                elif cannonball not in check:  # insufficient cluster size achieved with insertion so streak is reset
                    self.game.score.reset_streak()
            self.cluster_buffer = []

    def destroy_cluster(self, cluster_head, cluster_tail):
        self.game.sounds['Cluster'].play()
        pg.mixer.find_channel().play(self.game.sounds['Cluster'])
        if cluster_head == self.head_ball and cluster_tail == self.tail_ball:  # entire chunk is destroyed
            self.path.remove_chunk(self)

        elif cluster_head == self.head_ball:  # start of chunk is destroyed
            self.path.remove_start(self, cluster_tail)

        elif cluster_tail == self.tail_ball:  # end of chunk is destroyed
            self.tail_ball = self.cannonballs[cluster_head][0]
            self.cannonballs[self.tail_ball][1] = None
            self.destroy_cannonballs(cluster_head, cluster_tail)
        else:  # slice of chunk is destroyed in the middle
            self.path.remove_slice(self, cluster_head, cluster_tail)

    def destroy_cannonballs(self, start, end):  # cannonballs are removed and destroyed
        destroying = True
        while destroying:
            if start == end:
                destroying = False
            post = self.cannonballs[start][1]
            del self.cannonballs[start]
            start.destroy()
            start = post

    def get_random(self):  # returns random cannonball
        return random.choice(list(self.cannonballs.keys()))

    def get_colour_heads(self, colour):  # the first cannonball in each cluster of the specified colour
        colour_heads = []
        in_cluster = False

        current = self.head_ball
        while current is not None:
            if current.colour == colour and not in_cluster:
                colour_heads.append(current)
                in_cluster = True
            else:
                in_cluster = False
            current = self.cannonballs[current][1]

        return colour_heads


class Score:
    def __init__(self, game, score_x, score_y, streak_x, streak_y, size):
        self.game = game
        self.score_pos = (score_x, score_y)  # position of score text
        self.streak_pos = (streak_x, streak_y)  # position of streak text
        self.points = 0
        self.streak = 0
        self.size = size

    def points_from_cluster(self, cluster_size, colour, pos):
        acquired = cluster_size*10*min(max(2, self.streak)-1, 5)  # 10 per cannonball multiplied by streak count above and including 3
        self.points += acquired
        self.streak += 1

        S.Points(self.game, acquired, C.COLOURS[colour], pos)  # creates points animation

    def points_from_coin(self, acquired, pos):  # used by coints to directly add points
        self.points += acquired
        S.Points(self.game, acquired, C.YELLOW, pos)

    def draw(self, surface):  # draws 2 texts
        draw_text(surface, str(self.points), self.size, C.WHITE, *self.score_pos, C.FONT_MOON)
        draw_text(surface, str(self.streak), self.size, C.YELLOW, *self.streak_pos, C.FONT_MOON)

    def reset_streak(self):
        self.streak = 0


class Powerup:
    def __init__(self):
        self.powerups = ('Reverse_C', 'Slow_C')  # , 'Bomb_C')

    def upgrade(self, cannonball):
        powerup = random.choice(self.powerups)  # chooses random powerup
        cannonball.powerup = powerup
        match powerup:
            case 'Reverse_C':
                cannonball.load_image = MethodType(Powerup.load_image, cannonball)  # overwrites load_image method of the cannonball
                #  uses polymorphism to destroy the cannonball and the apply additional effects
                cannonball.destroy = MethodType(Powerup.destroy_wrapper(cannonball.destroy, Powerup.destroy_reverse), cannonball)
            case 'Slow_C':
                cannonball.load_image = MethodType(Powerup.load_image, cannonball)
                cannonball.destroy = MethodType(Powerup.destroy_wrapper(cannonball.destroy, Powerup.destroy_slow), cannonball)
            case 'Bomb_C':
                cannonball.load_image = MethodType(Powerup.load_image, cannonball)
                cannonball.destroy = MethodType(Powerup.destroy_wrapper(cannonball.destroy, Powerup.destroy_bomb), cannonball)

        cannonball.load_image()

    @staticmethod  # uses static method as Powerup and instance of class is not used
    def destroy_wrapper(destroy_func, destroy_wrapper):
        def wrapped(cannonball):
            destroy_func()  # already a method type from the cannonball so reference does not need to be passed
            destroy_wrapper(cannonball)
        return wrapped

    @staticmethod
    def load_image(cannonball):
        cannonball.image = Assets.assets[cannonball.powerup][cannonball.colour].copy()
        cannonball.rect = cannonball.image.get_rect()

    @staticmethod
    def destroy_reverse(cannonball):
        pg.mixer.find_channel().play(cannonball.game.sounds['Reverse'])
        cannonball.chunk.path.reverse(C.POWERUP_DURATION, C.POWERUP_REVERSE_VELOCITY)

    @staticmethod
    def destroy_slow(cannonball):
        pg.mixer.find_channel().play(cannonball.game.sounds['Slow'])
        cannonball.chunk.path.slow(C.POWERUP_DURATION)

    @staticmethod
    def destroy_bomb(cannonball):
        path = cannonball.chunk.path
        if not path.destroying_colour:
            path.colours_to_destroy.append(cannonball.colour)
