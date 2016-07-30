/**
 *  Icon Evas_Smart object, based on http://rephorm.com/rephorm/code/smartobj/
 */

#include "icon.h"
#include <stdlib.h>

static inline Evas_Smart *_icon_get_smart(void);
static void _icon_rearrange(Evas_Object *o, Evas_Coord *x, Evas_Coord *y, Evas_Coord *w, Evas_Coord *h);
static void _icon_fix_size(Evas_Object *o);

struct priv
{
    Evas_Object *image;
    Evas_Object *label;
    int padding;
};

#define DECL_PRIV(o) struct priv *priv = evas_object_smart_data_get((o))

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

void
icon_image_set(Evas_Object *o, const char *path)
{
    Evas_Coord w, h;
    DECL_PRIV(o);

    evas_object_image_file_set(priv->image, path, NULL);
    evas_object_image_size_get(priv->image, &w, &h);
    evas_object_resize(priv->image, w, h);
    evas_object_image_fill_set(priv->image, 0, 0, w, h);
    _icon_fix_size(o);
    _icon_rearrange(o, NULL, NULL, NULL, NULL);
}

void
icon_font_set(Evas_Object *o, const char *font, int size)
{
    DECL_PRIV(o);

    evas_object_text_font_set(priv->label, font, size);
    _icon_fix_size(o);
    _icon_rearrange(o, NULL, NULL, NULL, NULL);
}

void
icon_text_set(Evas_Object *o, const char *text)
{
    DECL_PRIV(o);

    evas_object_text_text_set(priv->label, text);
    _icon_fix_size(o);
    _icon_rearrange(o, NULL, NULL, NULL, NULL);
}

void
icon_freeze(Evas_Object *o)
{
}

void
icon_thaw(Evas_Object *o)
{
}


/***********************************************************************
 * Private API
 **********************************************************************/
static void
_icon_add(Evas_Object *o)
{
    struct priv *priv;
    Evas *evas;

    priv = malloc(sizeof(*priv));
    if (!priv)
        return;

    evas_object_smart_data_set(o, priv);
    evas = evas_object_evas_get(o);

    priv->padding = 3;

    priv->image = evas_object_image_add(evas);
    evas_object_smart_member_add(o, priv->image);

    priv->label = evas_object_text_add(evas);
    evas_object_smart_member_add(o, priv->label);
    evas_object_text_font_set(priv->label, "Sans", 10);
    evas_object_text_text_set(priv->label, "No-Name");
    evas_object_color_set(priv->label, 0, 0, 0, 255);
}

static void
_icon_del(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_del(priv->image);
    evas_object_del(priv->label);
    free(priv);
}

static inline Evas_Coord
_center(Evas_Coord offset, Evas_Coord slot, Evas_Coord width)
{
    return offset + (slot - width) / 2;
}

static void
_icon_move(Evas_Object *o, Evas_Coord x, Evas_Coord y)
{
    _icon_rearrange(o, &x, &y, NULL, NULL);
}

static void
_icon_resize(Evas_Object *o, Evas_Coord w, Evas_Coord h)
{
    _icon_rearrange(o, NULL, NULL, &w, &h);
}

static void
_icon_show(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_show(priv->image);
    evas_object_show(priv->label);
}

static void
_icon_hide(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_hide(priv->image);
    evas_object_hide(priv->label);
}

static void
_icon_rearrange(Evas_Object *o,
                       Evas_Coord *px,
                       Evas_Coord *py,
                       Evas_Coord *pw,
                       Evas_Coord *ph)
{
    Evas_Coord x, y, w, h, iw, ih, lw, lh;
    DECL_PRIV(o);

    evas_object_geometry_get(o, &x, &y, &w, &h);
    evas_object_geometry_get(priv->image, NULL, NULL, &iw, &ih);
    evas_object_geometry_get(priv->label, NULL, NULL, &lw, &lh);

    if (px)
        x = *px;
    if (py)
        y = *py;
    if (pw)
        w = *pw;
    if (ph)
        h = *ph;

    evas_object_move(priv->image, _center(x, w, iw),
                     _center(y, h, ih + lh + priv->padding));
    evas_object_move(priv->label, _center(x, w, lw),
                     _center(y, h, ih + priv->padding) + ih + priv->padding);
}

static void
_icon_fix_size(Evas_Object *o)
{
    Evas_Coord x, y, w, h, iw, ih, lw, lh, nw, nh;
    DECL_PRIV(o);

    evas_object_geometry_get(o, &x, &y, &w, &h);
    evas_object_geometry_get(priv->image, NULL, NULL, &iw, &ih);
    evas_object_geometry_get(priv->label, NULL, NULL, &lw, &lh);

    nw = w;
    if (nw < iw + lw + priv->padding)
        nw = iw + lw + priv->padding;

    nh = h;
    if (nh < ih + lh + priv->padding)
        nh = ih + lh + priv->padding;

    if (nw != w || nh != h)
        evas_object_resize(o, nw, nh);
}

static inline Evas_Smart *
_icon_get_smart(void)
{
    static Evas_Smart *smart = NULL;

    if (!smart) {
        smart = evas_smart_new("icon",
                               _icon_add,
                               _icon_del,
                               NULL, /* layer_set */
                               NULL, /* raise */
                               NULL, /* lower */
                               NULL, /* stack_above */
                               NULL, /* stack_below */
                               _icon_move,
                               _icon_resize,
                               _icon_show,
                               _icon_hide,
                               NULL, /* color_set */
                               NULL, /* clip_set */
                               NULL, /* clip_unset */
                               NULL /* data */
            );
    }

    return smart;
}
