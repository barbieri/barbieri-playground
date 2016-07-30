#include <Evas.h>
#include <Ecore.h>
#include <Ecore_Evas.h>
#include <stdio.h>
#include <math.h>

int main(int argc, char *argv[])
{
    Ecore_Evas *ee;
    Evas_Object *bg, *bridge, *img;
    const char *input;
    int r = 0, i, w = -1, h = -1, cr = 255, cg = 255, cb = 255, ca = -1, err;
    double scale = -1.0;

    if (argc < 2) {
        fprintf(stderr,
                "Usage:\n"
                "\t%s [options] <input>\n"
                "where options:\n"
                "\t-size=percentage%%|WxH|w=W|h=H\n"
                "\t-bg=#rrggbbaa\n",
                argv[0]);
        return 1;
    }

    input = argv[argc - 1];

    for (i = 1; i < argc - 1; i++) {
        const char *opt = argv[i];

        if (strncasecmp(opt, "-size=", sizeof("-size=") - 1) == 0) {
            opt += sizeof("-size=") - 1;

            if (strncasecmp(opt, "w=", 2) == 0) {
                char *end = NULL;
                w = strtol(opt + 2, &end, 10);
                if (!end || *end != '\0') {
                    fprintf(stderr, "ERROR: invalid decimal integer '%s'\n",
                            opt + 2);
                    return 1;
                } else if (w < 1) {
                    fprintf(stderr, "ERROR: invalid width %d, must be >= 1\n",
                            w);
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
                    fprintf(stderr, "ERROR: invalid height %d, must be >= 1\n",
                            h);
                    return 1;
                }
            } else if (strchr(opt, '%')) {
                char *end = NULL;
                scale = strtod(opt, &end);
                if (!end || *end != '%') {
                    fprintf(stderr, "ERROR: invalid percentual '%s'\n", opt);
                    return 1;
                } else if (scale <= 0.0) {
                    fprintf(stderr,
                            "ERROR: invalid percentual %g, must be > 0.0\n",
                            scale);
                    return 1;
                }
                scale /= 100.0;
            } else if (strchr(opt, 'x')) {
                if (sscanf(opt, "%dx%d", &w, &h) != 2) {
                    fprintf(stderr, "ERROR: invalid size format '%s'\n", opt);
                    return 1;
                } else if (w < 1) {
                    fprintf(stderr, "ERROR: invalid width %d, must be >= 1\n",
                            w);
                    return 1;
                } else if (h < 1) {
                    fprintf(stderr, "ERROR: invalid height %d, must be >= 1\n",
                            h);
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
        } else if (strncasecmp(opt, "-bg=", sizeof("-bg=") - 1) == 0) {
            char *end = NULL, tmp[3] = {0, 0, 0};
            opt += sizeof("-bg=") - 1;
            if (opt[0] == '#')
                opt++;

            if (strlen(opt) < 6) {
                fprintf(stderr, "ERROR: invalid color '%s'\n", opt);
                return 1;
            }

            cr = strtol(memcpy(tmp, opt, 2), &end, 16);
            if (!end || *end != '\0') {
                fprintf(stderr, "ERROR: invalid hex color value '%s'\n", tmp);
                return 1;
            }
            opt += 2;

            cg = strtol(memcpy(tmp, opt, 2), &end, 16);
            if (!end || *end != '\0') {
                fprintf(stderr, "ERROR: invalid hex color value '%s'\n", tmp);
                return 1;
            }
            opt += 2;

            cb = strtol(memcpy(tmp, opt, 2), &end, 16);
            if (!end || *end != '\0') {
                fprintf(stderr, "ERROR: invalid hex color value '%s'\n", tmp);
                return 1;
            }
            opt += 2;

            if (*opt != '\0') {
                ca = strtol(memcpy(tmp, opt, 2), &end, 16);
                if (!end || *end != '\0') {
                    fprintf(stderr, "ERROR: invalid hex color value '%s'\n",
                            tmp);
                    return 1;
                }
            }
        }
    }

    ecore_evas_init();
    ecore_init();
    evas_init();

    ee = ecore_evas_new(NULL, 0, 0, 1, 1, NULL);
    bg = evas_object_rectangle_add(ecore_evas_get(ee));
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
        } else if (w < 1 && h < 1) {

            if (iw > 1920) {
                w = 1920;
                h = ceil(ih * (double)1920 / (double)iw);
            } else if (ih > 1920) {
                h = 1920;
                w = ceil(iw * (double)1920 / (double)ih);
            } else {
                w = iw;
                h = ih;
            }
        } else {
            if (w < 1)
                w = ceil(iw * (double)h / (double)ih);
            else
                h = ceil(ih * (double)w / (double)iw);
        }

        if (iw != w && ih != h)
            evas_object_image_load_size_set(img, w, h);
    }

    evas_object_image_fill_set(img, 0, 0, w, h);
    evas_object_resize(img, w, h);
    evas_object_show(img);

    evas_object_image_alpha_set(bridge, evas_object_image_alpha_get(img));
    evas_object_image_fill_set(bridge, 0, 0, w, h);
    evas_object_image_size_set(bridge, w, h);
    evas_object_resize(bridge, w, h);
    evas_object_show(bridge);

    if (evas_object_image_alpha_get(img)) {
        if (ca < 0)
            ca = 0;
    } else {
        if (ca < 0)
            ca = 255;
    }

    if (ca < 1)
        evas_object_color_set(bg, 0, 0, 0, 0);
    else
        evas_object_color_set(bg,
                              cr * 255 / ca, cg * 255 / ca, cb * 255 / ca, ca);

    ecore_evas_alpha_set(ee, ca < 255);

    evas_object_resize(bg, w, h);
    evas_object_show(bg);

    ecore_evas_resize(ee, w, h);
    ecore_evas_show(ee);

    ecore_main_loop_begin();

  end:
    evas_object_del(img);
    evas_object_del(bridge);
    ecore_evas_free(ee);

    evas_shutdown();
    ecore_shutdown();
    ecore_evas_shutdown();

    return r;
}
