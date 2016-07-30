#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>
#include <sys/time.h>
#include "e_box.h"

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
    Ecore_Animator *mouse_down_anim;
    struct {
        Ecore_Animator *anim;
        unsigned long initial_delay_ms;
        unsigned accel_ms; /* (delay_ms * accel_ms) / 1000 */
        int dir;
        struct timeval first;
        struct timeval last;
        struct timeval start;
        unsigned long delay_ms;
        void (*stop_cb)(void *data);
    } scroll;
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

static void
select_item(app_t *app,
            int index)
{
    int y;

    if (index < 0 || index >= app->n_evas_items)
        return;

    app->current = index;
    dim_arrows(app);

    y = app->item_height * (index - SELECTED_ITEM_OFFSET);

    evas_object_move(app->e_box, app->box_x, app->box_y - y);
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
scroll_ended(app_t *app)
{
    select_item(app, app->current);
}

static int
scroll(void *data)
{
    app_t *app = data;
    struct timeval dif;
    unsigned long current_ms;
    double amount;
    int y;

    gettimeofday(&app->scroll.last, NULL);
    timersub(&app->scroll.last, &app->scroll.start, &dif);

    current_ms = tv2ms(&dif);

    if (current_ms >= app->scroll.delay_ms) {
        scroll_ended(app);
        app->scroll.anim = NULL;
        return 0;
    }

    amount = app->scroll.dir * ((double)current_ms / app->scroll.delay_ms - 1);
    y = app->item_height * (app->current - SELECTED_ITEM_OFFSET - amount);

    evas_object_move(app->e_box, app->box_x, app->box_y - y);

    return 1;
}

static void
scroll_reset(app_t *app, const struct timeval *p_now, int dir)
{
    app->scroll.dir = dir;
    app->scroll.first = *p_now;
    app->scroll.delay_ms = app->scroll.initial_delay_ms;
}

static void
scroll_init(app_t *app, const struct timeval *p_now, int dir)
{
    if (app->scroll.dir != dir)
        scroll_reset(app, p_now, dir);
    else {
        struct timeval dif;

        /* was already 'dir', check if to consider "continuous" press */
        timersub(p_now, &app->scroll.last, &dif);

        if (dif.tv_sec > 0 || dif.tv_usec > CONTINUOUS_KEYPRESS_INTERVAL)
            scroll_reset(app, p_now, dir);
        else {
            long ms;

            /* still pressing 'dir', accelerate */
            ms = (app->scroll.delay_ms * app->scroll.accel_ms) / 1000;
            if (ms >= 0)
                app->scroll.delay_ms = ms;
        }
    }
}

static void
scroll_setup(app_t *app, int dir)
{
    gettimeofday(&app->scroll.start, NULL);

    scroll_init(app, &app->scroll.start, dir);

    if (app->scroll.delay_ms < MINIMUM_SCROLL_DELAY) {
        app->scroll.last = app->scroll.start;
        scroll_ended(app);
        return;
    }

    app->scroll.anim = ecore_animator_add(scroll, app);
}

static void
move_down(app_t *app)
{
    if (app->current + 1 >= app->n_evas_items || app->scroll.anim)
        return;

    app->current++;
    scroll_setup(app, -1);
}

static void
move_up(app_t *app)
{
    if (app->current < 1 || app->scroll.anim)
        return;

    app->current--;
    scroll_setup(app, 1);
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
        move_down(app);
    else if (eq(k, "Up"))
        move_up(app);
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

static int
do_move_up(void *data)
{
    app_t *app = data;

    move_up(app);
    return 1;
}

static void
mouse_down_arrow_up(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    app_t *app = d;

    if (app->mouse_down_anim)
        ecore_animator_del(app->mouse_down_anim);

    app->mouse_down_anim = ecore_animator_add(do_move_up, app);
    move_up(app);
}

static void
mouse_up_arrow_up(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    app_t *app = d;

    if (app->mouse_down_anim)
        ecore_animator_del(app->mouse_down_anim);

    app->mouse_down_anim = NULL;
}

static int
do_move_down(void *data)
{
    app_t *app = data;

    move_down(app);
    return 1;
}

static void
mouse_down_arrow_down(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    app_t *app = d;

    if (app->mouse_down_anim)
        ecore_animator_del(app->mouse_down_anim);

    app->mouse_down_anim = ecore_animator_add(do_move_down, app);
    move_down(app);
}

static void
mouse_up_arrow_down(void *d, Evas *e, Evas_Object *obj, void *event_info)
{
    app_t *app = d;

    if (app->mouse_down_anim)
        ecore_animator_del(app->mouse_down_anim);

    app->mouse_down_anim = NULL;
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
    app.scroll.initial_delay_ms = 750;
    app.scroll.accel_ms = 600;
    setup_gui_list(&app);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(app.ee, resize_cb);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);

    evas_object_focus_set(app.edje_main, 1);

    o = edje_object_part_object_get(app.edje_main, "back_button");
    evas_object_event_callback_add(o, EVAS_CALLBACK_MOUSE_DOWN,
                                   mouse_down_back_button,
                                   &app);

    ecore_main_loop_begin();

    return 0;
}
