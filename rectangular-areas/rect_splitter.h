#ifndef __RECT_SPLITTER_H__
#define __RECT_SPLITTER_H__ 1

typedef struct list_node list_node_t;
typedef struct list list_t;
typedef struct rect rect_t;
typedef struct rect_node rect_node_t;

struct list_node
{
    struct list_node *next;
};

struct list
{
    struct list_node *head;
    struct list_node *tail;
};

struct rect
{
    short left;
    short top;
    short right;
    short bottom;
    short width;
    short height;
    int area;
};

struct rect_node
{
    struct list_node _lst;
    struct rect rect;
};


void rect_init(rect_t *r, int x, int y, int w, int h);
void rect_list_append_node(list_t *rects, list_node_t *node);
void rect_list_append(list_t *rects, const rect_t r);
void rect_list_append_xywh(list_t *rects, int x, int y, int w, int h);
void rect_list_concat(list_t *rects, list_t *other);
list_node_t *rect_list_unlink_next(list_t *rects, list_node_t *parent_node);
void rect_list_del_next(list_t *rects, list_node_t *parent_node);
void rect_list_clear(list_t *rects);
void rect_list_del_split_strict(list_t *rects, const rect_t del_r);
void rect_list_add_split_strict(list_t *rects, list_node_t *node);
list_node_t *rect_list_add_split_fuzzy(list_t *rects, list_node_t *node, int accepted_error);
void rect_list_merge_rects(list_t *rects, list_t *to_merge, int accepted_error);void rect_list_add_split_fuzzy_and_merge(list_t *rects, list_node_t *node, int split_accepted_error, int merge_accepted_error);

void rect_print(const rect_t r);
void rect_list_print(const list_t rects);


#endif /* __RECT_SPLITTER_H__ */
