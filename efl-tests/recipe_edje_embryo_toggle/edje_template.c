/**
 * From EFL Cookbook, example 9.1
 *
 * gcc `edje-config --cflags --libs` `ecore-config --cflags --libs` edje_template.c -o edje_template
 */
#include <stdio.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>

#define WIDTH 400
#define HEIGHT 400

Evas_Object *edje;

int
app_signal_exit(void *data, int type, void *event)
{

    ecore_main_loop_quit();
    return 1;
}

void
resize_cb(Ecore_Evas *ee)
{
    Evas *evas;
    Evas_Coord w, h;

    evas = ecore_evas_get(ee);

    evas_output_viewport_get(evas, NULL, NULL, &w, &h);
    evas_object_resize(edje, w, h);
}

int main(int argc, char *argv[])
{
    Ecore_Evas  *ee;
    Evas *evas;
    Evas_Coord edje_w, edje_h;

    if (argc < 3) {
        printf("Usage:\n\t%s <file.edj> <element>\n\n", argv[0]);
        return 1;
    }


    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();
    edje_init();

    ee = ecore_evas_software_x11_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
    evas = ecore_evas_get(ee);

    edje = edje_object_add(evas);
    edje_object_file_set(edje, argv[1], argv[2]);

    evas_object_move(edje, 0, 0);
    edje_object_size_min_get(edje, &edje_w, &edje_h);

    if (edje_w > 0 && edje_h > 0)
        evas_object_resize(edje, edje_w, edje_h);
    else
        evas_object_resize(edje, WIDTH, HEIGHT);

    if (edje_w > WIDTH || edje_h > HEIGHT)
        ecore_evas_resize(ee, WIDTH, HEIGHT);

    evas_object_show(edje);
    ecore_evas_show(ee);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(ee, resize_cb);

    ecore_main_loop_begin();

    return 0;
}
