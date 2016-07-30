#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from sqlobject import *
from eagle import *
import os
import datetime

db_filename = os.path.abspath("financeiro.db")
conn_str = "sqlite://" + db_filename
sqlhub.processConnection = connectionForURI(conn_str)

class Conta(SQLObject):
    pago = BoolCol(default=False)
    data = DateCol()
    nota_fiscal = StringCol()
    firma = StringCol()
    mercadorias = MultipleJoin("Mercadoria")


class Mercadoria(SQLObject):
    codigo = IntCol()
    quantidade = IntCol()
    valor = CurrencyCol()
    produto = StringCol()
    conta = ForeignKey("Conta")

Conta.createTable(ifNotExists=True)
Mercadoria.createTable(ifNotExists=True)


def mostrar_contas(app, *args):
    query = []

    mostrar_apenas = app["mostrar_apenas"]
    if mostrar_apenas == "Pagas":
        query.append(Conta.q.pago == True)
    elif mostrar_apenas == "Não Pagas":
        query.append(Conta.q.pago == False)

    filtro = app["filtro"].strip().replace('*', '%')
    if filtro:
        filtro = "%" + filtro + "%"
        query.append(OR(LIKE(Conta.q.nota_fiscal, filtro),
                        LIKE(Conta.q.firma, filtro)))

    table = app["table-contas"]
    del table[:]

    if query:
        contas = Conta.select(AND(*query), orderBy=Conta.q.data)
    else:
        contas = Conta.select(orderBy=Conta.q.data)

    for c in contas:
        table.append((c.pago, c.data, c.nota_fiscal, c.firma, c),
                     select=False,
                     autosize=False)
    table.columns_autosize()



def filtro_changed(app, filtro, value):
    if not app.filtro_changed_scheduled:
        def do_filtro_changed(app):
            mostrar_contas(app)
            app.filtro_changed_scheduled = False

        app.filtro_changed_scheduled = True
        app.timeout_add(200, do_filtro_changed)


def marcar_pago(app, button):
    selected = app["table-contas"].selected()
    if selected:
        for index, row in selected:
            row[0] = True
            row[4].pago = True


def mostrar_mercadorias(app, table, selected):
    table_mercadorias = app["table-mercadorias"]
    del table_mercadorias[:]
    if not selected:
        return

    for m in selected[0][1][4].mercadorias:
        table_mercadorias.append((m.codigo, m.quantidade, m.valor, m.produto),
                                 select=False,
                                 autosize=False)
    table_mercadorias.columns_autosize()

def adicionar_nova_conta(app, button):
    data = app["data"].split('-')
    data = [ int(i) for i in data ]
    data = datetime.date(*data)
    conta = Conta(data=data,
                  nota_fiscal=app["nota_fiscal"],
                  firma=app["firma"],
                  )

    app["data"] = ""
    app["nota_fiscal"] = ""
    app["firma"] = ""
    app.close()
    mostrar_contas(get_app_by_id("app_contas"))


def cancelar_nova_conta(app, *args):
    if app["data"] or \
       app["nota_fiscal"] or \
       app["firma"] or \
       len(app["table-mercadorias"]) > 0:
        return confirm("Dados não salvos, deseja cancelar a operação?")
    return True


def nova_conta(app, button):
    app_edit = App(title="Conta",
                   id="app_edit_conta",
                   quit_callback=cancelar_nova_conta,
                   center=(Entry(id="data",
                                 label="Data",
                                 ),
                           Entry(id="nota_fiscal",
                                 label="Nota fiscal",
                                 ),
                           Entry(id="firma",
                                 label="Firma",
                                 ),
                           Table(id="table-mercadorias",
                                 label="Mercadorias",
                                 editable=True,
                                 headers=("Código", "Qtd", "Valor", "Produto"),
                                 types=(int, int, float, str),
                                 ),
                           ),
                   bottom=(Button(id="salvar",
                                  label="Salvar",
                                  callback=adicionar_nova_conta,
                                  ),
                           Button(id="cancelar",
                                  label="Cancelar",
                                  callback=lambda app, button: app.close(),
                                  ),
                           ),
                   )


app = App(title="Financeiro",
          id="app_contas",
          top=(Button(id="nova-conta",
                      label="Nova Conta",
                      callback=nova_conta,
                      ),
               ),
          center=(Group(id="group-contas",
                        label="Contas",
                        expand_policy=ExpandPolicy.All(),
                        children=(Group(id="group-filtro",
                                        label=None,
                                        border=None,
                                        horizontal=True,
                                        children=(Selection(id="mostrar_apenas",
                                                            label="Mostrar apenas",
                                                            options=("Pagas",
                                                                     "Não Pagas",
                                                                     "Ambas"),
                                                            value="Não Pagas",
                                                            expand_policy=ExpandPolicy.Vertical(),
                                                            callback=mostrar_contas,
                                                            ),
                                                  VSeparator(expand_policy=ExpandPolicy.FillVertical()),
                                                  Entry(id="filtro",
                                                        label="Procura",
                                                        expand_policy=ExpandPolicy.All(),
                                                        callback=filtro_changed,
                                                        ),
                                                  ),
                                        ),
                                  Table(id="table-contas",
                                        label=None,
                                        editable=True,
                                        headers=("P?", "Data", "Nota Fiscal", "Firma", "Obj"),
                                        types=(bool, str, str, str, object),
                                        hidden_columns_indexes=(4,),
                                        selection_callback=mostrar_mercadorias,
                                        user_widgets=Button(id="pagar",
                                                            label="Marcar como pago",
                                                            callback=marcar_pago,
                                                            ),
                                        ),
                                  ),
                        ),
                  Group(id="group-mercadorias",
                        label="Mercadorias",
                        expand_policy=ExpandPolicy.All(),
                        children=(Table(id="table-mercadorias",
                                        label=None,
                                        headers=("Código", "Qtd", "Valor", "Produto"),
                                        types=(int, int, float, str),
                                        ),
                                  ),
                        ),

                  )
          )
app.filtro_changed_scheduled = False
app.idle_add(mostrar_contas)


run()
