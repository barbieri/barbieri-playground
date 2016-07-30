#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>

#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Ball Animation"
#define WM_NAME "BallAnimation"
#define WM_CLASS "main"

typedef struct app
{
    char *theme;
    Evas_Object *edje_main;
    Evas_Object *obj;
    Ecore_Evas  *ee;
    Evas *evas;
    int fs;
    int dx;
    int dy;
    Ecore_Animator *anim;
} app_t;

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
    } else if (eq(k, "Up"))
        app->dy -= 1;
    else if (eq(k, "Down"))
        app->dy += 1;
    else if (eq(k, "Left"))
        app->dx -= 1;
    else if (eq(k, "Right"))
        app->dx += 1;
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
}

static int
do_anim(void *data)
{
    app_t *app = (app_t *)data;
    int x, y, w, h, win_w, win_h;

    evas_object_geometry_get(app->obj, &x, &y, &w, &h);
    evas_object_geometry_get(app->edje_main, NULL, NULL, &win_w, &win_h);

    if (app->dx + x >= 0 && app->dx + x + w < win_w)
        x = app->dx + x;
    else
        app->dx = -app->dx;

    if (app->dy + y >= 0 && app->dy + y + h < win_h)
        y = app->dy + y;
    else
        app->dy = -app->dy;

    evas_object_move(app->obj, x, y);

    return 1;
}

static Ecore_Evas *
init_ecore_evas(const char *engine)
{
    Ecore_Evas *ee = NULL;

    if (strcmp(engine, "x11-16") == 0)
        if (ecore_evas_engine_type_supported_get
            (ECORE_EVAS_ENGINE_SOFTWARE_X11_16)) {
            ee = ecore_evas_software_x11_16_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
            fprintf(stderr, "Using X11 16bpp engine!\n");
        } else {
            ee = ecore_evas_software_x11_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
            fprintf(stderr, "Using X11 engine!\n");
        }
    else if (strcmp(engine, "x11") == 0) {
        ee = ecore_evas_software_x11_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
        fprintf(stderr, "Using X11 engine!\n");
    }

    return ee;
}

int
main(int argc, char *argv[])
{
    app_t app;
    int i;
    char *engine = "x11-16";

    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();
    edje_init();

    srandom(time(NULL));

    edje_frametime_set(1.0 / 30.0);

    memset(&app, 0, sizeof(app));
    app.dx = (random() * 10) / RAND_MAX - 5;
    app.dy = (random() * 10) / RAND_MAX - 5;

    app.theme = THEME;
    app.fs = 0;

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            app.fs = 1;
        else if (strncmp (argv[i], "-theme=", sizeof("-theme=") - 1) == 0)
            app.theme = argv[i] + sizeof("-theme=") - 1;
        else if (strncmp (argv[i], "-dx=", sizeof("-dx=") - 1) == 0)
            app.dx = atoi(argv[i] + sizeof("-dx=") - 1);
        else if (strncmp (argv[i], "-dy=", sizeof("-dy=") - 1) == 0)
            app.dy = atoi(argv[i] + sizeof("-dy=") - 1);
        else if (strncmp (argv[i], "-engine=", sizeof("-engine=") - 1) == 0)
            engine = argv[i] + sizeof("-engine=") - 1;

    app.ee = init_ecore_evas(engine);
    if (!app.ee) {
        fprintf(stderr, "Could not init engine '%s'.\n", engine);
        return 1;
    }
    ecore_evas_data_set(app.ee, "app", &app);
    ecore_evas_title_set(app.ee, TITLE);
    ecore_evas_name_class_set(app.ee, WM_NAME, WM_CLASS);
    ecore_evas_fullscreen_set(app.ee, app.fs);

    fprintf(stderr, "Move: %d, %d\n", app.dx, app.dy);

    app.evas = ecore_evas_get(app.ee);

    app.edje_main = edje_object_add(app.evas);
    evas_data_attach_set(app.evas, &app);
    if (!edje_object_file_set(app.edje_main, app.theme, THEME_GROUP)) {
        fprintf(stderr, "Failed to load file \"%s\", part \"%s\".\n",
                app.theme, THEME_GROUP);
        return 1;
    }

    app.obj = edje_object_part_object_get(app.edje_main, "obj");

    evas_object_move(app.edje_main, 0, 0);
    evas_object_resize(app.edje_main, WIDTH, HEIGHT);

    evas_object_show(app.edje_main);
    ecore_evas_show(app.ee);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(app.ee, resize_cb);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);
    evas_object_focus_set(app.edje_main, 1);

    app.anim = ecore_animator_add(do_anim, &app);

    ecore_main_loop_begin();

    return 0;
}
