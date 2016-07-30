#ifndef __KEY_MONITOR_H__
#define __KEY_MONITOR_H__

#include <Ecore.h>

typedef struct key_monitor key_monitor_t;
typedef void (*key_monitor_callback_t)(void *data, key_monitor_t *monitor);

struct key_monitor
{
    Ecore_Timer *unset_down_timer;
    int is_down;
    struct {
        key_monitor_callback_t down;
        key_monitor_callback_t up;
    } callbacks;
    void *data;
};

void key_monitor_down(key_monitor_t *m);
void key_monitor_up(key_monitor_t *m);
void key_monitor_setup(key_monitor_t *m, key_monitor_callback_t down_cb, key_monitor_callback_t up_cb, void *data);


#endif /* __KEY_MONITOR_H__ */
