/**
 * GLib-based URL utils.
 *
 * Serialize a query string and construct a hash table of lists.
 *
 * @author Gustavo Sverzut Barbieri <barbieri@gmail.com>
 *
 ******************************************************************************
 * Copyright (C) 2006 Gustavo Sverzut Barbieri
 *
 * The GLib-based URL utils is free software; you can
 * redistribute it and/or modify it under the terms of the GNU Lesser
 * General Public License as published by the Free Software
 * Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * The GLib-based URL utils is distributed in the hope that it
 * will be useful, but WITHOUT ANY WARRANTY; without even the implied
 * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with the GLib-based URL utils; if not, write to
 * the Free Software Foundation, Inc., 59 Temple Place, Suite 330,
 * Boston, MA 02111-1307 USA.
 */

#include <string.h>
#include <limits.h>
#include <stdlib.h>
#include "utils.h"



static void
free_str_list_element (gchar *s,
		       gpointer d)
{
    g_free (s);
}

/**
 * Free a list of gchar*.
 */
void
free_str_list (GSList *list)
{
    g_slist_foreach (list, (GFunc)free_str_list_element, NULL);
    g_slist_free (list);
}


struct str_join_param {
    const gchar *sep;
    GString *string;
};

static void
str_join_element (const gchar *s,
		  struct str_join_param *p)
{
    if (p->string->str && *p->string->str)
	p->string = g_string_append (p->string, p->sep);
    p->string = g_string_append (p->string, s);
}

/**
 * Join a list of strings using given separator.
 *
 * @return newly allocated string.
 */
gchar *
str_join (const gchar *sep,
	  GSList *list)
{
    GString *s = g_string_new (NULL);
    struct str_join_param p = {
	.sep = sep,
	.string = s
    };
    g_slist_foreach (list, (GFunc)str_join_element, &p);

    return g_string_free (s, FALSE);
}

/**
 * Simplify a path, removing duplicate slashes and accessing parent
 * directories ("/a/../b" -> "/b").
 */
gchar *
simplify_path (gchar *str)
{
    gchar *base, *p, *last_slash;

    if (!str)
	return NULL;

    last_slash = NULL;
    base = str;
    for (p = base; *p != 0; p++, *base = *p) {
	if (*p == '/') {
	    if (last_slash + 1 != p) /* skip duplicate slashes */
		base++;
	    last_slash = p;
	} else
	    base++;
    }

    last_slash = NULL;
    base = str;
    for (p = base; *p != 0; p++, base++, *base = *p) {
	if (*p == '/') {
	    if (last_slash) {
		gchar *itr, *last_comp;
		/* check if it's an access to parent (/../) */
		last_comp = last_slash + 1;

		for (itr = last_comp; *itr == '.'; itr++);
		if (*last_comp == '.' && itr == p) {
		    if (last_slash > str) {
			/* remove last component */
			base = last_slash - 1;
			for (; base >= str && *base != '/'; base--);

			if (base < str)
			    base = str;
			p = memmove (base, p, strlen (p) + 1);
		    } else
			p = memmove (str, p, strlen (p) + 1);
		}
	    } else {
		gchar *itr;
		for (itr = str; *itr == '.'; itr++);
		if (*str == '.' && itr == p)
		    p = memmove (str, p, strlen (p) + 1);
		base = str;
	    }
	    last_slash = base;
	}

    }

    if (!*p)
	base --;

    for (p = base; p >= str && *p == '.'; p--);
    if ((p > str && *p == '/') || (p <= str))
	*(p + 1) = 0;

    return str;
}


/**
 * Given a path, return its components in a single linked list.
 *
 * @note Each single linked list is a newly allocated string.
 */
GSList *
get_path_list (const gchar *path)
{
    const gchar *begin, *end;
    GSList *list = NULL;

    begin = path;
    if (!begin)
	return NULL;

    while ((end = strchr (begin, '/')) != NULL) {
	gint len = end - begin;
	if (len) {
	    gchar *s = g_strndup (begin, len);
	    list = g_slist_prepend (list, s);
	}

	begin = end + 1;
    }

    if (strlen (begin) > 0) {
	gchar *s = g_strdup (begin);
	list = g_slist_prepend (list, s);
    }

    list = g_slist_reverse (list);

    return list;
}



/**
 * Get real path rooted to 'root' directory.
 *
 * This function uses realpath, thus removing '..' of components.
 *
 * @return this function returns NULL if resulting realpath doesn't start
 * with root's realpath, otherwise it returns the value.
 */
gchar *
get_real_path (const gchar *root,
	       const gchar *path)
{
    char resolved_root[PATH_MAX] = "";
    char resolved_path[PATH_MAX] = "";
    gchar *fname, *ret;

    ret = realpath (root, resolved_root);
    if (!ret)
	return NULL;

    fname = g_build_path (G_DIR_SEPARATOR_S, resolved_root, path, NULL);
    ret = realpath (fname, resolved_path);
    g_free (fname);

    if (ret) {
	if (strncmp (resolved_root, ret, strlen (resolved_root)) == 0)
	    ret = g_strdup (ret);
	else
	    ret = NULL;
    }

    return ret;
}


/**
 * Get extra path elements of 'path' after 'base'.
 *
 * @note if resulting path begins with '/' it will be skipped and the
 * returned value will never begin with this character.
 *
 * @return NULL if 'base' is not inside 'path' or pointer to element in
 * 'path'.
 */
const gchar *
get_extra_path (const gchar *base,
		const gchar *path)
{
    const gchar *extra;
    gint a, b;

    a = strlen (path);
    b = strlen (base);

    g_assert (a >= 0);
    g_assert (b >= 0);

    if (strncmp (base, path, b) != 0) {
	g_debug ("Action path [%s] should be in URL path [%s]\n", base, path);
	return NULL;
    } else {
	extra = path + b; /* skip common part */
	while (*extra == '/')
	    extra++;
    }

    return extra;
}
