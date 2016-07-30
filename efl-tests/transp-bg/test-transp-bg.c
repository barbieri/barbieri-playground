#include <Evas.h>
#include <Ecore.h>
#include <Ecore_Evas.h>
#include <Edje.h>
#include <stdlib.h>
#include <stdio.h>

int main(void) {
    Evas_Object *o;
    Ecore_Evas *ee;
    int r;

    evas_init();
    ecore_init();
    ecore_evas_init();
    edje_init();

    ee = ecore_evas_new(NULL, 0, 0, 320, 240, NULL);
    if (!ee)
        return -1;

    o = edje_object_add(ecore_evas_get(ee));
    if (!edje_object_file_set(o, "test.edj", "main")) {
        fprintf(stderr, "could not load edje: %d\n",
                edje_object_load_error_get(o));
        return -2;
    }
    evas_object_resize(o, 320, 240);
    evas_object_show(o);

    ecore_evas_alpha_set(ee, 1);
    ecore_evas_borderless_set(ee, 1);
    ecore_evas_show(ee);
    ecore_main_loop_begin();

    return 0;
}
