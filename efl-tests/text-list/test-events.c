#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>
#include <sys/time.h>
#include "key_monitor.h"

#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Events Test"
#define WM_NAME "EventTest"
#define WM_CLASS "main"

static inline int
eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
}

typedef struct app
{
    char *theme;
    Evas_Object *edje_main;
    Ecore_Evas  *ee;
    Evas *evas;
    struct {
        key_monitor_t down;
        key_monitor_t up;
    } keys;
} app_t;

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
        key_monitor_down(&app->keys.down);
    else if (eq(k, "Up"))
        key_monitor_down(&app->keys.up);
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


static int
app_signal_exit(void *data, int type, void *event)
{

    ecore_main_loop_quit();
    return 1;
}

static void
move_down_start(void *data, key_monitor_t *m)
{
    app_t *app = (app_t *)data;

    fprintf(stderr, "move down start: %p\n", app);
}

static void
move_down_stop(void *data, key_monitor_t *m)
{
    app_t *app = (app_t *)data;

    fprintf(stderr, "move down stop: %p\n", app);
}

int
main(int argc, char *argv[])
{
    app_t app;

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


    evas_object_show(app.edje_main);
    ecore_evas_show(app.ee);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);
    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_UP,
                                   key_up, &app);


    key_monitor_setup(&app.keys.down, move_down_start, move_down_stop, &app);

    evas_object_focus_set(app.edje_main, 1);

    ecore_main_loop_begin();

    return 0;
}
