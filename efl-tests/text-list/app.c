#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>
#include "e_box.h"

#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Text List Test"
#define WM_NAME "TextList"
#define WM_CLASS "main"

typedef struct app
{
    char *infile;
    Evas_Object *edje_main;
    Evas_Object *e_box;
    Ecore_Evas  *ee;
    Evas *evas;
    int current;
} app_t;

static inline int
eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
}

static Evas_Object *
_new_list_item(app_t *app, const char *text)
{
    Evas_Object *obj;

    obj = edje_object_add(app->evas);
    edje_object_file_set(obj, THEME, "list_item");
    edje_object_part_text_set(obj, "label", text);

    return obj;
}

static void
_populate(app_t *app)
{
    FILE *fp;

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

    while (!feof(fp)) {
        Evas_Object *obj;
        Evas_Coord w, h;
        char *line;
        unsigned n;
        int i;

        n = 0;
        line = NULL;
        i = getline(&line, &n, fp);
        if (i < 0)
            break;

        if (i == 0) {
            free(line);
            continue;
        }
        line[i - 1] = '\0';

        obj = _new_list_item(app, line);
        e_box_pack_end(app->e_box, obj);
        edje_object_size_min_calc(obj, &w, &h);
        e_box_pack_options_set(obj, 1, 1, 1, 0, 0.0, 0.5, w, h, 9999, h);
        evas_object_show(obj);

        free(line);
    }

    if (fp != stdin)
        fclose(fp);

    e_box_align_set(app->e_box, 0.0, 1.0);
    app->current = 0;
}

static void
move_down(app_t *app)
{
    fprintf(stderr, "down\n");
}

static void
move_up(app_t *app)
{
    fprintf(stderr, "up\n");
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
    else if (eq(k, "f")) {
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
}

int
main(int argc, char *argv[])
{
    app_t app;
    int i;

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

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            ecore_evas_fullscreen_set(app.ee, 1);
        else if (argv[i][0] != '-')
            app.infile = argv[i];

    app.evas = ecore_evas_get(app.ee);

    app.edje_main = edje_object_add(app.evas);
    evas_data_attach_set(app.evas, &app);
    if (!edje_object_file_set(app.edje_main, THEME, THEME_GROUP)) {
        fprintf(stderr, "Failed to load file \"%s\", part \"%s\".\n",
                THEME, THEME_GROUP);
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

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(app.ee, resize_cb);

    evas_object_event_callback_add(app.edje_main, EVAS_CALLBACK_KEY_DOWN,
                                   key_down, &app);
    evas_object_focus_set(app.edje_main, 1);

    ecore_main_loop_begin();

    return 0;
}
