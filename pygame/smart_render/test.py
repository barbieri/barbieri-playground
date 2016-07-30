#!/usr/bin/env python

import pygame
from smart_render import *
from pygame.locals import *

SCREEN_SIZE = (800, 600)
SCREEN_DEPTH = 0
FPS = 24

class Image(object):
    _cache = {}
    __slots__ = ("image", "filename", "convert", "has_alpha", "_spec")

    def __init__(self, filename, has_alpha=False, convert=True):
        self.filename = filename
        self.convert = convert
        self.has_alpha = has_alpha
        self._spec = (filename, convert, has_alpha)
        self.image = self._get_cache()
    # __init__()


    def _set_cache(self):
        self._cache[self._spec] = self.image
    # _set_cache()


    def _get_cache(self):
        return self._cache.get(self._spec, None)
    # _get_cache()


    def _get_cache_raw(self):
        return self._cache.get((self.filename, False, False), None)
    # _get_cache_raw()


    def load(self):
        if self.image:
            return self.image

        img = self._get_cache()
        if img:
            self.image = img
            return img

        img = self._get_cache_raw()
        if not img:
            img = pygame.image.load(self.filename)

        if self.convert:
            if self.has_alpha:
                img.set_alpha(255, RLEACCEL)
                img = img.convert_alpha()
            else:
                img = img.convert()

        self.image = img
        self._set_cache()
        return img
    # load()


    def __str__(self):
        return "%s(filename=%s, has_alpha=%s, convert=%s)" % \
               (self.__class__.__name__, self.filename, self.has_alpha,
                self.convert)
    # __str__()
# Image


class Sun(SmartSpriteDrag):
    img_on = Image("imgs/sun_on.png", has_alpha=True)
    img_off = Image("imgs/sun_off.png", has_alpha=True)
    mask = Image("imgs/sun_mask.png")

    def __init__(self, app, x=0, y=0):
        SmartSpriteDrag.__init__(self, app.objs)
        self.app = app
        self.rect = Rect(x, y, 20, 20)
        self.status_on = True
    # __init__()


    def drag_start(self, x, y):
        dx = x - self.rect.left
        dy = y - self.rect.top

        if self.mask.image.get_at((dx, dy))[0] == 255:
            return SmartSpriteDrag.drag_start(self, x, y)
        else:
            return False
    # drag_start()


    def setup_status(self):
        if self.status_on:
            img = self.img_on.image
        else:
            img = self.img_off.image

        if img != self.image:
            self.dirty = True
            self.rect.size = img.get_size()
            self.image = img
    # setup_status()


    def images_loaded(self):
        self.setup_status()
    # images_loaded()


    def set_status(self, status):
        if status == self.status_on:
            return

        self.status_on = status
        self.setup_status()
    # set_status()
# Sun


class Switcher(SmartSprite):
    img_on = Image("imgs/switch_on.png")
    img_off = Image("imgs/switch_off.png")

    def __init__(self, app, x=0, y=0):
        SmartSprite.__init__(self, app.objs)
        self.app = app
        self.status_on = True
        self.rect = Rect(x, y, 32, 32)
    # __init__()


    def setup_status(self):
        if self.status_on:
            img = self.img_on.image
        else:
            img = self.img_off.image

        if img != self.image:
            self.dirty = True
            self.rect.size = img.get_size()
            self.image = img
    # setup_status()


    def images_loaded(self):
        self.setup_status()
    # images_loaded()


    def mouse_click(self, x, y):
        self.status_on = not self.status_on
        self.setup_status()
        self.app.sun.set_status(self.status_on)
    # mouse_click()
# Switcher


class BouncingSun(SmartSprite):
    img = Image("imgs/sun_on.png", has_alpha=True)

    def __init__(self, app, x=0, y=0):
        SmartSprite.__init__(self, app.objs)
        self.app = app
        self.rect = Rect(x, y, 20, 20)
        self.speed_x = 2
        self.speed_y = 2
        self.screen_w, self.screen_h = self.app.screen.get_size()
    # __init__()


    def images_loaded(self):
        self.image = self.img.image
        self.rect.size = self.image.get_size()
        self.app.animations.append(self.anim)
    # images_loaded()


    def anim(self, t):
        self.move_rel(self.speed_x, self.speed_y)
        if self.screen_w < self.rect.right or self.rect.left < 0:
            self.speed_x = - self.speed_x

        if self.screen_h < self.rect.bottom or self.rect.top < 0:
            self.speed_y = - self.speed_y
    # anim()
# BouncingSun


class App(object):
    def __init__(self, res=(800, 600), flags=0, depth=16, fps=24):
        self.screen = pygame.display.set_mode(res, flags, depth)
        self.run = False
        self.clock = None
        self.fps = fps
        self.drag = None
        self.animations = []

        self.screen.fill(0)
        self.font = pygame.font.Font("font.ttf", 20)
        self.objs = SmartGroup()
        self.setup_gui()
        self.load_images()
    # __init__()


    def show_msg(self, msg, x=0, y=0, color=(255, 255, 255, 255)):
        txt = self.font.render(msg, 1, color)
        self.screen.blit(txt, (x, y))
        pygame.display.update((x, y) + txt.get_size())
    # show_msg()


    def load_images(self):
        self.show_msg("Loading images...")

        self.bg = pygame.image.load("imgs/background.png").convert()

        for sprite in self.objs.sprites():
            for attr in dir(sprite):
                obj = getattr(sprite, attr)
                if isinstance(obj, Image):
                    obj.load()
            sprite.images_loaded()
    # load_images()


    def setup_gui(self):
        self.sun = Sun(self, 200, 200)
        self.switcher = Switcher(self, 0, 0)
        self.bouncer = BouncingSun(self, 400, 300)

        self.sun.show()
        self.switcher.show()
        self.bouncer.show()
    # setup_gui()


    def handle_events(self):
        for e in pygame.event.get():
            if e.type == QUIT:
                self.run = False
                return False

            elif e.type == MOUSEBUTTONDOWN:
                x, y = e.pos

                o = self.objs.item_at(x, y)
                if not o:
                    continue

                elif isinstance(o, SmartSpriteDrag):
                    self.objs.above_all(o)
                    if o.drag_start(x, y):
                        self.drag = o
                        return True

                # default action is click, even if cannot drag
                o.mouse_click(x, y)


            elif self.drag and e.type == MOUSEBUTTONUP:
                x, y = e.pos
                self.drag.drag_end(x, y)
                self.drag = None

            elif self.drag and e.type == MOUSEMOTION:
                x, y = e.pos
                self.drag.drag_update(x, y)

        return True
    # handle_events()


    def loop(self):
        self.run = True
        self.clock = pygame.time.Clock()

        self.screen.blit(self.bg, (0, 0))
        self.objs.draw(self.screen)
        pygame.display.update()

        while self.run:
            t = self.clock.tick(self.fps)

            if not self.handle_events():
                break

            if self.animations:
                t = pygame.time.get_ticks()
                for a in self.animations:
                    a(t)

            if self.objs.dirty:
                #print "dirty", self.clock.get_fps()
                self.objs.clear(self.screen, self.bg)
                r = self.objs.draw(self.screen)
                pygame.display.update(r)
                self.dirty = False

        print "FPS:", self.clock.get_fps()
    # loop()
# App



if __name__ == "__main__":
    pygame.init()

    flags = HWSURFACE | ASYNCBLIT
    app = App(res=SCREEN_SIZE, flags=flags, depth=SCREEN_DEPTH, fps=FPS)
    app.loop()
