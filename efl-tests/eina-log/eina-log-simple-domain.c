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
   if ((!d->name) || (strcmp(d->name, "mydomain") != 0))
     eina_log_print_cb_stderr(d, level, file, fnc, line, fmt, NULL, args);
   else
     {
        fprintf(stderr, "%d: ", level);
        vfprintf(stderr, fmt, args);
        putc('\n', stderr);
     }
}

int main(int argc, char *argv[])
{
   int log_domain;

   eina_init();
   eina_log_print_cb_set(_my_log_cb, NULL);

   log_domain = eina_log_domain_register("mydomain", NULL);

   EINA_LOG_ERR("Hi there: %d", 1234);
   EINA_LOG_DOM_ERR(log_domain, "Just for domain: %x", 0xff00);

   eina_shutdown();
   return 0;
}
