#!/usr/bin/env python2.4

import sys
from eagle import *
from easy_tapioca import *


def contact_list_cmp( a, b ):
    online_a = a[ 0 ]
    online_b = b[ 0 ]
    if online_a == online_b:
        return cmp( a[ 1 ], b[ 1 ] )
    else:
        return -1 * cmp( online_a, online_b )
# contact_list_cmp()


def contacts_changed( conn, contact ):
    if not contact:
        return

    contacts = conn.contacts.values()
    tmp = []
    for c in contacts:
        if c.id:
            alias = c.alias or c.id
            tmp.append( ( c.is_online(), alias ) )
    contacts = tmp
    contacts.sort( contact_list_cmp )

    app = get_app_by_id( "contacts" )
    app[ "contact_list" ][ : ] = contacts
# contacts_changed()


def format_contact_list( app, table, row, col, value ):
    if col == 1:
        if table[ row ][ 0 ]:
            return Table.CellFormat( bold=True )
        else:
            return Table.CellFormat( fgcolor="#666666" )
# format_contact_list()


try:
    username = sys.argv[ 1 ]
except IndexError:
    sys.stderr.write( "Usage:\n\t%s <username> [password]\n\n" % sys.argv[ 0 ] )
    sys.exit( -1 )

try:
    password = sys.argv[ 2 ]
except IndexError:
    import getpass
    password = ''
    while not password:
        password = getpass.getpass()

conn = TapiocaConnection( username,
                          conn_params={ "username": username,
                                        "password": password,
                                        "server-address": "talk.google.com",
                                        "server-port": "5222",
                                        "use-encryption": "1" },
                          contacts_callback=contacts_changed )

app = App( id="contacts",
           title="Tapioca",
           left=Table( id="contact_list",
                       label=None,
                       show_headers=False,
                       headers=( "Connected?", "Alias" ),
                       hidden_columns_indexes=( 0, ),
                       types=( bool, str  ),
                       cell_format_func=format_contact_list,
                       ),
           )
run()
