#!/usr/bin/python

"""
Split given rectangles so rectangles don't overlap.
"""

import heapq
from pygame import Rect

class RectSplitter(object):
    def __init__(self):
        self.rects = []

    def split_strict(self, r):
        """Split rectangles strictly, no merge is done and already existing
        rectangles are never modified.
        """
        rects = self.rects
        if len(rects) == 0:
            rects.append(r)
            return

        R = Rect
        dirty = [r]
        index = 0
        while dirty:
            if index == len(rects):
                rects.extend(dirty)
                break

            new_dirty = []
            current = rects[index]

            for r in dirty:
                if r.left < current.left:
                    max_left = current.left
                else:
                    max_left = r.left

                if r.right < current.right:
                    min_right = r.right
                else:
                    min_right = current.right

                if r.top < current.top:
                    max_top = current.top
                else:
                    max_top = r.top

                if r.bottom < current.bottom:
                    min_bottom = r.bottom
                else:
                    min_bottom = current.bottom

                intra_width = min_right - max_left
                intra_height = min_bottom - max_top

                if intra_width == r.width and intra_height == r.height:
                        # .-------.cur
                        # | .---.r|
                        # | |   | |
                        # | `---' |
                        # `-------'
                        continue

                if intra_width <= 0 or intra_height <= 0:
                    # .---.cur     .---.r
                    # |   |        |   |
                    # `---+---.r   `---+---.cur
                    #     |   |        |   |
                    #     `---'        `---'
                    new_dirty.append(r)
                    continue

                h_1 = current.top - r.top
                h_2 = r.bottom - current.bottom
                w_1 = current.left - r.left
                w_2 = r.right - current.right

                if h_1 > 0:
                    #   .--.r                    .---.r2
                    #   |  |                     |   |
                    # .-------.cur     .---.r    '---'
                    # | |  |  |     -> |   |   +
                    # | `--'  |        `---'
                    # `-------'
                    new_dirty.append(R(r.left, r.top, r.width, h_1))
                    r.height -= h_1
                    r.top = current.top

                if h_2 > 0:
                    # .-------.cur
                    # | .---. |        .---.r
                    # | |   | |    ->  |   |
                    # `-------'        `---'   +  .---.r2
                    #   |   |                     |   |
                    #   `---'r                    `---'
                    new_dirty.append(R(r.left, current.bottom, r.width, h_2))
                    r.height -= h_2

                if w_1 > 0:
                    # r  .----.cur
                    # .--|-.  |      .--.r2   .-.r
                    # |  | |  |  ->  |  |   + | |
                    # `--|-'  |      `--'     `-'
                    #    `----'
                    new_dirty.append(R(r.left, r.top, w_1, r.height))
                    r.width -= w_1
                    r.left = current.left

                if w_2 > 0:
                    # .----.cur
                    # |    |
                    # |  .-|--.r      .-.r   .--.r2
                    # |  | |  |    -> | |  + |  |
                    # |  `-|--'       `-'    `--'
                    # `----'
                    new_dirty.append(R(current.right, r.top, w_2, r.height))
                    r.width -= w_2

            index += 1
            dirty = new_dirty

    def _split(self, r, accepted_error=0):
        rects = self.rects
        if len(rects) == 0:
            rects.append(r)
            return 0

        R = Rect
        dirty = [r]
        rects_removed = 0
        while dirty:
            r = dirty.pop(0)
            i = 0
            while i < len(rects):
                current = rects[i]

                if r.left < current.left:
                    max_left = current.left
                    min_left = r.left
                else:
                    max_left = r.left
                    min_left = current.left

                if r.right < current.right:
                    min_right = r.right
                    max_right = current.right
                else:
                    min_right = current.right
                    max_right = r.right

                if r.top < current.top:
                    max_top = current.top
                    min_top = r.top
                else:
                    max_top = r.top
                    min_top = current.top

                if r.bottom < current.bottom:
                    min_bottom = r.bottom
                    max_bottom = current.bottom
                else:
                    min_bottom = current.bottom
                    max_bottom = r.bottom

                intra_width = min_right - max_left
                intra_height = min_bottom - max_top

                if intra_width == r.width and intra_height == r.height:
                        # .-------.cur
                        # | .---.r|
                        # | |   | |
                        # | `---' |
                        # `-------'
                        break

                if intra_width == current.width and \
                   intra_height == current.height:
                        # .-------.r
                        # | .---.cur
                        # | |   | |
                        # | `---' |
                        # `-------'
                        del rects[i]
                        rects_removed += 1
                        continue

                if intra_width > 0 and intra_height > 0:
                    intra_area = intra_width * intra_height
                else:
                    intra_area = 0

                current_area = current.width * current.height
                r_area = r.width * r.height

                outer_width = max_right - min_left
                outer_height = max_bottom - min_top
                outer_area = outer_width * outer_height

                area = current_area + r_area - intra_area
                if outer_area - area <= accepted_error:
                    # merge them, remove both and add merged
                    del rects[i]
                    rects_removed += 1
                    current.left = min_left
                    current.top = min_top
                    current.width = outer_width
                    current.height = outer_height
                    dirty.append(current)
                    break

                if intra_area <= accepted_error:
                    # .---.cur     .---.r
                    # |   |        |   |
                    # `---+---.r   `---+---.cur
                    #     |   |        |   |
                    #     `---'        `---'
                    # no split, no merge
                    i += 1
                    continue

                h_1 = current.top - r.top
                h_2 = r.bottom - current.bottom
                w_1 = current.left - r.left
                w_2 = r.right - current.right

                split = False

                if h_1 > 0:
                    #   .--.r                    .---.r2
                    #   |  |                     |   |
                    # .-------.cur     .---.r    '---'
                    # | |  |  |     -> |   |   +
                    # | `--'  |        `---'
                    # `-------'
                    dirty.append(R(r.left, r.top, r.width, h_1))
                    r.height -= h_1
                    r.top = current.top
                    split = True

                if h_2 > 0:
                    # .-------.cur
                    # | .---. |        .---.r
                    # | |   | |    ->  |   |
                    # `-------'        `---'   +  .---.r2
                    #   |   |                     |   |
                    #   `---'r                    `---'
                    dirty.append(R(r.left, current.bottom, r.width, h_2))
                    r.height -= h_2
                    split = True

                if (w_1 > 0 or w_2 > 0) and current.height == r.height:
                    # merge them
                    del rects[i]
                    rects_removed += 1
                    current.left = min_left
                    current.width = outer_width
                    dirty.append(current)
                    break

                if w_1 > 0:
                    # r  .----.cur
                    # .--|-.  |      .--.r2   .-.r
                    # |  | |  |  ->  |  |   + | |
                    # `--|-'  |      `--'     `-'
                    #    `----'
                    dirty.append(R(r.left, r.top, w_1, r.height))
                    r.width -= w_1
                    r.left = current.left
                    split = True

                if w_2 > 0:
                    # .----.cur
                    # |    |
                    # |  .-|--.r      .-.r   .--.r2
                    # |  | |  |    -> | |  + |  |
                    # |  `-|--'       `-'    `--'
                    # `----'
                    dirty.append(R(current.right, r.top, w_2, r.height))
                    r.width -= w_2
                    split = True

                if split:
                    break

                i += 1
            else:
                rects.append(r)

        return rects_removed

    def _merge(self, index, accepted_error=0):
        if index < 0 or index >= len(self.rects):
            return

        to_merge = self.rects[index:]
        self.rects = rects = self.rects[:index]
        while to_merge:
            r1 = to_merge.pop(0)
            r1_area = r1.width * r1.height

            for i, r2 in enumerate(rects):
                r2_area = r2.width * r2.height

                if r1.left < r2.left:
                    min_left = r1.left
                else:
                    min_left = r2.left

                if r1.right > r2.right:
                    max_right = r1.right
                else:
                    max_right = r2.right

                if r1.top < r2.top:
                    min_top = r1.top
                else:
                    min_top = r2.top

                if r1.bottom > r2.bottom:
                    max_bottom = r1.bottom
                else:
                    max_bottom = r2.bottom

                outer_width = max_right - min_left
                outer_height = max_bottom - min_top
                outer_area = outer_width * outer_height

                area = r1_area + r2_area

                if outer_area - area <= accepted_error:
                    # remove both r1 and r2, create r3
                    # actually r3 uses r1 instance, saves memory
                    r1.left = min_left
                    r1.top = min_top
                    r1.width = outer_width
                    r1.height = outer_height
                    to_merge.append(r1)
                    del rects[i]
                    break
            else:
                # not merged with any, add to rects
                rects.append(r1)

    def add(self, r, accepted_error=0):
        idx = len(self.rects)
        idx -= self._split(r, accepted_error)
        self._merge(idx, accepted_error)
# RectSplitter
