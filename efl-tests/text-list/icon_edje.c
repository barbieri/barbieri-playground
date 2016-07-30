#include "icon.h"
#include <Edje.h>
#include <stdlib.h>
#include <stdio.h> /* XXXXX */

#define LABEL "label"
#define IMAGE "image"

static inline Evas_Smart *_icon_get_smart(void);

struct priv
{
    Evas_Object *edje;
    Evas_Object *image;
    Evas_Coord w;
    Evas_Coord h;
};

#define DECL_PRIV(o) struct priv *priv = evas_object_smart_data_get((o))
#define RETURN_IF_ZERO(v) do { if ((v) == 0) return; } while (0)

/***********************************************************************
 * Public API
 **********************************************************************/
Evas_Object *
icon_new(Evas *evas)
{
    Evas_Object *obj;

    obj = evas_object_smart_add(evas, _icon_get_smart());

    return obj;
}

static void
_image_recalc_size(Evas_Object *o)
{
    Evas_Coord x, y, iw, ih, nw, nh;
    DECL_PRIV(o);
    double pw, ph, p;

    RETURN_IF_ZERO(priv->w);
    RETURN_IF_ZERO(priv->h);

    evas_object_image_size_get(priv->image, &iw, &ih);
    RETURN_IF_ZERO(iw);
    RETURN_IF_ZERO(ih);

    pw = (double)priv->w / (double)iw;
    ph = (double)priv->h / (double)ih;

    p = pw;
    if (p > ph)
        p = ph;

    nw = iw * p;
    nh = ih * p;
    x = (priv->w - nw) / 2;
    y = (priv->h - nh) / 2;

    edje_extern_object_aspect_set(priv->image, EDJE_ASPECT_CONTROL_BOTH,
                                  nw, nh);
    evas_object_image_fill_set(priv->image, 0, 0, nw, nh);
}

void
icon_image_set(Evas_Object *o, const char *path)
{
    DECL_PRIV(o);

    edje_object_freeze(priv->edje);

    evas_object_image_file_set(priv->image, path, NULL);
    _image_recalc_size(o);

    edje_object_thaw(priv->edje);
}

void
icon_text_set(Evas_Object *o, const char *text)
{
    DECL_PRIV(o);

    edje_object_part_text_set(priv->edje, LABEL, text);
}

void
icon_freeze(Evas_Object *o)
{
    DECL_PRIV(o);

    edje_object_freeze(priv->edje);
}

void
icon_thaw(Evas_Object *o)
{
    DECL_PRIV(o);

    edje_object_thaw(priv->edje);
}


/***********************************************************************
 * Private API
 **********************************************************************/
static void
_icon_add(Evas_Object *o)
{
    struct priv *priv;
    Evas *evas;
    const char *theme;
    int w, h;

    priv = calloc(1, sizeof(*priv));
    if (!priv)
        return;

    evas_object_smart_data_set(o, priv);
    evas = evas_object_evas_get(o);
    theme = evas_object_data_get(o, "edje_file");

    if (!theme)
        theme = evas_hash_find(evas_data_attach_get(evas), "edje_file");

    if (!theme) {
        fprintf(stderr, "No edje_file found on evas or icon_edje object.\n");
        return;
    }

    priv->edje = edje_object_add(evas);
    evas_object_smart_member_add(priv->edje, o);
    edje_object_file_set(priv->edje, theme, "icon_edje");
    edje_object_size_min_get(priv->edje, &w, &h);
    evas_object_resize(priv->edje, w, h);
    evas_object_resize(o, w, h);

    edje_object_part_geometry_get(priv->edje, IMAGE, NULL, NULL,
                                  &priv->w, &priv->h);

    priv->image = evas_object_image_add(evas_object_evas_get(o));
    evas_object_smart_member_add(priv->image, o);
    edje_object_part_swallow(priv->edje, IMAGE, priv->image);
}

static void
_icon_del(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_del(priv->image);
    evas_object_del(priv->edje);
    free(priv);
}

static void
_icon_move(Evas_Object *o, Evas_Coord x, Evas_Coord y)
{
    DECL_PRIV(o);

    evas_object_move(priv->edje, x, y);
}

static void
_icon_resize(Evas_Object *o, Evas_Coord w, Evas_Coord h)
{
    DECL_PRIV(o);

    edje_object_freeze(priv->edje);

    evas_object_resize(priv->edje, w, h);
    _image_recalc_size(o);

    edje_object_thaw(priv->edje);


    edje_object_part_geometry_get(priv->edje, IMAGE, NULL, NULL,
                                  &priv->w, &priv->h);
}

static void
_icon_show(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_show(priv->edje);
}

static void
_icon_hide(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_hide(priv->edje);
}

static void
_icon_color_set(Evas_Object *o, int r, int g, int b, int a)
{
    DECL_PRIV(o);

    evas_object_color_set(priv->edje, r, g, b, a);
}

static void
_icon_clip_set(Evas_Object *o, Evas_Object *clip)
{
    DECL_PRIV(o);

    evas_object_clip_set(priv->edje, clip);
}

static void
_icon_clip_unset(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_clip_unset(priv->edje);
}

static inline Evas_Smart *
_icon_get_smart(void)
{
    static Evas_Smart_Class cls = {
        .name = "icon_edje",
        .version = EVAS_SMART_CLASS_VERSION,
        .add = _icon_add,
        .del = _icon_del,
        .move = _icon_move,
        .resize = _icon_resize,
        .show = _icon_show,
        .hide = _icon_hide,
        .color_set = _icon_color_set,
        .clip_set = _icon_clip_set,
        .clip_unset = _icon_clip_unset,
        .data = NULL
    };
    static Evas_Smart *smart = NULL;

    if (!smart)
        smart = evas_smart_class_new(&cls);

    return smart;
}
