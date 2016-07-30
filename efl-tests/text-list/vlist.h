#ifndef __VLIST_H__
#define __VLIST_H__

#include <Evas.h>

typedef struct _Evas_List vlist_item_handle_t;

enum
{
    VLIST_ERROR_NONE = 0,
    VLIST_ERROR_NO_ITEM_SIZE
};

typedef enum
{
    VLIST_SCROLL_DIR_UP = 1,
    VLIST_SCROLL_DIR_NONE = 0,
    VLIST_SCROLL_DIR_DOWN = -1
} vlist_scroll_dir_t;

typedef int (*vlist_search_func_t)(const Evas_Object *o, const void *func_data, const void *item_data);
typedef void (*vlist_selection_changed_cb_t)(Evas_Object *o, void *item_data, int index, void *user_data);
typedef Evas_Object *(*vlist_row_new_t)(Evas_Object *list, Evas *evas, void *user_data);
typedef void (*vlist_row_set_t)(Evas_Object *list, Evas_Object *row, void *item_data, void *user_data);
typedef void (*vlist_row_freeze_t)(Evas_Object *list, Evas_Object *row, void *user_data);
typedef void (*vlist_row_thaw_t)(Evas_Object *list, Evas_Object *row, void *user_data);

typedef struct
{
    vlist_row_new_t new;
    vlist_row_set_t set;
    vlist_row_freeze_t freeze;
    vlist_row_thaw_t thaw;
} vlist_row_ops_t;

Evas_Object *vlist_new(Evas *evas, int item_h, vlist_row_ops_t row_ops, void *user_data);
void vlist_conf_set(Evas_Object *o, int centered_selected_item, int selected_item_offset);
void vlist_conf_get(Evas_Object *o, int *centered_selected_item, int *selected_item_offset);
void vlist_scroll_conf_set(Evas_Object *o, double speed,  double accel, double min_stop_speed);
void vlist_scroll_conf_get(Evas_Object *o, double *speed, double *accel, double *min_stop_speed);

int   vlist_find(Evas_Object *o, const void *data);
int   vlist_rfind(Evas_Object *o, const void *data);
int   vlist_search(Evas_Object *o, vlist_search_func_t func, const void *func_data, void **item_data);
int   vlist_rsearch(Evas_Object *o, vlist_search_func_t func, const void *func_data, void **item_data);
void *vlist_item_nth_get(Evas_Object *o, int index);
void *vlist_item_nth_set(Evas_Object *o, int index, void *new_data);

const Evas_List *vlist_itr_nth(Evas_Object *o, int index);
const Evas_List *vlist_itr_find(Evas_Object *o, const void *data);
const Evas_List *vlist_itr_rfind(Evas_Object *o, const void *data);
const Evas_List *vlist_itr_search(Evas_Object *o, vlist_search_func_t func, const void *func_data, void **item_data);
const Evas_List *vlist_itr_rsearch(Evas_Object *o, vlist_search_func_t func, const void *func_data, void **item_data);
void            *vlist_itr_item_get(Evas_Object *o, const Evas_List *itr);
void            *vlist_itr_item_set(Evas_Object *o, const Evas_List *itr, void *new_data);

void vlist_append(Evas_Object *o, void *data);
void vlist_prepend(Evas_Object *o, void *data);
void vlist_itr_append(Evas_Object *o, void *data, const Evas_List *itr);
void vlist_itr_prepend(Evas_Object *o, void *data, const Evas_List *itr);

void *vlist_remove(Evas_Object *o, void *data);
void *vlist_itr_remove(Evas_Object *o, const Evas_List *itr);

int  vlist_error_get(void);
void vlist_scroll_start(Evas_Object *o, vlist_scroll_dir_t dir);
void vlist_scroll_stop(Evas_Object *o, vlist_scroll_dir_t dir);
int  vlist_count(Evas_Object *o);
void vlist_selected_content_get(Evas_Object *o, void **item_data, int *index);
void vlist_connect_selection_changed(Evas_Object *o, vlist_selection_changed_cb_t func, void *user_data);
void vlist_freeze(Evas_Object *o);
void vlist_thaw(Evas_Object *o);

#endif /* __VLIST_H__ */
