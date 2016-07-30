#!/usr/bin/env python2.4

### Comments to Tapioca:
# rename connect->login
# rename disconnect->logout

import gobject
import tapioca.client


class TapiocaPresence( object ):
    def __init__( self, presence, id, status, status_desc, has_phone ):
        self._presence = presence
        self.id = id
        self.status = status
        self.status_desc = status_desc
        self.has_phone = has_phone
# TapiocaPresence


class TapiocaContact( object ):
    def __init__( self, connection, id, alias=None, group=None, state=None ):
        self._jids = {}
        self._conn = connection
        self.id = id
        self.alias = alias
        self.group = group
        self.state = state
    # __init__()


    def __setitem__( self, key, value ):
        self._jids[ key ] = value
    # __setitem__()


    def __getitem__( self, key ):
        return self._jids[ key ]
    # __getitem__()


    def is_online( self ):
        for presence in self._jids.itervalues():
            if presence.status != tapioca.PRESENCE_STATUS_OFFLINE:
                return True

        return False
    # is_online()


    def has_phone( self ):
        for jid, presence in self._jids.iteritems():
            if presence.has_phone:
                return True

        return False
    # has_phone()


    def get_presences_with_status( self, status ):
        result = []
        for presence in self._jids.itervalues():
            if presence.status == status:
                result.append( presence )

        return result
    # get_jids_with_status()


    def get_presences_with_phone( self ):
        result = []
        for presence in self._jids.itervalues():
            if presence.has_phone:
                result.append( presence )

        return result
    # get_presences_with_phone()
# TapiocaContact



class TapiocaConnection( object ):
    _connection_manager = tapioca.client.ConnectionManager()

    STATE_OFF   = tapioca.CONNECTION_STATE_DISCONNECTED
    STATE_LOGIN = tapioca.CONNECTION_STATE_CONNECTING
    STATE_ON    = tapioca.CONNECTION_STATE_CONNECTED


    def __init__( self, id, protocol="xmpp", conn_params=None,
                  contacts_callback=None ):
        if not isinstance( conn_params, dict ):
            raise ValueError( "conn_params must be a dict!" )


        self.id = id
        self._conn_params = conn_params
        self._protocol = protocol
        self._contacts = None
        self._presence = None
        self.contacts = None
        self.state = self.STATE_OFF
        self._contacts_callback = contacts_callback

        self._conn = self._connection_manager.create_connection( protocol )
        gobject.GObject.connect( self._conn, "state-changed",
                                 self.__handle_state_changed__ )
        gobject.GObject.connect( self._conn, "error",
                                 self.__handle_error__ )

        self.login()
    # __init__()


    def login( self ):
        self._conn.connect( self.id, self._conn_params )
    # login()


    def __handle_state_changed_connected__( self, conn ):
        self._contacts = self._conn.get_contact_list()
        self._presence = self._conn.get_presence()
        self.contacts = {}

        self._contacts.connect( "contacts-retrieved",
                                self.__handle_contacts_retrieved__ )
        self._presence.connect( "status-updated",
                                self.__handle_status_updated__ )

        self._contacts.request_contacts()
        self._presence.subscribe( tapioca.PRESENCE_STATUS_AVAILABLE, "" )

        self.state = self.STATE_ON
    # __handle_state_changed_connected__()


    def __handle_state_changed_disconnected__( self, conn ):
        self._contacts = None
        self._presence = None
        self.contacts = None
        self.state = self.STATE_OFF
    # __handle_state_changed_disconnected__()


    def __handle_state_changed_connecting__( self, conn ):
        self.state = self.STATE_LOGIN
    # __handle_state_changed_connecting__()


    def __handle_state_changed__( self, conn, state ):
        if state == tapioca.CONNECTION_STATE_CONNECTED:
            self.__handle_state_changed_connected__( conn )
        elif state == tapioca.CONNECTION_STATE_DISCONNECTED:
            self.__handle_state_changed_disconnected__( conn )
        elif state == tapioca.CONNECTION_STATE_CONNECTING:
            self.__handle_state_changed_connecting__( conn )
        else:
            raise ValueError( "Unhandled state: %s for connection %s" %
                              ( state, conn ) )
    # __handle_state_changed__()


    def __handle_error__( self, conn, error_code ):
        raise NotImplementedError( ( "We still don't handle error %s for "
                                     "connection %s" ) % ( error_code, conn ) )
    # __handle_error__()


    def __handle_contacts_retrieved__( self, contacts, addr, alias, group,
                                       state ):
        c = TapiocaContact( self._conn, addr, alias, group, state )
        self.contacts[ addr ] = c
        self._presence.request_status( [ addr ] )
        if self._contacts_callback:
            self._contacts_callback( self, c )
    # __handle_contacts_retrieved__()


    def __handle_status_updated__( self, presence, jid, status, status_desc,
                                   phone_capability ):
        try:
            addr = jid.split( "/", 1 )[ 0 ]
        except:
            print "Invalud jid=%s" % ( jid, )
            return
        try:
            c = self.contacts[ addr ]
        except KeyError, e:
            print ( "presence status updated for contact with jid=%s, but it "
                    "was not retrieved before. Ignored" ) % jid
            return

        c[ jid ] = TapiocaPresence( presence, jid, status, status_desc,
                                    phone_capability )
        if self._contacts_callback:
            self._contacts_callback( self, c )
    # __handle_status_updated__()
# TapiocaConnection
