#include "parser.h"
#include "serializer.h"
#include <string.h>

struct query_parse_test {
    char *name;
    char *query;
    char *expected;
};

static void
print_list (gchar *e, GString *s)
{
    g_string_append_printf (s, "[%s]", e);
}

static void
print_hash (gchar *k, GSList *v, GString *s)
{
    g_string_append_printf (s, "[%s]=", k);
    if (v) {
	g_slist_foreach (v, (GFunc)print_list, s);
	g_string_append_c (s, '\n');
    } else
	g_string_append (s, "(null)\n");
}

static gboolean
test_parse (const struct query_parse_test test)
{
    GHashTable *d;
    GString *s;
    gboolean r;

    g_print ("\n### test: %s\n>>> parse of \"%s\"\n", test.name, test.query);

    s = g_string_new ("");
    d = parse_query (test.query);
    g_hash_table_foreach (d, (GHFunc)print_hash, s);
    g_hash_table_destroy (d);

    g_print ("%s", s->str);
    r = strcmp (s->str, test.expected) == 0;

    if (!r){
	g_print ("!!! INCORRECT. Expected:\n");
	g_print ("%s\n", test.expected);
    }

    g_string_free (s, TRUE);

    return r;
}

/*
 * These tests may fail due reordering in hash table, not necessarily
 * hash table will keep insertion order.
 * If this is the case, please check results.
 */
static struct query_parse_test tests[] = {
    {
	.name="Empty",
	.query="",
	.expected=""
    },
    {
	.name="No value",
	.query="a",
	.expected="[a]=(null)\n"
    },
    {
	.name="Single pair",
	.query="a=b",
	.expected="[a]=[b]\n"
    },
    {
	.name="Single pair with trailing '&'",
	.query="a=1&",
	.expected="[a]=[1]\n"
    },
    {
	.name="Single with encoded (+) value",
	.query="a=b+c",
	.expected="[a]=[b c]\n"
    },
    {
	.name="Single with encoded (hexa) value",
	.query="a=b%63",
	.expected="[a]=[bc]\n"
    },
    {
	.name="Single with encoded (hexa) value inside",
	.query="a=b%63d",
	.expected="[a]=[bcd]\n"
    },
    {
	.name="Single with broken encoded (hexa) value",
	.query="a=b%6",
	.expected="[a]=[b]\n"
    },
    {
	.name="Multiple pairs",
	.query="a=1&b=2",
	.expected="[a]=[1]\n[b]=[2]\n"
    },
    {
	.name="Multiple pairs, first without value",
	.query="a=&b=2",
	.expected="[a]=(null)\n[b]=[2]\n"
    },
    {
	.name="Multiple pairs, second without value",
	.query="a=1&b=",
	.expected="[a]=[1]\n[b]=(null)\n"
    },
    {
	.name="Multiple pairs, none with value",
	.query="a=&b=",
	.expected="[a]=(null)\n[b]=(null)\n"
    },
    {
	.name="Multiple pairs, first without equal sign",
	.query="a&b=",
	.expected="[a]=(null)\n[b]=(null)\n"
    },
    {
	.name="Multiple pairs, second without equal sign",
	.query="a=&b",
	.expected="[a]=(null)\n[b]=(null)\n"
    },
    {
	.name="Multiple pairs, none with equal sign",
	.query="a&b",
	.expected="[a]=(null)\n[b]=(null)\n"
    },
    {
	.name="Multiple values for same key",
	.query="a=1&a=2",
	.expected="[a]=[1][2]\n"
    },
    { NULL, NULL, NULL },
};



int main(int argc, char *argv[])
{
    struct query_parse_test *t;
    unsigned n_tests=0, failed = 0;

    t = tests;
    while (t->query) {
	n_tests++;
	if (!test_parse (*t))
	    failed++;
	t++;
    }
    g_print ("Ran %u tests, %u failed.\n", n_tests, failed);

    return 0;
}
