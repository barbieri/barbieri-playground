#!/usr/bin/env python

from pygame.locals import Rect, RLEACCEL
from pygame.sprite import Sprite, Group
import pygame

__license__ = "GPL"
__author__ = "Gustavo Sverzut Barbieri"
__author_email__ = "barbieri@gmail.com"
__url__ = "http://www.gustavobarbieri.com.br/"
__doc__ = """\
Pygame offers some basic scene managers called pygame.sprite.Group, but
they're  very basic and not optimized for drawing just screen areas that
changed.

This module provides a SmartGroup that deals with SmartSprite and tracks
rendering just dirty areas, minimizing overhead.

It's based on pygame.sprite.OrderedUpdates, but does better tracking of
states and also split rectangles to be updated, avoiding copy background
and update same area more than once.

LIMITATIONS
===========

 * One sprite can be in just one group
"""

__all__ = ("SmartGroup", "SmartSprite", "SmartSpriteDrag")

def _split_internal(clean, index, dirty):
    # Python's access to methods and globals are not the fastest... try to help
    clean_extend = clean.extend
    clean_len = clean.__len__

    R = Rect

    if clean_len == 0 and len(dirty) == 1:
        clean_extend(dirty)
        return

    while dirty:
        new_list = []
        new_list_append = new_list.append

        if index == clean_len():
            clean_extend(dirty)

        current = clean[index]

        current_left = current.left
        current_right = current.right
        current_top = current.top
        current_bottom = current.bottom

        for r in dirty:
            r_left = r.left
            r_right = r.right
            r_top = r.top
            r_bottom = r.bottom
            r_width = r.width
            r_height = r.height

            h_1 = current_top - r_top
            h_2 = r_bottom - current_bottom
            w_1 = current_left - r_left
            w_2 = r_right - current_right

            if w_1 <= 0 and w_2 <= 0 and h_1 <= 0 and h_2 <= 0:
                # .-------.cur
                # | .---.r|
                # | |   | |
                # | `---' |
                # `-------'
                continue

            elif r_right <= current_left or r_left >= current_right or \
                 r_top >= current_bottom or r_bottom <= current_top:
                # .---.cur     .---.r
                # |   |        |   |
                # `---+---.r   `---+---.cur
                #     |   |        |   |
                #     `---'        `---'
                new_list_append(r)

            else:
                if r_width >= r.height:
                    # r is bigger on width, split horizontally
                    if h_1 > 0:
                        #   .--.r                    .---.r2
                        #   |  |                     |   |
                        # .-------.cur     .---.r    '---'
                        # | |  |  |     -> |   |   +
                        # | `--'  |        `---'
                        # `-------'
                        new_list_append(R(r_left, r_top, r_width, h_1))
                        r.height = r_height = r_height - h_1
                        r.top = r_top = current_top

                    if h_2 > 0:
                        # .-------.cur
                        # | .---. |        .---.r
                        # | |   | |    ->  |   |
                        # `-------'        `---'   +  .---.r2
                        #   |   |                     |   |
                        #   `---'r                    `---'
                        new_list_append(R(r_left, current_bottom,
                                          r_width, h_2))
                        r.height = r_height = r_height - h_2

                    if w_1 > 0:
                        # r  .----.cur
                        # .--|-.  |      .--.r2   .-.r
                        # |  | |  |  ->  |  |   + | |
                        # `--|-'  |      `--'     `-'
                        #    `----'
                        new_list_append(R(r_left, r_top, w_1, r_height))
                        r.width = r_width = r_width - w_1
                        r.left = r_left = current_left

                    if w_2 > 0:
                        # .----.cur
                        # |    |
                        # |  .-|--.r      .-.r   .--.r2
                        # |  | |  |    -> | |  + |  |
                        # |  `-|--'       `-'    `--'
                        # `----'
                        new_list_append(R(current_right, r_top, w_2, r_height))
                        r.width = r_width = r_width - w_2

                else:
                    # r is bigger on height, split vertically first.
                    if w_1 > 0:
                        # r  .----.cur
                        # .--|-.  |      .--.r2   .-.r
                        # |  | |  |  ->  |  |   + | |
                        # `--|-'  |      `--'     `-'
                        #    `----'
                        new_list_append(R(r_left, r_top, w_1, r_height))
                        r.width = r_width = r_width - w_1
                        r.left = r_left = current_left

                    if w_2 > 0:
                        # .----.cur
                        # |    |
                        # |  .-|--.r      .-.r   .--.r2
                        # |  | |  |    -> | |  + |  |
                        # |  `-|--'       `-'    `--'
                        # `----'
                        new_list_append(R(current_right, r_top, w_2, r_height))
                        r.width = r_width = r_width - w_2

                    if h_1 > 0:
                        #   .--.r                    .---.r2
                        #   |  |                     |   |
                        # .-------.cur     .---.r    '---'
                        # | |  |  |     -> |   |   +
                        # | `--'  |        `---'
                        # `-------'
                        new_list_append(R(r_left, r_top, r_width, h_1))
                        r.height = r_height = r_height - h_1
                        r.top = r_top = current_top

                    if h_2 > 0:
                        # .-------.cur
                        # | .---. |        .---.r
                        # | |   | |    ->  |   |
                        # `-------'        `---'   +  .---.r2
                        #   |   |                     |   |
                        #   `---'r                    `---'
                        new_list_append(R(r_left, current_bottom,
                                          r_width, h_2))
                        r.height = r_height = r_height - h_2

        index += 1
        dirty = new_list
# _split_internal()

def _split_rects_add(clean, r):
    _split_internal(clean, 0, [r])
# _split_rects_add()


def _cmp_area(r1, r2):
    return cmp(r2.width * r2.height, r1.width * r1.height)
# _cmp_area()


class SmartSprite(Sprite):
    __slots__ = ("_group", "_zindex", "_dirty", "_alpha", "_visible",
                 "damaged", "last_state", "rect", "image")

    def __init__(self, *args):
        if not hasattr(self, "image"):
            self.image = None
        if not hasattr(self, "rect"):
            self.rect = Rect(0, 0, 32, 32)

        self._group = args[0]
        self._visible = False
        self._zindex = 0
        self._dirty = True
        self._alpha = 255
        self.damaged = False
        self.damaged_areas = []
        self.last_state = None

        Sprite.__init__(self, *args)
    # __init__()


    def __cmp__(self, obj):
        return cmp(self._zindex, obj.zindex)
    # __cmp__()


    def get_dirty(self):
        return self._dirty
    # get_dirty()


    def set_dirty(self, v):
        self._dirty = v
        if v:
            self._group.dirty = True
    # set_dirty()
    dirty = property(get_dirty, set_dirty)


    def get_alpha(self):
        return self._alpha
    # get_alpha()


    def set_alpha(self, v):
        if v == self._alpha:
            return

        self._alpha = v
        if self.image:
            self.image.set_alpha(v, RLEACCEL)
            self.dirty = True
    # set_alpha()
    alpha = property(get_alpha, set_alpha)


    def get_zindex(self):
        return self._zindex
    # get_zindex()


    def set_zindex(self, v):
        if v == self._zindex:
            return

        self._zindex = v
    # set_zindex()
    zindex = property(get_zindex, set_zindex)


    def get_visible(self):
        return self._visible
    # get_visible()


    def set_visible(self, v):
        if v == self._visible:
            return

        self._visible = v
        self.dirty = True
    # set_visible()
    visible = property(get_visible, set_visible)


    def show(self):
        self.visible = True
    # show()


    def hide(self):
        self.visible = False
    # hide()


    def move(self, x, y):
        r = self.rect
        d = False

        if r.left != x:
            r.left = x
            d = True

        if r.top != y:
            r.top = y
            d = True

        if d:
            self.dirty = True
    # move()


    def move_rel(self, dx, dy):
        if dx == 0 and dy == 0:
            return

        self.rect.move_ip(dx, dy)
        self.dirty = True
    # move_rel()


    def last_state_changed(self):
        return self.last_state and self.last_state.changed()
    # last_state_changed()


    def mouse_click(self, x, y):
        pass
    # mouse_click()


    def __str__(self):
        return ("%s(rect=%s, zindex=%s, visible=%s, dirty=%s, "
                "alpha=%s, damaged=%s, group=%s, last_state=%s)" )% \
                (self.__class__.__name__, self.rect, self.zindex,
                 self.visible, self.dirty, self.alpha, self.damaged,
                 self._group, self.last_state)
    # __str__()
# SmartSprite


class SmartSpriteDrag(SmartSprite):
    __slots__ = ("drag_x", "drag_y")

    def __init__(self, *args):
        SmartSprite.__init__(self, *args)
        self.drag_x = None
        self.drag_y = None
    # __init__()


    def drag_start(self, x, y):
        self.drag_x = self.rect.left - x
        self.drag_y = self.rect.top - y
        return True
    # drag_start()


    def drag_update(self, x, y):
        self.move(x + self.drag_x, y + self.drag_y)
    # drag_update()


    def drag_end(self, x, y):
        self.drag_update(x, y)
        self.drag_x = None
        self.drag_y = None
    # drag_end()
# SmartSpriteDrag


class SmartSpriteState(object):
    __slots__ = ("sprite", "rect", "alpha", "visible", "zindex", "image")
    def __init__(self, sprite):
        self.sprite = sprite
        self.rect = Rect(sprite.rect)
        self.alpha = sprite.alpha
        self.visible = sprite.visible
        self.image = sprite.image
    # __init__()


    def changed(self):
        sprite = self.sprite
        return self.rect != sprite.rect or \
               self.alpha != sprite.alpha or \
               self.visible != sprite.visible or \
               self.image != sprite.image
    # changed()

    def __str__(self):
        return "%s(rect=%s, alpha=%s, visible=%s)" % \
               (self.__class__.__name__, self.rect, self.alpha, self.visible)
    # __str__()
# SmartSpriteState


class SmartGroup(Group):
    def __init__(self, *sprites):
        self._spritelist = []
        Group.__init__(self, *sprites)
    # __init__()


    def sprites(self):
        return iter(self._spritelist)
    # sprites()


    def add_internal(self, sprite):
        Group.add_internal(self, sprite)
        sprite.zindex = len(self._spritelist)
        self._spritelist.append(sprite)
        if sprite.visible:
            self.dirty = True
    # add_internal()


    def remove_internal(self, sprite):
        if sprite.last_state:
            self.lostsprites.append(sprite.last_state.rect)

        del self._spritelist[sprite.zindex]
        sprite.zindex = None

        if sprite.visible:
            self.dirty = True

        Group.remove_internal(self, sprite)
    # remove_internal()


    def sort(self):
        self._spritelist.sort()
        for i, o in enumerate(self._spritelist):
            o.zindex = i
    # sort()


    def above_all(self, sprite):
        if not sprite or sprite.zindex + 1 == len(self._spritelist):
            return

        spritelist = self._spritelist
        del spritelist[sprite.zindex]

        i = sprite.zindex
        size = len(spritelist)
        while i < size:
            s = spritelist[i]
            s.zindex = i
            i += 1

        sprite.zindex = i
        spritelist.append(sprite)
    # above_all()


    def below_all(self, sprite):
        if not sprite:
            return

        spritelist = self._spritelist
        del spritelist[sprite.zindex]

        spritelist.insert(0, sprite)
        for i, s in enumerate(spritelist):
            s.zindex = i
    # below_all()


    def __len__(self):
        return len(self._spritelist)
    # __len__()


    def item_at(self, x, y):
        spritelist = self._spritelist

        i = len(spritelist) - 1
        while i >= 0:
            o = spritelist[i]
            i -= 1

            if o.rect.collidepoint(x, y):
                return o

        return None
    # item_at()


    def clear(self, surface, bg):
        # make heavily used symbols local, avoid python performance hit
        split_rects_add = _split_rects_add
        spritelist = self._spritelist
        spritelist_len = len(spritelist)
        changed = self.lostsprites
        changed_append = changed.append

        for sprite in spritelist:
            if not sprite.last_state_changed():
                continue

            state = sprite.last_state
            changed_append(state.rect)

            i = sprite.zindex
            while i < spritelist_len:
                s2 = spritelist[i]
                i += 1

                if s2.dirty or not s2.visible:
                    continue

                r = state.rect.clip(s2.rect)
                if r:
                    r2 = Rect((r.left - s2.rect.left,
                               r.top - s2.rect.top),
                              r.size)
                    s2.damaged_areas.append((r, r2))
                    s2.damaged = True
        # for in spritelist

        changed.sort(_cmp_area)
        split_rects = []
        for r in changed:
            split_rects_add(split_rects, r)

        surface_blit = surface.blit
        dirty = []
        dirty_append = dirty.append
        for r in split_rects:
            r = surface_blit(bg, r, r)
            dirty_append(r)

            for s in spritelist:
                if s.dirty or s.damaged or not s.visible:
                    continue

                state = s.last_state
                r2 = r.clip(state.rect)
                if r2:
                    r3 = Rect(r2.left - s.rect.left, r2.top - s.rect.top,
                              r2.width, r2.height)
                    surface_blit(s.image, r2, r3)
            # for in spritelist
        # for in split_rects

        self.lostsprites = dirty
    # clear()


    def draw(self, surface):
        if not self.dirty:
            return

        # make heavily used symbols local, avoid python performance hit
        split_rects_add = _split_rects_add

        dirty = self.lostsprites
        dirty_append = dirty.append
        self.lostsprites = []

        surface_blit = surface.blit

        for s in self._spritelist:
            if not s.visible:
                s.last_state = None
                continue

            elif s.dirty:
                r = surface_blit(s.image, s.rect)
                s.last_state = SmartSpriteState(s)
                s.dirty = False
                dirty_append(r)

            elif s.damaged:
                for dst, area in s.damaged_areas:
                    r = surface_blit(s.image, dst, area)
                    dirty_append(r)

                del s.damaged_areas[:]
                s.damaged = False

        dirty.sort(_cmp_area)
        split_rects = []
        for r in dirty:
            split_rects_add(split_rects, r)

        self.dirty = False
        return split_rects
    # draw()
# SmartGroup

