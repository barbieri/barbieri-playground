#include <Ecore.h>
#include <Evas.h>
#include <Ecore_Evas.h>
#include <Edje.h>
#include <stdio.h>
#include <string.h>
#include "icon.h"

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
    Evas_Object *icon;
} app_t;

static void
center_icon(app_t *app)
{
    int w, h, iw, ih;

    evas_object_geometry_get(app->edje_main, NULL, NULL, &w, &h);
    evas_object_geometry_get(app->icon, NULL, NULL, &iw, &ih);
    evas_object_move(app->icon, (w - iw)/2, (h - ih)/2);
}

static void
move_icon(app_t *app, int off_x, int off_y)
{
    int x, y;

    evas_object_geometry_get(app->icon, &x, &y, NULL, NULL);

    x += off_x;
    y += off_y;

    evas_object_move(app->icon, x, y);
}

static void
resize_icon(app_t *app, int value)
{
    int w, h;

    evas_object_geometry_get(app->icon, NULL, NULL, &w, &h);
    w += value;
    h += value;

    evas_object_resize(app->icon, w, h);
}

static void
toggle_icon(app_t *app)
{
    int v;

    v = evas_object_visible_get(app->icon);
    if (v)
        evas_object_hide(app->icon);
    else
        evas_object_show(app->icon);
}

static inline int
eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
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
    } else if (eq(k, "c"))
        center_icon(app);
    else if (eq(k, "Left"))
        move_icon(app, -1, 0);
    else if (eq(k, "Right"))
        move_icon(app, +1, 0);
    else if (eq(k, "Up"))
        move_icon(app, 0, -1);
    else if (eq(k, "Down"))
        move_icon(app, 0, +1);
    else if (eq(k, "Return"))
        toggle_icon(app);
    else if (eq(k, "equal"))
        resize_icon(app, +1);
    else if (eq(k, "minus"))
        resize_icon(app, -1);
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
    center_icon(app);
}

int
main(int argc, char *argv[])
{
    app_t app;
    int i;
    char *path;
    Evas_Hash *hash;

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

    path = NULL;
    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            ecore_evas_fullscreen_set(app.ee, 1);
        else if (strncmp (argv[i], "-theme=", sizeof("-theme=") - 1) == 0)
            app.theme = argv[i] + sizeof("-theme=") - 1;
        else if (argv[i][0] != '-')
            path = argv[i];

    if (!path) {
        fprintf(stderr, "Missing icon name.\n");
        return 1;
    }

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

    app.icon = icon_new(app.evas);
    icon_text_set(app.icon, path);
    icon_image_set(app.icon, path);
    center_icon(&app);
    evas_object_show(app.icon);

    ecore_main_loop_begin();

    return 0;
}
