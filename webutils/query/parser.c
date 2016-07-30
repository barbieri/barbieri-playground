/**
 * GLib-based URL query parser.
 *
 * Parse a query string and construct a hash table of lists.
 *
 * @author Gustavo Sverzut Barbieri <barbieri@gmail.com>
 *
 ******************************************************************************
 * Copyright (C) 2006 Gustavo Sverzut Barbieri
 *
 * The GLib-based URL query parser is free software; you can
 * redistribute it and/or modify it under the terms of the GNU Lesser
 * General Public License as published by the Free Software
 * Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * The GLib-based URL query parser is distributed in the hope that it
 * will be useful, but WITHOUT ANY WARRANTY; without even the implied
 * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with the GLib-base URL query parser; if not, write to
 * the Free Software Foundation, Inc., 59 Temple Place, Suite 330,
 * Boston, MA 02111-1307 USA.
 */

#include <glib.h>
#include <string.h>
#include <stdlib.h>
#include "parser.h"

static void
free_query_value_element (gchar *element,
			  gpointer data)
{
    g_free (element);
}

static void
free_query_value (GSList *value_list)
{
    if (!value_list)
	return;

    g_slist_foreach (value_list, (GFunc)free_query_value_element, NULL);
    g_slist_free (value_list);
}

/**
 * Decode string between start and end.
 *
 * Decoding consists in replacing '+' with ' ' and %NN with chr(NN),
 * NN being a hexadecimal.
 *
 * @return allocated memory with decoded string.
 */
static gchar *
decode (const gchar *start, const gchar *end)
{
    gchar *r, *itr;
    gint len;

    len = end - start;
    g_assert (len >= 0);
    r = g_malloc (len + 1);

    for (itr = r; start < end; itr++, start++) {
	switch (*start) {
	case '+':
	    *itr = ' ';
	    break;

	case '%':
	    if (end - start >= 3) {
		gchar *p = g_strndup (start + 1, 2);
		glong conv = strtol (p, NULL, 16);
		g_free (p);
		*itr = (gchar)conv;
		start += 2;
	    } else {
		gint n = end - start;
		g_warning ("Invalid hexadecimal representation. Expected "
			   "%%NN where N are numbers between 0 and F. "
			   "Got \"%.*s\".\n",
			   n, start);
		start = end;
		itr --;
	    }
	    break;

	default:
	    *itr = *start;
	}
    }
    *itr = '\0';

    return r;
}


/**
 * Add pair to hash table.
 *
 * @note If value is NULL, key will be added to hash table, but no
 * node will be added because we don't keep empty (NULL) nodes.
 */
static void
add_query_pair (GHashTable *dic,
		gchar *key,
		gchar *value)
{
    GSList *value_list;
    gchar *old_key;

    if (g_hash_table_lookup_extended (dic, key,
				      (gpointer*)&old_key,
				      (gpointer*)&value_list)) {
	/* We don't keep empty list nodes. */
	if (value) {
	    g_hash_table_steal (dic, old_key);
	    value_list = g_slist_append (value_list, value);
	    g_hash_table_insert (dic, key, value_list);

	    /* There is one key already, free previous key. */
	    g_free (old_key);
	}
    } else {
	/* Not present in hash table yet, add it.
	 *
	 * We don't keep empty list nodes, but we still add key to hash table.
	 */
	if (value)
	    value_list = g_slist_append (NULL, value);
	else
	    value_list = NULL;

	g_hash_table_insert (dic, key, value_list);
    }
}


/**
 * Parse a pair in the form string=string present between start and
 * end and add it to given hash table.
 *
 * Strings will be decoded using decode() before they're added to hash
 * table.
 *
 * @see decode()
 */
static void
parse_query_pair (GHashTable *dic,
		  const gchar *start,
		  const gchar *end)
{
    const gchar *sep;
    gint len = end - start;

    g_assert (len >= 0);

    sep = memchr (start, '=', len);
    if (sep == start) {
	g_warning ("Invalid query pair \"%.*s\". Misses key!\n", len, start);
	return;
    } else {
	gchar *key, *value;

	if (sep) {
	    gint len_key, len_value;
	    len_key = sep - start;
	    sep++;
	    len_value = end - sep;

	    g_assert (len_key >= 0);
	    g_assert (len_value >= 0);

	    key = decode (start, start + len_key);
	    if (len_value)
		value = decode (sep, sep + len_value);
	    else
		value = NULL;

	} else {
	    key = decode (start, end);
	    value = NULL;
	}

	add_query_pair (dic, key, value);
    }
}

/**
 * Parse URL's query argument.
 *
 * Query is a hash table, with keys being strings and values being a
 * single linked list of strings.
 *
 * Examples:
 *  - \c{"a=1"}: this is a single key "a" with a list of values with
 *    single element "1".
 *  - \c{"a="} or \c{"a"}: this is a single key "a" with an empty list
 *    of values.
 *  - \c{"a=1&b=2"}: two keys ("a" and "b"), each with single list of
 *     values, "1" and "2" respectively.
 *  - \c{"a=&b="} or \c{"a&b"}: two keys ("a" and "b") with empty list
 *    of values.
 *  - \c{"a=1&a=2"}: single key "a" with a list of values with two
 *    elements: "1" and "2".
 *
 * Data structures are:
 *  - keys: \c{gchar*}
 *  - values: \c{GSList*} of \c{gchar*}.
 */
GHashTable *
parse_query (const gchar *query)
{
    const gchar *end, *start, *limit;
    int len;
    GHashTable *dic;

    if (!query)
	return NULL;

    dic = g_hash_table_new_full (g_str_hash,
				 g_str_equal,
				 g_free,
				 (GDestroyNotify)free_query_value);

    len = strlen (query);
    limit = query + len;

    for (start = query; start < limit; start = end) {
	end = strchr (start, '&');
	if (!end)
	    end = limit;

	parse_query_pair (dic, start, end);

	while (*end == '&')
	    end++;
    }


    return dic;
}
