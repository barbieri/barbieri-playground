/**
 * GLib-based URL query serializer.
 *
 * Serialize a query string and construct a hash table of lists.
 *
 * @author Gustavo Sverzut Barbieri <barbieri@gmail.com>
 *
 ******************************************************************************
 * Copyright (C) 2006 Gustavo Sverzut Barbieri
 *
 * The GLib-based URL query serializer is free software; you can
 * redistribute it and/or modify it under the terms of the GNU Lesser
 * General Public License as published by the Free Software
 * Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * The GLib-based URL query serializer is distributed in the hope that it
 * will be useful, but WITHOUT ANY WARRANTY; without even the implied
 * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with the GLib-base URL query serializer; if not, write to
 * the Free Software Foundation, Inc., 59 Temple Place, Suite 330,
 * Boston, MA 02111-1307 USA.
 */

#include <glib.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include "serializer.h"

/**
 * Encode string.
 *
 * Encode consists in replacing ' ' with '+' and non-alpha-numeric
 * characters to %NN (NN being an hexadecimal).
 *
 * @return allocated memory with decoded string.
 */
static gchar *
encode(const gchar *s)
{
    GString *str = g_string_new (NULL);
    const gchar *p;

    for (p = s; *p != 0; p++) {
	if (*p == ' ')
	    g_string_append_c (str, '+');
	else if (!isalnum (*p))
	    g_string_append_printf (str, "%%%02X", *p);
	else
	    g_string_append_c (str, *p);
    }

    return g_string_free (str, FALSE);
}


struct serialize_query_value_element {
    gchar *key;
    GString *string;
};

static void
serialize_query_value_element (const gchar *value,
			       const struct serialize_query_value_element *p)
{
    gchar *s;

    if (p->string->str && *p->string->str)
	g_string_append_c (p->string, '&');

    s = encode (value);
    g_string_append_printf (p->string, "%s=%s", p->key, s);
    g_free (s);
}


static void
serialize_query_element (const gchar *key,
			 GSList *values,
			 GString *str)
{
    struct serialize_query_value_element p = {
	.key = encode (key),
	.string = str,
    };

    if (values)
	g_slist_foreach (values, (GFunc)serialize_query_value_element, &p);
    else {
	if (str->str && *str->str)
	    g_string_append_c (str, '&');
	g_string_append_printf (str, "%s=", p.key);
    }
    g_free (p.key);
}


gchar *
serialize_query (GHashTable *query)
{
    GString *str = g_string_new (NULL);

    g_hash_table_foreach (query, (GHFunc)serialize_query_element, str);

    return g_string_free (str, FALSE);
}
