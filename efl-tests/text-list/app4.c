#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>
#include <sys/time.h>
#include <math.h>
#include "e_box.h"
#include "key_monitor.h"

#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Text List Test"
#define WM_NAME "TextList"
#define WM_CLASS "main"

#define SELECTED_ITEM_OFFSET 1

/* same key within this interval is considered continuous press */
#define CONTINUOUS_KEYPRESS_INTERVAL 75000 /* microseconds */

/* delays less than this amount are considered 0 */
#define MINIMUM_SCROLL_DELAY 10 /* milliseconds */

#define F_PRECISION 0.00001


typedef struct app
{
    char *infile;
    char *theme;
    Evas_Object *edje_main;
    Evas_Object *e_box;
    Evas_Object *arrow_up;
    Evas_Object *arrow_down;
    Ecore_Evas  *ee;
    Evas *evas;
    Evas_List *items;
    int current;
    Evas_Object **evas_items;
    int n_evas_items;
    int item_height;
    int box_y;
    int box_x;
    int y_max;
    int y_min;
    struct {
        Ecore_Animator *anim;
        enum {
            SCROLL_UP = -1,
            SCROLL_NONE = 0,
            SCROLL_DOWN = 1
        } dir;
        double y;
        struct timeval t0;
        int y0;
        double v0;
        double accel;
        enum {
            STOP_NONE = 0,
            STOP_INIT = 1,
            STOP_CHECK = 2
        } stop;
        int t1;
        double abs_v0;
        double abs_accel;
    } scroll;
    struct {
        key_monitor_t down;
        key_monitor_t up;
    } keys;
} app_t;

static inline unsigned long
tv2ms(const struct timeval *tv)
{
    return tv->tv_sec * 1000 + tv->tv_usec / 1000;
}

static inline int
eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
}

static inline void
_add_item(app_t *app, const char *txt)
{
    app->items = evas_list_append(app->items, strdup(txt));
}

static void
_populate(app_t *app)
{
    FILE *fp;
    char *line;
    unsigned n;

    if (app->infile) {
        fp = fopen(app->infile, "r");
        if (fp == NULL) {
            fprintf(stderr, "Could not open file for reading \"%s\": %s\n",
                    app->infile, strerror(errno));
            return;
        }
    } else {
        fprintf(stderr, "No input file provided, reading from stdin.\n");
        fp = stdin;
    }


    line = malloc(128);
    n = 128;

    while (!feof(fp)) {
        int i;

        i = getline(&line, &n, fp);
        if (i < 0)
            break;
        else if (i == 0)
            continue;

        line[i - 1] = '\0';

        _add_item(app, line);
    }

    free(line);

    if (fp != stdin)
        fclose(fp);
}

static Evas_Object *
_new_list_item(app_t *app, const char *text)
{
    Evas_Object *obj;

    obj = edje_object_add(app->evas);
    edje_object_file_set(obj, app->theme, "list_item");
    edje_object_part_text_set(obj, "label", text);

    return obj;
}

static void mouse_down_arrow_up(void *d, Evas *e, Evas_Object *obj, void *event_info);
static void mouse_up_arrow_up(void *d, Evas *e, Evas_Object *obj, void *event_info);
static void mouse_down_arrow_down(void *d, Evas *e, Evas_Object *obj, void *event_info);
static void mouse_up_arrow_down(void *d, Evas *e, Evas_Object *obj, void *event_info);

static void
destroy_gui_list(app_t *app)
{
    if (!app->evas_items)
        return;

    e_box_freeze(app->e_box);
    while (app->n_evas_items > 0) {
        Evas_Object *obj;

        app->n_evas_items--;

        obj = app->evas_items[app->n_evas_items];

        e_box_unpack(obj);
        evas_object_del(obj);
    }
    e_box_thaw(app->e_box);

    free(app->evas_items);
    app->evas_items = NULL;

    evas_object_event_callback_del(app->arrow_up,
                                   EVAS_CALLBACK_MOUSE_DOWN,
                                   mouse_down_arrow_up);
    evas_object_event_callback_del(app->arrow_up,
                                   EVAS_CALLBACK_MOUSE_UP,
                                   mouse_up_arrow_up);

    evas_object_event_callback_del(app->arrow_down,
                                   EVAS_CALLBACK_MOUSE_DOWN,
                                   mouse_down_arrow_down);
    evas_object_event_callback_del(app->arrow_down,
                                   EVAS_CALLBACK_MOUSE_UP,
                                   mouse_up_arrow_down);
}

static void
dim_arrows(app_t *app)
{
    double p;
    int c;

    p = ((float)(app->current + 1)) / ((float)app->n_evas_items);
    c = 255 * p;
    if (c > 255)
        c = 255;
    if (c < 0)
        c = 0;
    evas_object_color_set(app->arrow_up, c, c, c, c);

    p = (float)app->current / ((float)app->n_evas_items);
    c = 255 * (1.0 - p);
    if (c > 255)
        c = 255;
    if (c < 0)
        c = 0;
    evas_object_color_set(app->arrow_down, c, c, c, c);
}

static inline int
item_pos(app_t *app, int idx)
{
    return app->item_height * (idx - SELECTED_ITEM_OFFSET);
}

static inline int
item_at_pos(app_t *app, int y)
{
    int idx, p;

    idx = y / app->item_height + SELECTED_ITEM_OFFSET;
    p = item_pos(app, idx);

    if (app->scroll.dir == SCROLL_DOWN && p < y)
        idx++;

    if (app->scroll.dir == SCROLL_UP && p > y)
        idx--;

    if (idx < 0)
        idx = 0;

    if (idx > app->n_evas_items - 1)
        idx = app->n_evas_items - 1;

    return idx;
}

static void
select_item(app_t *app,
            int index)
{
    int y;

    if (index < 0 || index >= app->n_evas_items)
        return;

    app->current = index;
    dim_arrows(app);

    y = item_pos(app, index);
    app->scroll.y = y;
    fprintf(stderr, "selected %d at y=%d\n", index, y);

    evas_object_move(app->e_box, app->box_x, app->box_y - y);
}

static void
scroll_end(app_t *app)
{
    app->scroll.v0 = 0;
    app->scroll.accel = 0;
    app->scroll.dir = SCROLL_NONE;
    app->scroll.anim = NULL;
    app->scroll.stop = STOP_NONE;
}

static inline void
setup_fix_scroll_stop(app_t *app, int y, const struct timeval now, int t)
{
    int y1, idx;

    if (app->scroll.stop != STOP_INIT) {
        fprintf(stderr,
                "setup_fix_scroll_stop: scroll.stop != STOP_INIT, %d\n",
                app->scroll.stop);
        return;
    }

    app->scroll.stop = STOP_CHECK;

    app->scroll.v0 += app->scroll.accel * t;
    app->scroll.t0 = now;
    app->scroll.y0 = y;

    idx = app->current;
    if (app->scroll.dir == SCROLL_DOWN)
        do {
            y1 = item_pos(app, idx);
            idx++;
        } while (y1 <= y);
    else
        do {
            y1 = item_pos(app, idx);
            idx--;
        } while (y1 >= y);

    if (y1 < app->y_min)
        y1 = app->y_min;

    if (y1 > app->y_max)
        y1 = app->y_max;

    if (y1 == y)
        scroll_end(app);
    else
        app->scroll.accel = - app->scroll.v0 * app->scroll.v0 / (2 * (y1 - y));
}

static int
scroll(void *data)
{
    app_t *app = (app_t *)data;
    struct timeval now, dif;
    int t, r, idx;
    double y, v;

    if (fabs(app->scroll.accel) < F_PRECISION) {
        scroll_end(app);
        return 0;
    }

    gettimeofday(&now, NULL);
    timersub(&now, &app->scroll.t0, &dif);
    t = tv2ms(&dif);

    v = app->scroll.v0 + app->scroll.accel * t;
    y = app->scroll.y0 + app->scroll.v0 * t + app->scroll.accel * t * t / 2;

    /* bounds checking */
    if (y < app->y_min) {
        y = app->y_min;
        r = 0;
    } else if (y > app->y_max) {
        y = app->y_max;
        r = 0;
    } else
        r = 1;

    /* check current item */
    idx = item_at_pos(app, y);
    if (idx != app->current) {
        app->current = idx;
        dim_arrows(app);
    }

    switch (app->scroll.stop) {
    case STOP_NONE:
        break;
    case STOP_INIT:
        setup_fix_scroll_stop(app, y, now, t);
        break;
    case STOP_CHECK:
        if (app->scroll.dir * v < F_PRECISION) {
            y = item_pos(app, app->current);
            r = 0;
        }
        break;
    }

    app->scroll.y = y;
    evas_object_move(app->e_box, app->box_x, app->box_y - (int)y);

    //printf("stop=%d, current=%d, dir=%d, y=%+3.3f, v=%+2.5f, a=%+2.5f\n", app->scroll.stop, app->current, app->scroll.dir, y, v, app->scroll.accel);

    if (r == 0)
        scroll_end(app);

    return r;
}

static void
scroll_start(app_t *app, int dir)
{
    app->scroll.dir = dir;

    gettimeofday(&app->scroll.t0, NULL);
    app->scroll.y0 = app->scroll.y;
    app->scroll.v0 = dir * app->scroll.abs_v0;
    app->scroll.accel = dir * app->scroll.abs_accel;
    app->scroll.stop = STOP_NONE;

    if (!app->scroll.anim)
        app->scroll.anim = ecore_animator_add(scroll, app);
}

static void
scroll_stop(app_t *app, int dir)
{
    if (app->scroll.dir == dir)
        app->scroll.stop = STOP_INIT;
}

static void
setup_gui_list(app_t *app)
{
    Evas_Object *obj;
    Evas_List *itr;
    int item_w, item_h, box_w, box_h, i, n_items;

    destroy_gui_list(app);

    obj = _new_list_item(app, NULL);
    edje_object_size_min_calc(obj, &item_w, &item_h);
    evas_object_del(obj);
    app->item_height = item_h;

    e_box_freeze(app->e_box);
    evas_object_geometry_get(app->e_box,
                             &app->box_x, &app->box_y,
                             &box_w, &box_h);

    n_items = evas_list_count(app->items);

    app->y_min = -SELECTED_ITEM_OFFSET * item_h;
    app->y_max = (n_items - SELECTED_ITEM_OFFSET - 1) * item_h;

    app->n_evas_items = n_items;
    app->evas_items = malloc(n_items * sizeof(Evas_Object *));
    itr = app->items;

    for (i = 0; i < n_items; i++, itr = evas_list_next(itr)) {
        Evas_Object *obj;

        obj = _new_list_item(app, evas_list_data(itr));
        app->evas_items[i] = obj;
        e_box_pack_end(app->e_box, obj);
        edje_object_size_min_calc(obj, &item_w, &item_h);
        e_box_pack_options_set(obj, 1, 1, 1, 0, 0.0, 0.5,
                               item_w, item_h, 9999, item_h);
        evas_object_show(obj);
    }

    e_box_align_set(app->e_box, 0.0, 1.0);

    app->arrow_down = edje_object_part_object_get(app->edje_main,
                                                  "arrow_down");
    app->arrow_up = edje_object_part_object_get(app->edje_main,
                                                "arrow_up");

    select_item(app, 0);

    evas_object_event_callback_add(app->arrow_up,
                                   EVAS_CALLBACK_MOUSE_DOWN,
                                   mouse_down_arrow_up,
                                   app);
    evas_object_event_callback_add(app->arrow_up,
                                   EVAS_CALLBACK_MOUSE_UP,
                                   mouse_up_arrow_up,
                                   app);

    evas_object_event_callback_add(app->arrow_down,
                                   EVAS_CALLBACK_MOUSE_DOWN,
                                   mouse_down_arrow_down,
                                   app);
    evas_object_event_callback_add(app->arrow_down,
                                   EVAS_CALLBACK_MOUSE_UP,
                                   mouse_up_arrow_down,
                                   app);

    e_box_thaw(app->e_box);
}

static void
key_down(void *data, Evas *e, Evas_Object *obj, void *event_info)
{
    Evas_Event_Key_Down *ev;
    app_t *app;
    const char *k;

    ev = (Evas_Event_Key_Down *)event_info;
    app = (app_t *)data;

    k = ev->keyname;

    if (eq(k, "Down"))
        key_monitor_down(&app->keys.down);
    else if (eq(k, "Up"))
        key_monitor_down(&app->keys.up);
    else if (eq(k, "Escape"))
        ecore_main_loop_quit();
    else if (eq(k, "f") || eq(k, "F6")) {
        if (ecore_evas_fullscreen_get(app->ee)) {
            ecore_evas_fullscreen_set(app->ee, 0);
            ecore_evas_cursor_set(app->ee, NULL, 0, 0, 0);
        } else {
            ecore_evas_fullscreen_set(app->ee, 1);
            ecore_evas_cursor_set(app->ee, " ", 999, 0, 0);
        }
    }
}

static void
key_up(void *data, Evas *e, Evas_Object *obj, void *event_info)
{
    Evas_Event_Key_Up *ev;
    app_t *app;
    const char *k;

    ev = (Evas_Event_Key_Up *)event_info;
    app = (app_t *)data;

    k = ev->keyname;

    if (eq(k, "Down"))
        key_monitor_up(&app->keys.down);
    else if (eq(k, "Up"))
        key_monitor_up(&app->keys.up);
}

static void
move_up_start(void *d)
{
    app_t *app = (app_t *)d;

    if (app->current < 1)
        return;

    scroll_start(app, SCROLL_UP);
    fprintf(stderr, "mouse_up_start at %d\n", app->current);
}

static void
move_up_stop(void *d)
{
    app_t *app = (app_t *)d;

    scroll_stop(app, SCROLL_UP);
    fprintf(stderr, "mouse_up_stop at %d\n", app->current);
}

static void
key_up_start(void *d, key_monitor_t *m)
{
    move_up_start(d);
}

static void
key_up_stop(void *d, key_monitor_t *m)
{
    move_up_stop(d);
}

static void
mouse_down_arrow_up(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    move_up_start(d);
}

static void
mouse_up_arrow_up(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    move_up_stop(d);
}

static void
move_down_start(void *d)
{
    app_t *app = (app_t *)d;

    if (app->current + 1 >= app->n_evas_items)
        return;

    scroll_start(app, SCROLL_DOWN);
    fprintf(stderr, "mouse_up_start at %d\n", app->current);
}

static void
move_down_stop(void *d)
{
    app_t *app = (app_t *)d;

    scroll_stop(app, SCROLL_DOWN);
    fprintf(stderr, "mouse_down_stop at %d\n", app->current);
}

static void
key_down_start(void *d, key_monitor_t *m)
{
    move_down_start(d);
}

static void
key_down_stop(void *d, key_monitor_t *m)
{
    move_down_stop(d);
}

static void
mouse_down_arrow_down(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    move_down_start(d);
}

static void
mouse_up_arrow_down(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    move_down_stop(d);
}

static void
mouse_down_back_button(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    ecore_main_loop_quit();
}

static int
app_signal_exit(void *data, int type, void *event)
{

    ecore_main_loop_quit();
    return 1;
}

static void
resize_cb(Ecore_Evas *ee)
{
    app_t *app;
    Evas_Coord w, h;

    app = ecore_evas_data_get(ee, "app");
    evas_output_viewport_get(app->evas, NULL, NULL, &w, &h);
    evas_object_resize(app->edje_main, w, h);
    setup_gui_list(app);
}

int
main(int argc, char *argv[])
{
    app_t app;
    int i;
    Evas_Object *o;

    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();
    edje_init();

    edje_frametime_set(1.0 / 30.0);

    memset(&app, 0, sizeof(app));

    app.ee = ecore_evas_software_x11_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
    ecore_evas_data_set(app.ee, "app", &app);
    ecore_evas_title_set(app.ee, TITLE);
    ecore_evas_name_class_set(app.ee, WM_NAME, WM_CLASS);
    app.theme = THEME;

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            ecore_evas_fullscreen_set(app.ee, 1);
        else if (strncmp (argv[i], "-theme=", sizeof("-theme=") - 1) == 0)
            app.theme = argv[i] + sizeof("-theme=") - 1;
        else if (argv[i][0] != '-')
            app.infile = argv[i];

    app.evas = ecore_evas_get(app.ee);

    app.edje_main = edje_object_add(app.evas);
    evas_data_attach_set(app.evas, &app);
    if (!edje_object_file_set(app.edje_main, app.theme, THEME_GROUP)) {
        fprintf(stderr, "Failed to load file \"%s\", part \"%s\".\n",
                app.theme, THEME_GROUP);
        return 1;
    }


    evas_object_move(app.edje_main, 0, 0);
    evas_object_resize(app.edje_main, WIDTH, HEIGHT);

    app.e_box = e_box_add(app.evas);
    e_box_orientation_set(app.e_box, 0);
    e_box_homogenous_set(app.e_box, 0);
    e_box_align_set(app.e_box, 0.0, 0.5);

    edje_object_part_swallow(app.edje_main, "contents_swallow", app.e_box);

    evas_object_show(app.edje_main);
    evas_object_show(app.e_box);
    ecore_evas_show(app.ee);

    _populate(&app);
    app.scroll.abs_v0 = 0.2;
    app.scroll.abs_accel = 0.0001;
    setup_gui_list(&app);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(app.ee, resize_cb);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);
    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_UP,
                                   key_up, &app);

    key_monitor_setup(&app.keys.down, key_down_start, key_down_stop, &app);
    key_monitor_setup(&app.keys.up, key_up_start, key_up_stop, &app);

    evas_object_focus_set(app.edje_main, 1);

    o = edje_object_part_object_get(app.edje_main, "back_button");
    evas_object_event_callback_add(o, EVAS_CALLBACK_MOUSE_DOWN,
                                   mouse_down_back_button,
                                   &app);

    ecore_main_loop_begin();

    return 0;
}
