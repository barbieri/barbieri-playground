#include <stdlib.h>
#include <Ecore_Evas.h>
#include <Ecore.h>
#include <Edje.h>

#define WIDTH 800
#define HEIGHT 480
#define THEME "default.edj"
#define THEME_GROUP "main"
#define TITLE "Animation Test - please click and hold to start it"
#define WM_NAME "LoadingAnimation"
#define WM_CLASS "main"

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
    Evas_Object *edje;
    Evas_Coord w, h;

    evas = ecore_evas_get(ee);
    edje = evas_data_attach_get(evas);

    evas_output_viewport_get(evas, NULL, NULL, &w, &h);
    evas_object_resize(edje, w, h);
}

int main(int argc, char *argv[])
{
    Ecore_Evas  *ee;
    Evas *evas;
    Evas_Object *edje;
    Evas_Coord edje_w, edje_h;
    int i;

    ecore_init();
    ecore_app_args_set(argc, (const char **)argv);
    ecore_evas_init();
    edje_init();

    edje_frametime_set(1.0 / 30.0);

    ee = ecore_evas_software_x11_new(NULL, 0,  0, 0, WIDTH, HEIGHT);
    ecore_evas_title_set(ee, TITLE);
    ecore_evas_name_class_set(ee, WM_NAME, WM_CLASS);

    for (i=1; i < argc; i++)
        if (strcmp (argv[i], "-fs") == 0)
            ecore_evas_fullscreen_set(ee, 1);

    evas = ecore_evas_get(ee);

    edje = edje_object_add(evas);
    evas_data_attach_set(evas, edje);
    edje_object_file_set(edje, THEME, THEME_GROUP);
    evas_object_move(edje, 0, 0);
    evas_object_resize(edje, WIDTH, HEIGHT);

    evas_object_show(edje);
    ecore_evas_show(ee);

    ecore_event_handler_add(ECORE_EVENT_SIGNAL_EXIT, app_signal_exit, NULL);
    ecore_evas_callback_resize_set(ee, resize_cb);

    ecore_main_loop_begin();

    return 0;
}
