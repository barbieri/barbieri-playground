#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <sys/time.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>

#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Scale Animation"
#define WM_NAME "ScaleAnimation"
#define WM_CLASS "main"

typedef struct app
{
    char *theme;
    Evas_Object *edje_main;
    Evas_Object *obj;
    Ecore_Evas  *ee;
    Evas *evas;
    int fs;
    int enlarge;
    int x;
    int y;
    int max_w;
    int max_h;
    int min_w;
    int min_h;
    int dw;
    int dh;
    struct timeval start;
    int total_ms;
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
    }
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
    evas_object_move(app->obj, app->x, app->y);
}

static int
do_anim(void *data)
{
    struct timeval now, dif;
    app_t *app = (app_t *)data;
    int dif_ms, w, h;
    double scale;

    gettimeofday(&now, NULL);
    timersub(&now, &app->start, &dif);
    dif_ms = dif.tv_sec * 1000 + dif.tv_usec / 1000;

    if (dif_ms >= app->total_ms) {
        app->start = now;
        app->enlarge = !app->enlarge;
        return 1;
    }

    scale = (double)dif_ms / (double)app->total_ms;
    if (!app->enlarge) {
        scale = 1 - scale;
    }

    w = app->min_w + app->dw * scale;
    h = app->min_h + app->dh * scale;

    evas_object_image_fill_set(app->obj, 0, 0, w, h);
    evas_object_resize(app->obj, w, h);

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

    edje_frametime_set(1.0 / 30.0);

    memset(&app, 0, sizeof(app));

    app.fs = 0;
    app.theme = THEME;
    app.total_ms = 1000;
    app.x = 0;
    app.y = 0;
    app.max_w = 600;
    app.max_h = 600;
    app.enlarge = 1;

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            app.fs = 1;
        else if (strncmp (argv[i], "-theme=", sizeof("-theme=") - 1) == 0)
            app.theme = argv[i] + sizeof("-theme=") - 1;
        else if (strncmp (argv[i], "-time=", sizeof("-time=") - 1) == 0)
            app.total_ms = atoi(argv[i] + sizeof("-time=") - 1);
        else if (strncmp (argv[i], "-x=", sizeof("-x=") - 1) == 0)
            app.x = atoi(argv[i] + sizeof("-x=") - 1);
        else if (strncmp (argv[i], "-y=", sizeof("-y=") - 1) == 0)
            app.y = atoi(argv[i] + sizeof("-y=") - 1);
        else if (strncmp (argv[i], "-w=", sizeof("-w=") - 1) == 0)
            app.max_w = atoi(argv[i] + sizeof("-w=") - 1);
        else if (strncmp (argv[i], "-h=", sizeof("-h=") - 1) == 0)
            app.max_h = atoi(argv[i] + sizeof("-h=") - 1);
        else if (strncmp (argv[i], "-engine=", sizeof("-engine=") - 1) == 0)
            engine = argv[i] + sizeof("-engine=") - 1;

    if (app.total_ms < 1)
        app.total_ms = 1000;

    app.ee = init_ecore_evas(engine);
    if (!app.ee) {
        fprintf(stderr, "Could not init engine '%s'.\n", engine);
        return 1;
    }
    ecore_evas_data_set(app.ee, "app", &app);
    ecore_evas_title_set(app.ee, TITLE);
    ecore_evas_name_class_set(app.ee, WM_NAME, WM_CLASS);
    ecore_evas_fullscreen_set(app.ee, app.fs);

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
    ecore_evas_callback_resize_set(app.ee, resize_cb);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);
    evas_object_focus_set(app.edje_main, 1);

    /* E-devel says we shouldn't use this way, so do not use it in
     * real code.
     *
     * Edje objects should just operate with state changes.
     */
    app.obj = edje_object_part_object_get(app.edje_main, "obj");
    evas_object_image_size_get(app.obj, &app.min_w, &app.min_h);
    evas_object_move(app.obj, app.x, app.y);

    if (app.max_w < app.min_w)
        app.max_w = app.min_w;

    if (app.max_h < app.min_h)
        app.max_h = app.min_h;

    app.dw = app.max_w - app.min_w;
    app.dh = app.max_h - app.min_h;

    fprintf(stderr, "time to scale: %dms, at %d,%d from %dx%d to %dx%d\n",
            app.total_ms, app.x, app.y, app.min_w, app.min_h,
            app.max_w, app.max_h);

    gettimeofday(&app.start, NULL);
    app.anim = ecore_animator_add(do_anim, &app);

    ecore_main_loop_begin();

    return 0;
}
