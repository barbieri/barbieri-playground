#define _GNU_SOURCE
#include "vlist.h"
#include <Ecore.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h> /* XXXXX */
#include <stdarg.h>
#include <strings.h>
#include <assert.h>
#include <sys/time.h>

#define DATA_KEY "vlist_node"

#define F_PRECISION 0.00001

static int _vlist_error = VLIST_ERROR_NONE;
static inline Evas_Smart *_vlist_get_smart(void);

struct scroll_param
{
    double y;
    vlist_scroll_dir_t dir;
    struct timeval t0;
    int y0;
    int y1;
    double v0;
    double accel;
    enum {
        STOP_NONE = 0,
        STOP_CHECK = 1
    } stop;
};

struct priv
{
    Evas_Object *self;
    Evas *evas;
    int frozen;
    int dirty;
    int centered_selected_item;
    int selected_item_offset;
    Evas_Coord item_h;
    Evas_List *contents;         /**< list of void pointer */
    Evas_List *objs;             /**< list of Evas_Object */
    Evas_List *selected_content; /**< pointer to node with void pointer */
    int selected_index;          /**< index of selected item */
    Evas_List *last_used_obj;    /**< pointer to node with Evas_Object */
    Evas_List *first_used_obj;   /**< pointer to node with Evas_Object */
    Evas_Object *clip;
    struct {
        Evas_Coord x;
        Evas_Coord y;
        Evas_Coord w;
        Evas_Coord h;
    } geometry;
    struct {
        struct scroll_param param;
        struct {
            double speed;
            double accel;
            double min_stop_speed;
        } init;
        Ecore_Animator *anim;
    } scroll;
    struct {
        vlist_selection_changed_cb_t selection_changed;
    } callback;
    struct {
        void *selection_changed;
    } callback_data;
    vlist_row_ops_t row_ops;
    void *row_ops_data;
};

#define DECL_PRIV(o)                                                    \
   struct priv *priv = evas_object_smart_data_get((o))
#define DECL_PRIV_SAFE(o)                                               \
   struct priv *priv = (o) ? evas_object_smart_data_get((o)) : NULL
#define DECL_SCROLL_PARAM(priv)                                         \
   struct scroll_param *scroll_param = &(priv)->scroll.param
#define DECL_SCROLL_PARAM_CONST(priv)                                   \
   const struct scroll_param *scroll_param = &(priv)->scroll.param
#define DECL_SCROLL_PARAM_SAFE(priv)                                    \
   struct scroll_param *scroll_param = (priv) ? &(priv)->scroll.param : NULL

#define RETURN_IF_ZERO(v)                                               \
   do { if ((v) == 0) return; } while (0)
#define RETURN_IF_NULL(v)                                               \
   do { if ((v) == NULL) return; } while(0)
#define RETURN_VAL_IF_NULL(v, r)                                        \
   do { if ((v) == NULL) return (r); } while(0)

#ifndef NDEBUG
static inline void
_dbg(const char *file, int line, const char *func, const char *fmt, ...)
{
    va_list ap;
    const char *f;

    f = rindex(file, '/');
    if (!f)
        f = file;

    fprintf(stderr, "%s:%d:%s() ", f, line, func);

    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);

    fputc('\n', stderr);
}
#else
static inline void
_dbg(const char *file, int line, const char *func, const char *fmt, ...)
{}
#endif
#define DBG(fmt, ...)                                                   \
   _dbg(__FILE__, __LINE__, __FUNCTION__, fmt, ## __VA_ARGS__)

static inline unsigned long
tv2ms(const struct timeval *tv)
{
    return tv->tv_sec * 1000 + tv->tv_usec / 1000;
}

static inline int
in_interval(const double d, const double delim)
{
    return d < delim && d > -delim;
}

static inline int
is_zero(const double d)
{
    return in_interval(d, F_PRECISION);
}

static inline void
_freeze(struct priv *priv)
{
    priv->frozen++;

    if (priv->frozen == 1) {
        evas_event_freeze(priv->evas);
        if (priv->row_ops.freeze) {
            vlist_row_freeze_t func = priv->row_ops.freeze;
            Evas_List *itr;

            for (itr = priv->objs; itr != NULL; itr = itr->next)
                func(priv->self, itr->data, priv->row_ops_data);
        }
    }
}

static void _vlist_recalc(struct priv *priv);


static inline void
_thaw(struct priv *priv)
{
    priv->frozen--;

    if (priv->frozen == 0) {
        if (priv->dirty)
            _vlist_recalc(priv);

        if (priv->row_ops.thaw) {
            vlist_row_thaw_t func = priv->row_ops.thaw;
            Evas_List *itr;

            for (itr = priv->objs; itr != NULL; itr = itr->next)
                func(priv->self, itr->data, priv->row_ops_data);
        }

        evas_event_thaw(priv->evas);
    } else if (priv->frozen < 0) {
        DBG("Thaw count larger than freeze! (frozen=%d)", priv->frozen);
        priv->frozen = 0;
    }
}

void
vlist_freeze(Evas_Object *o)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    _freeze(priv);
}

void
vlist_thaw(Evas_Object *o)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    _thaw(priv);
}

static inline void
_obj_content_node_del(struct priv *priv, Evas_Object *child)
{
    evas_object_data_del(child, DATA_KEY);
    priv->row_ops.set(priv->self, child, NULL, priv->row_ops_data);
}

static inline Evas_List *
_obj_content_node_get(Evas_Object *child)
{
    return evas_object_data_get(child, DATA_KEY);
}

static inline void
_obj_content_node_set(struct priv *priv, Evas_Object *child, Evas_List *node)
{
    if (priv->row_ops.freeze)
        priv->row_ops.freeze(priv->self, child, priv->row_ops_data);
    _obj_content_node_del(priv, child);

    priv->row_ops.set(priv->self, child,
                      node ? node->data : NULL, priv->row_ops_data);

    evas_object_data_set(child, DATA_KEY, node);
    if (priv->row_ops.thaw)
        priv->row_ops.thaw(priv->self, child, priv->row_ops_data);
}

static inline int
_vlist_elapsed_ms(const struct priv *priv, const struct timeval *tv)
{
    struct timeval dif;
    int t;

    timersub(tv, &priv->scroll.param.t0, &dif);
    t = tv2ms(&dif);

    return t;
}

static inline int
_vlist_elapsed_ms_now(const struct priv *priv)
{
    struct timeval now;

    gettimeofday(&now, NULL);
    return _vlist_elapsed_ms(priv, &now);
}

static inline double
_vlist_pos_at_ms(const struct priv *priv, const int t)
{
    DECL_SCROLL_PARAM_CONST(priv);

    return  scroll_param->y0 + scroll_param->v0 * t +
        scroll_param->accel * t * t / 2;
}

static inline double
_vlist_pos_at_tv(const struct priv *priv, const struct timeval *tv)
{
    int t;

    t = _vlist_elapsed_ms(priv, tv);
    return _vlist_pos_at_ms(priv, t);
}

static inline double
_vlist_pos_now(const struct priv *priv)
{
    int t;

    t = _vlist_elapsed_ms_now(priv);
    return _vlist_pos_at_ms(priv, t);
}

static inline double
_vlist_speed_at_ms(const struct priv *priv, const int t)
{
    DECL_SCROLL_PARAM_CONST(priv);

    return scroll_param->v0 + scroll_param->accel * t;
}

static inline double
_vlist_speed_at_tv(const struct priv *priv, const struct timeval *tv)
{
    int t;

    t = _vlist_elapsed_ms(priv, tv);
    return _vlist_speed_at_ms(priv, t);
}

static inline double
_vlist_speed_now(const struct priv *priv)
{
    int t;

    t = _vlist_elapsed_ms_now(priv);
    return _vlist_speed_at_ms(priv, t);
}

void
_vlist_print(struct priv *priv)
{
    Evas_List *cont_itr, *obj_itr, *first_cont;
    int window, window_count, cont_count, correct_index;
    int bug_last, bug_first, bug_selected, bug_index;

    correct_index = -1;
    bug_last = 0;
    bug_first = 0;
    bug_selected = priv->contents && !priv->selected_content;
    window_count = 0;

    obj_itr = priv->objs;

    fprintf(stderr,
            "STAT.   CONT.ITR.     OBJECT CONTENT\n"
            "-----   --------- ---------- ------\n");

    first_cont = obj_itr ? _obj_content_node_get(obj_itr->data) : NULL;
    while (!first_cont && obj_itr && obj_itr->next) {
        int last, first;

        last = (obj_itr == priv->last_used_obj);
        if (last)
            bug_last = 1;

        first = (obj_itr == priv->first_used_obj);
        if (first)
            bug_first = 1;

        fprintf(stderr,
                "[ W %c%c] %10p %10p %p%s\n",
                first ? 'F' : ' ',
                last ? 'L' : ' ',
                NULL, obj_itr->data, NULL,
                last ? " BUG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" : "");

        obj_itr = obj_itr->next;
        first_cont = _obj_content_node_get(obj_itr->data);
        window_count++;
    }

    window = 0;
    bug_index = 0;
    cont_itr = priv->contents;
    cont_count = 0;
    for (; cont_itr != NULL; cont_itr = cont_itr->next, cont_count++) {
        int selected, last, first;
        char pos[1024] = "";

        selected = 0;
        if (first_cont == cont_itr && obj_itr) {
            window = 1;
            first_cont = first_cont->next;
        }

        if (!obj_itr)
            window = 0;

        if (window)
            window_count++;

        if (priv->selected_content == cont_itr) {
            DECL_SCROLL_PARAM(priv);

            if (window_count != priv->selected_item_offset + 2)
                bug_selected = 2;

            if (!window)
                bug_selected = 3;

            if (priv->selected_index != cont_count) {
                bug_index = 1;
                correct_index = cont_count;
            }

            selected = 1;
            sprintf(pos, " idx=%d y=%0.3f (%d, %d), y0=%03d v=%0.4f, a=%0.4f",
                    priv->selected_index,
                    scroll_param->y, -priv->item_h, priv->item_h,
                    scroll_param->y0, scroll_param->v0, scroll_param->accel);
        } else
            pos[0] = '\0';

        last = (window && obj_itr == priv->last_used_obj);
        if (last && !(cont_itr->next == NULL || obj_itr->next == NULL))
            bug_last = 1;

        first = (window && obj_itr == priv->first_used_obj);
        if (first && !(cont_itr->prev == NULL || obj_itr->prev == NULL))
            bug_first = 1;


        if ((selected && (bug_selected || bug_index)) ||
            (last && bug_last) ||
            (first && bug_first))
            strcat(pos, "    BUG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");

        fprintf(stderr,
                "[C%c%c%c%c] %10p %10p %p%s\n",
                window ? 'W' : ' ',
                selected ? 'S' : ' ',
                first ? 'F' : ' ',
                last ? 'L' : ' ',
                cont_itr,
                (window && obj_itr) ? obj_itr->data : NULL,
                cont_itr->data,
                pos);

        if (window && obj_itr)
            obj_itr = obj_itr->next;
    }


    for (; obj_itr; obj_itr = obj_itr->next) {
        int last, first;

        last = (obj_itr == priv->last_used_obj);
        if (last)
            bug_last = 1;

        first = (obj_itr == priv->first_used_obj);
        if (first)
            bug_first = 1;

        fprintf(stderr,
                "[ W %c%c] %10p %10p %p%s\n",
                first ? 'F' : ' ',
                last ? 'L' : ' ',
                NULL, obj_itr->data, NULL,
                last ? " BUG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" : "");
    }

    fprintf(stderr,
            "-----   --------- ---------- ------\n"
            "STAT.   CONT.ITR.     OBJECT CONTENT\n");

    if (bug_last || bug_selected || bug_index) {
        fprintf(stderr, "\nBUG REPORT:\n");

        if (bug_last)
            fprintf(stderr, "\tLAST: priv->last_used_obj is not correct!\n");


        switch (bug_selected) {
        case 1:
            fprintf(stderr,
                    "\tSELECTED: priv->selected_content not set, but "
                    "priv->contents != NULL\n");
            break;
        case 2:
            fprintf(stderr,
                    "\tSELECTED: priv->selected_content is not the %d pos of "
                    "window\n", priv->selected_item_offset + 2);
            break;
        case 3:
            fprintf(stderr,
                    "\tSELECTED: priv->selected_content out of window\n");
            break;
        default:
            break;
        }

        if (bug_index)
            fprintf(stderr, "\tINDEX: priv->selected_index (%d) is not "
                    "correct (%d)!\n",
                    priv->selected_index, correct_index);

        fprintf(stderr, "\n\n");
    }

    for (obj_itr = priv->objs; obj_itr; obj_itr = obj_itr->next) {
        Evas_List *cont;
        void *item;

        cont = _obj_content_node_get(obj_itr->data);
        item = cont ? cont->data : NULL;

        fprintf(stderr, "cont=%10p, obj=%10p    %p\n",
                cont, obj_itr->data, item);
    }

    if (priv->frozen)
        fprintf(stderr, "Frozen count=%d\n", priv->frozen);

    assert(!bug_last && !bug_selected && !bug_index);
}

#ifdef VLIST_DEBUG
#define DBG_INTERNALS(priv, fmt, ...)                                       \
   do {                                                                     \
      _dbg(__FILE__, __LINE__, __FUNCTION__, fmt, ## __VA_ARGS__);          \
      _vlist_print(priv);                                                   \
      _dbg(__FILE__, __LINE__, __FUNCTION__, fmt, ## __VA_ARGS__);          \
   } while(0)
#else
#define DBG_INTERNALS(priv, fmt, ...)                                       \
   _dbg(__FILE__, __LINE__, __FUNCTION__, fmt, ## __VA_ARGS__)
#endif /* VLIST_DEBUG */

static inline int
_vlist_fill_objs(struct priv *priv, Evas_List *obj_itr, Evas_List *cont_itr)
{
    int i;

    if (!priv->first_used_obj)
        priv->first_used_obj = obj_itr;

    i = 0;
    while (obj_itr && cont_itr) {
        priv->last_used_obj = obj_itr;
        _obj_content_node_set(priv, obj_itr->data, cont_itr);

        obj_itr = obj_itr->next;
        cont_itr = cont_itr->next;
        i++;
    }

    return i;
}

static inline void
_vlist_fill_blanks(struct priv *priv)
{
    Evas_List *itr;

    if (priv->last_used_obj)
        itr = priv->last_used_obj->next;
    else
        itr = priv->objs;

    for (; itr != NULL; itr = itr->next)
        _obj_content_node_set(priv, itr->data, NULL);

    if (priv->first_used_obj)
        for (itr = priv->first_used_obj->prev; itr != NULL; itr = itr->prev)
            _obj_content_node_set(priv, itr->data, NULL);
}

static void
_vlist_emit_selection_changed(struct priv *priv)
{
    if (!priv->callback.selection_changed || !priv->selected_content)
        return;

    priv->callback.selection_changed(priv->self,
                                     priv->selected_content->data,
                                     priv->selected_index,
                                     priv->callback_data.selection_changed);
}

static void
_vlist_recalc(struct priv *priv)
{
    Evas_List *obj_itr, *cont_itr, *prev_selected;

    if (priv->frozen > 0) {
        priv->dirty = 1;
        return;
    }

    prev_selected = priv->selected_content;

    if (priv->last_used_obj) {
        obj_itr = priv->last_used_obj->next;
        cont_itr = _obj_content_node_get(priv->last_used_obj->data);
        if (cont_itr)
            cont_itr = cont_itr->next;
    } else {
        int i;

        if (!priv->selected_content) {
            priv->selected_content = priv->contents;
            if (priv->contents)
                priv->selected_index = 0;
            else
                priv->selected_index = -1;
        }

        i = priv->selected_item_offset + 1;
        cont_itr = priv->selected_content;
        /* go to first (previous) possible content */
        if (cont_itr)
            for (; i > 0 && cont_itr->prev; i--)
                cont_itr = cont_itr->prev;

        obj_itr = priv->objs;
        /* if not enough content, skip those empty */
        for (; i > 0 && obj_itr; i--)
            obj_itr = obj_itr->next;
        priv->first_used_obj = obj_itr;
    }
    _vlist_fill_objs(priv, obj_itr, cont_itr);
    _vlist_fill_blanks(priv);
    DBG_INTERNALS(priv, "After recalc");

    /* check current item */
    if (prev_selected != priv->selected_content)
        _vlist_emit_selection_changed(priv);

    priv->dirty = 0;
}

static inline int
_vlist_can_scroll(struct priv *priv, vlist_scroll_dir_t dir)
{
    if (dir == VLIST_SCROLL_DIR_DOWN)
        return !!priv->selected_content->next;
    else
        return !!priv->selected_content->prev;
}

static inline void
_vlist_update_objs_pos(struct priv *priv)
{
    Evas_List *itr;
    Evas_Coord x, y;

    x = priv->geometry.x;
    y = priv->geometry.y + priv->scroll.param.y - priv->item_h;

    for (itr = priv->objs; itr != NULL; itr = itr->next) {
        Evas_Object *child;

        child = itr->data;
        evas_object_move(child, x, y);
        y += priv->item_h;
    }
}

/*
 * Promote last item to head, rotating upwards.
 *
 * Assumes:
 *  * items_over < evas_list_count(priv->objs)
 *  * priv->first_used_obj != NULL
 *  * priv->selected_content != NULL
 */
static inline int
_vlist_scroll_fix_y_up(struct priv *priv, int items_over)
{
    Evas_List *last, *cont_itr;

    assert(priv->first_used_obj != NULL);
    assert(priv->selected_content != NULL);

    last = evas_list_last(priv->objs);

    cont_itr = _obj_content_node_get(priv->first_used_obj->data);
    cont_itr = cont_itr->prev;

    for (; priv->selected_content->prev && items_over > 0; items_over--) {
        Evas_List *tmp;
        Evas_Object *child;

        child = last->data;

        tmp = last->prev;
        if (priv->last_used_obj == last)
            priv->last_used_obj = tmp;

        priv->objs = evas_list_promote_list(priv->objs, last);
        last = tmp;

        _obj_content_node_set(priv, child, cont_itr);
        if (cont_itr) {
            cont_itr = cont_itr->prev;
            priv->first_used_obj = priv->objs;
        }

        priv->selected_content = priv->selected_content->prev;
        priv->selected_index--;
    }

    return items_over == 0;
}

/*
 * Remove head, append it's data, rotating downwards
 *
 * Assumes:
 *  * items_over < evas_list_count(priv->objs)
 *  * priv->last_used_obj != NULL
 *  * priv->selected_content != NULL
 */
static inline int
_vlist_scroll_fix_y_down(struct priv *priv, int items_over)
{
    Evas_List *cont_itr;

    assert(priv->last_used_obj != NULL);
    assert(priv->selected_content != NULL);

    cont_itr = _obj_content_node_get(priv->last_used_obj->data);
    cont_itr = cont_itr->next;

    for (; priv->selected_content->next && items_over > 0; items_over--) {
        Evas_Object *child;

        child = priv->objs->data;

        if (priv->first_used_obj == priv->objs)
            priv->first_used_obj = priv->objs->next;

        priv->objs = evas_list_remove_list(priv->objs, priv->objs);
        priv->objs = evas_list_append(priv->objs, child);

        _obj_content_node_set(priv, child, cont_itr);
        if (cont_itr) {
            cont_itr = cont_itr->next;
            priv->last_used_obj = evas_list_last(priv->objs);
        }

        priv->selected_content = priv->selected_content->next;
        priv->selected_index++;
    }

    return items_over == 0;
}

/*
 * Walks up to the new selected content, then triggers recalc.
 *
 * Assumes:
 *  * priv->selected_content != NULL
 */
static inline int
_vlist_scroll_fix_y_up_complete(struct priv *priv, int items_over)
{
    Evas_List *cont_itr;

    assert(priv->selected_content);

    cont_itr = priv->selected_content;
    for (; cont_itr->prev && items_over > 0; items_over--) {
        cont_itr = cont_itr->prev;
        priv->selected_content--;
    }

    priv->selected_content = cont_itr;
    priv->first_used_obj = NULL;
    priv->last_used_obj = NULL;
    _vlist_recalc(priv);

    return items_over == 0;
}

/*
 * Walks down to the new selected content, then triggers recalc.
 *
 * Assumes:
 *  * priv->selected_content != NULL
 */
static inline int
_vlist_scroll_fix_y_down_complete(struct priv *priv, int items_over)
{
    Evas_List *cont_itr;

    assert(priv->selected_content);

    cont_itr = priv->selected_content;
    for (; cont_itr->next && items_over > 0; items_over--) {
        cont_itr = cont_itr->next;
        priv->selected_content++;
    }

    priv->selected_content = cont_itr;
    priv->first_used_obj = NULL;
    priv->last_used_obj = NULL;
    _vlist_recalc(priv);

    return items_over == 0;
}

static inline int
_vlist_scroll_fix_y(struct priv *priv, double *py, const struct timeval now)
{
    DECL_SCROLL_PARAM(priv);
    Evas_List *prev_selected;
    int items_over, y, t, r;

    DBG("y=%f", *py);

    r = -1;

    prev_selected = priv->selected_content;

    y = (*py);

    items_over = y / priv->item_h;
    *py = y % priv->item_h;

    t = _vlist_elapsed_ms(priv, &now);
    scroll_param->y0 = *py;
    scroll_param->t0 = now;
    scroll_param->v0 = _vlist_speed_at_ms(priv, t);

    if (items_over < 0)
        items_over = -items_over;

    /* Check if to do rotation and how to do it */
    if (items_over > evas_list_count(priv->objs)) {
        if (scroll_param->dir == VLIST_SCROLL_DIR_DOWN)
            r = _vlist_scroll_fix_y_down_complete(priv, items_over);
        else if (scroll_param->dir == VLIST_SCROLL_DIR_UP)
            r = _vlist_scroll_fix_y_up_complete(priv, items_over);
    } else {
        if (scroll_param->dir == VLIST_SCROLL_DIR_DOWN)
            r = _vlist_scroll_fix_y_down(priv, items_over);
        else if (scroll_param->dir == VLIST_SCROLL_DIR_UP)
            r =  _vlist_scroll_fix_y_up(priv, items_over);
    }

    /* check current item */
    if (prev_selected != priv->selected_content)
        _vlist_emit_selection_changed(priv);

    assert(r != -1);

    return r;
}

static void
_vlist_scroll_end(struct priv *priv)
{
    DECL_SCROLL_PARAM(priv);

    if (priv->scroll.anim) {
        ecore_animator_del(priv->scroll.anim);
        priv->scroll.anim = NULL;
    }
    scroll_param->stop = STOP_NONE;
    scroll_param->dir = VLIST_SCROLL_DIR_NONE;
    scroll_param->v0 = 0.0;
    scroll_param->accel = 0.0;
}

static int
_vlist_scroll(void *data)
{
    Evas_Object *o = (Evas_Object *)data;
    DECL_PRIV(o);
    DECL_SCROLL_PARAM(priv);
    struct timeval now;
    int t, r;
    double y, v;

    if (!priv->selected_content ||
        (is_zero(scroll_param->v0) && is_zero(scroll_param->accel))) {
        scroll_param->y = 0;
        _freeze(priv);
        _vlist_update_objs_pos(priv);
        _vlist_scroll_end(priv);
        _thaw(priv);
        return 0;
    }

    _freeze(priv);

    gettimeofday(&now, NULL);
    t = _vlist_elapsed_ms(priv, &now);
    y = _vlist_pos_at_ms(priv, t);
    v = _vlist_speed_at_ms(priv, t);

    if (scroll_param->stop == STOP_CHECK &&
        scroll_param->dir * v < F_PRECISION) {
        y = scroll_param->y1;
        r = 0;
        _vlist_scroll_fix_y(priv, &y, now);

    } else if (y < -priv->item_h || y > priv->item_h) {
        r = _vlist_scroll_fix_y(priv, &y, now);

        if (r)
            r = _vlist_can_scroll(priv, scroll_param->dir);

        if (r == 0)
            y = 0;

    } else
        r = 1;

    scroll_param->y = y;
    _vlist_update_objs_pos(priv);

    if (r == 0)
        _vlist_scroll_end(priv);

    _thaw(priv);

    DBG_INTERNALS(priv, "After scroll");

    return r;
}

/***********************************************************************
 * Public API
 **********************************************************************/
Evas_Object *
vlist_new(Evas *evas, int item_h, vlist_row_ops_t row_ops, void *user_data)
{
    Evas_Object *obj;
    struct priv *priv;

    _vlist_error = VLIST_ERROR_NONE;

    obj = evas_object_smart_add(evas, _vlist_get_smart());
    priv = evas_object_smart_data_get(obj);
    if (!priv) {
        evas_object_del(obj);
        return NULL;
    }

    priv->item_h = item_h;
    priv->row_ops = row_ops;
    priv->row_ops_data = user_data;

    return obj;
}

int
vlist_error_get(void)
{
    return _vlist_error;
}

void
vlist_conf_set(Evas_Object *o, int centered_selected_item,
               int selected_item_offset)
{
    DECL_PRIV(o);
    RETURN_IF_NULL(priv);

    if (selected_item_offset < 0)
        centered_selected_item = 1;

    priv->centered_selected_item = centered_selected_item;
    priv->selected_item_offset = selected_item_offset;

    priv->first_used_obj = NULL;
    priv->last_used_obj = NULL;
    _vlist_recalc(priv);
}

void
vlist_conf_get(Evas_Object *o, int *centered_selected_item,
               int *selected_item_offset)
{
    DECL_PRIV(o);
    RETURN_IF_NULL(priv);

    if (centered_selected_item)
        *centered_selected_item = priv->centered_selected_item;

    if (selected_item_offset)
        *selected_item_offset = priv->selected_item_offset;

}

void
vlist_scroll_conf_set(Evas_Object *o, double speed,  double accel,
                      double min_stop_speed)
{
    DECL_PRIV(o);
    RETURN_IF_NULL(priv);

    if (speed < 0.0)
        speed = -speed;

    if (accel < 0.0)
        accel = -accel;

    priv->scroll.init.speed = speed;
    priv->scroll.init.accel = accel;
    priv->scroll.init.min_stop_speed = min_stop_speed;
}

void
vlist_scroll_conf_get(Evas_Object *o, double *speed, double *accel,
                      double *min_stop_speed)
{
    DECL_PRIV(o);
    RETURN_IF_NULL(priv);

   if (speed)
        *speed = priv->scroll.init.speed;

    if (accel)
        *accel = priv->scroll.init.accel;

    if (min_stop_speed)
        *min_stop_speed = priv->scroll.init.min_stop_speed;
}

int
vlist_find(Evas_Object *o, const void *data)
{
    Evas_List *itr;
    int i;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, -1);

    for (itr = priv->contents, i = 0; itr != NULL; itr = itr->next, i++)
        if (itr->data == data)
            return i;

    return -1;
}

int
vlist_rfind(Evas_Object *o, const void *data)
{
    Evas_List *itr;
    int i;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, -1);

    i = evas_list_count(priv->contents) - 1;
    itr = evas_list_last(priv->contents);
    for (; itr != NULL; itr = itr->prev, i--)
        if (itr->data == data)
            return i;

    return -1;
}

int
vlist_search(Evas_Object *o, vlist_search_func_t func,
             const void *func_data, void **item_data)
{
    Evas_List *itr;
    int i;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, -1);

    for (itr = priv->contents, i = 0; itr != NULL; itr = itr->next, i++)
        if (func(o, func_data, itr->data)) {
            if (item_data)
                *item_data = itr->data;
            return i;
        }

    return -1;
}

int
vlist_rsearch(Evas_Object *o, vlist_search_func_t func,
              const void *func_data, void **item_data)
{
    Evas_List *itr;
    int i;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, -1);

    i = evas_list_count(priv->contents) - 1;
    itr = evas_list_last(priv->contents);
    for (; itr != NULL; itr = itr->prev, i--)
        if (func(o, func_data, itr->data)) {
            if (item_data)
                *item_data = itr->data;
            return i;
        }

    return -1;
}

void *
vlist_item_nth_get(Evas_Object *o, int index)
{
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    return evas_list_nth(priv->contents, index);
}

void *
vlist_item_nth_set(Evas_Object *o, int index, void *new_data)
{
    Evas_List *itr, *obj_itr;
    void *old_data;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    itr = evas_list_nth_list(priv->contents, index);
    if (!itr)
        return NULL;

    old_data = itr->data;
    itr->data = new_data;

    for (obj_itr = priv->objs; obj_itr != NULL; obj_itr = obj_itr->next)
        if (_obj_content_node_get(obj_itr->data) == itr) {
            _obj_content_node_set(priv, obj_itr->data, itr);
            break;
        }

    return old_data;
}

const Evas_List *
vlist_itr_nth(Evas_Object *o, int index)
{
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    return evas_list_nth_list(priv->contents, index);
}

const Evas_List *
vlist_itr_find(Evas_Object *o, const void *data)
{
    Evas_List *itr;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    for (itr = priv->contents; itr != NULL; itr = itr->next)
        if (itr->data == data)
            return itr;

    return NULL;
}

const Evas_List *
vlist_itr_rfind(Evas_Object *o, const void *data)
{
    Evas_List *itr;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    itr = evas_list_last(priv->contents);
    for (; itr != NULL; itr = itr->prev)
        if (itr->data == data)
            return itr;

    return NULL;
}

const Evas_List *
vlist_itr_search(Evas_Object *o, vlist_search_func_t func,
             const void *func_data, void **item_data)
{
    Evas_List *itr;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    for (itr = priv->contents; itr != NULL; itr = itr->next)
        if (func(o, func_data, itr->data)) {
            if (item_data)
                *item_data = itr->data;
            return itr;
        }

    return NULL;
}

const Evas_List *
vlist_itr_rsearch(Evas_Object *o, vlist_search_func_t func,
                  const void *func_data, void **item_data)
{
    Evas_List *itr;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    itr = evas_list_last(priv->contents);
    for (; itr != NULL; itr = itr->prev)
        if (func(o, func_data, itr->data)) {
            if (item_data)
                *item_data = itr->data;
            return itr;
        }

    return NULL;
}

void *
vlist_itr_item_get(Evas_Object *o, const Evas_List *itr)
{
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);
    RETURN_VAL_IF_NULL(itr, NULL);

    return itr->data;
}

void *
vlist_itr_item_set(Evas_Object *o, const Evas_List *itr, void *new_data)
{
    void *old_data;
    Evas_List *citr, *obj_itr;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);
    RETURN_VAL_IF_NULL(itr, NULL);

    citr = (Evas_List*)itr;

    old_data = citr->data;
    citr->data = new_data;

    for (obj_itr = priv->objs; obj_itr != NULL; obj_itr = obj_itr->next)
        if (_obj_content_node_get(obj_itr->data) == itr) {
            _obj_content_node_set(priv, obj_itr->data, (Evas_List *)itr);
            break;
        }

    return old_data;
}

void
vlist_append(Evas_Object *o, void *data)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    priv->contents = evas_list_append(priv->contents, data);
    _vlist_recalc(priv);
}

void
vlist_prepend(Evas_Object *o, void *data)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    priv->first_used_obj = NULL;
    priv->last_used_obj = NULL;
    priv->contents = evas_list_prepend(priv->contents, data);
    priv->selected_index++;
    _vlist_recalc(priv);
}

void *
vlist_remove(Evas_Object *o, void *data)
{
    Evas_List *itr;
    int selected_found;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);

    selected_found = 0;
    for (itr = priv->contents; itr != NULL; itr = itr->next) {
        if (priv->selected_content == itr)
            selected_found = 1;

        if (itr->data == data) {

            if (priv->selected_content == itr) {
                if (itr->prev) {
                    priv->selected_content = itr->prev;
                    priv->selected_index--;
                } else
                    priv->selected_content = itr->next;
            } else if (!selected_found)
                priv->selected_index--;

            priv->contents = evas_list_remove_list(priv->contents, itr);

            priv->first_used_obj = NULL;
            priv->last_used_obj = NULL;
            _vlist_recalc(priv);

            return data;
        }
    }

    return NULL;
}

static inline int
_is_node_before(const Evas_List *mark, const Evas_List *itr)
{
    for (; itr != NULL; itr = itr->prev)
        if (mark == itr)
            return 1;

    return 0;
}

static inline int
_is_node_after(const Evas_List *mark, const Evas_List *itr)
{
    for (; itr != NULL; itr = itr->next)
        if (mark == itr)
            return 1;

    return 0;
}

static inline int
_vlist_selected_is_after_node(const struct priv *priv, const Evas_List *itr)
{
    if (priv->selected_index * 2 < evas_list_count(priv->contents))
        return !_is_node_before(priv->selected_content, itr);
    else
        return _is_node_after(priv->selected_content, itr);
}

void
vlist_itr_append(Evas_Object *o, void *data, const Evas_List *itr)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    if (!itr) {
        vlist_append(o, data);
        return;
    }

    priv->first_used_obj = NULL;
    priv->last_used_obj = NULL;
    priv->contents = evas_list_append_relative_list(priv->contents, data,
                                                    (Evas_List *)itr);

    if (priv->selected_content != itr &&
        _vlist_selected_is_after_node(priv, itr))
        priv->selected_index++;

    _vlist_recalc(priv);
}

void
vlist_itr_prepend(Evas_Object *o, void *data, const Evas_List *itr)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    if (!itr) {
        vlist_prepend(o, data);
        return;
    }

    priv->first_used_obj = NULL;
    priv->last_used_obj = NULL;
    priv->contents = evas_list_prepend_relative_list(priv->contents, data,
                                                     (Evas_List *)itr);

    if (priv->selected_content == itr ||
        _vlist_selected_is_after_node(priv, itr))
        priv->selected_index++;

    _vlist_recalc(priv);
}

void *
vlist_itr_remove(Evas_Object *o, const Evas_List *itr)
{
    void *data;
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, NULL);
    RETURN_VAL_IF_NULL(itr, NULL);

    if (priv->selected_content == itr) {
        if (itr->prev) {
            priv->selected_content = itr->prev;
            priv->selected_index--;
        } else
            priv->selected_content = itr->next;
    } else if (_vlist_selected_is_after_node(priv, itr))
        priv->selected_index--;

    data = itr->data;
    priv->contents = evas_list_remove_list(priv->contents, (Evas_List *)itr);

    priv->first_used_obj = NULL;
    priv->last_used_obj = NULL;
    _vlist_recalc(priv);

    return data;
}

void
vlist_scroll_start(Evas_Object *o, vlist_scroll_dir_t dir)
{
    DECL_PRIV_SAFE(o);
    DECL_SCROLL_PARAM_SAFE(priv);
    RETURN_IF_NULL(priv);
    struct timeval now;
    double y;

    if (!priv->selected_content)
        return;

    if (dir <= 0)
        dir = VLIST_SCROLL_DIR_DOWN;
    else
        dir = VLIST_SCROLL_DIR_UP;

    if (dir == scroll_param->dir && scroll_param->stop == STOP_NONE)
        return;

    if (!_vlist_can_scroll(priv, dir))
        return;

    gettimeofday(&now, NULL);
    if (scroll_param->dir == VLIST_SCROLL_DIR_NONE)
        y = 0.0;
    else
        y = _vlist_pos_at_tv(priv, &now);

    scroll_param->dir = dir;
    scroll_param->t0 = now;
    scroll_param->y = y;
    scroll_param->y0 = y;
    scroll_param->v0 = dir * priv->scroll.init.speed;
    scroll_param->accel = dir * priv->scroll.init.accel;
    scroll_param->stop = STOP_NONE;

    if (!priv->scroll.anim)
        priv->scroll.anim = ecore_animator_add(_vlist_scroll, o);
}

static inline void
_vlist_scroll_fix_stop(struct priv *priv)
{
    DECL_SCROLL_PARAM(priv);
    struct timeval now;
    int t, d, can_scroll;

    _freeze(priv);

    scroll_param->stop = STOP_CHECK;

    gettimeofday(&now, NULL);
    t = _vlist_elapsed_ms(priv, &now);
    scroll_param->y = _vlist_pos_at_tv(priv, &now);

    /* rearrange contents in objects, fix y and y0 */
    if (scroll_param->y < -priv->item_h ||
        scroll_param->y > priv->item_h)
        _vlist_scroll_fix_y(priv, &scroll_param->y, now);
    else {
        scroll_param->y0 = scroll_param->y;
        scroll_param->t0 = now;
    }
    scroll_param->y1 = scroll_param->dir * priv->item_h;

    can_scroll = _vlist_can_scroll(priv, scroll_param->dir);
    if (!can_scroll)
        scroll_param->y = 0;
    _vlist_update_objs_pos(priv);

    d = scroll_param->y1 - scroll_param->y0;
    /* must stop now or later? */
    if (d == 0 || !can_scroll)
        _vlist_scroll_end(priv);
    else {
        double v2, min_stop_speed;

        scroll_param->v0 = _vlist_speed_at_tv(priv, &now);

        min_stop_speed = priv->scroll.init.min_stop_speed;
        if (in_interval(scroll_param->v0, min_stop_speed))
            scroll_param->v0 = scroll_param->dir * min_stop_speed;

        v2 = scroll_param->v0 * scroll_param->v0;
        scroll_param->accel = -v2 / (2 * d);
    }

    _thaw(priv);
}

void
vlist_scroll_stop(Evas_Object *o, vlist_scroll_dir_t dir)
{
    DECL_PRIV_SAFE(o);
    DECL_SCROLL_PARAM_SAFE(priv);
    RETURN_IF_NULL(priv);

    if (!priv->scroll.anim)
        return;

    if (scroll_param->dir != dir || scroll_param->stop != STOP_NONE)
        return;

    if (!priv->selected_content)
        _vlist_scroll_end(priv);
    else
        _vlist_scroll_fix_stop(priv);
}

int
vlist_count(Evas_Object *o)
{
    DECL_PRIV_SAFE(o);
    RETURN_VAL_IF_NULL(priv, -1);

    return evas_list_count(priv->contents);
}

void
vlist_selected_content_get(Evas_Object *o, void **item_data, int *index)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    if (!priv->selected_content) {
        if (item_data)
            *item_data = NULL;
        if (index)
            *index = -1;
    } else {
        if (item_data)
            *item_data = priv->selected_content->data;
        if (index)
            *index = priv->selected_index;
    }
}

void
vlist_connect_selection_changed(Evas_Object *o,
                                vlist_selection_changed_cb_t func,
                                void *user_data)
{
    DECL_PRIV_SAFE(o);
    RETURN_IF_NULL(priv);

    priv->callback.selection_changed = func;
    priv->callback_data.selection_changed = user_data;
}


/***********************************************************************
 * Private API
 **********************************************************************/
static Evas_Object *
_vlist_child_new(Evas_Object *o)
{
    Evas_Object *child;
    DECL_PRIV(o);

    child = priv->row_ops.new(priv->self, priv->evas, priv->row_ops_data);
    evas_object_resize(child, priv->geometry.w, priv->item_h);
    evas_object_smart_member_add(child, o);
    evas_object_clip_set(child, priv->clip);
    evas_object_show(child);

    return child;
}

static void
_vlist_child_del(struct priv *priv, Evas_Object *child)
{
    evas_object_hide(child);

    _obj_content_node_del(priv, child);
    evas_object_smart_member_del(child);
    evas_object_clip_unset(child);
    evas_object_del(child);
}

static void
_vlist_add(Evas_Object *o)
{
    struct priv *priv;

    priv = calloc(1, sizeof(*priv));
    RETURN_IF_NULL(priv);

    priv->self = o;
    priv->evas = evas_object_evas_get(o);
    priv->selected_index = -1;

    priv->clip = evas_object_rectangle_add(priv->evas);
    evas_object_smart_member_add(priv->clip, o);
    evas_object_color_set(priv->clip, 255, 255, 255, 255);

    priv->scroll.init.speed = 0.1;
    priv->scroll.init.accel = 0.001;

    evas_object_smart_data_set(o, priv);
}

static void
_vlist_del(Evas_Object *o)
{
    Evas_List *itr;
    DECL_PRIV(o);
    RETURN_IF_NULL(priv);

    _freeze(priv);

    evas_list_free(priv->contents);

    itr = priv->objs;
    while (itr) {
        Evas_Object *child;

        child = itr->data;
        _vlist_child_del(priv, child);

        itr = evas_list_remove_list(itr, itr);
    }

    evas_object_del(priv->clip);

    _thaw(priv);

    free(priv);
}

static void
_vlist_move(Evas_Object *o, Evas_Coord x, Evas_Coord y)
{
    DECL_PRIV(o);

    priv->geometry.x = x;
    priv->geometry.y = y;

    _freeze(priv);
    evas_object_move(priv->clip, x, y);
    _vlist_update_objs_pos(priv);
    _thaw(priv);
}

static void
_vlist_resize(Evas_Object *o, Evas_Coord w, Evas_Coord h)
{
    Evas_List *itr;
    int y, n_items;
    DECL_PRIV(o);

    n_items = h / priv->item_h;
    h = n_items * priv->item_h; /* just show full items */

    if (priv->geometry.w == w && priv->geometry.h == h)
        return;

    _freeze(priv);

    priv->geometry.w = w;
    priv->geometry.h = h;
    evas_object_resize(priv->clip, w, h);

    if (n_items < 1)
        return;

    if (priv->centered_selected_item) {
        int val;

        val = n_items / 2;
        if (val != priv->selected_item_offset) {
            priv->selected_item_offset = val;
            priv->first_used_obj = NULL;
            priv->last_used_obj = NULL;
            priv->dirty = 1;
            fprintf(stderr, "selected_item_offset = %d, n_items=%d\n",
                    priv->selected_item_offset, n_items);
        }
    }

    if (n_items < priv->selected_item_offset + 1)
        n_items = priv->selected_item_offset + 1;

    n_items += 2; /* spare items before and after visible area */

    /* If shrink, remove extra objects */
    while (n_items < evas_list_count(priv->objs)) {
        Evas_List *n;

        n = evas_list_last(priv->objs);
        _vlist_child_del(priv, n->data);

        if (priv->last_used_obj == n)
            priv->last_used_obj = n->prev;

        priv->objs = evas_list_remove_list(priv->objs, n);
    }

    /* Resize existing objects */
    for (itr = priv->objs; itr != NULL; itr = itr->next)
        evas_object_resize(itr->data, w, priv->item_h);

    y = priv->geometry.y + priv->scroll.param.y +
        (evas_list_count(priv->objs) - 1) * priv->item_h;

    /* If grow, create new objects */
    if (n_items > evas_list_count(priv->objs)) {
        while (n_items > evas_list_count(priv->objs)) {
            Evas_Object *child;

            child = _vlist_child_new(o); /* size is automatic */
            evas_object_move(child, priv->geometry.x, y);

            y += priv->item_h;
            priv->objs = evas_list_append(priv->objs, child);
        }
        _vlist_recalc(priv);
    }

    _thaw(priv);
}

static void
_vlist_show(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_show(priv->clip);
}

static void
_vlist_hide(Evas_Object *o)
{
    DECL_PRIV(o);
    RETURN_IF_NULL(priv); /* in case that _vlist_add failed */

    evas_object_hide(priv->clip);
}

static void
_vlist_color_set(Evas_Object *o, int r, int g, int b, int a)
{
    DECL_PRIV(o);

    evas_object_color_set(priv->clip, r, g, b, a);
}

static void
_vlist_clip_set(Evas_Object *o, Evas_Object *clip)
{
    DECL_PRIV(o);

    evas_object_clip_set(priv->clip, clip);
}

static void
_vlist_clip_unset(Evas_Object *o)
{
    DECL_PRIV(o);

    evas_object_clip_unset(priv->clip);
}

static inline Evas_Smart *
_vlist_get_smart(void)
{
    static Evas_Smart_Class cls = {
        .name = "vlist",
        .version = EVAS_SMART_CLASS_VERSION,
        .add = _vlist_add,
        .del = _vlist_del,
        .move = _vlist_move,
        .resize = _vlist_resize,
        .show = _vlist_show,
        .hide = _vlist_hide,
        .color_set = _vlist_color_set,
        .clip_set = _vlist_clip_set,
        .clip_unset = _vlist_clip_unset,
        .data = NULL
    };
    static Evas_Smart *smart = NULL;

    if (!smart)
        smart = evas_smart_class_new(&cls);

    return smart;
}
