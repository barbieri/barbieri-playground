/*
 * Simulates basics of structure introspection using C.
 *
 * Compile:
 *
 *    gcc -o introspection introspection.c -Wall -std=c99
 *
 */
#include <stdio.h>

#define offsetof(TYPE, MEMBER)  __builtin_offsetof(TYPE, MEMBER)
#define typeof(v) __typeof__(v)

struct map
{
        const char *name;
        enum {
                MAP_TYPE_UNKNOWN,
                MAP_TYPE_INT,
                MAP_TYPE_STR,
                MAP_TYPE_DOUBLE
        } type;
        unsigned offset;
};

#define _STR(v) #v
#define STR(v) _STR(v)
#define MAP(strtype, field, fieldtype)                                  \
        {STR(field), fieldtype, offsetof(strtype, field)}
#define MAP_SENTINEL {NULL, MAP_TYPE_UNKNOWN, 0}


static void
print_map_int(const struct map *map, const void *data)
{
        const void *value;

        value = ((const char *)data) + map->offset;

        printf("%s=", map->name);
        switch (map->type) {
        case MAP_TYPE_UNKNOWN:
                printf("<ERROR>");
                break;
        case MAP_TYPE_INT:
                printf("%d", *(int *)value);
                break;
        case MAP_TYPE_STR:
                printf("%s", *(char **)value);
                break;
        case MAP_TYPE_DOUBLE:
                printf("%f", *(double *)value);
                break;
        }
}

static void
print_map(const struct map *map, const void *data)
{
        const struct map *p;

        for (p = map; p->name != NULL; p++) {
                print_map_int(p, data);
                if ((p + 1)->name != NULL)
                        putchar(' ');
        }

        putchar('\n');
}

struct row
{
        int i;
        char *s;
        double f;
};

int
main(void)
{
        const struct row *p, *p_end;
        const struct row rows[] = {
                {1, "test", 12.34},
                {2, "abc", 5678.9},
                {3, "xxx", 2.0},
        };
        const struct map map[] = {
                MAP(struct row, i, MAP_TYPE_INT),
                MAP(struct row, s, MAP_TYPE_STR),
                MAP(struct row, f, MAP_TYPE_DOUBLE),
                MAP_SENTINEL
        };

        p_end = rows + sizeof(rows) / sizeof(*rows);
        for (p = rows; p < p_end; p++)
                print_map(map, p);

        return 0;
}
