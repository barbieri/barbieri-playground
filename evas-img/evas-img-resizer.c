#include <Evas.h>
#include <Ecore_Evas.h>
#include <stdio.h>
#include <math.h>

int main(int argc, char *argv[])
{
    Ecore_Evas *ee;
    Evas_Object *bridge, *img;
    const char *opt, *input, *output, *params;
    int r = 0, w = -1, h = -1, err;
    double scale = -1.0;

    if (argc < 4) {
        fprintf(stderr,
                "Usage:\n"
                "\t%s <percentage%%|WxH|w=W|h=H> <input> <output>"
                " [save-params]\n"
                "where save-params is evas supported parameters, like:\n"
                "\tquality=85\n"
                "\tcompress=9\n",
                argv[0]);
        return 1;
    }

    opt = argv[1];
    input = argv[2];
    output = argv[3];
    params = argv[4];

    if (strncasecmp(opt, "w=", 2) == 0) {
        char *end = NULL;
        w = strtol(opt + 2, &end, 10);
        if (!end || *end != '\0') {
            fprintf(stderr, "ERROR: invalid decimal integer '%s'\n",
                    opt + 2);
            return 1;
        } else if (w < 1) {
            fprintf(stderr, "ERROR: invalid width %d, must be >= 1\n", w);
            return 1;
        }
    } else if (strncasecmp(opt, "h=", 2) == 0) {
        char *end = NULL;
        h = strtol(opt + 2, &end, 10);
        if (!end || *end != '\0') {
            fprintf(stderr, "ERROR: invalid decimal integer '%s'\n",
                    opt + 2);
            return 1;
        } else if (h < 1) {
            fprintf(stderr, "ERROR: invalid height %d, must be >= 1\n", h);
            return 1;
        }
    } else if (strchr(opt, '%')) {
        char *end = NULL;
        scale = strtod(opt, &end);
        if (!end || *end != '%') {
            fprintf(stderr, "ERROR: invalid percentual '%s'\n", opt);
            return 1;
        } else if (scale <= 0.0) {
            fprintf(stderr, "ERROR: invalid percentual %g, must be > 0.0\n",
                    scale);
            return 1;
        }
        scale /= 100.0;
    } else if (strchr(opt, 'x')) {
        if (sscanf(opt, "%dx%d", &w, &h) != 2) {
            fprintf(stderr, "ERROR: invalid size format '%s'\n", opt);
            return 1;
        } else if (w < 1) {
            fprintf(stderr, "ERROR: invalid width %d, must be >= 1\n", w);
            return 1;
        } else {
            fprintf(stderr, "ERROR: invalid height %d, must be >= 1\n", h);
            return 1;
        }
    } else {
        fprintf(stderr,
                "ERROR: first parameter must be in format:\n"
                "\tpercentage%%    - example: 10%%\n"
                "\tWxH            - example: 1024x768\n"
                "\tw=W            - example: w=1024\n"
                "\th=H            - example: h=768\n"
                "But '%s' was used!\n",
                opt);
        return 1;
    }

    ecore_evas_init();
    evas_init();

    ee = ecore_evas_buffer_new(1, 1);
    bridge = ecore_evas_object_image_new(ee);
    img = evas_object_image_add(ecore_evas_object_evas_get(bridge));
    evas_object_image_smooth_scale_set(img, EINA_TRUE);

    if (w > 0 && h > 0)
        evas_object_image_load_size_set(img, w, h);

    evas_object_image_file_set(img, input, NULL);
    err = evas_object_image_load_error_get(img);
    if (err != EVAS_LOAD_ERROR_NONE) {
        const char *msg = evas_load_error_str(err);
        fprintf(stderr, "ERROR: could not load '%s': %s\n", input, msg);
        r = 1;
        goto end;
    }

    if (w < 1 || h < 1) {
        int iw, ih;
        evas_object_image_size_get(img, &iw, &ih);

        if (iw < 0 || ih < 0) {
            fprintf(stderr, "ERROR: invalid source image size %dx%d (%s)\n",
                    iw, ih, input);
            goto end;
        }

        if (scale > 0) {
            w = ceil(iw * scale);
            h = ceil(ih * scale);
        } else if (w < 1)
            w = ceil(iw * (double)h / (double)ih);
        else if (h < 1)
            h = ceil(ih * (double)w / (double)iw);

        if (iw != w && ih != h)
            evas_object_image_load_size_set(img, w, h);
    }

    printf("output: %s, size: %dx%d, alpha: %s, params: %s\n",
           output, w, h,
           evas_object_image_alpha_get(img) ? "yes" : "no",
           params ? params : "<none>");

    evas_object_image_fill_set(img, 0, 0, w, h);
    evas_object_resize(img, w, h);
    evas_object_show(img);

    evas_object_image_alpha_set(bridge, evas_object_image_alpha_get(img));
    evas_object_image_size_set(bridge, w, h);
    ecore_evas_manual_render(ecore_evas_object_ecore_evas_get(bridge));

    evas_object_image_save(bridge, output, NULL, params);

  end:
    evas_object_del(img);
    evas_object_del(bridge);
    ecore_evas_free(ee);

    evas_shutdown();
    ecore_evas_shutdown();

    return r;
}
