#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <string.h>

static char **ignored_split(char *str)
{
    size_t allocated, used;
    char **ignored, *a, *b;

    if (!str)
        return NULL;

    ignored = malloc(sizeof(char *) * 32);
    allocated = 32;
    used = 0;

    a = str;
    do {
        b = strchr(a, ':');
        if (b) {
            *b = '\0';
            b++;
            if (b - a == 0) {
                goto end;
            }
        }

        if (used == allocated) {
            allocated += 8;
            ignored = realloc(ignored, allocated * sizeof(char *));
        }
        ignored[used++] = a;

      end:
        a = b;
    } while (a);

    if (used == allocated) {
        allocated++;
        ignored = realloc(ignored, allocated * sizeof(char *));
    }
    ignored[used] = NULL;
    return ignored;
}

static int is_ignored(char *const* ignored, const char *reference)
{
    if (!ignored)
        return 0;
    for (; *ignored != NULL; ignored++)
        if (strcmp(reference, *ignored) == 0)
            return 1;
    return 0;
}

static int already_used(char *const* paths, size_t count, const char *reference)
{
    char *const*itr = paths, *const*end = itr + count;
    for (; itr < end; itr++)
        if (strcmp(reference, *itr) == 0)
            return 1;
    return 0;
}

int main(int argc, char *argv[])
{
    char *path, *a, *b, resolved[PATH_MAX];
    char **paths, **ignored;
    size_t used, allocated, i;

    if (argc <= 1) {
        path = getenv("PATH");
        ignored = ignored_split(getenv("PATH_IGNORED"));
    } else if (argc == 2) {
        path = argv[1];
        ignored = ignored_split(getenv("PATH_IGNORED"));
    } else {
        path = argv[1];
        ignored = ignored_split(argv[2]);
    }

    paths = malloc(sizeof(char *) * 32);
    allocated = 32;
    used = 0;

    a = path;
    do {
        b = strchr(a, ':');
        if (b) {
            *b = '\0';
            b++;
            if (b - a == 0) {
                goto end;
            }
        }

        if (already_used(paths, used, a))
            goto end;
        if (!realpath(a, resolved))
            goto end;
        if (is_ignored(ignored, resolved))
            goto end;
        if (used == allocated) {
            allocated += 8;
            paths = realloc(paths, allocated * sizeof(char *));
        }
        paths[used++] = strdup(resolved);

      end:
        a = b;
    } while (a);

    for (i = 0; i < used; i++) {
        fputs(paths[i], stdout);
        if (i + 1 < used)
            putc(':', stdout);
    }
    putc('\n', stdout);

    return 0;
}
