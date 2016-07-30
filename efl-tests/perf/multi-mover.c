#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <sys/time.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>

#define WIDTH 800
#define HEIGHT 480
#define IMG_SPACING 64
#define TITLE "Mover"
#define WM_NAME "EvasMover"
#define WM_CLASS "main"

typedef struct app
{
    Evas_Object **objs;
    int n_objs;
    Evas_Object *bg;
    Ecore_Evas  *ee;
    Evas *evas;
    int steps;
    int fs;
    int img_spacing;
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

static void
move_objects(app_t *app, int ox, int oy)
{
    int i, y;

    y = 0;
    for (i = 0; i < app->n_objs; i++) {
        evas_object_move(app->objs[i], ox, oy + y);
        y += app->img_spacing;
    }
}

int
main(int argc, char *argv[])
{
    Evas_List *files, *itr;
    struct timeval start, end, dif;
    app_t app;
    int i, x, y;
    char *engine = "x11-16";

    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();

    memset(&app, 0, sizeof(app));

    app.steps = 500;
    app.fs = 0;
    app.dx = 100;
    app.dy = 100;
    app.img_spacing = IMG_SPACING;
    files = NULL;

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            app.fs = 1;
        else if (strncmp (argv[i], "-dx=", sizeof("-dx=") - 1) == 0)
            app.dx = atoi(argv[i] + sizeof("-dx=") - 1);
        else if (strncmp (argv[i], "-dy=", sizeof("-dy=") - 1) == 0)
            app.dy = atoi(argv[i] + sizeof("-dy=") - 1);
        else if (strncmp (argv[i], "-steps=", sizeof("-steps=") - 1) == 0)
            app.steps = atoi(argv[i] + sizeof("-steps=") - 1);
        else if (strncmp (argv[i], "-spacing=", sizeof("-spacing=") - 1) == 0)
            app.img_spacing = atoi(argv[i] + sizeof("-spacing=") - 1);
        else if (argv[i][0] != '-')
            files = evas_list_append(files, argv[i]);
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

    app.bg = evas_object_image_add(app.evas);
    evas_object_image_file_set(app.bg, "background.png", NULL);
    evas_object_image_fill_set(app.bg, 0, 0, WIDTH, HEIGHT);
    evas_object_resize(app.bg, WIDTH, HEIGHT);
    evas_object_show(app.bg);

    app.n_objs = evas_list_count(files);
    app.objs = malloc(sizeof(Evas_Object *) * app.n_objs);
    y = 0;
    for (i = 0, itr = files; i < app.n_objs; i++, itr = itr->next) {
        int w, h, r;
        char *fname;

        fname = itr->data;

        app.objs[i] = evas_object_image_add(app.evas);
        evas_object_image_file_set(app.objs[i], fname, NULL);
        r = evas_object_image_load_error_get(app.objs[i]);
        if (r != EVAS_LOAD_ERROR_NONE) {
            fprintf(stderr, "Failed to load image '%s'\n", (char*)itr->data);
            continue;
        }
        evas_object_image_size_get(app.objs[i], &w, &h);
        evas_object_image_fill_set(app.objs[i], 0, 0, w, w);
        evas_object_resize(app.objs[i], w, h);
        evas_object_move(app.objs[i], 0, y);
        evas_object_show(app.objs[i]);
        fprintf(stderr, "Loaded image #%d '%s' (%dx%d)\n", i, fname, w, h);
        y += app.img_spacing;
    }

    ecore_evas_show(app.ee);

    x = 0;
    y = 0;

    gettimeofday(&start, NULL);
    for (i=0; i < app.steps; i++) {
        move_objects(&app, x, y);
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
    fprintf(stderr, "Done %d steps in %06lu.%06lu s (FPS=%03.3f).\n",
            app.steps, dif.tv_sec, dif.tv_usec,
            (double)(app.steps * 1e6) /
            (double)(dif.tv_sec * 1e6 + dif.tv_usec) );

    ecore_main_loop_begin();


    return 0;
}
