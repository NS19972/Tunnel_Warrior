#######################################################
# Copyright © 2019-2099 Nikita Serov. All rights reserved
# Author: Nikita Serov

# Мой первый проект, был создан в ноябре 2019-го года
#######################################################

import pygame as pg
import random
from noise import snoise2
import os, sys
from pygame.locals import *
import time
import math
import threading
import winsound
from win32api import GetSystemMetrics

pg.init()
pg.font.init()

##Helper functions

# helper function that takes in dictionary keys and returns a list of them
def getList(dict):
    list = []
    for key in dict.keys():
        list.append(key)
    return list


# Function that decomposes an angle into x and y coordinates
def angle(theta):
    return [math.sin(theta), math.cos(theta)]


def degrees(vector):  # Function that converts a vector into degrees (0 degrees is defined as vertical)
    return math.atan2(-vector[0], -vector[1]) * 180 / math.pi


def randomize_direction(vector,
                        max_offset):  # Generates a randomized direction relative to a given vector, with a variable offset.
    vector = norm(vector)
    offset = (random.random() * 2 * max_offset) - max_offset
    theta = degrees(vector) + offset
    new_vector = [math.sin((theta + 180) * 2 * math.pi / 360), math.cos((theta + 180) * 2 * math.pi / 360)]
    return new_vector


def perpendicular_direction(
        vector):  # Generates a randomized direction relative to a given vector, with a variable offset.
    vector = norm(vector)
    offset = random.choice([90, -90])
    theta = degrees(vector) + offset
    new_vector = [math.sin((theta + 180) * 2 * math.pi / 360), math.cos((theta + 180) * 2 * math.pi / 360)]
    return new_vector


# Return damage to be equally split between player health and armor
def dmgsplit(damage):
    dmgfactor = random.random()
    return damage * dmgfactor, damage * (1 - dmgfactor)


# Function used to calculate if any two objects collide. Collision is defined as if two objects share the same tile.
# Although PyGame has some built-in functionality for detecting collisions, its methods are not suitable for things such as
# line of sight detection, and for the purposes of this game this collision function is faster.
def collision(object1, object2, tile_size):
    if object1.x // tile_size == object2.x // tile_size and object1.y // tile_size == object2.y // tile_size:
        return True


# Each character will occupy several tiles at a time, determined by their 'hit box'.
# This function calculates which tiles a character occupies (ie. if a character is in lava or in water).
def get_tiles(corners, game_map):
    tiles = []
    for corner in corners:
        (x, y) = map(lambda xy: int(xy // game_map.tile_size), corner)
        try:  # add a try/except clause because the code might pick up non-existent tiles and crash if near the border
            tiles.append(game_map.tiles[x][y].type)
        except:
            tiles.append(None)
    return tiles


# Function that moves the player to prevent getting stuck when colliding with objects (ie. world border)
def back_up(var):
    if var < 0:
        var += 1
    else:
        var -= 1
    return var


# The following function allows for smooth movement along the combination of any two axes.
# ie. onstead of a movement speed of 2.4 being rounded down to 2 each time, the .4 is stored in a separate variable, becomes
# .8 and 1.2 in the following ticks, and upon which 1 is subtracted from the remainder and added to the whole offset,
# so one can move 7 pixels in 3 turns.
def calculate_movement(position, vel, pos_rem, speed):
    for i in range(len(position)):
        position[i] += round(vel[i] * speed)
        pos_rem[i] += (vel[i] * speed - round(vel[i] * speed))
        if pos_rem[i] >= 1:
            position[i] += 1
            pos_rem[i] -= 1
        elif pos_rem[i] <= -1:
            position[i] -= 1
            pos_rem[i] += 1
    return position, pos_rem


def simple_move(position, vel,
                speed):  # much simpler version of the movement system, used for resource-intensive vision algorithm
    for i in range(len(position)):
        position[i] += round(vel[i] * speed)
    return position


def is_between(point, limits):  # Function to check if a number lies in a certain range
    if point >= limits[0] and point <= limits[1]:
        return True
    elif point <= limits[0] and point >= limits[1]:
        return True


def is_between_degrees(vector1, vector2, limits):
    if (is_between(degrees(vector1), [degrees(vector2) - limits, degrees(vector2) + limits]) or is_between(
            degrees(vector1) - 360, [degrees(vector2) - limits, degrees(vector2) + limits])):
        return True


def in_box(coord1, coord2, coord3,
           projectile_size=0):  # function checks if a coordinate lies between two other coordinates.
    hitbox_mod = projectile_size / 2
    if is_between(coord1[0], (coord2[0] - hitbox_mod, coord3[0] + hitbox_mod)) and is_between(coord1[1], (
    coord2[1] - hitbox_mod, coord3[1] + hitbox_mod)):
        return True


def in_bounds(coord, game_map):  # <-- function checks if a coordinate is within map boundaries
    if in_box(coord, (0, 0), (game_map.xsize * game_map.tile_size - 1, game_map.ysize * game_map.tile_size - 1)):
        return True


def in_screen(entity,
              player):  # <-- checks if an entity is within the 'screen' bounds of the player (doesn't require an actual player)
    padding = 50  # padding is 50 pixels
    if is_between(entity.xy[0], (player.xy[0] - half_width - padding, player.xy[0] + half_width + padding)) and \
            is_between(entity.xy[1], (player.xy[1] - half_height - padding, player.xy[1] + half_height + padding)):
        return True
    else:
        return False


def norm(vector):  # Normalizes a vector such that its components add up to a magnitude of one
    mag = 0
    for i in iter(vector): mag += i ** 2
    mag = mag ** 0.5
    for i in range(len(vector)):
        try:
            vector[i] /= mag  # add a try/except clause to avoid division-by-zero error when standing still.
        except:
            vector[i] = 0
    return vector


def distance(point1, point2):  # Calculates the distance between two points.
    sum_ = 0
    for i in range(len(point1)):
        sum_ += (point1[i] - point2[i]) ** 2
    final = sum_ ** 0.5
    return final


# Creates a thread and allows the sounds to run asynchronously!!!
def Play_sound(file, a=1):
    t1 = threading.Thread(target=lambda: Play(file, a))
    t1.daemon = True
    t1.start()


def Play(file, a=0):
    winsound.PlaySound(file, a)


def Play_sound_ambiance(
        file):  # Have to use two separate modules to play background and foreground sounds, because both winsound and pygame mixer suck and don't actually support asynchronous playbacks even though they state they do...
    if Audio is not None:
        pg.mixer.music.load(file)
        pg.mixer.music.play()


def center_image(pos,
                 img_size=32):  # provides the coordinate-based centers to an image, instead of having the 'origin' in the top-left corner.
    return [pos[0] + int(img_size / 2), pos[1] + int(img_size / 2)]


def word(direction):  # Takes in a direction vector and returns its value in English words.
    if direction == (0, 1):
        return 'front'
    elif direction == (1, 0):
        return 'right'
    elif direction == (-1, 0):
        return 'left'
    elif direction == (0, -1):
        return 'back'


def round_mag(num):  # rounds a number so that it retains its sign, but increases in magnitude.
    if num >= 0:
        result = math.ceil(num)
    else:
        result = math.floor(num)
    return result


def round_vector(vector):  # Rounds a vector to an angle of 0, 90, 180, or 270 degrees.
    vector = norm(vector)
    return_vector = []
    for element in vector:
        sign = get_sign(element)
        return_vector.append(round(element ** 2) * sign)
    if return_vector[0] == return_vector[1]:  # This safety-measure will be called very, very rarely
        sign0 = get_sign(vector[0])
        return_vector[0] = 1 * sign0
    return return_vector


def get_sign(i):
    if i < 0:
        return -1
    else:
        return 1


def opposite(direction):  # Returns the opposite of a given direction (180 degree rotation).
    new_direction = [-direction[0], -direction[1]]


###Constants

lava_texture = pg.image.load(
    'images/terrain/lava.png')  # Pre-load all the textures once, as to avoid laoding them every time
water_texture = pg.image.load('images/terrain/water.png')  # a new tile is drawn
sediment_texture = pg.image.load('images/terrain/sediment.png')
cave_texture = pg.image.load('images/terrain/cave.png')
bedrock_texture = pg.image.load('images/terrain/bedrock.png')
rock_texture = pg.image.load('images/terrain/rock.png')

noise_texture = pg.image.load('images/ambiance/noise.png')


# Character textures
class Textures():  # Create empty class to set all textures
    def __init__(self):
        pass

textures = Textures()

# Load all the necessary textures into the textures class.

def load_textures(directory):
    for subdir, dirs, files in os.walk(directory):
        for file in files:
            file = file[:-4]  # remove .png from file name
            setattr(textures, file, pg.image.load(directory + '/' + file + '.png'))


load_textures('images/enemy')
load_textures('images/player')
load_textures('images/static')
load_textures('images/ui')

illegal_tiles = ["rock", "bedrock", "sediment", None]  # This list contains all tile types that can't be moved through.
vision_tiles = ['lava', 'cave', 'water']  # This list contains all tiles that light can pass through
bad_tiles = ['lava', None]  # List containing tiles AI shouldn't walk into.
liquids = ['water', 'lava']  # List containing blocks that one can see across, but not shoot across easily.

directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Express direction as a set of coordinates for processing.

ambiances = ['Sounds/ambiance/ambiance1.wav', 'Sounds/ambiance/ambiance2.wav',
             'Sounds/ambiance/ambiance3.wav']  # <-- A random sound will be played from this list.

game_speed = 30  # determines how many ticks per second the game runs at.


class Button:
    def __init__(self, x, y, length, height, screen, function, clicksound="clicked.wav", active=True):
        self.x = x
        self.y = y
        self.length = length
        self.height = height
        self.screen = screen
        self.function = function
        self.clicksound = clicksound
        self.area = pg.Rect(self.x - self.height / 2, self.y, self.length + self.height, self.height)
        self.hover = True
        self.active = active

    def __repr__(self):
        return 'A clickable button, optionally connected to some function.'

    def __str__(self):
        return 'A class used to create and draw clickable buttons, which are connected to some function.'

    def draw(self, shape, mpos, clicked, text=None, font_size=50, rgb=(67, 0, 207), text_rgb=(220, 180, 200)):
        if self.active:
            rgb = rgb
            self.mpos = mpos

            draw_button = pg.Rect(self.x, self.y, self.length, self.height)

            if not self.area.collidepoint(self.mpos):
                self.hover = False

            else:
                rgb = (134, 0, 207)
                if not self.hover:
                    Play_sound('Sounds/ui/hover.wav')
                self.hover = True
                if clicked:
                    Play_sound('Sounds/ui/' + self.clicksound)
                    self.function.__call__()
            pg.draw.rect(self.screen, rgb, draw_button)

        def triangles():
            pg.draw.polygon(self.screen, rgb, [[self.x, self.y], [self.x - self.height / 2, self.y + self.height / 2],
                                               [self.x, self.y + self.height]])
            pg.draw.polygon(self.screen, rgb, [[self.x + self.length, self.y],
                                               [self.x + self.height / 2 + self.length, self.y + self.height / 2],
                                               [self.x + self.length, self.y + self.height]])

        if shape == "triangles":
            triangles()

        if text is not None:
            font = pg.font.SysFont('Sans', font_size)
            text = font.render(text, True, text_rgb)
            text_rect = text.get_rect(center=(self.x + self.length / 2, self.y + self.height / 2))
            self.screen.blit(text, text_rect)

    def activate(self):  # activates the button
        self.active = True


class Index_Button(Button):
    def draw(self, texture_path, mpos, clicked, text=None, font_size=40, text_rgb=(220, 180, 200)):
        self.mpos = mpos
        if not self.area.collidepoint(self.mpos):
            self.hover = False
        else:
            self.hover = True
            if clicked:
                Play_sound('Sounds/ui/' + self.clicksound)
                self.function.__call__()

        texture = pg.image.load(texture_path)
        texture = pg.transform.scale(texture, (self.length, self.height))
        self.mpos = mpos
        self.screen.blit(texture, (self.x, self.y))


def write_text(textfont, text, font_size, rgb, horizontal, vertical, screen):
    font = pg.font.SysFont(textfont, font_size)
    text = font.render(text, True, rgb)
    text_rect = text.get_rect(center=(horizontal, vertical))
    screen.blit(text, text_rect)


def write_text_from_file(textfont, file_path, font_size, rgb, horizontal, vertical, screen, offset_x=0, offset_y=0,
                         limit_y=0,
                         center=True):  # Modified function designed to read multiple lines from text files and write them to a pygame screen.
    font = pg.font.SysFont(textfont, font_size)
    i = 0
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for i, line in enumerate(lines):
            line = line[0:-1]  # <--- delete last character in string to avoid a bug.
            text = font.render(line, True, rgb)
            if is_between(vertical + i * font_size + offset_y, [limit_y, screen_height]):
                if center:
                    text_rect = text.get_rect(center=(horizontal + offset_x, vertical + i * font_size + offset_y))
                else:
                    text_rect = (horizontal + offset_x, vertical + i * font_size + offset_y)
                screen.blit(text, text_rect)
        return i

##Button Functions

def button_function(): #Placeholder function for new buttons.
    pass

#Function to exit the game
def quit_game():
    Play_sound('Sounds/ui/clicked2.wav')
    pg.time.wait(980) #Wait for one second to allow sound file to play
    pg.quit()
    sys.exit()

class Game:
    def __init__(self, horizontal_size, vertical_size):
        self.run = True
        self.screen = pg.display.set_mode((horizontal_size, vertical_size),
                                          pg.RESIZABLE)  # Screen is not resizable because of pixel art!!!
        self.scale = (horizontal_size + vertical_size) * 0.1

        global screen_width;
        global screen_height;
        global half_width;
        global half_height
        # define very useful global variables which pertain to the size of the pygame screen.
        screen_width = int(pg.display.Info().current_w)
        screen_height = int(pg.display.Info().current_h)
        half_width = int(pg.display.Info().current_w / 2)
        half_height = int(pg.display.Info().current_h / 2)

        global circle_radius;
        circle_radius = (screen_width * screen_height) ** 0.38

    class Menu():
        def __init__(self, parent):
            self.bg = pg.transform.scale(pg.image.load('images/background.png'), (screen_width, screen_height))
            self.mx, self.my = pg.mouse.get_pos()
            self.clicked = False
            self.screen = parent.screen
            self.mouse_down = False
            self.dragging = False

        def screen_resize(self, eventw,
                          eventh):  # Re-calculates all the necessary parameters to change the screen size. Note: changing the screen also changes how some game mechanics work, as the project
            self.screen = pg.display.set_mode((eventw, eventh), pg.RESIZABLE)  # began without screen-resizing in mind.
            global screen_width;
            global screen_height;
            global half_width;
            global half_height
            screen_width = int(pg.display.Info().current_w)
            screen_height = int(pg.display.Info().current_h)
            half_width = int(pg.display.Info().current_w / 2)
            half_height = int(pg.display.Info().current_h / 2)
            global circle_radius;
            circle_radius = (screen_width * screen_height) ** 0.38

            self.bg = pg.transform.scale(pg.image.load('images/background.png'), (screen_width, screen_height))

        def pygame_menu(self, scroll_limit=None,
                        condition=True):  # Define the set of instructions for pygame as a single function, to avoid having to copy/paste the function
            for event in pg.event.get():
                if event.type == QUIT:
                    pg.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.clicked = True
                        self.mouse_down = True
                    elif scroll_limit is not None and event.button == 4 and condition:
                        self.offset_y = min(0, self.offset_y + 20)
                    elif scroll_limit is not None and event.button == 5 and condition:
                        self.offset_y = max(scroll_limit, self.offset_y - 20)
                elif event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        self.mouse_down = False
                elif event.type == VIDEORESIZE:
                    self.screen_resize(event.w, event.h)

                if scroll_limit is not None:
                    self.draw_scrollbar(scroll_limit, self.mouse_down)

                pg.display.update()

        def draw_scrollbar(self, scroll_limit, mouse_down):
            if scroll_limit < 0:
                height_offset = abs(self.offset_y / scroll_limit) * (screen_height - 200 - 32)
                mx, my = pg.mouse.get_pos()
                x_position = screen_width - 50
                y_position = 100
                self.Scroll_Bar(self, x_position, y_position, self.screen, (mx, my), scroll_limit, mouse_down)

                self.Scroll_Button(self, x_position, y_position - 16, self.screen, (mx, my), scroll_limit, 1,
                                   self.clicked)
                self.Scroll_Button(self, x_position, screen_height - y_position, self.screen, (mx, my), scroll_limit,
                                   -1, self.clicked)

        class Scroll_Button(Button):
            def __init__(self, parent, x, y, screen, mpos, scroll_limit, direction, clicked):
                self.parent = parent
                self.x = x
                self.y = y
                self.screen = screen
                self.clicked = clicked
                self.scroll_limit = scroll_limit
                self.mpos = mpos
                self.area = pg.Rect(self.x, self.y, 32, 32)  # Scroll buttons are fixed in size at 32 x 32 pixels.
                self.direction = direction  # Determines if the button scrolls up or down.
                assert self.direction == 1 or self.direction == -1  # Throw an error if the direction is not +1 or -1.
                if self.direction == 1:
                    self.texture = textures.scroll_arrow_up
                else:
                    self.texture = textures.scroll_arrow_down
                self.draw()

            def draw(self):
                self.screen.blit(self.texture, (self.x, self.y))
                if self.area.collidepoint(self.mpos) and self.clicked:
                    self.parent.offset_y += self.direction * 100
                    if self.direction == 1 and self.parent.offset_y > 0:
                        self.parent.offset_y = 0
                    elif self.direction == -1 and self.parent.offset_y < self.scroll_limit:
                        self.parent.offset_y = self.scroll_limit

        class Scroll_Bar(Button):
            def __init__(self, parent, x_pos, y_pos, screen, mpos, scroll_limit, button_down):
                self.parent = parent
                self.x_pos = x_pos
                self.y_pos = y_pos
                self.screen = screen
                self.mpos = mpos
                self.button_down = button_down
                self.area = pg.Rect(self.x_pos, 100, 32,
                                    screen_height - 200)  # Area for where the scroll bar can be clicked is the entire column.
                self.area2 = pg.Rect(0, 100, screen_width,
                                     screen_height - 200)  # Area for where the scroll bar can be dragged
                self.texture = textures.scroll_bar
                self.draw(parent.offset_y, scroll_limit)

            def draw(self, offset_y, scroll_limit):
                height_offset = abs(self.parent.offset_y / scroll_limit) * (screen_height - 200 - 32)
                self.screen.blit(self.texture, (self.x_pos, 100 + height_offset))
                if self.area.collidepoint(self.mpos) and self.button_down:
                    self.parent.dragging = True
                elif not self.area2.collidepoint(self.mpos) or not self.button_down:
                    self.parent.dragging = False

                if self.parent.dragging:
                    self.parent.offset_y = ((self.mpos[1] - 100) / (screen_height - 200)) * scroll_limit

                pg.draw.rect(self.screen, (100, 100, 100), (self.x_pos, self.y_pos, 32, screen_height - 200), 4)

        def main_menu(self, parent):
            self.clicked = False  # assert that clicked is False so that a new button in the same location doesnt get clicked automatically
            while True:
                self.button_start = Button(half_width - parent.scale, screen_height / 5, parent.scale * 2,
                                           parent.scale * 0.5, parent.screen,
                                           function=lambda: self.select_difficulty(parent))
                self.button_how_to_play = Button(half_width - parent.scale, 2 * screen_height / 5, parent.scale * 2,
                                                 parent.scale * 0.5, parent.screen,
                                                 function=lambda: self.how_to_play(parent))
                self.button_index = Button(half_width - parent.scale, 3 * screen_height / 5, parent.scale * 2,
                                           parent.scale * 0.5, parent.screen,
                                           function=lambda: self.access_index(parent))
                self.button_quit = Button(half_width - parent.scale, 4 * screen_height / 5, parent.scale * 2,
                                          parent.scale * 0.5, parent.screen, quit_game)

                self.screen.blit(self.bg, (0, 0))
                mx, my = pg.mouse.get_pos()
                # Draw buttons inside the loop, so that they can be redrawn if the mouse is hovering over them
                self.button_start.draw('triangles', (mx, my), self.clicked, text="New Game")
                self.button_how_to_play.draw('triangles', (mx, my), self.clicked, text="How To Play")
                self.button_index.draw('triangles', (mx, my), self.clicked, text="Access the Index")
                self.button_quit.draw('triangles', (mx, my), self.clicked, text="Quit Game")

                self.clicked = False
                self.pygame_menu()

        def how_to_play(self, parent):
            self.offset_x = 0
            self.offset_y = 0

            img_items_tutorial = pg.image.load('images/tutorial/tutorial-items.png')
            img_aiming_tutorial = pg.image.load('images/tutorial/tutorial-aiming.png')
            img_enemy = textures.Enemy_Magna_Shot_left
            running = True
            while running:
                self.button_back = Button(half_width - 0.5 * parent.scale, 20, parent.scale, parent.scale * 0.25,
                                          parent.screen, function=lambda: self.main_menu(parent))
                self.draw_tile_background(self.screen)
                mx, my = pg.mouse.get_pos()
                text_size = min(int(screen_height / 35), int(screen_width / 55))
                num_lines = write_text_from_file('Sans', 'text/how to play.txt', text_size,
                                                 (230, 240, 230), half_width / 3, screen_height / 8, self.screen,
                                                 offset_y=self.offset_y, center=False)

                self.screen.blit(img_items_tutorial,
                                 (half_width / 8 - 24, screen_height / 8 + int(text_size * 7.5) + self.offset_y))
                self.screen.blit(img_aiming_tutorial,
                                 (half_width / 8 - 24, screen_height / 8 + int(text_size * 14) + self.offset_y))
                self.screen.blit(pg.transform.scale(textures.biopack_texture, (96, 96)), (half_width / 8 - 24,
                                                                                          screen_height / 8 + int(
                                                                                              text_size * 21.5) + self.offset_y))  # Text size is static so images have to be defined statically to align with text.
                self.screen.blit(pg.transform.scale(water_texture, (48, 48)),
                                 (half_width / 8 - 24, screen_height / 8 + int(text_size * 29) + self.offset_y))
                self.screen.blit(pg.transform.scale(lava_texture, (48, 48)),
                                 (half_width / 8 + 24, screen_height / 8 + int(text_size * 29) + self.offset_y))
                self.screen.blit(pg.transform.scale(noise_texture, (72, 72)),
                                 (half_width / 8 - 24, screen_height / 8 + int(text_size * 34) + self.offset_y))
                self.screen.blit(pg.transform.scale(img_enemy, (72, 72)),
                                 (half_width / 8 - 24, screen_height / 8 + int(text_size * 37) + self.offset_y))

                self.button_back.draw('triangles', (mx, my), self.clicked, font_size=40, text="Main Menu")

                self.clicked = False
                padding = text_size
                self.pygame_menu(scroll_limit=min(0, -num_lines * text_size + half_height - padding))

        def access_index(self, parent):
            self.offset_y = 0
            index_list = []  # Generate index list based off files in the relevant folder.
            for subdir, dirs, files in os.walk('text/Index'):
                for file in files:
                    file = file[:-4]  # Delete .txt in file name
                    index_list.append(file)

            self.text_file_path = None

            running = True
            self.dropdown_menu = False
            while running:
                self.button_back = Button(half_width - 0.5 * parent.scale, 20, parent.scale, parent.scale * 0.25,
                                          parent.screen, function=lambda: self.main_menu(parent))
                self.draw_tile_background(self.screen)
                text_size = min(int(screen_height / 35), int(screen_width / 55))
                
                if self.text_file_path is not None:
                    num_lines = write_text_from_file('Times New Roman', self.text_file_path, text_size, (208, 182, 212),
                                                     screen_width / 2, screen_height / 3, self.screen,
                                                     offset_y=self.offset_y, limit_y=screen_height / 3.4)
                else:
                    num_lines = 0

                mx, my = pg.mouse.get_pos()
                self.button_back.draw('triangles', (mx, my), self.clicked, font_size=40, text="Main Menu")
                write_text('Sans', 'Enter your query:', 40, (180, 180, 200), screen_width / 2, screen_height / 8,
                           self.screen)

                button_width = 600;
                button_height = 60
                index_button = Index_Button(half_width - button_width / 2, half_height / 3, button_width, button_height,
                                            self.screen, function=self.toggle_drop_menu)

                if self.dropdown_menu:  # <--- Enables toggling dropdown menus.
                    for num, index in enumerate(index_list):
                        entry_height = int(screen_height / 32)
                        setattr(self, "index_dropdown_" + str(num), Button(half_width - button_width / 2,
                                                                           half_height / 3 + entry_height * (
                                                                               num) + button_height, button_width,
                                                                           entry_height, self.screen,
                                                                           function=lambda: self.index_text_function(
                                                                               index)))
                        getattr(self, "index_dropdown_" + str(num)).draw('rectangles', (mx, my), self.clicked,
                                                                         text=index, font_size=entry_height - 3,
                                                                         rgb=(0, 0, 0), text_rgb=(220, 180, 200))

                index_button.draw('images/ui/Index_Button.png', (mx, my),
                                  self.clicked)  # <--- draw index button last so it overlaps.
                self.clicked = False
                padding = text_size
                self.pygame_menu(scroll_limit=min(0, -num_lines * text_size + (screen_height * 2 / 3) - padding),
                                 condition=not self.dropdown_menu)

        def toggle_drop_menu(self):
            if not self.dropdown_menu:
                self.dropdown_menu = True
            else:
                self.dropdown_menu = False
                self.offset_y = 0

        def index_text_function(self, index):
            self.toggle_drop_menu()
            self.text_file_path = "text/Index/" + index + ".txt"

        @staticmethod  # <--- Trying out static methods, this doesn't necessarily need to be a static method.
        def draw_tile_background(screen):
            for i in range(0, screen_width // 32 + 1):
                for j in range(0, screen_height // 32 + 1):
                    screen.blit(cave_texture, (i * 32, j * 32))

        def select_difficulty(self, parent):
            self.game_instance = parent.Main_Game(self.screen, self,
                                                  player=lambda: Player())  # Initialize game instance before difficulty is selected
            self.selecting = True

            self.screen.blit(self.bg, (0, 0))

            self.clicked = False
            while self.selecting:
                write_text('Sans', 'Choose Difficulty', 80, (167, 176, 220), screen_width / 2, screen_height / 4,
                           self.screen)
                self.button_easy = Button(screen_width / 2 - parent.scale * 1.25, 2 * screen_height / 5,
                                          parent.scale * 2.5, parent.scale * 0.5, parent.screen,
                                          function=lambda: self.game_instance.generate(1))
                self.button_medium = Button(screen_width / 2 - parent.scale * 1.25, 3 * screen_height / 5,
                                            parent.scale * 2.5, parent.scale * 0.5, parent.screen,
                                            function=lambda: self.game_instance.generate(2))
                self.button_hard = Button(screen_width / 2 - parent.scale * 1.25, 4 * screen_height / 5,
                                          parent.scale * 2.5, parent.scale * 0.5, parent.screen,
                                          function=lambda: self.game_instance.generate(3))
                self.button_back = Button(0, 5 * screen_height / 6, parent.scale,
                                          parent.scale * 0.25, parent.screen, function=lambda: self.main_menu(parent))
                self.screen.blit(self.bg, (0, 0))
                mx, my = pg.mouse.get_pos()

                self.button_easy.draw('triangles', (mx, my), self.clicked, font_size=30,
                                      text="As easy as any other conquest.",
                                      text_rgb=(0, 255, 0))  # "Not even a battle"
                self.button_medium.draw('triangles', (mx, my), self.clicked, font_size=20,
                                        text="This battle could go either way...",
                                        text_rgb=(255, 220, 77))
                self.button_hard.draw('triangles', (mx, my), self.clicked, font_size=30,
                                      text="We have never faced such challenges before.", text_rgb=(226, 76, 72))
                self.button_back.draw('triangles', (mx, my), self.clicked, font_size=35, text="Main Menu")

                self.clicked = False
                self.pygame_menu()

    class Main_Game():
        def __init__(self, screen, parent, player=None):
            self.parent = parent
            self.map = Map(50, 50, 1)
            self.iter_freq = 15  # Determines when and how often some calculations will be run.
            self.characters = []  # A list of all characters (player and NPCs)
            self.projectiles = []  # A list containing all projectiles fired from weapons
            self.static_objects = []  # List containing all static objects (weapons, health, ammo) on the map
            self.screen = screen
            self.clock = pg.time.Clock()
            self.show_circle = False

            # Values pertaining to the screen's width and height will be accessed often, so it is better to record them once
            # instead of having to calculate them each time. Though this adds more lines of code, the run-time execution will be faster.

            self.border_left = -half_width  # determine where the borders of the map are
            self.border_up = -half_height
            self.border_right = (self.map.xsize - 1) * self.map.tile_size + self.border_left + 10
            self.border_down = (self.map.ysize - 1) * self.map.tile_size + self.border_up
            # pick a random starting position for the player
            self.map.generate()

            self.player = Player(self)
            self.player.xy = self.get_random_start()
            self.iter_num = 0
            self.noise_num = 0

            self.text_num = 0  # Text num regulates how long a text will be displayed on the screen.
            self.display_noise = 0
            self.text = ""
            self.vector = [0, 1]  # initialize to avoid potential crashes.

            self.enemies_live = True
            self.clicked = False

        def generate(self,
                     difficulty):  # This function will set the difficulty and call the draw function, which will draw the tiles.
            self.difficulty = difficulty
            self.playing = True
            self.num_enemies = int(random.randint(5, 8) * (math.sqrt(self.difficulty)))
            for i in range(self.num_enemies):
                enemy = Enemy(self)
                enemy.xy = self.get_random_start(True)

            self.create_objects()

            self.team_sees_player = [None, 0]
            while self.playing:
                if self.player.alive and self.enemies_live:
                    pg.display.update()
                    self.get_fire_vector()
                    for event in pg.event.get():
                        if event.type == QUIT:
                            pg.quit()
                            sys.exit()
                        elif event.type == KEYDOWN:
                            if event.key == K_w:
                                self.player.xy_vel[1] -= 1
                            elif event.key == K_d:
                                self.player.xy_vel[0] += 1
                            elif event.key == K_s:
                                self.player.xy_vel[1] += 1
                            elif event.key == K_a:
                                self.player.xy_vel[0] -= 1
                            elif event.key == K_SPACE:
                                if self.player.active_weapon.__class__.__name__ == "Sonic_Disintegrator":
                                    self.player.toggle_blaster()
                            elif event.key == K_r:
                                self.player.active_weapon.reload()
                            elif event.key == K_t:
                                if self.show_circle:  # Toggle showing the circle which denotes where the player can click.
                                    self.show_circle = False
                                elif not self.show_circle:
                                    self.show_circle = True
                            elif event.key == K_1:
                                self.player.equip_weapon("Sonic_Disintegrator")
                            elif event.key == K_2:
                                self.player.equip_weapon("Bolt_Driver")
                            elif event.key == K_3:
                                self.player.equip_weapon("MAR")
                            elif event.key == K_4:
                                self.player.equip_weapon("Plasmacaster")
                            elif event.key == K_5:
                                self.player.equip_weapon("Laser_Array")
                            elif event.key == K_ESCAPE:
                                Play_sound(None, 1)  # stops all sounds
                                menu = self.pause_Menu()
                        elif event.type == MOUSEBUTTONDOWN:  # draw a vector between the player and the clicked position and fire in that direction.
                            if event.button == 1:
                                self.clicked = True
                                self.player.active_weapon.fire(self.vector)
                        elif event.type == KEYUP:
                            if event.key == K_w:
                                self.player.xy_vel[1] = 0
                            elif event.key == K_d:
                                self.player.xy_vel[0] = 0
                            elif event.key == K_s:
                                self.player.xy_vel[1] = 0
                            elif event.key == K_a:
                                self.player.xy_vel[0] = 0
                            elif event.key == K_SPACE:
                                Play_sound(None, 1)
                        elif event.type == MOUSEBUTTONUP:
                            if event.button == 1 and self.player.active_weapon.automatic_fire:
                                self.player.active_weapon.fire(self.vector)
                        elif event.type == VIDEORESIZE:
                            self.screen_resize(event.w, event.h)

                elif not self.player.alive:
                    while self.playing: self.game_over(False)
                elif not self.enemies_live:
                    while self.playing: self.game_over(True)
                for char in self.characters:
                    # A character's 'hit box' is determined by four points that will be updated and checked
                    char.set_corners()
                    char.set_tiles()
                    char.break_tile()
                    char.set_sprite()
                    char.update_speed()
                    char.update_direction()
                    char.dynamic_move()
                # draw method for player and map has to be between getting character vision and drawing projectiles.
                self.draw(player=self.player)
                self.player.get_vision()

                for item in self.static_objects:  # Update static objects
                    item.draw()
                    if item.is_active:
                        item.update()
                    if not item.is_active:  # Can't make a simple else statement because object won't disappear instantly then.
                        self.static_objects.remove(item)
                self.enemies_live = False
                for char in self.characters:
                    char.active_weapon.reduce_cd()
                    char.draw(self.screen)
                    if char.__class__.__name__ == "Enemy" and char.alive:
                        self.enemies_live = True
                        char.update_pathfinding()
                        if not char.sees_player and not char.saw_player: char.passive_move()
                        if (self.iter_num) % self.iter_freq == 0:  # Only run once every 15 iterations.
                            char.check_player_seen(self.player)
                            if char.sees_player:
                                char.hostile_mode()
                            elif char.saw_player:
                                char.searching_mode()
                            elif char.team_sees_player[0]:
                                char.act_as_team(self.team_sees_player[0])

                            if char.team_sees_player[1] > self.team_sees_player[1]:  # update the team_sees_player variables for all enemies depending on the time at which the player was seen.
                                self.team_sees_player = char.team_sees_player
                            char.team_sees_player = self.team_sees_player

                if self.playing:
                    self.get_noise()
                    for projectile in self.projectiles:
                        if projectile.is_active:
                            projectile.update(self.characters, self.screen, self.player.xy, self.map)
                        else:  # remove the projectile if it isn't active anymore
                            self.projectiles.remove(projectile)
                self.update_text()
                if self.show_circle: pg.draw.circle(self.screen, (255, 0, 0), (half_width + 16, half_height + 16),
                                                    int(circle_radius),
                                                    1)  # draw a red circle to indicate where the player can click to fire weapon.
                self.clock.tick(game_speed)  # Limit the game to 30 ticks per second.
                self.iter_num += 1
                if self.iter_num > 4500:
                    self.iter_num = 1
                    if self.difficulty == 3:  # On the hardest difficulty, add a new enemy once every 150 seconds.
                        enemy = Enemy(self)
                        enemy.xy = self.get_random_start(True)

        def draw(self, player):
            padding = 2
            self.screen.fill((0, 0, 0))
            # Only draw tiles that are on the screen to avoid unnecessary lag.
            # max(a, b) statement is required to avoid drawing tiles in incorrect locations when near the border of the map.
            (x, y) = map(lambda xy: int(xy // self.map.tile_size), center_image(player.xy))
            x1 = x - half_width // self.map.tile_size;
            y1 = y - half_height // self.map.tile_size
            for i in range(max(0, x1 - padding),
                           min(x1 + screen_width // self.map.tile_size + padding, self.map.xsize)):
                for j in range(max(0, y1 - padding),
                               min(y1 + screen_height // self.map.tile_size + padding, self.map.ysize)):
                    if self.player.in_los[i][j] == 1 or distance(self.map.tiles[i][j].xy,
                                                                 self.player.xy) < self.player.vision_range:
                        self.map.tiles[i][j].draw(self.screen, i, j, self.map,
                                                  [self.player.xy[0] - half_width, self.player.xy[1] - half_height])

        def screen_resize(self, eventw, eventh):
            self.parent.screen_resize(eventw, eventh)
            global num_tiles_in_width;
            global num_tiles_in_height
            num_tiles_in_width = screen_width // self.map.tile_size
            num_tiles_in_height = screen_height // self.map.tile_size
            self.screen.fill((0, 0, 0))
            self.draw(player=self.player)
            for char in self.characters:
                char.draw(self.screen)

        def get_noise(self):  # Occasionally draws an indicator to signify where the enemy is.
            self.noise_num += random.random()
            if self.noise_num > 1500:
                self.noise_num = 0
                random_index = random.randint(1, len(self.characters) - 1)
                while not self.characters[random_index].alive:
                    random_index = random.randint(1, len(self.characters) - 1)
                position = self.characters[random_index].xy
                self.vector_to_enemy = norm([position[0] - self.player.xy[0], position[1] - self.player.xy[1]])
                self.display_noise = 90
                Play_sound_ambiance(random.choice(ambiances))

            if self.display_noise > 0:
                self.display_noise -= 1
                if self.display_noise % 30 > 15:  # Flashes the noise symbol to show the direction of the enemy.
                    posx = int((1 + 0.9 * self.vector_to_enemy[0]) * half_width)
                    posy = int((1 + 0.9 * self.vector_to_enemy[1]) * half_height)
                    rotated_noise_texture = pg.transform.rotate(noise_texture, degrees(
                        self.vector_to_enemy) + 180)  # Displays the noise coming from a specific direction.
                    self.screen.blit(rotated_noise_texture, (posx, posy))

        def create_objects(self):  # Creates static objects on the game map.
            num_MAR_ammo = random.randint(1, 5)
            for i in range(num_MAR_ammo):
                MARAmmo(self, textures.MAR_Ammo_texture)
            num_MAR = 1
            for i in range(num_MAR):
                MAR_Static(self, textures.MAR_texture)
            num_biogel_pack = random.randint(10, 20) * (4 - self.difficulty)
            for i in range(num_biogel_pack):
                Biopack(self, textures.biopack_texture)
            num_bolts_ammo = random.randint(5, 10)
            for i in range(num_bolts_ammo):
                Bolt_Ammo(self, textures.bolts_ammo_texture)
            num_plasmacaster = random.randint(1, 2)
            for i in range(num_plasmacaster):
                Plasmacaster_Static(self, textures.Plasmacaster_texture)
            num_plasmacaster_ammo = random.randint(1, 3)
            for i in range(num_plasmacaster_ammo):
                Plasmacaster_Ammo(self, textures.Plasmacaster_ammo_texture)
            num_laserarray = random.randint(1, 3)
            for i in range(num_laserarray):
                Laser_Array_Static(self, textures.Laser_Array_texture)

        def pause_Menu(self):
            self.paused = True
            self.clicked = False
            while self.paused:
                self.button_end = Button(half_width - 200, screen_height / 16, 400, 80, self.screen,
                                         function=self.stop_playing, active=True)
                mx, my = pg.mouse.get_pos()
                write_text('Sans', 'Paused', 60, (247, 212, 195), half_width, int(half_height / 2), self.screen)
                self.button_end.draw('triangles', (mx, my), self.clicked, font_size=60, text="Main Menu",
                                     text_rgb=(180, 180, 180))
                for event in pg.event.get():
                    if event.type == QUIT:
                        pg.quit()
                        sys.exit()
                    elif event.type == KEYDOWN:
                        if event.key == K_ESCAPE:
                            self.button_end.active = False
                            self.paused = False
                    elif event.type == MOUSEBUTTONDOWN:
                        if event.button == 1:
                            self.clicked = True
                    elif event.type == VIDEORESIZE:
                        self.screen_resize(event.w, event.h)
                pg.display.update()

        def update_text(self):
            if self.text_num >= 1:
                self.text_num -= 1
                write_text('Sans', self.text, 25, (220, 230, 255), half_width, int(7 * screen_height / 8),
                           self.screen)

                # Function starts characters at a randomized location, that isn't in lava.

        # Also sets the current tile to cave if it isn't a water tile.
        def get_random_start(self, enemy=False):
            x = random.randint(0, self.map.xsize - 1)
            xpos = x * self.map.tile_size
            y = random.randint(0, self.map.ysize - 1)
            ypos = y * self.map.tile_size
            # Avoid using recursive function, in the very unlikely scenario that maximum function call depth might be reached.
            if enemy:
                condition = self.map.tiles[x][y].Perlin_heat < self.map.lava_limit - 0.1 and distance([xpos, ypos],
                                                                                                      self.player.xy) > self.map.xsize * self.map.tile_size / 2
            else:
                condition = self.map.tiles[x][y].Perlin_heat < self.map.lava_limit - 0.1
            while not condition:
                x = random.randint(0, self.map.xsize - 1)
                xpos = x * self.map.tile_size
                y = random.randint(0, self.map.ysize - 1)
                ypos = y * self.map.tile_size
                if enemy:
                    condition = self.map.tiles[x][y].Perlin_heat < self.map.lava_limit - 0.1 and distance([xpos, ypos],
                                                                                                          self.player.xy) > self.map.xsize * self.map.tile_size / 2
                else:
                    condition = self.map.tiles[x][y].Perlin_heat < self.map.lava_limit - 0.1
            pos = [xpos, ypos]
            if self.map.tiles[x][y].type != 'water':
                self.map.tiles[x][y].set_type('cave')
            return pos

        def get_enemy_start(self):  # Sets the position of the enemy (testing purposes)
            x = random.randint(0, self.map.xsize - 1)
            xpos = x * self.map.tile_size
            y = random.randint(0, self.map.ysize - 1)
            ypos = y * self.map.tile_size
            while self.map.tiles[x][y].Perlin_heat > self.map.lava_limit - 0.05 or distance([xpos, ypos],
                                                                                            self.player.xy) < 1000:
                x = random.randint(0, self.map.xsize - 1)
                xpos = x * self.map.tile_size
                y = random.randint(0, self.map.ysize - 1)
                ypos = y * self.map.tile_size
            pos = [xpos, ypos]
            if self.map.tiles[x][y].type != 'water':
                self.map.tiles[x][y].set_type('cave')
            return pos

        def get_fire_vector(self):
            self.mx, self.my = pg.mouse.get_pos()
            if distance([self.mx, self.my], center_image([half_width,
                                                          half_height])) <= circle_radius:  # only fire if the player clicks a point near the screen's center.
                self.vector = norm([(self.mx - half_width - 8), (self.my - half_height - 8)])

        def get_tile_type(self, x, y, tile_type):
            x = int(x);
            y = int(y)
            if self.map.tiles[x][y].type == tile_type:
                return True

        def game_over(self, win):
            self.button_end = Button(half_width - 200, screen_height / 16, 400, 80, self.screen,
                                     function=self.stop_playing, active=True)
            if win:
                write_text('Sans', 'The Force Marines are Victorious.', 80, (0, 0, 255), half_width,
                           int(half_height / 2), self.screen)
            else:
                write_text('Sans', 'The Traphon are Victorious.', 80, (255, 0, 0), half_width, int(half_height / 2),
                           self.screen)
            mx, my = pg.mouse.get_pos()
            self.button_end.draw('triangles', (mx, my), self.clicked, font_size=60, text="Main Menu",
                                 text_rgb=(180, 180, 180))
            self.clicked = False
            for event in pg.event.get():
                if event.type == QUIT:
                    pg.quit()
                    sys.exit()
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        Play_sound(None, 1)
                        pg.quit()
                        sys.exit()
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.clicked = True
                elif event.type == VIDEORESIZE:
                    self.screen_resize(event.w, event.h)
            self.player.xy_vel = [0, 0]
            pg.display.update()

        def stop_playing(self):  # sets playing to false and allows to return to the main menu
            Play_sound(None, 1)
            self.paused = False
            self.playing = False
            self.parent.selecting = False  # Make the game go to the main menu instead of 'selecting difficulty' screen.


class Map:
    def __init__(self, xsize, ysize, tile_size):
        self.xsize = xsize
        self.ysize = ysize
        self.tile_size = tile_size * 32  # tile size must be a multiple of 32 because the textures are 32x32 pixels.
        self.tiles = []

        self.po = [random.random() * 1000 for i in
                   range(6)]  # Introduce random perlin-value offsets to generate different maps each time

        self.lava_limit = 0.30  # Terrain is lava if corresponding perlin value is above this
        self.water_limit = -0.38  # Terrain is underground water if corresponding perlin value is below this
        self.bedrock_limit = 0.2  # Terrain is bedrock if corresponding perlin value is above this
        self.sediment_limit = -0.1  # Terrain is soft sediment if corresponding perlin value is below this
        self.empty_limit = -0.3  # Terrain is generated as empty (ie. natural cave) if corresponding perlin value is below this

        global num_tiles_in_width;
        global num_tiles_in_height
        num_tiles_in_width = screen_width // self.tile_size
        num_tiles_in_height = screen_height // self.tile_size

    def generate(self):
        for x in range(self.xsize):
            tile_list = []
            for y in range(self.ysize):
                tile = Tile(self, x, y)
                tile_list.append(
                    tile)  # Write all tiles into a matrix-style list, so that we know the coordinate of each tile.
            self.tiles.append(tile_list)

    def retrieve_tile_type(self, x, y):
        if is_between(x, [0, self.xsize - 1]) and is_between(y, [0, self.ysize - 1]):
            return self.tiles[x][y].type
        return None  # Return none if index is out of bounds.


class Tile:
    def __init__(self, Parent_class, x, y, po_1=0, po_2=0, po_3=0):
        self.xy = [x * Parent_class.tile_size, y * Parent_class.tile_size]
        self.Parent_class = Parent_class

        self.Perlin_heat = snoise2(float(x * 0.06 + Parent_class.po[0]), float(y * 0.06 + Parent_class.po[1]),
                                   octaves=10, persistence=0.1, lacunarity=2.2, repeatx=4000, repeaty=4000)
        self.Perlin_rock = snoise2(float(x * 0.1 + Parent_class.po[2]), float(y * 0.1 + Parent_class.po[3]), octaves=12,
                                   persistence=0.2, lacunarity=1.8, repeatx=4000, repeaty=4000)
        self.Perlin_empty = snoise2(float(x * 0.1 + Parent_class.po[4]), float(y * 0.1 + Parent_class.po[5]),
                                    octaves=14, persistence=0.3, lacunarity=1.8, repeatx=4000, repeaty=4000)
        self.durability = None

        if self.Perlin_heat > Parent_class.lava_limit:
            self.type = 'lava'; self.durability = None  # There are different priorities when generating
        elif self.Perlin_heat < Parent_class.water_limit:
            self.type = 'water'; self.durability = None  # terrain; a tile cannot be lava and bedrock
        elif self.Perlin_empty < Parent_class.empty_limit:
            self.type = 'cave'; self.durability = None  # at the same time.
        elif self.Perlin_rock >= Parent_class.bedrock_limit:
            self.type = 'bedrock'; self.durability = 150
        elif self.Perlin_rock < Parent_class.sediment_limit:
            self.type = 'sediment'; self.durability = 30
        else:
            self.type = 'rock'; self.durability = 60

        self.texture = eval(self.type + '_texture')
        self.texture = pg.transform.scale(self.texture, (Parent_class.tile_size, Parent_class.tile_size))

    def draw(self, screen, x, y, game_map, offset=[0, 0]):
        screen.blit(self.texture, (x * game_map.tile_size - offset[0], y * game_map.tile_size - offset[1]))

    def set_type(self, new_type):  # Sets the tile to the desired tile and changes the texture correspondingly.
        self.type = new_type
        self.texture = eval(self.type + '_texture')
        self.texture = pg.transform.scale(self.texture, (self.Parent_class.tile_size, self.Parent_class.tile_size))

    def chip(self, amount=1):
        if self.type in illegal_tiles:  # can only chip tiles that aren't passable.
            self.durability -= amount
            if self.durability <= 0:
                self.set_type('cave')
                self.durability = 0


class Player:
    def __init__(self, parent):
        self.parent = parent
        self.health_cap = 100
        self.health = self.health_cap
        self.armor_cap = 100
        self.armor = self.armor_cap
        self.corners = []
        self.vision_range = 3 * self.parent.map.tile_size
        self.xy = [0, 0]
        self.xy_rem = [0, 0]
        self.xy_vel = [0, 0]  # Create an offset velocity to allow things to move continuously while a key is held down.
        self.alive = True
        self.direction = random.choice(directions)
        self.weapons = [Sonic_Disintegrator(20, None, None, self), Bolt_Driver(15, 24, 12, self)]
        self.active_weapon = self.weapons[0]
        self.tiles = []  # determines what tiles a player currently occupies (should be in up to four tiles at any time)
        self.speed = 3
        parent.characters.append(self)
        self.weapon_fired = 0
        self.breaking = False  # determines if player's sonic disintegrator is breaking a tile
        self.in_los = [[0 for j in range(0, self.parent.map.ysize)] for i in range(0,
                                                                                   self.parent.map.xsize)]  # List containing all tile-coordinates of the tiles the player can currently see.

        self.iter_offset = random.randint(1,
                                          self.parent.iter_freq - 1)  # Occasional computations will be run for different characters at different times to reduce lag.

    def equip_weapon(self, weapon_name):
        for weapon in self.weapons:
            if str(weapon.__class__.__name__) == weapon_name:
                self.active_weapon = weapon

    def update_speed(self):
        self.speed = 3
        for tile in self.tiles:
            if tile == 'water':  # reduce the character's speed if they are partly or fully submerged in water.
                self.speed -= 0.25
            if tile == 'lava':
                self.speed -= 0.5
                self.take_damage(0.01)

    def draw_ui(self, screen):
        screen.blit(textures.UI_Screen_1, (0, screen_height - 64))
        screen.blit(textures.UI_Screen_2, (screen_width - 256, screen_height - 64))
        write_text('Sans', str(max(0, math.ceil(self.health))), 30, (177, 177, 177), 180,
                   screen_height - 49, screen)
        write_text('Sans', str(max(0, math.ceil(self.armor))), 30, (177, 177, 177), 180,
                   screen_height - 14, screen)

        weapon_name = (str(self.active_weapon.__class__.__name__)).replace('_', ' ')
        write_text('Sans', weapon_name, 18, (177, 177, 177), screen_width - 140, screen_height - 55,
                   screen)
        if self.active_weapon.ammo is not None:
            write_text('Sans', str(int(self.active_weapon.ammo)), 30, (177, 177, 177),
                       screen_width - 80, screen_height - 30, screen)
            if not self.active_weapon.reloading or self.active_weapon.ammo == 0:
                write_text('Sans', str(int(self.active_weapon.in_clip)), 18, (177, 177, 177),
                           screen_width - 80, screen_height - 8, screen)
            else:
                write_text('Sans', "Reloading", 18, (177, 177, 177), screen_width - 60,
                           screen_height - 12, screen)
        else:
            write_text('Sans', str('INF'), 30, (177, 177, 177), screen_width - 80,
                       screen_height - 30, screen)
            write_text('Sans', str('INF'), 18, (177, 177, 177), screen_width - 80,
                       screen_height - 12, screen)

    def project(self, direction, amount, offset=[0,
                                                 0]):  # Gets the new coordinates of a character without moving them, to check if the desired position is valid.
        new_corners = []
        x = direction[0] * 2.5
        y = direction[1] * 2.5
        for corner in self.corners:
            new_corners.append([corner[0] + round(x * amount) + offset[0], corner[1] + round(y * amount) + offset[1]])
        return new_corners

    def valid(self, direction, amount):
        if not in_bounds([self.xy[0] + direction[0] * amount, self.xy[1] + direction[1] * amount], self.parent.map):
            return False
        tiles = get_tiles(self.project(direction, amount), self.parent.map)
        for it in illegal_tiles:
            if it in tiles:
                return False
        return True

    def take_damage(self, amount):  # Function allows a unit to take damage and die from damage.
        if self.alive and amount > 0:
            health_dmg, armor_dmg = dmgsplit(amount)
            self.health -= health_dmg
            self.armor -= armor_dmg
            if self.health <= 0:
                self.alive = False
                if self.__class__.__name__ == "Enemy" and distance(self.xy, self.parent.player.xy) < 1000:
                    Play_sound("Sounds/characters/enemydeath.wav")

    def set_sprite(
            self):  # This function will be called whenever the texture is changed (ie. character moves differently or weapon is changed)
        x, y = self.get_tile_coords()
        self.px, self.py = -self.parent.player.xy[0] + half_width + self.xy[0], -self.parent.player.xy[
            1] + half_height + self.xy[1]
        numx = self.parent.player.xy[0] // self.parent.map.tile_size;
        numy = self.parent.player.xy[
                   1] // self.parent.map.tile_size  # <--offsets pertaining to the player's vision map.
        if self.parent.player.in_los[x][y] == 1 or distance(self.xy,
                                                            self.parent.player.xy) <= self.parent.player.vision_range:  # only render the character if the player can see the tile or enemy is very close.
            if self.alive:
                self.sprite = eval('textures.' + str(self.__class__.__name__) + '_' + str(
                    self.active_weapon.__class__.__name__) + '_' + word(self.direction))
                self.draw(self.parent.screen)
            else:
                self.sprite = pg.image.load(
                    'images/' + str(self.__class__.__name__) + '/' + str(self.__class__.__name__) + '_death.png')
        else:
            self.sprite = None

    def update_direction(self):  # define rules for updating the player's direction and sprite
        if self.xy_vel[0] > 0 and self.xy_vel[0] >= abs(self.xy_vel[1]):
            self.direction = (1, 0)
        elif self.xy_vel[0] < 0 and self.xy_vel[0] <= abs(self.xy_vel[1]):
            self.direction = (-1, 0)
        elif self.xy_vel[1] > 0 and self.xy_vel[1] > abs(self.xy_vel[0]):
            self.direction = (0, 1)
        elif self.xy_vel[1] < 0 and self.xy_vel[1] < abs(self.xy_vel[0]):
            self.direction = (0, -1)

        self.set_sprite()

    def draw(self, screen):
        screen.blit(self.sprite, (int(pg.display.Info().current_w / 2), int(pg.display.Info().current_h / 2)))
        self.draw_ui(screen)
        for weapon in self.weapons:
            weapon.refresh()

    def set_corners(self):
        self.corners = [(self.xy[0] + 6, self.xy[1] + 4), (self.xy[0] + 24, self.xy[1] + 4),
                        (self.xy[0] + 6, self.xy[1] + 29), (self.xy[0] + 24, self.xy[
                1] + 29)]  # 6, 4, 24, and 29 are offset values that define a character's hitbox.

    ### DYNAMIC MOVEMENT SYSTEM!!!
    def dynamic_move(self):
        if self.alive:
            self.xy_vel = norm(self.xy_vel)
            if self.valid(self.xy_vel, self.speed):
                self.xy, self.xy_rem = calculate_movement(self.xy, self.xy_vel, self.xy_rem, self.speed)

            else:
                temp_speed = self.speed
                while temp_speed > 0.8 and not self.valid(self.xy_vel, temp_speed):
                    temp_speed /= 2
                    if self.valid(self.xy_vel, temp_speed):
                        self.xy, self.xy_rem = calculate_movement(self.xy, self.xy_vel, self.xy_rem, temp_speed)
                if not temp_speed <= 0.8:
                    self.xy, self.xy_rem = calculate_movement(self.xy, self.xy_vel, self.xy_rem, temp_speed)
                else:
                    temp_speed = self.speed
                    while temp_speed > 0.8 and not self.valid([self.xy_vel[0], 0], temp_speed):
                        temp_speed /= 2
                    if not temp_speed <= 0.8:
                        self.xy, self.xy_rem = calculate_movement(self.xy, [self.xy_vel[0], 0], self.xy_rem, temp_speed)
                    temp_speed = self.speed
                    while temp_speed > 0.8 and not self.valid([0, self.xy_vel[1]], temp_speed):
                        temp_speed /= 2
                    if not temp_speed <= 0.8:
                        self.xy, self.xy_rem = calculate_movement(self.xy, [0, self.xy_vel[1]], self.xy_rem, temp_speed)

    def break_tile(self):  # function that starts slowly breaking a tile.
        if self.breaking is True and self.active_weapon.__class__.__name__ == "Sonic_Disintegrator":  # only run this code if sonic disintegrator is active, otherwise skip it all.
            center = center_image(self.xy)
            (x, y) = map(lambda xy: int(xy // self.parent.map.tile_size), center)
            if self.not_stuck():
                x += self.direction[0]
                y += self.direction[1]
                if is_between(x, (0, self.parent.map.xsize - 1)) and is_between(y, (0, self.parent.map.ysize - 1)):
                    self.parent.map.tiles[x][y].chip()
            else:
                for corner in self.corners:  # Debug: if the player spawns in a tile, break the tile which the player is located in.
                    x = corner[0] // self.parent.map.tile_size;
                    y = corner[1] // self.parent.map.tile_size
                    if self.parent.map.retrieve_tile_type(x, y) in illegal_tiles[0:-1]:
                        self.parent.map.tiles[x][y].chip()
            if self.__class__.__name__ == "Player": 
                self.sound_delay -= 1 #<-- variable used to regulate the rate at which sound plays.
                if self.sound_delay == 0:
                    self.sound_delay = 20
                    Play_sound('Sounds/weapons/Sonic Disintegrator Hum.wav')

    def not_stuck(self):
        for corner in self.corners:
            x = corner[0] // self.parent.map.tile_size;
            y = corner[1] // self.parent.map.tile_size
            if self.parent.map.retrieve_tile_type(x, y) in illegal_tiles[0:-1]:
                return False
        return True

    def set_tiles(self):
        self.tiles = get_tiles(self.corners, self.parent.map)

    def toggle_blaster(self):  # toggles the sonic disintegrator
        if self.breaking is False:
            self.breaking = True
            self.sound_delay = 1

        else:
            self.breaking = False
            Play_sound(None, 1)
            
    # determines and updates the tiles the player can see
    def get_vision(self):
        padding = 2
        (x, y) = map(lambda xy: int(xy // self.parent.map.tile_size), center_image(self.xy))
        x1 = x - half_width // self.parent.map.tile_size;
        y1 = y - half_height // self.parent.map.tile_size
        if int((self.parent.iter_num) % self.parent.iter_freq) == 0:
            self.get_los(x1, y1)

    def get_los(self, x1,
                y1):  # <--algorithm to check which tiles are within a character's direct line of sight. Computationally expensive.
        self.in_los = [[0 for j in range(0, self.parent.map.ysize)] for i in range(0, self.parent.map.xsize)]
        for n in range(4 * num_tiles_in_width):
            photon = Photon(self, angle(n * 3.14 / (2 * num_tiles_in_width)), self.parent.map.tile_size,
                            self.parent.map)
            while in_screen(photon, self) and photon.get_tile_type() in vision_tiles:
                photon.move()
                if in_bounds(photon.xy, self.parent.map):
                    xtile, ytile = photon.get_tile()
                    self.in_los[xtile][ytile] = 1
        # guarantees that photons will travel in directions perpendicular to the player's location.
        for n in range(4):
            photon = Photon(self, angle(n * math.pi / 2), self.parent.map.tile_size, self.parent.map)
            while in_screen(photon, self) and photon.get_tile_type() in vision_tiles:
                photon.move()
                if in_bounds(photon.xy, self.parent.map):
                    xtile, ytile = photon.get_tile()
                    self.in_los[xtile][ytile] = 1

    def get_tile_coords(self):
        return (self.xy[0] + 16) // self.parent.map.tile_size, (self.xy[1] + 16) // self.parent.map.tile_size

    def get_tile_coords_tuple(self):

        return ((self.xy[0] + 16) // self.parent.map.tile_size, (self.xy[1] + 16) // self.parent.map.tile_size)


class Enemy(Player):
    def __init__(self, parent):
        self.parent = parent
        self.health_cap = random.randint(1, 100) * parent.difficulty ** 0.5
        self.health = self.health_cap
        self.armor_cap = 0
        self.armor = self.armor_cap
        self.corners = []
        self.vision_range = 0
        self.xy = [0, 0]
        self.xy_rem = [0, 0]
        self.xy_vel = [0, 0]  # Create an offset velocity to allow things to move continuously while a key is held down.
        self.healthbar_width = 20
        self.weapon_fired = 0
        self.alive = True
        self.direction = random.choice(directions)
        self.weapons = [Sonic_Disintegrator(12, None, None, self), Magna_Shot(5, 20, 5, self)]
        self.active_weapon = self.weapons[0]
        self.tiles = []  # determines what tiles a player currently occupies (should be in up to four tiles at any time)
        self.speed = 2.8
        parent.characters.append(self)
        self.breaking = False  # determines if player's sonic disintegrator is breaking a tile
        self.in_los = [[0 for j in range(0, self.parent.map.ysize)] for i in range(0,
                                                                                   self.parent.map.xsize)]  # List containing all tile-coordinates of the tiles the player can currently see.
        self.saw_player = None  # Whether enemy saw player previously and wants to investigate that location.
        self.sees_player = False  # Whether individual sees the player
        self.team_sees_player = [None,
                                 0]  # Whether any Storm Warrior sees the player, and can relay those coordinates to their teammates.
        self.move_orders = []
        self.move_persistence = 0
        self.correction_duration = 0
        self.clearing_corner = False

        self.iter_offset = random.randint(1, self.parent.iter_freq - 1)

    def draw(self, screen):
        if self.sprite is not None:
            screen.blit(self.sprite, (self.px, self.py))
            if self.alive:
                self.draw_healthbar(self.px, self.py - 10)
                self.parent.noise_num = 0  # Don't show where enemies are if any enemy is already in line of sight.

    def draw_healthbar(self, xpos, ypos):  # Draw a healthbar to show AI's relative health.
        green_width = int(self.health / self.health_cap * self.healthbar_width)
        red_width = self.healthbar_width - green_width
        pg.draw.rect(self.parent.screen, (0, 200, 0), (xpos, ypos, green_width, 5))
        if self.health < self.health_cap: pg.draw.rect(self.parent.screen, (200, 0, 0),
                                                       (xpos + green_width, ypos, red_width, 5))

    def passive_move(self):  # movement algorithm when AI doesn't see the player.
        if self.move_persistence == 0:
            self.move_persistence = random.randint(5, 15) * 11
            roll_num = random.random()
            if roll_num > 0.4:
                self.prev_xy_vel = self.xy_vel
                self.xy_vel = list(random.choice(directions))
                while self.xy_vel == opposite(
                        self.prev_xy_vel):  # Generate a direction that isn't the opposite of the last direction.
                    self.xy_vel = list(random.choice(directions))
            else:
                self.xy_vel = list(self.direction_to_player())
                if not self.avoid_lava(self.xy_vel, self.speed * 2.5): self.xy_vel = [0,
                                                                                      0]; self.move_persistence = 0  # avoid walking into lava or out of bounds arbitrarily.
        else:
            if not self.avoid_lava(self.xy_vel, self.speed * 2.5):
                self.move_persistence = 0

            elif not self.valid(self.xy_vel, self.speed):
                self.toggle_breaking()
                self.check_sides()
            else:
                self.move_persistence -= 1

    def direction_to_player(self):  # Gets the direction to the player while passively searching.
        x_axis = self.xy[0] - self.parent.player.xy[0]
        y_axis = self.xy[1] - self.parent.player.xy[1]

        if abs(x_axis) >= abs(y_axis):
            if x_axis >= 0:
                direction = (-1, 0)
            else:
                direction = (1, 0)
        else:
            if y_axis >= 0:
                direction = (0, -1)
            else:
                direction = (0, 1)
        return direction

    def avoid_lava(self, direction, amount):  # Function used to prevent AI from moving into lava or out of bounds
        if not in_bounds([self.xy[0] + direction[0] * amount, self.xy[1] + direction[1] * amount], self.parent.map):
            return False
        tiles = get_tiles(self.project(direction, amount), self.parent.map)
        for tile in tiles:
            if tile in bad_tiles:
                return False
        return True

    def check_sides(self):  # Algorithm prevents AI from getting stuck between two blocks while digging.
        if not self.clearing_corner:
            straight_line = round_vector(self.xy_vel)
            for count in [5, 4, 3, 2]:  # <-- different magnitudes
                vector = perpendicular_direction(straight_line)  # <-- Guarantees the creation of a perpendicular vector
                if self.valid_check_sides(self.xy_vel, self.speed,
                                          [abs(vector[0]) * self.speed * count, vector[1] * self.speed * count]):
                    self.prev_xy_vel = self.xy_vel
                    self.xy_vel = vector;
                    self.correction_duration = count
                    self.clearing_corner = True
                    break  # break iteration to conserve computational resources.
                elif self.valid_check_sides(self.xy_vel, self.speed,
                                            [-abs(vector[0]) * self.speed * count, -vector[1] * self.speed * count]):
                    self.prev_xy_vel = self.xy_vel
                    self.xy_vel = [-vector[0], -vector[1]];
                    self.correction_duration = count
                    self.clearing_corner = True
                    break

    def update_pathfinding(self):
        if self.correction_duration > 0:
            self.correction_duration -= 1
        elif self.clearing_corner:
            self.xy_vel = self.prev_xy_vel; self.clearing_corner = False

    def valid_check_sides(self, direction, amount,
                          offset_vector):  # Function used to check if AI can move to the side of a block.
        tiles = get_tiles(self.project(direction, amount, offset_vector), self.parent.map)
        for it in illegal_tiles:
            if it in tiles:
                return False
        return True

    def check_player_seen(self, player):
        if self.get_tile_coords_tuple() == player.get_tile_coords_tuple() or self.get_los(player):
            self.sees_player = True
            self.saw_player = player.xy
            self.team_sees_player = [player.get_tile_coords_tuple(), time.time()]

    def hostile_mode(self):  # Activates when the player is within the enemy's line of sight.
        vector_to_player = norm([self.parent.player.xy[0] - self.xy[0], self.parent.player.xy[1] - self.xy[1]])
        distance_to_player = distance(self.parent.player.xy, self.xy)
        if not self.clear_shot(vector_to_player, distance_to_player - 32, int(self.parent.map.tile_size / 2),
                               illegal_tiles):  # Start digging towards player if can't move directly to player
            self.toggle_breaking()
            self.check_sides()

        else:  # Otherwise start moving to player and firing.
            self.toggle_firing()

            vector_to_player = norm([self.parent.player.xy[0] - self.xy[0], self.parent.player.xy[1] - self.xy[1]])
            self.count_num = 0
            self.xy_vel = self.check_linear_path(vector_to_player, distance_to_player)

            if self.clear_shot(vector_to_player, distance_to_player, self.parent.map.tile_size * 2, liquids,
                               True) and in_screen(self,
                                                   self.parent.player):  # Don't fire if there is too much lava or water in the way, or if outside the player's screen.
                self.active_weapon.fire(randomize_direction(vector_to_player, 3))

    def searching_mode(self):  # Will go to where the player was last seen.
        self.xy_vel = norm([self.saw_player[0] - self.xy[0], self.saw_player[1] - self.xy[1]])
        if distance(self.xy, self.saw_player) < 20:
            self.saw_player = None  # Resume regular patrol if AI is on that point, and the player is nowhere to be found.
            xpos, ypos = self.parent.player.get_tile_coords()
            if self.team_sees_player[0] == [xpos, ypos]:  # Whole team knows that player isn't there anymore.
                self.team_sees_player = [None, time.time()]
        elif not self.valid(self.xy_vel, self.speed):
            self.toggle_breaking()
            self.check_sides()

    def check_linear_path(self, vector_to_player,
                          distance):  # Pathfinding algorithm to player. Generates a new random path if existing path collides with anything.
        num_points = int(
            distance * 1.5 // self.parent.map.tile_size)  # Check slightly more points than necessary, to avoid points potentially clipping through diagonal blocks.
        len_point = int(self.parent.map.tile_size / 1.5)
        correct_path = False
        while self.count_num < 3 and not correct_path:
            correct_path = True
            self.count_num += 1
            try:
                if distance(self.xy, self.parent.player.xy) >= 500:
                    new_vector = randomize_direction(vector_to_player, 10)
                else:
                    new_vector = randomize_direction(vector_to_player, 90)
            except:
                new_vector = randomize_direction(vector_to_player, 90)

            for i in range(num_points):
                point = [self.xy[0] + (new_vector[0] * len_point * (i + 1)),
                         self.xy[1] + (new_vector[1] * len_point * (i + 1))]
                x = int(point[0] // self.parent.map.tile_size);
                y = int(point[1] // self.parent.map.tile_size)
                if self.parent.map.retrieve_tile_type(x, y) in illegal_tiles:
                    correct_path = False
        self.count_num = 0
        if self.count_num >= 3:  # If computer can't generate a good path after three tries, it picks the direct path to the player (which is always valid)
            new_vector = vector_to_player
        return new_vector

    def act_as_team(self, position):  # Enemies converge on the player if any team-mate sees the player.
        if distance(self.xy,
                    self.parent.player.xy) < 1600 and position is not None:  # Only converge if enemy is within a certain distance from the player to start with.
            self.toggle_breaking()
            if self.xy[0] // self.parent.map.tile_size != position[0]:
                self.xy_vel = norm([position[0] - ((self.xy[0] + 16) // self.parent.map.tile_size), 0])
                self.check_sides()
            elif self.xy[1] // self.parent.map.tile_size != position[1]:
                self.xy_vel = norm([0, position[1] - ((self.xy[1] + 16) // self.parent.map.tile_size)])
                self.check_sides()
            elif (self.xy[1] + 16) // self.parent.map.tile_size == position[1] and (
                    self.xy[0] + 16) // self.parent.map.tile_size == position[0]:
                self.team_sees_player = [None, time.time()]
            if not self.valid(self.xy_vel, self.speed): self.check_sides()
            if not self.avoid_lava(self.xy_vel, self.speed * 15):
                self.xy_vel = perpendicular_direction(self.xy_vel)

    def clear_shot(self, vector, distance, sample_rate, avoid_tiles, look_for_friendlies=False):
        num_points = int(distance // sample_rate)
        if num_points > 0:
            for i in range(num_points):
                point = [self.xy[0] + vector[0] * sample_rate * i + 1, self.xy[1] + vector[1] * sample_rate * i + 1]
                x = int(point[0] // self.parent.map.tile_size);
                y = int(point[1] // self.parent.map.tile_size)
                if self.parent.map.retrieve_tile_type(x, y) in avoid_tiles:
                    return False
            if look_for_friendlies:  # Run this piece of code to avoid stupid-tier friendly fire.
                for i in range(min(num_points, 3)):
                    point = [self.xy[0] + vector[0] * sample_rate * i + 1, self.xy[1] + vector[1] * sample_rate * i + 1]
                    for char in self.parent.characters:
                        if char.__class__.__name__ == self.__class__.__name__ and char is not self:
                            friendly_to_bullet = ((char.xy[0] - point[0]) ** 2 + (char.xy[1] - point[
                                1]) ** 2) ** 0.5  # Python is stupid and won't allow these points to be called in any kind of function, returns nonsense errors.
                            enemy_to_bullet = ((self.parent.player.xy[0] - point[0]) ** 2 + (
                                        self.parent.player.xy[1] - point[1]) ** 2) ** 0.5
                            condition = friendly_to_bullet < 20 or friendly_to_bullet < enemy_to_bullet
                            if condition:
                                return False

        return True

    def get_los(self, player):  # <--AI version of this algorithm is much less resource-intensive
        vector_to_player = norm([self.parent.player.xy[0] - self.xy[0], self.parent.player.xy[1] - self.xy[1]])
        photon = Photon(self, vector_to_player, self.parent.map.tile_size, self.parent.map)
        while in_screen(photon, self) and photon.get_tile_type() in vision_tiles:
            photon.move()
            if photon.check_collision(player):
                return True

    def toggle_breaking(self):
        if self.active_weapon.__class__.__name__ is not "Sonic_Disintegrator": self.equip_weapon("Sonic_Disintegrator")
        if not self.breaking: 
            self.toggle_blaster()

    def toggle_firing(self):
        if self.active_weapon.__class__.__name__ is not "Magna_Shot": self.equip_weapon("Magna_Shot")


##Classes for different kinds of weapons

# base constructor class for weapons
class Weapon:
    def __init__(self, rate_of_fire, ammo, clip_size, wielder, automatic_fire=False, sound=10):
        self.rof = rate_of_fire  # rate of fire is measured in game-ticks it takes to cool down.
        self.cooldown = 0
        self.ammo = ammo
        self.wielder = wielder
        self.clip_size = clip_size
        self.in_clip = clip_size
        self.fire_num = 0
        self.iter = 0
        self.sound = sound
        self.automatic_fire = automatic_fire
        self.reloading = False
        self.firing = False

    def reduce_cd(self):
        if self.cooldown > 0:
            self.cooldown -= 1  # reduces the weapon's cooldown every tick of the game.
        elif self.cooldown == 0 and self.reloading:
            self.reloading = False
            self.in_clip = min(self.ammo, self.clip_size)

    def refresh(self):  # ensures that the weapon resets its firing rate even when the player is not wielding it
        if self.iter == 0:
            self.fire_num = 0
        else:
            self.iter -= 1

    def reload(self):
        if self.in_clip != self.clip_size and self.in_clip != self.ammo:  # Can't reload if clip is already full or if there isn't any ammo to reload.
            self.cooldown = 300
            self.reloading = True
            self.firing = False


class Sonic_Disintegrator(Weapon):
    def fire(self, direction):
        if self.cooldown == 0 and is_between_degrees(self.wielder.direction, direction,
                                                     90) and not self.wielder.breaking:
            Sonic_Wave(self, direction, 8, self.wielder.parent.map, 40)
            self.cooldown = self.rof
            Play_sound('Sounds/weapons/Sonic Blast.wav')
            self.wielder.weapon_fired = self.sound


class Bolt_Driver(Weapon):
    def fire(self, direction):
        if self.cooldown == 0 and is_between_degrees(self.wielder.direction, direction,
                                                     90) and self.ammo > 0 and self.in_clip > 0:
            Bolt(self, direction, 30, self.wielder.parent.map, 30)
            if self.fire_num < 2:
                self.cooldown = self.rof; self.fire_num += 1;
            else:
                self.fire_num = 0; self.cooldown = self.rof * 3; self.iter = self.rof * 3  # after three shots are fired in quick succession, implement a higher cooldown
            self.ammo -= 1;
            self.in_clip -= 1
            Play_sound('Sounds/weapons/BoltDriver_Standard.wav')
            self.wielder.weapon_fired = self.sound
            if self.in_clip <= 0:
                self.reload()
            self.iter = self.cooldown * 4


class Magna_Shot(Weapon):
    def fire(self, direction):
        if self.cooldown == 0 and self.ammo > 0 and self.in_clip > 0:
            Magnaround(self, direction, 15, self.wielder.parent.map, 15 * (self.wielder.parent.difficulty ** 0.5))
            self.cooldown = self.rof
            self.ammo -= 1;
            self.in_clip -= 1
            Play_sound('Sounds/weapons/Magna Shot Fire.wav')
            self.wielder.weapon_fired = self.sound
        if self.in_clip <= 0: self.reload()

    def reload(self):
        self.cooldown = 200
        self.reloading = True
        self.in_clip = min(self.ammo, self.clip_size)


class MAR(Weapon):
    def fire(self, direction):
        if self.cooldown == 0 and is_between_degrees(self.wielder.direction, direction,
                                                     90) and self.ammo > 0 and self.in_clip > 0:
            MARRound(self, direction, 10, self.wielder.parent.map, 30)
            self.cooldown = self.rof
            self.ammo -= 1;
            self.in_clip -= 1
            Play_sound('Sounds/weapons/Magna Shot Fire.wav')
            self.wielder.weapon_fired = self.sound
        if self.in_clip <= 0: self.reload()


class Plasmacaster(Weapon):
    def fire(self, direction):
        if not self.firing:
            self.firing = True
            self.direction = direction
        else:
            self.firing = False

    def reduce_cd(self):
        if self.cooldown > 0: self.cooldown -= 1
        if self.firing:  # function is used to allow for automatic fire for the plasmacaster.
            if is_between_degrees(self.wielder.direction, self.wielder.parent.vector,
                                  90) and self.ammo > 0 and self.in_clip > 0:
                self.cooldown = 2
                Plasmashot(self, randomize_direction(self.wielder.parent.vector, 3), 15, self.wielder.parent.map, 3)
                self.ammo -= 1
                self.in_clip -= 1
                Play_sound('Sounds/weapons/plasmacaster.wav')
            elif self.in_clip <= 0:
                self.reload()
            else:
                self.firing = False
        elif self.cooldown == 0 and self.reloading:
            self.reloading = False
            self.in_clip = min(self.ammo, self.clip_size)


class Laser_Array(Weapon):
    def fire(self, direction):
        if self.cooldown == 0 and is_between_degrees(self.wielder.direction, direction, 90) and self.ammo > 0:
            Laser(self, direction, 16, self.wielder.parent.map, 20)
            self.cooldown = self.rof
            self.ammo -= 1
            self.in_clip -= 1
            Play_sound('Sounds/weapons/laser array.wav')

    def reload(self):  # Weapon has no reload mechanic.
        pass


class Static_Object():  # Constructor class, not used.
    def __init__(self, instance, texture):
        self.instance = instance
        self.game_map = instance.map
        self.texture = texture
        self.superimposed = True
        while self.superimposed:  # Generate a new random position if existing tile already has an object in it. Don't let two objects superimpose over eachother in the same tile.
            self.superimposed = False
            self.x = random.randint(0, (self.game_map.xsize - 1) * self.game_map.tile_size)
            self.y = random.randint(0, (self.game_map.xsize - 1) * self.game_map.tile_size)
            self.xtile = int(self.x // self.game_map.tile_size)
            self.ytile = int(self.y // self.game_map.tile_size)
            for item in instance.static_objects:
                if distance([self.x, self.y], [item.x, item.y]) < 16:
                    self.superimposed = True
        instance.static_objects.append(self)
        self.is_active = True

    def update(self):
        if distance([self.x, self.y], self.instance.player.xy) <= 20:
            self.pick_up()

    def draw(self):
        (x1, y1) = map(lambda xy: int(xy // self.game_map.tile_size), self.instance.player.xy)
        x2 = x1 - half_width // self.game_map.tile_size;
        y2 = y1 - half_width // self.game_map.tile_size
        if self.instance.player.in_los[self.xtile][self.ytile] or distance([self.x, self.y],
                                                                           self.instance.player.xy) < self.instance.player.vision_range:
            px, py = -self.instance.player.xy[0] + half_width + self.x, -self.instance.player.xy[
                1] + half_height + self.y
            self.instance.screen.blit(self.texture, (px, py))

    def pick_up(self):  # Whatever is picked up depends on the type of static object.
        self.is_active = False


class MARAmmo(Static_Object):
    def pick_up(self):
        for weapon in self.instance.player.weapons:
            if weapon.__class__.__name__ == "MAR":
                weapon.ammo += 3
                self.is_active = False
                self.instance.text_num = 100
                self.instance.text = "Picked up some self-propelled rounds."


class Biopack(Static_Object):
    def pick_up(self):
        if self.instance.player.health < 100:
            amount = self.instance.player.health + random.randint(20, 40)
            self.instance.player.health = min(self.instance.player.health_cap, amount)
            self.is_active = False
            self.instance.text_num = 100
            self.instance.text = "Picked up some restoration gel."


class MAR_Static(Static_Object):
    def pick_up(self):
        temp_var = True  # Tempvar determines if picking up the object will add ammunition to existing MAR or add a new MAR to the player's weapon list.
        for weapon in self.instance.player.weapons:
            if weapon.__class__.__name__ == "MAR":
                weapon.ammo += 2
                temp_var = False
                self.is_active = False
                self.instance.text_num = 100
                self.instance.text = "Picked up a Mass-Accelerator Repeater."
        if temp_var:
            ammo = random.randint(1, 4)
            self.instance.player.weapons.append(MAR(45, ammo, min(3, ammo), self.instance.player))
            self.is_active = False
            self.instance.text_num = 100
            self.instance.text = "Picked up a Mass-Accelerator Repeater."


class Bolt_Ammo(Static_Object):
    def pick_up(self):
        for weapon in self.instance.player.weapons:
            if weapon.__class__.__name__ == "Bolt_Driver":
                weapon.ammo += 5
        self.is_active = False
        self.instance.text_num = 100
        self.instance.text = "Picked up some armor-piercing bolts."


class Plasmacaster_Static(Static_Object):
    def pick_up(self):
        temp_var = True
        for weapon in self.instance.player.weapons:
            if weapon.__class__.__name__ == "Plasmacaster":
                weapon.ammo += 100
                temp_var = False
                self.is_active = False
                self.instance.text_num = 100
                self.instance.text = "Picked up a Plasmacaster."
        if temp_var:
            self.instance.player.weapons.append(Plasmacaster(3, 200, 50, self.instance.player, True))
            self.is_active = False
            self.instance.text_num = 100
            self.instance.text = "Picked up a Plasmacaster."


class Plasmacaster_Ammo(Static_Object):
    def pick_up(self):
        for weapon in self.instance.player.weapons:
            if weapon.__class__.__name__ == "Plasmacaster":
                weapon.ammo += 100
                self.is_active = False
                self.instance.text_num = 100
                self.instance.text = "Picked up some rapid energy cells."


class Laser_Array_Static(Static_Object):
    def pick_up(self):
        temp_var = True
        for weapon in self.instance.player.weapons:
            if weapon.__class__.__name__ == "Laser_Array":
                weapon.ammo += 100
                temp_var = False
                self.is_active = False
                self.instance.text_num = 100
                self.instance.text = "Picked up a Laser Array."
        if temp_var:
            self.instance.player.weapons.append(Laser_Array(20, 50, 50, self.instance.player))
            self.is_active = False
            self.instance.text_num = 100
            self.instance.text = "Picked up a Laser Array."


###Classes for different kinds of projectiles

# baseline constructor class
class Projectile():
    def __init__(self, weapon, direction, speed, game_map, damage=None):
        self.weapon = weapon
        self.direction = direction
        self.speed = speed
        self.texture = pg.image.load("images/projectiles/" + str(self.weapon.__class__.__name__) + "_Projectile.png")
        self.damage = damage  # determines how much damage the projectile does upon hitting a target.
        self.xy = [weapon.wielder.xy[0], weapon.wielder.xy[1]]
        self.xy_rem = [weapon.wielder.xy_rem[0], weapon.wielder.xy_rem[1]]
        self.is_active = True
        self.game_map = game_map
        self.size = 16  # refers to the size of the projectile in pixels (16 by default).
        menu.game_instance.projectiles.append(self)

    def update(self, characters_list, screen, offset):
        self.xy, self.xy_rem = calculate_movement(self.xy, self.direction, self.xy_rem, self.speed)
        if self.damage <= 0:
            self.is_active = False
        self.check_collision(characters_list)
        if self.is_active:
            self.draw(screen, offset)

    def draw(self, screen, player_pos):
        if self.texture is not None:
            texture = pg.transform.rotate(self.texture, degrees(self.direction))
            screen.blit(texture, (self.xy[0] + half_width - player_pos[0], self.xy[1] + half_height - player_pos[
                1]))  # draw particle in the center of its position, will use 16x16 pixel images

    def get_tile(self):
        return self.xy[0] // self.game_map.tile_size, self.xy[1] // self.game_map.tile_size

    def get_tile_type(self):
        return self.game_map.retrieve_tile_type(int((self.xy[0] + 8) // self.game_map.tile_size),
                                                int((self.xy[1] + 8) // self.game_map.tile_size))

    def check_collision(self, characters_list):
        for character in characters_list:
            if in_box(center_image(self.xy, 16), character.corners[0], character.corners[-1],
                      projectile_size=self.size) and character is not self.weapon.wielder and character.alive:
                character.take_damage(self.damage)
                self.is_active = False


class Photon(Projectile):
    def __init__(self, player, direction, speed, game_map):
        self.xy = center_image(player.xy)
        self.player = player
        self.direction = direction
        self.speed = speed
        self.game_map = game_map

    def move(self):
        self.xy = simple_move(self.xy, self.direction, self.speed)

    def check_collision(self, player):
        if distance(self.xy, [player.xy[0] + 16, player.xy[1] + 16]) < 20:
            return True


class Sonic_Wave(Projectile):
    def update(self, characters_list, screen, offset, game_map):
        self.xy, self.xy_rem = calculate_movement(self.xy, self.direction, self.xy_rem, self.speed)
        self.damage -= 2  # damage falls rapidly as the sonic wave moves
        tile_type = self.get_tile_type()
        if self.damage <= 0 or tile_type in illegal_tiles:  # can't shoot through walls.
            self.is_active = False
        self.check_collision(characters_list)
        self.size += 3
        self.texture = pg.transform.scale(self.texture, (self.size, self.size))
        if self.is_active:
            self.draw(screen, offset)


class Bolt(Projectile):
    def update(self, characters_list, screen, offset, game_map):
        self.xy, self.xy_rem = calculate_movement(self.xy, self.direction, self.xy_rem, self.speed)
        self.damage -= 0.02
        tile_type = self.get_tile_type()
        self.speed -= 0.05
        if tile_type == 'lava':
            self.damage -= 4; self.speed -= 4  # Water and lava slow down and reduce damage from bolt projectiles
        elif tile_type == 'water':
            self.damage -= 2; self.speed -= 2
        if tile_type in illegal_tiles or self.speed <= 10:
            self.is_active = False
        self.check_collision(characters_list)
        if self.is_active:
            self.draw(screen, offset)


class Magnaround(Projectile):
    def __init__(self, weapon, direction, speed, game_map, damage=None):
        self.weapon = weapon
        self.direction = direction
        self.speed = speed
        self.damage = damage  # determines how much damage the projectile does upon hitting a target.
        self.texture = pg.image.load("images/projectiles/" + str(self.weapon.__class__.__name__) + "_Projectile.png")
        self.xy = [weapon.wielder.xy[0], weapon.wielder.xy[1]]
        self.xy_rem = [weapon.wielder.xy_rem[0], weapon.wielder.xy_rem[1]]
        self.is_active = True
        self.game_map = game_map
        self.size = 16  # refers to the size of the projectile in pixels (16 by default).
        menu.game_instance.projectiles.append(self)
        self.scan_value = 50

    def update(self, characters_list, screen, offset, game_map):
        self.xy, self.xy_rem = calculate_movement(self.xy, self.direction, self.xy_rem, self.speed)
        tile = self.get_tile_type()
        if tile in illegal_tiles:
            self.explode(characters_list)
        elif tile == 'lava':
            self.speed -= 5
        elif tile == 'water':
            self.speed -= 3
        if self.speed < 10: self.is_active = False
        self.check_collision(characters_list)
        self.scan(characters_list)
        if self.is_active:
            self.draw(screen, offset)

    def scan(self,
             characters_list):  # The projectile scans its position relative to the player, so that it explodes at the shortest possible distance from the player if it can't hit the player.
        for character in characters_list:  # Traphon rounds have proximity-detonation fuses.
            if distance(character.xy,
                        self.xy) < self.scan_value and character.__class__.__name__ is not self.weapon.wielder.__class__.__name__ and character.alive:
                if distance(self.project(self.scan_value), character.xy) >= distance(self.xy, character.xy):
                    self.explode(characters_list)
                else:
                    self.scan_value = distance(self.xy, character.xy)

    def project(self, scanvalue):
        return [self.xy[0] + self.direction[0] * self.scan_value, self.xy[1] + self.direction[1] * self.scan_value]

    def explode(self, characters_list):
        if self.is_active:
            self.is_active = False
            for char in characters_list:
                if char.alive:
                    distance_to_explosion = distance(char.xy, self.xy)
                    if distance_to_explosion < 100:
                        char.take_damage((15 - 15 * (distance_to_explosion / 100)) * (
                                    self.weapon.wielder.parent.difficulty ** 0.5))  # character takes up to 15 points of additional explosive damage from the projectile, depending on the exact distance. Self-damage is enabled.
            if distance(self.xy, characters_list[0].xy) < 1000:
                Play_sound('Sounds/weapons/Magna Shot Explode.wav')

    def check_collision(self, characters_list):
        for character in characters_list:
            if in_box(self.xy, character.corners[0], character.corners[-1],
                      projectile_size=self.size) and character is not self.weapon.wielder and character.alive:
                character.take_damage(self.damage)
                self.explode(characters_list)
            else:
                self.scan(characters_list)


class MARRound(Projectile):
    def update(self, characters_list, screen, offset, game_map):
        self.check_collision(characters_list)
        self.xy, self.xy_rem = calculate_movement(self.xy, self.direction, self.xy_rem, self.speed)

        self.speed += 3
        if distance(self.xy, self.weapon.wielder.xy) > half_width * 1.5 or self.speed <= 5:
            self.is_active = False
        tile = self.get_tile_type()
        if tile in illegal_tiles:
            self.explode(characters_list)
        elif tile == "lava":
            self.speed -= 12
        elif tile == "water":
            self.speed -= 3
        if self.is_active: self.draw(screen, offset)

    def explode(self, characters_list):
        if self.is_active:
            self.is_active = False
            for char in characters_list:
                if char.alive:
                    distance_to_explosion = distance(char.xy, self.xy)
                    if distance_to_explosion < 200:
                        char.take_damage(50 - distance_to_explosion / 4)
                    x, y = self.get_tile()
                    for i in range(max(0, x - 2), min(x + 3, self.game_map.xsize - 1)):
                        for j in range(max(0, y - 2), min(y + 3, self.game_map.ysize - 1)):
                            dist = distance(self.xy, center_image(self.game_map.tiles[i][j].xy))
                            self.game_map.tiles[i][j].chip(200 - 2 * dist)
            if distance(self.xy, characters_list[0].xy) < 1000:
                Play_sound('Sounds/weapons/Magna Shot Explode.wav')

    def check_collision(self, characters_list):
        for character in characters_list:
            if in_box(self.xy, character.corners[0], character.corners[-1],
                      projectile_size=self.size) and character is not self.weapon.wielder and character.alive:
                self.damage = 30 + (
                            self.speed - 10) * 3.5  # <--- Set the damage according to the projectile's current velocity.
                character.take_damage(self.damage)
                self.explode(characters_list)


class Plasmashot(Projectile):
    def update(self, characters_list, screen, offset, game_map):
        self.xy, self.xy_rem = calculate_movement(self.xy, self.direction, self.xy_rem, self.speed)
        self.damage -= 0.02
        tile_type = self.get_tile_type()
        self.speed -= 0.1
        if tile_type == 'lava':
            self.damage -= 0.3; self.speed -= 5
        elif tile_type == 'water':
            self.damage -= 0.5; self.speed -= 4
        if tile_type in illegal_tiles or self.speed <= 10:
            self.is_active = False
        self.check_collision(characters_list)
        if self.is_active:
            self.draw(screen, offset)


class Laser(Projectile):
    def update(self, characters_list, screen, offset, game_map):
        while self.is_active:
            self.xy, self.xy_rem = calculate_movement(self.xy, self.direction, self.xy_rem, self.speed)
            self.damage -= 0.5
            tile_type = self.get_tile_type()
            if tile_type in illegal_tiles or self.damage < 5:
                self.is_active = False
            if tile_type in liquids: self.damage -= 5
            self.check_collision(characters_list)
            if self.is_active: self.draw(screen, offset)

#Small line of code to allow the program to run even if no audio device is plugged in.
Audio = True
try:
    pg.mixer.init()
except:
    Audio = None

if __name__ == "__main__":
    my_game = Game(1200, 800)
    menu = my_game.Menu(my_game)
    menu.main_menu(my_game)

    input()