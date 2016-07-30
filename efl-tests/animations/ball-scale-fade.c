#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
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
    struct {
        int dx;
        int dy;
    } move;
    struct {
        int fade_in;
        struct timeval start;
        int total_ms;
    } fade;
    struct {
        int enlarge;
        int max_w;
        int max_h;
        int min_w;
        int min_h;
        int dw;
        int dh;
        struct timeval start;
        int total_ms;
    } scale;
    Ecore_Animator *anim;
} app_t;

static inline int
eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
}

#define max(a, b) (((a) > (b)) ? (a) : (b))

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
        app->move.dy -= 1;
    else if (eq(k, "Down"))
        app->move.dy += 1;
    else if (eq(k, "Left"))
        app->move.dx -= 1;
    else if (eq(k, "Right"))
        app->move.dx += 1;
    else if (eq(k, "1"))
        app->fade.total_ms = max(app->fade.total_ms - 100, 100);
    else if (eq(k, "2"))
        app->fade.total_ms += 100;
    else if (eq(k, "3"))
        app->scale.total_ms = max(app->scale.total_ms - 100, 100);
    else if (eq(k, "4"))
        app->scale.total_ms += 100;
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

static void
do_move(app_t *app, const struct timeval *p_now)
{
    int x, y, w, h, win_w, win_h;

    evas_object_geometry_get(app->obj, &x, &y, &w, &h);
    evas_object_geometry_get(app->edje_main, NULL, NULL, &win_w, &win_h);

    if (app->move.dx + x >= 0 && app->move.dx + x + w < win_w)
        x = app->move.dx + x;
    else
        app->move.dx = -app->move.dx;

    if (app->move.dy + y >= 0 && app->move.dy + y + h < win_h)
        y = app->move.dy + y;
    else
        app->move.dy = -app->move.dy;

    evas_object_move(app->obj, x, y);
}

static void
do_fade(app_t *app, const struct timeval *p_now)
{
    struct timeval dif;
    int dif_ms, v;
    double scale;

    timersub(p_now, &app->fade.start, &dif);
    dif_ms = dif.tv_sec * 1000 + dif.tv_usec / 1000;

    if (dif_ms >= app->fade.total_ms) {
        app->fade.fade_in = !app->fade.fade_in;
        app->fade.start = *p_now;
        return;
    }

    scale = (double)dif_ms / (double)app->fade.total_ms;
    if (app->fade.fade_in)
        v = 255 * scale;
    else
        v = 255 * (1 - scale);

    evas_object_color_set(app->obj, v, v, v, v);
}

static void
do_scale(app_t *app, const struct timeval *p_now)
{
    struct timeval dif;
    int dif_ms, w, h;
    double scale;

    timersub(p_now, &app->scale.start, &dif);
    dif_ms = dif.tv_sec * 1000 + dif.tv_usec / 1000;

    if (dif_ms >= app->scale.total_ms) {
        app->scale.start = *p_now;
        app->scale.enlarge = !app->scale.enlarge;
        return;
    }

    scale = (double)dif_ms / (double)app->scale.total_ms;
    if (!app->scale.enlarge) {
        scale = 1 - scale;
    }

    w = app->scale.min_w + app->scale.dw * scale;
    h = app->scale.min_h + app->scale.dh * scale;

    evas_object_image_fill_set(app->obj, 0, 0, w, h);
    evas_object_resize(app->obj, w, h);
}

static int
do_anim(void *data)
{
    struct timeval now;
    app_t *app = (app_t *)data;

    gettimeofday(&now, NULL);

    do_scale(app, &now);
    do_move(app, &now);
    do_fade(app, &now);

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
    app.move.dx = (random() * 10) / RAND_MAX - 5;
    app.move.dy = (random() * 10) / RAND_MAX - 5;

    app.ee = ecore_evas_software_x11_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
    ecore_evas_data_set(app.ee, "app", &app);
    ecore_evas_title_set(app.ee, TITLE);
    ecore_evas_name_class_set(app.ee, WM_NAME, WM_CLASS);

    app.fs = 0;
    app.theme = THEME;
    app.fade.total_ms = 1000;
    app.scale.total_ms = 1000;
    app.scale.max_w = 400;
    app.scale.max_h = 400;
    app.scale.enlarge = 1;

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            app.fs = 1;
        else if (strncmp (argv[i], "-theme=", sizeof("-theme=") - 1) == 0)
            app.theme = argv[i] + sizeof("-theme=") - 1;
        else if (strncmp (argv[i], "-dx=", sizeof("-dx=") - 1) == 0)
            app.move.dx = atoi(argv[i] + sizeof("-dx=") - 1);
        else if (strncmp (argv[i], "-dy=", sizeof("-dy=") - 1) == 0)
            app.move.dy = atoi(argv[i] + sizeof("-dy=") - 1);
        else if (strncmp (argv[i], "-time-fade=",
                          sizeof("-time-fade=") - 1) == 0)
            app.fade.total_ms = atoi(argv[i] + sizeof("-time-fade=") - 1);
        else if (strncmp (argv[i], "-time-scale=",
                          sizeof("-time-scale=") - 1) == 0)
            app.scale.total_ms = atoi(argv[i] + sizeof("-time-scale=") - 1);
        else if (strncmp (argv[i], "-w=", sizeof("-w=") - 1) == 0)
            app.scale.max_w = atoi(argv[i] + sizeof("-w=") - 1);
        else if (strncmp (argv[i], "-h=", sizeof("-h=") - 1) == 0)
            app.scale.max_h = atoi(argv[i] + sizeof("-h=") - 1);
        else if (strncmp (argv[i], "-engine=", sizeof("-engine=") - 1) == 0)
            engine = argv[i] + sizeof("-engine=") - 1;

    if (app.fade.total_ms < 1)
        app.fade.total_ms = 1000;

    if (app.scale.total_ms < 1)
        app.scale.total_ms = 1000;

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

    evas_object_image_size_get(app.obj, &app.scale.min_w, &app.scale.min_h);

    if (app.scale.max_w < app.scale.min_w)
        app.scale.max_w = app.scale.min_w;

    if (app.scale.max_h < app.scale.min_h)
        app.scale.max_h = app.scale.min_h;

    app.scale.dw = app.scale.max_w - app.scale.min_w;
    app.scale.dh = app.scale.max_h - app.scale.min_h;

    fprintf(stderr,
            "time to scale: %dms, fade: %dms, from %dx%d to %dx%d, "
            "move %d, %d\n",
            app.scale.total_ms, app.fade.total_ms,
            app.scale.min_w, app.scale.min_h,
            app.scale.max_w, app.scale.max_h,
            app.move.dx, app.move.dy);

    gettimeofday(&app.fade.start, NULL);
    app.scale.start = app.fade.start;
    app.anim = ecore_animator_add(do_anim, &app);

    ecore_main_loop_begin();

    return 0;
}
