#include "marshaller-string-array.h"
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>
#include <sys/types.h>
#include <sys/ioctl.h>

static int
get_term_cols(void)
{
        struct winsize ws;

        ioctl(1, TIOCGWINSZ, &ws);
        return (ws.ws_col >= 6) ? ws.ws_col : 80;
}

static const int DUMP_BYTE_SIZE = 6;
static inline void
dump_byte(FILE *stream, char b)
{
        fprintf(stream, " %02x", b);
        if (isprint(b))
                fprintf(stream, "(%c)", b);
        else
                fputs("---", stream);
}

static void
dump_buf(FILE *stream, int cols, int buflen, const char *buf)
{
        int cc;

        fprintf(stream, "%p(%d):\n", buf, buflen);

        cc = DUMP_BYTE_SIZE;
        for (;buflen > 0; buf++, buflen--) {
                if (cols > 0 && cc >= cols) {
                        fputc('\n', stream);
                        cc = DUMP_BYTE_SIZE;
                }

                dump_byte(stream, *buf);
                cc += DUMP_BYTE_SIZE;

        }
        fputc('\n', stream);
}

int
main(int argc, const char **argv)
{
        char *buf, **reply;
        int i, buflen, reqlen, replylen;

        buf = NULL;
        buflen = 0;

        buf = marshal_string_array(&buflen, buf, &reqlen, argc, argv);
        dump_buf(stderr, get_term_cols(), buflen, buf);

        reply = unmarshal_string_array(buf, &replylen);
        printf("Parsed string is:\n");
        for (i = 0; i < replylen; i++)
                printf("\targv[%d]=\"%s\"\n", i, reply[i]);

        free(buf);

        return 0;
}
