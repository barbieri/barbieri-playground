#include <Ecore.h>
#include <Evas.h>
#include <Ecore_Evas.h>
#include <Edje.h>
#include <stdio.h>
#include <string.h>
#include "icon.h"

#define MIN_PADDING 5
#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Icon Viewer Test"
#define WM_NAME "IconViewer"
#define WM_CLASS "main"

typedef struct app
{
    char *theme;
    Evas_Object *edje_main;
    Ecore_Evas  *ee;
    Evas *evas;
    Evas_List *icons;
    Ecore_Animator *anim;
    double start_time;
    double max_time;
    int dir;
    int line_height;
    int last_y;
    int off_y;
} app_t;

static inline int
eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
}

static void
layout_items(app_t *app)
{
    Evas_List *itr;
    int iw, ih, ew, eh, x, y, padding, items_per_row;

    evas_object_geometry_get(app->icons->data, NULL, NULL, &iw, &ih);
    evas_object_geometry_get(app->edje_main, NULL, NULL, &ew, &eh);

    items_per_row = ew / iw;
    if (items_per_row < 1)
        return;

    do {
        padding = (ew - (iw * items_per_row)) / (items_per_row + 1);
        items_per_row--;
    } while (padding < items_per_row && items_per_row > 0);

    app->line_height = padding + ih;

    evas_event_freeze(app->evas);
    x = padding;
    y = app->off_y;

    for (itr = app->icons; itr != NULL; itr = itr->next) {
        Evas_Object *o;

        if (x + iw >= ew) {
            x = padding;
            y += padding + ih;
        }

        o = itr->data;
        evas_object_move(o, x, y);

        x += iw + padding;
    }
    evas_event_thaw(app->evas);
}

static void
move_icons(app_t *app, int y)
{
    Evas_List *itr;
    int oy;


    oy = y - app->last_y;

    evas_event_freeze(app->evas);
    for (itr = app->icons; itr != NULL; itr = itr->next) {
        Evas_Object *o = itr->data;
        int iy, ix;

        evas_object_geometry_get(o, &ix, &iy, NULL, NULL);
        iy += oy;
        evas_object_move(o, ix, iy);
    }
    evas_event_thaw(app->evas);

    app->off_y += oy;
    app->last_y = y;
}

static int
move_anim(void *d)
{
    app_t *app = (app_t *)d;
    double now;
    int y;

    now = ecore_time_get();

    if (now > app->start_time + app->max_time) {
        move_icons(app, app->dir * app->line_height);
        app->anim = NULL;
        return 0;
    }

    y = app->dir * app->line_height * (now - app->start_time) / app->max_time;
    move_icons(app, y);

    return 1;
}

static void
move_down(app_t *app)
{
    if (app->anim)
        return;

    app->start_time = ecore_time_get();
    app->dir = 1;
    app->last_y = 0;
    app->anim = ecore_animator_add(move_anim, app);
}

static void
move_up(app_t *app)
{
    if (app->anim)
        return;

    app->start_time = ecore_time_get();
    app->dir = -1;
    app->last_y = 0;
    app->anim = ecore_animator_add(move_anim, app);
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

    if (eq(k, "Escape"))
        ecore_main_loop_quit();
    else if (eq(k, "f") || eq(k, "F6")) {
        if (ecore_evas_fullscreen_get(app->ee)) {
            ecore_evas_fullscreen_set(app->ee, 0);
            ecore_evas_cursor_set(app->ee, NULL, 0, 0, 0);
        } else {
            ecore_evas_fullscreen_set(app->ee, 1);
            ecore_evas_cursor_set(app->ee, " ", 999, 0, 0);
        }
    } else if (eq(k, "Down"))
        move_down(app);
    else if (eq(k, "Up"))
        move_up(app);
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
    layout_items(app);
}

int
main(int argc, char *argv[])
{
    app_t app;
    int i;
    Evas_Hash *hash;

    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();
    edje_init();

    edje_frametime_set(1.0 / 20.0);

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

    app.evas = ecore_evas_get(app.ee);

    app.edje_main = edje_object_add(app.evas);

    hash = evas_hash_add(NULL, "edje_file", app.theme);
    evas_data_attach_set(app.evas, hash);
    if (!edje_object_file_set(app.edje_main, app.theme, THEME_GROUP)) {
        fprintf(stderr, "Failed to load file \"%s\", part \"%s\".\n",
                app.theme, THEME_GROUP);
        return 1;
    }

    evas_object_move(app.edje_main, 0, 0);
    evas_object_resize(app.edje_main, WIDTH, HEIGHT);

    evas_object_show(app.edje_main);
    ecore_evas_show(app.ee);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(app.ee, resize_cb);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);

    evas_object_focus_set(app.edje_main, 1);


    for (i=1; i < argc; i++)
        if (argv[i][0] != '-') {
            Evas_Object *o;
            const char *path;

            path = argv[i];

            o = icon_new(app.evas);
            icon_text_set(o, path);
            icon_image_set(o, path);
            evas_object_show(o);

            app.icons = evas_list_append(app.icons, o);
        }

    if (!app.icons) {
        fprintf(stderr, "No icons provided.\n");
        return 1;
    }

    layout_items(&app);
    app.max_time = 1.0;

    ecore_main_loop_begin();

    return 0;
}
