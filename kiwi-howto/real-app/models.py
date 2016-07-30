from sqlobject import *
from sqlobject.dbconnection import ConnectionHub

hub = ConnectionHub()
__connection__ = hub


class Person(SQLObject):
    name = StringCol(length=100, default=None)
    address = StringCol(default=None)
    birthday = DateCol(default=None)
    phones = MultipleJoin("Phone")
    category = ForeignKey("Category", default=None)


class Phone(SQLObject):
    number = StringCol(length=20, default=None)
    person = ForeignKey("Person")


class Category(SQLObject):
    name = StringCol(length=20, alternateID=True)
    persons = RelatedJoin("Person")


def createTables(ifNotExists=True):
    Person.createTable(ifNotExists=ifNotExists)
    Phone.createTable(ifNotExists=ifNotExists)
    Category.createTable(ifNotExists=ifNotExists)

def setConnection(connURI):
    hub.threadConnection = connectionForURI(connURI)

def transaction():
    conn = hub.getConnection()
    conn.autoCommit = 0
    trans = conn.transaction()
    return trans
