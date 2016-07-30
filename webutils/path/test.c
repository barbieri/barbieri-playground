#include "utils.h"

struct test_simplify_path {
    const gchar *request;
    const gchar *expected;
} test_simplify_path[] = {
    {
	.request="/a",
	.expected="/a",
    },
    {
	.request="//a",
	.expected="/a",
    },
    {
	.request="/a/",
	.expected="/a/",
    },
    {
	.request="/a//",
	.expected="/a/",
    },
    {
	.request="/a/b",
	.expected="/a/b",
    },
    {
	.request="/a///b",
	.expected="/a/b",
    },
    {
	.request="/a/c/../b",
	.expected="/a/b",
    },
    {
	.request="/a/c/../b/",
	.expected="/a/b/",
    },
    {
	.request="../a",
	.expected="/a",
    },
    {
	.request="../../a/",
	.expected="/a/",
    },
    {
	.request="/a/b/../......./c/",
	.expected="/c/",
    },
    {
	.request=NULL,
	.expected=NULL,
    },
};

gboolean
do_test_simplify_path (const struct test_simplify_path t)
{
    gboolean ret;
    gchar *s = g_strdup (t.request);
    s = simplify_path (s);

    ret = strcmp (s, t.expected) == 0;
    g_print (">>> simplify_path (\"%s\") = \"%s\"\n", t.request, s);
    if (!ret)
	g_print ("FAILED: expected \"%s\"\n", t.expected);

    g_free (s);

    return ret;
}


int
main (int argc,
      char *argv[])
{
    struct test_simplify_path *t_simp;
    unsigned n_tests=0, failed = 0;

    t_simp = test_simplify_path;
    while (t_simp->request) {
	n_tests++;
	if (!do_test_simplify_path (*t_simp))
	    failed++;
	t_simp++;
    }
    g_print ("Ran %u tests, %u failed.\n", n_tests, failed);

    return 0;
}
