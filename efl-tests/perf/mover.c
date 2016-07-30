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
#define TITLE "Mover"
#define WM_NAME "EvasMover"
#define WM_CLASS "main"

typedef struct app
{
    char *theme;
    Evas_Object *edje_main;
    Evas_Object *obj;
    Ecore_Evas  *ee;
    Evas *evas;
    int steps;
    int fs;
    int dx;
    int dy;
} app_t;

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
    struct timeval start, end, dif;
    char *engine = "x11-16";
    app_t app;
    int i, x, y;

    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();
    edje_init();

    memset(&app, 0, sizeof(app));

    app.theme = THEME;
    app.steps = 500;
    app.fs = 0;
    app.dx = 300;
    app.dy = 300;

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            app.fs = 1;
        else if (strncmp (argv[i], "-theme=", sizeof("-theme=") - 1) == 0)
            app.theme = argv[i] + sizeof("-theme=") - 1;
        else if (strncmp (argv[i], "-dx=", sizeof("-dx=") - 1) == 0)
            app.dx = atoi(argv[i] + sizeof("-dx=") - 1);
        else if (strncmp (argv[i], "-dy=", sizeof("-dy=") - 1) == 0)
            app.dy = atoi(argv[i] + sizeof("-dy=") - 1);
        else if (strncmp (argv[i], "-steps=", sizeof("-steps=") - 1) == 0)
            app.steps = atoi(argv[i] + sizeof("-steps=") - 1);
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

    x = 0;
    y = 0;

    gettimeofday(&start, NULL);
    for (i=0; i < app.steps; i++) {
        evas_object_move(app.obj, x, y);
        evas_render_updates(app.evas);
        if (x == app.dx || y == app.dy) {
            x = 0;
            y = 0;
        } else {
            x = app.dx;
            y = app.dy;
        }
    }
    gettimeofday(&end, NULL);
    timersub(&end, &start, &dif);
    fprintf(stderr, "Done %d steps in %06lu.%06lu s.\n",
            app.steps, dif.tv_sec, dif.tv_usec);


    return 0;
}
