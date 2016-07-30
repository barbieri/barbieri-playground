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

#ifndef _WEBUTILS_QUERY_PARSER_H_
#define _WEBUTILS_QUERY_PARSER_H_

#include <glib.h>

GHashTable *
parse_query (const gchar *query);

#endif /* _WEBUTILS_QUERY_PARSER_H_ */
