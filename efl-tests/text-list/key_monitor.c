#include "key_monitor.h"
#include <stdlib.h>

#define CONTINUOUS_KEYPRESS_INTERVAL 0.050 /* seconds */

void
key_monitor_down(key_monitor_t *m)
{
    if (m->unset_down_timer) {
        ecore_timer_del(m->unset_down_timer);
        m->unset_down_timer = NULL;
    }

    if (!m->is_down) {
        m->is_down = 1;

        if (m->callbacks.down)
            m->callbacks.down(m->data, m);
    }
}

static int
unset_down(void *data)
{
    key_monitor_t *m = (key_monitor_t *)data;

    m->unset_down_timer = NULL;
    m->is_down = 0;

    if (m->callbacks.up)
        m->callbacks.up(m->data, m);

    return 0;
}

void
key_monitor_up(key_monitor_t *m)
{
    if (m->unset_down_timer || !m->is_down)
        return;

    m->unset_down_timer = ecore_timer_add(CONTINUOUS_KEYPRESS_INTERVAL,
                                          unset_down, m);
}

void
key_monitor_setup(key_monitor_t *m,
                  key_monitor_callback_t down_cb,
                  key_monitor_callback_t up_cb,
                  void *data)
{
    m->is_down = 0;
    m->callbacks.down = down_cb;
    m->callbacks.up = up_cb;
    m->data = data;
}
