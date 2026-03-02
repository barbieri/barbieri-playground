# helpers
import locale; locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

def format_number(value, decimals=2):
    return locale.format_string(f"%.{decimals}f", value, grouping=True)

def format_currency(value):
    return locale.currency(value, grouping=True)

def format_percentage(value, decimals=2):
    return format_number(value * 100, decimals) + '%'

def parse_number(value, default=None):
    if not value and default is not None:
        return default
    return locale.atof(value)

def parse_currency(value, default=None):
    return parse_number(value.strip(locale.currency(0, grouping=True).replace('0', '')), default=default)

def parse_percentage(value, default=None):
    if not value and default is not None:
        return default / 100
    return parse_number(value.strip('%'), default=default) / 100

# Logic:

area_total = parse_number(input("Área total da propriedade (Alq): "))
percentual_produtivo = parse_percentage(input("Percentual de área produtiva (padrão 80%): "), default=80)
toneladas_por_alqueire_produtivo = parse_number(input("Toneladas por Alqueire Produtivo-Ano: "))

toneladas_ano = area_total * percentual_produtivo * toneladas_por_alqueire_produtivo
print(f"Produtividade: Toneladas por ano: {format_number(toneladas_ano)}, por mês: {format_number(toneladas_ano / 12)}")

atr_acumulado = parse_currency(input("Valor do Kg ATR em Reais (R$) (ex: CONSECANA): "))
indice_cana_na_esteira = parse_number(input("Índice Cana na Esteira (Kg ATR) (padrão 121,97): "), default=121.97)
fun_rural = 1.5 / 100 # Descontado 1.5% de Fundo Rural (FunRural)
valor_atr_liquido_funrural = atr_acumulado * indice_cana_na_esteira * (1 - fun_rural)
print(f"Valor do Kg ATR em Reais (R$) já descontado o FunRural: {format_currency(valor_atr_liquido_funrural)}")

valor_producao = valor_atr_liquido_funrural * toneladas_ano
print(f"Valor total da produção já descontado o FunRural: {format_currency(valor_producao)}, por mês: {format_currency(valor_producao / 12)}")

percentual_pagamento_a_vista = parse_percentage(input("Percentual de Pagamento à vista (padrão 80%): "), default=80)
if round(percentual_pagamento_a_vista, 3) < 1:
    valor_producao_a_vista = valor_producao * percentual_pagamento_a_vista
    valor_producao_fechamento = valor_producao - valor_producao_a_vista
    print(f"Valor da produção à vista: {format_currency(valor_producao_a_vista)} (mensal: {format_currency(valor_producao_a_vista / 12)}), fechamento de safra: {format_currency(valor_producao_fechamento)}")

valor_alqueire = parse_currency(input("Valor do Alqueire (R$): "))
valor_alqueire_produtivo = valor_alqueire / percentual_produtivo
valor_total = area_total * valor_alqueire
print(f"Valor da Propriedade: {format_currency(valor_total)}, alqueire Produtivo: {format_currency(valor_alqueire_produtivo)}")

rendimento = valor_producao / valor_total
print(f"Rendimento ao ano: {format_percentage(rendimento)}")
