#include <Eina.h>
#include <systemd/sd-journal.h>

/* http://0pointer.de/blog/projects/journal-submit */
/* gcc -o test test.c `pkg-config --libs --cflags eina libsystemd-journal` */

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
    char filestr[PATH_MAX + sizeof("CODE_FILE=")];
    char linestr[128];
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

    snprintf(filestr, sizeof(filestr), "CODE_FILE=%s", file);
    snprintf(linestr, sizeof(linestr), "CODE_LINE=%d", line);
    sd_journal_printv_with_location(priority, filestr, linestr, fnc, fmt, args);
}

int main(int argc, char *argv[])
{
    eina_init();
    eina_log_print_cb_set(_my_log_cb, NULL);

    EINA_LOG_ERR("Hi there: %d", 1234);

    eina_shutdown();
    return 0;
}
