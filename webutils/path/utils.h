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

#ifndef _WEBUTILS_PATH_UTILS_H_
#define _WEBUTILS_PATH_UTILS_H_

#include <glib.h>

void
free_str_list (GSList *list);

gchar *
str_join (const gchar *sep,
	  GSList *list);

gchar *
simplify_path (gchar *str);

GSList *
get_path_list (const gchar *path);

gchar *
get_real_path (const gchar *root,
	       const gchar *path);

const gchar *
get_extra_path (const gchar *base,
		const gchar *path);


#endif /* _WEBUTILS_PATH_UTILS_H_ */
