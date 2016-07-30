#include "rect_splitter.h"
#include <stdio.h>
#include <stdlib.h>
#include <SDL.h>

static const int no_wait = 0;
static const int no_draw = 0;

static void
wait(void)
{
    if (no_wait || no_draw)
        return;

    while (1) {
        SDL_Event ev;

        SDL_WaitEvent(&ev);
        switch (ev.type) {
        case SDL_QUIT:
            exit(0);
            break;
        case SDL_KEYDOWN:
            return;
        default:
            break;
        }
    }
}

struct test_case {
    char *name;
    int n_rects;
    SDL_Rect rects[64];
};
static struct test_case test_cases[] = {
    {.name = "side-by-side-horizontal",
     .n_rects = 2,
     .rects = {{0, 0, 100, 100}, {100, 0, 100, 100}}},
    {.name = "side-by-side-vertical",
     .n_rects = 2,
     .rects = {{0, 0, 100, 100}, {0, 100, 100, 100}}},
    {.name = "contained",
     .n_rects = 2,
     .rects = {{0, 0, 100, 100}, {25, 25, 50, 50}}},
    {.name = "contains",
     .n_rects = 2,
     .rects = {{25, 25, 50, 50}, {0, 0, 100, 100}}},
    {.name = "horizontal",
     .n_rects = 2,
     .rects = {{0, 0, 100, 100}, {50, 0, 100, 100}}},
    {.name = "vertical",
     .n_rects = 2,
     .rects = {{0, 0, 100, 100}, {0, 50, 100, 100}}},
    {.name = "rotative_hole_1",
     .n_rects = 4,
     .rects = {{0, 0, 300, 100}, {200, 0, 100, 300},
               {0, 200, 300, 100}, {0, 0, 100, 300}}},
    {.name = "rotative_hole_2",
     .n_rects = 4,
     .rects = {{0, 0, 30, 10}, {20, 0, 10, 30},
               {0, 20, 30, 10}, {0, 0, 10, 30}}},
    {.name = "rotative_fill_1",
     .n_rects = 5,
     .rects = {{0, 0, 300, 100}, {200, 0, 100, 300},
               {0, 200, 300, 100}, {0, 0, 100, 300}, {100, 100, 100, 100}}},
    {.name = "rotative_fill_2",
     .n_rects = 5,
     .rects = {{0, 0, 30, 10}, {20, 0, 10, 30},
               {0, 20, 30, 10}, {0, 0, 10, 30}, {10, 10, 10, 10}}},
    {.name = "T_1",
     .n_rects = 2,
     .rects = {{0, 50, 150, 50}, {100, 0, 100, 150}}},
    {.name = "T_2",
     .n_rects = 2,
     .rects = {{100, 0, 100, 150}, {0, 50, 150, 50}}},
    {.name = "T_3",
     .n_rects = 2,
     .rects = {{50, 0, 50, 150}, {0, 100, 150, 100}}},
    {.name = "T_4",
     .n_rects = 2,
     .rects = {{0, 100, 150, 100}, {50, 0, 50, 150}}},
    {.name = "cascade-no-merge_1",
     .n_rects = 3,
     .rects = {{0, 0, 100, 100}, {50, 50, 100, 100}, {100, 100, 100, 100}}},
    {.name = "cascade-no-merge_2",
     .n_rects = 3,
     .rects = {{100, 100, 100, 100}, {50, 50, 100, 100}, {0, 0, 100, 100}}},
    {.name = "cascade-no-merge_3",
     .n_rects = 3,
     .rects = {{50, 50, 100, 100}, {100, 100, 100, 100}, {0, 0, 100, 100}}},
    {.name = "cascade-no-merge_4",
     .n_rects = 3,
     .rects = {{50, 50, 100, 100}, {0, 0, 100, 100}, {100, 100, 100, 100}}},
    {.name = "cascade-merge_1",
     .n_rects = 3,
     .rects = {{0, 0, 100, 100}, {4, 4, 100, 100}, {8, 8, 100, 100}}},
    {.name = "cascade-merge_2",
     .n_rects = 3,
     .rects = {{8, 8, 100, 100}, {4, 4, 100, 100}, {0, 0, 100, 100}}},
    {.name = "cascade-merge_3",
     .n_rects = 3,
     .rects = {{4, 4, 100, 100}, {8, 8, 100, 100}, {0, 0, 100, 100}}},
    {.name = "cascade-merge_4",
     .n_rects = 3,
     .rects = {{4, 4, 100, 100}, {0, 0, 100, 100}, {8, 8, 100, 100}}},
    {.name = "cross-all-fat_1",
     .n_rects = 3,
     .rects = {{50, 0, 50, 150}, {0, 50, 150, 50}}},
    {.name = "cross-all-fat_2",
     .n_rects = 2,
     .rects = {{0, 50, 150, 50}, {50, 0, 50, 150}}},
    {.name = "cross-all-thin_1",
     .n_rects = 2,
     .rects = {{50, 0, 4, 150}, {0, 50, 150, 4}}},
    {.name = "cross-all-thin_2",
     .n_rects = 2,
     .rects = {{0, 50, 150, 4}, {50, 0, 4, 150}}},
    {.name = "cross-horiz-fat-vert-thin_1",
     .n_rects = 2,
     .rects = {{50, 0, 4, 150}, {0, 50, 150, 50}}},
    {.name = "cross-horiz-fat-vert-thin_2",
     .n_rects = 2,
     .rects = {{0, 50, 150, 50}, {50, 0, 4, 150}}},
    {.name = "cross-horiz-thin-vert-fat_1",
     .n_rects = 2,
     .rects = {{50, 0, 50, 150}, {0, 50, 150, 4}}},
    {.name = "cross-horiz-thin-vert-fat_2",
     .n_rects = 2,
     .rects = {{0, 50, 150, 4}, {50, 0, 50, 150}}},
    {.name = "checker-big",
     .n_rects = 5,
     .rects = {{0, 0, 50, 50}, {100, 0, 50, 50},
               {50, 50, 50, 50}, {0, 100, 50, 50}, {100, 100, 50, 50}}},
    {.name = "checker-small",
     .n_rects = 5,
     .rects = {{0, 0, 5, 5}, {10, 0, 5, 5},
               {5, 5, 5, 5}, {0, 10, 5, 5}, {10, 10, 5, 5}}},
    {.name = "snake_1",
     .n_rects = 7,
     .rects = {{0, 0, 50, 50}, {3, 3, 50, 50}, {6, 6, 50, 50},
               {9, 9, 50, 50}, {6, 12, 50, 50}, {3, 15, 50, 50},
               {0, 18, 50, 50}}},
    {.name = "snake_2",
     .n_rects = 7,
     .rects = {{0, 18, 50, 50}, {3, 15, 50, 50}, {6, 12, 50, 50},
               {9, 9, 50, 50}, {6, 6, 50, 50}, {3, 3, 50, 50},
               {0, 0, 50, 50}}},
    {.name = "snake_3",
     .n_rects = 7,
     .rects = {{9, 9, 50, 50}, {0, 18, 50, 50}, {3, 15, 50, 50},
               {6, 12, 50, 50}, {6, 6, 50, 50}, {3, 3, 50, 50},
               {0, 0, 50, 50}}},
    {.name = "snake_4",
     .n_rects = 7,
     .rects = {{9, 9, 50, 50}, {0, 18, 50, 50}, {3, 15, 50, 50},
               {6, 12, 50, 50}, {6, 6, 50, 50}, {3, 3, 50, 50},
               {0, 0, 50, 50}}},
    {.name = NULL, .n_rects = 0}
};



#define RGBA(r, g, b, a)                                                \
    (((r) << 24) | ((g) << 16) | ((b) << 8) | (a))
#define N_COLORS 12
static const Uint32 color[N_COLORS] = {
    RGBA(255, 0, 0, 100),
    RGBA(0, 255, 0, 100),
    RGBA(0, 0, 255, 100),
    RGBA(255, 255, 0, 100),
    RGBA(255, 0, 255, 100),
    RGBA(0, 255, 255, 100),
    RGBA(255, 100, 100, 100),
    RGBA(100, 255, 100, 100),
    RGBA(100, 100, 255, 100),
    RGBA(255, 255, 100, 100),
    RGBA(255, 100, 255, 100),
    RGBA(100, 255, 255, 100)
};
static const Uint32 color_black = RGBA(0, 0, 0, 255);

static void
draw_rect(SDL_Surface *screen, const rect_t r, Uint32 color, int dx, int dy)
{
    SDL_Rect rect;
    SDL_Surface *surf;

    if (no_draw)
        return;

    surf = SDL_CreateRGBSurface(SDL_SRCALPHA, r.width, r.height, 32,
                                0xff << 24, 0xff << 16, 0xff << 8, 0xff);

    rect.x = 1;
    rect.y = 1;
    rect.w = r.width - 2;
    rect.h = r.height - 2;
    SDL_FillRect(surf, &rect, color);

    rect.x = 0;
    rect.y = 0;
    rect.w = r.width;
    rect.h = 1;
    SDL_FillRect(surf, &rect, color_black);
    rect.y = r.height - 1;
    SDL_FillRect(surf, &rect, color_black);

    rect.x = 0;
    rect.y = 1;
    rect.w = 1;
    rect.h = r.height - 2;
    SDL_FillRect(surf, &rect, color_black);
    rect.x = r.width - 1;
    SDL_FillRect(surf, &rect, color_black);

    rect.x = r.left + dx;
    rect.y = r.top + dy;
    rect.w = r.width;
    rect.h = r.height;
    SDL_BlitSurface(surf, NULL, screen, &rect);

    SDL_FreeSurface(surf);
}

static void
clear(SDL_Surface *screen, SDL_Rect *r)
{
    if (no_draw)
        return;

    SDL_FillRect(screen, r, 0xffffffff);
}

static void
update(SDL_Surface *screen)
{
    if (no_draw)
        return;

    SDL_Flip(screen);
}

static rect_t
rect_from_sdl(const SDL_Rect sdl_rect)
{
    rect_t r;

    rect_init(&r, sdl_rect.x, sdl_rect.y, sdl_rect.w, sdl_rect.h);
    return r;
}

static void
test_case_draw_original(SDL_Surface *screen, const struct test_case *test_case,
                        int dx, int dy, int *max_x, int *max_y)
{
    int i;

    SDL_WM_SetCaption(test_case->name, NULL);

    *max_x = 0;
    *max_y = 0;
    for (i = 0; i < test_case->n_rects; i++) {
        rect_t r;

        r = rect_from_sdl(test_case->rects[i]);
        draw_rect(screen, r, color[i % N_COLORS], dx, dy);
        if (*max_x < r.right)
            *max_x = r.right;
        if (*max_y < r.bottom)
            *max_y = r.bottom;
    }
}

static void
rect_list_draw(SDL_Surface *screen, const list_t rects, int dx, int dy,
               int pause)
{
    list_node_t *node;
    int i;

    for (i = 0, node = rects.head; node != NULL; i++, node = node->next) {
        rect_t r;

        r = ((rect_node_t *)node)->rect;
        draw_rect(screen, r, color[i % N_COLORS], dx, dy);
        if (pause) {
            update(screen);
            wait();
        }
    }
    if (!pause)
        update(screen);
}

static void
test_case_draw_area(SDL_Surface *screen, const struct test_case *test_case,
                    SDL_Rect *area)
{
    int i;

    for (i = 0; i < test_case->n_rects; i++) {
        rect_t r;

        r = rect_from_sdl(test_case->rects[i]);
        draw_rect(screen, r, RGBA(0, 0, 0, 20), area->x, area->y);
    }
}

static void
rect_list_check_consistent(const list_t rects)
{
    const rect_node_t *p;
    int failed;

    failed = 0;

    for (p = (const rect_node_t *)rects.head; p != NULL;
         p = (const rect_node_t *)p->_lst.next) {
        int f;

        f = 0;
        if (p->rect.area != p->rect.width * p->rect.height) {
            fprintf(stderr,
                    ">>> inconsistent rect: %p, area=%d, wxh=%dx%d (%d)\n",
                    p, p->rect.area, p->rect.width, p->rect.height,
                    p->rect.width * p->rect.height);
            f++;
        }

        if (p->rect.right != p->rect.left + p->rect.width) {
            fprintf(stderr,
                    ">>> inconsistent rect: %p, right=%d, left+width=%d + %d "
                    "(%d)\n",
                    p, p->rect.right, p->rect.left, p->rect.width,
                    p->rect.left * p->rect.width);
            f++;
        }

        if (p->rect.bottom != p->rect.top + p->rect.height) {
            fprintf(stderr,
                    ">>> inconsistent rect: %p, bottom=%d, top+height=%d + %d "
                    "(%d)\n",
                    p, p->rect.bottom, p->rect.top, p->rect.height,
                    p->rect.top * p->rect.height);
            f++;
        }
        if (f) {
            fprintf(stderr, "!!!!!! Failed %d tests\n\n", f);
            failed++;
        }
    }

    if (failed) {
        fprintf(stderr, "%d failures\n", failed);
        exit(1);
    }
}

static void
test_case_process_and_draw(SDL_Surface *screen,
                           const struct test_case *test_case, SDL_Rect *area)
{
    list_t non_overlaps = {.head = NULL, .tail = NULL};
    int i;

    printf("test: %s\n", test_case->name);

    for (i = 0; i < test_case->n_rects; i++) {
        char title[128];
        rect_t r;
        rect_node_t *rn;

        r = rect_from_sdl(test_case->rects[i]);

        rn = malloc(sizeof(rect_node_t));
        rn->_lst.next = NULL;
        rn->rect = r;

        printf("ADD: ");
        rect_print(rn->rect);
        putchar('\n');

#define ACCEPTED_SPLIT_ERROR 300
#define ACCEPTED_MERGE_ERROR 300
#define TEST_SPLIT_AND_MERGE 1
//#define TEST_SPLIT_FUZZY 1
//#define TEST_MERGE
#if defined(TEST_SPLIT_STRICT)
        rect_list_add_split_strict(&non_overlaps, (list_node_t *)rn);
#elif defined(TEST_SPLIT_FUZZY)
        list_node_t *n;
        n = rect_list_add_split_fuzzy(&non_overlaps, (list_node_t *)rn,
                                      ACCEPTED_SPLIT_ERROR);
        rect_list_check_consistent(non_overlaps);

#if defined(TEST_MERGE)
        if (n && n->next) {
            list_t to_merge;

            to_merge.head = n->next;
            to_merge.tail = non_overlaps.tail;
            non_overlaps.tail = n;
            n->next = NULL;

            printf("\n>>>> RECTS:\n");
            rect_list_print(non_overlaps);
            printf(">>>> TO MERGE:\n");
            rect_list_print(to_merge);
            printf("\n");

            rect_list_merge_rects(&non_overlaps, &to_merge,
                                  ACCEPTED_MERGE_ERROR);
            rect_list_check_consistent(non_overlaps);
        }
#endif /* TEST_MERGE */
#elif defined(TEST_SPLIT_AND_MERGE)
        rect_list_add_split_fuzzy_and_merge(&non_overlaps, (list_node_t *)rn,
                                            ACCEPTED_SPLIT_ERROR,
                                            ACCEPTED_MERGE_ERROR);
        rect_list_check_consistent(non_overlaps);
#endif

        snprintf(title, sizeof(title),
                 "test: %s, add %d,%d+%dx%d, HIT ENTER...",
                 test_case->name, r.left, r.top, r.width, r.height);
        SDL_WM_SetCaption(title, NULL);

        rect_list_print(non_overlaps);
        rect_list_draw(screen, non_overlaps, area->x, area->y, 0);
        wait();
        clear(screen, area);
    }

    test_case_draw_area(screen, test_case, area);
    wait();
    rect_list_draw(screen, non_overlaps, area->x, area->y, 1);

    rect_list_clear(&non_overlaps);
}

#define MARGIN_LEFT 100
#define MARGIN_TOP 50
#define SCREEN_WIDTH 800
#define SCREEN_HEIGHT 480
int
main(int argc, char *argv[])
{
    SDL_Surface *screen;
    struct test_case *itr;

    SDL_Init(SDL_INIT_VIDEO|SDL_INIT_NOPARACHUTE);
    atexit(SDL_Quit);

    screen = SDL_SetVideoMode(SCREEN_WIDTH, SCREEN_HEIGHT, 16, 0);
    if (!screen) {
        fprintf(stderr, "could not init SDL\n");
        return 1;
    }

    for (itr = test_cases; itr->name != NULL; itr++) {
        SDL_Rect rect;
        int max_x, max_y;

        clear(screen, NULL);
        test_case_draw_original(screen, itr, MARGIN_LEFT, MARGIN_TOP,
                                &max_x, &max_y);
        update(screen);

        rect.x = SCREEN_WIDTH - MARGIN_LEFT - max_x;
        rect.y = MARGIN_TOP;
        rect.w = max_x;
        rect.h = max_y;

        test_case_process_and_draw(screen, itr, &rect);
    }

    return 0;
}
