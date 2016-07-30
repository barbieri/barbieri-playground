#include <Eina.h>

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
    fprintf(stderr, "%d: ", level);
    vfprintf(stderr, fmt, args);
    putc('\n', stderr);
}

int main(int argc, char *argv[])
{
    eina_init();
    eina_log_print_cb_set(_my_log_cb, NULL);

    EINA_LOG_ERR("Hi there: %d", 1234);

    eina_shutdown();
    return 0;
}
