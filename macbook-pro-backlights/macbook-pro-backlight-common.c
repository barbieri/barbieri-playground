#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>

static void usage(const char *prog)
{
    fprintf(stderr, "Usage:\n\t%s [-step|+step|=value]\n", prog);
}

int main(int argc, char *argv[])
{
    int old, new, max;
    double step;
    char *p;
    FILE *f;

    f = fopen(DEV_VAL, "rb");
    if (!f) {
        fprintf(stderr, "could not open for reading '%s': %s\n", DEV_VAL, strerror(errno));
        return 1;
    }

    if (fscanf(f, "%d", &old) != 1) {
        fprintf(stderr, "could not read integer from '%s': %s\n", DEV_VAL, strerror(errno));
        fclose(f);
        return 1;
    }
    fclose(f);

    f = fopen(DEV_MAX, "rb");
    if (!f) {
        fprintf(stderr, "could not open for reading '%s': %s\n", DEV_MAX, strerror(errno));
        return 1;
    }

    if (fscanf(f, "%d", &max) != 1) {
        fprintf(stderr, "could not read integer from '%s': %s\n", DEV_MAX, strerror(errno));
        fclose(f);
        return 1;
    }
    fclose(f);

    if (max < 0) {
        fprintf(stderr, "invalid maximum value: %d\n", max);
        return 1;
    }

    if (argc < 2) {
        new = ((old * 100 + max * 10) / 100);
        if (new == old)
            new++;
        new %= (max + 1);
    } else if (argc != 2) {
        usage(argv[0]);
        return 2;
    } else if (strcmp(argv[1], "-h") == 0) {
        usage(argv[0]);
        return 0;
    } else {
        switch (argv[1][0]) {
        case '?': {
            printf("actual value: %d (%0.f%%, max: %d)\n", old, old * 100.0 / max, max);
            return 0;
        }
        case '-':
            step = strtod(argv[1] + 1, &p);
            if (*p == '%') {
                new = (old * 100 - step) / 100;
                if (new == old)
                    new--;
            } else if (*p == '\0')
                new = old - step;
            else {
                fprintf(stderr, "invalid step value: %s\n", argv[1] + 1);
                return 2;
            }
            break;
        case '+':
            step = strtod(argv[1] + 1, &p);
            if (*p == '%') {
                new = (old * 100 + step) / 100;
                if (new == old)
                    new++;
            } else if (*p == '\0')
                new = old + step;
            else {
                fprintf(stderr, "invalid step value: %s\n", argv[1] + 1);
                return 2;
            }
            break;
        case '=':
            new = strtod(argv[1] + 1, &p);
            if (*p == '%')
                new = (max * new) / 100;
            else if (*p != '\0') {
                fprintf(stderr, "invalid value: %s\n", argv[1] + 1);
                return 2;
            }
            break;
        default:
            fprintf(stderr, "invalid action '%c' for parameter '%s'.\n", argv[1][0], argv[1]);
            usage(argv[0]);
            return 2;
        }
    }

    if (new < 0)
        new = 0;
    else if (new > max)
        new = max;

    f = fopen(DEV_VAL, "wb");
    if (!f) {
        fprintf(stderr, "could not open for writing '%s': %s\n", DEV_VAL, strerror(errno));
        return 1;
    }

    fprintf(f, "%d", new);
    fclose(f);

    return 0;
}
