#include <Eina.h>
#include <syslog.h>

/* gcc -o test test.c `pkg-config --libs --cflags eina` */

static void
_my_log_cb(const Eina_Log_Domain *d,
           Eina_Log_Level level,
           const char *file,
           const char *fnc,
           int line,
           const char *fmt,
           void *data,
           va_list args)
{
    int priority;
    switch (level) {
     case EINA_LOG_LEVEL_CRITICAL:
        priority = LOG_CRIT;
        break;
     case EINA_LOG_LEVEL_ERR:
        priority = LOG_ERR;
        break;
     case EINA_LOG_LEVEL_WARN:
        priority = LOG_WARNING;
        break;
     case EINA_LOG_LEVEL_INFO:
        priority = LOG_INFO;
        break;
     case EINA_LOG_LEVEL_DBG:
        priority = LOG_DEBUG;
        break;
     default:
        priority = level + LOG_CRIT;
    }
    vsyslog(priority, fmt, args);
}

int main(int argc, char *argv[])
{
    eina_init();
    eina_log_print_cb_set(_my_log_cb, NULL);

    EINA_LOG_ERR("Hi there: %d", 1234);

    eina_shutdown();
    return 0;
}
