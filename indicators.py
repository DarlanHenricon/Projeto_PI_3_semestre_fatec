# -*- coding: utf-8 -*-
"""
Catálogo de indicadores financeiros conhecidos do Informe de Resultados do
Santander Brasil (BRGAAP). Usado para:
  1) normalizar rótulos extraídos do PDF (que podem variar levemente entre
     páginas/trimestres) para um nome canônico;
  2) atribuir categoria e unidade padrão a cada indicador;
  3) decidir se uma célula numérica corresponde a % ou a um valor monetário.

Este catálogo NÃO restringe o que pode ser extraído: qualquer linha de
tabela com rótulo + números é candidata a virar um registro. O catálogo
apenas melhora a padronização de nomes/unidades quando há correspondência.
Indicadores fora do catálogo são mantidos com o rótulo original (limpo) e
unidade inferida a partir do próprio valor (ex.: presença de '%').
"""
import re

# (regex do rótulo tal como aparece no PDF -> (nome canônico, categoria, unidade))
INDICATOR_MAP = [
    (r"^lucro l[ií]quido gerencial$", "Lucro líquido gerencial", "Desempenho financeiro", "R$ milhões"),
    (r"^lucro l[ií]quido cont[áa]bil$", "Lucro líquido contábil", "Desempenho financeiro", "R$ milhões"),
    (r"^lucro l[ií]quido$", "Lucro líquido", "Desempenho financeiro", "R$ milhões"),
    (r"^resultado operacional$", "Resultado operacional", "Desempenho financeiro", "R$ milhões"),
    (r"^resultado gerencial antes de impostos$", "Resultado antes de impostos", "Desempenho financeiro", "R$ milhões"),
    (r"^resultado n[ãa]o operacional$", "Resultado não operacional", "Desempenho financeiro", "R$ milhões"),
    (r"^margem financeira bruta$", "Margem financeira bruta", "Desempenho financeiro", "R$ milhões"),
    (r"^margem financeira l[íi]quida$", "Margem financeira líquida", "Desempenho financeiro", "R$ milhões"),
    (r"^margem financeira$", "Margem financeira", "Desempenho financeiro", "R$ milhões"),
    (r"^margem financeira com clientes$|^clientes \(margem\)$", "Margem financeira com clientes", "Desempenho financeiro", "R$ milhões"),
    (r"^margem financeira com o mercado$|^margem com o mercado$", "Margem financeira com o mercado", "Desempenho financeiro", "R$ milhões"),
    (r"^receita total$", "Receita total", "Desempenho financeiro", "R$ milhões"),
    (r"^comiss(õ|o)es$|^total comiss(õ|o)es$", "Comissões", "Desempenho financeiro", "R$ milhões"),
    (r"^receitas de prest.* servi[çc]os", "Receitas de prestação de serviços e tarifas bancárias", "Desempenho financeiro", "R$ milhões"),

    (r"^carteira de cr[ée]dito$", "Carteira de crédito", "Crédito e risco", "R$ milhões"),
    (r"^carteira de cr[ée]dito ampliada[1-9]?$", "Carteira de crédito ampliada", "Crédito e risco", "R$ milhões"),
    (r"^carteira renegociada$", "Carteira renegociada", "Crédito e risco", "R$ milhões"),
    (r"^write.?off$", "Write-off", "Crédito e risco", "R$ milhões"),
    (r"^resultado de pdd( gerencial)?$", "Resultado de PDD", "Crédito e risco", "R$ milhões"),
    (r"^provis[ãa]o de cr[ée]dito$", "Provisão de crédito", "Crédito e risco", "R$ milhões"),
    (r"^recupera[çc][ãa]o de cr[ée]dito$", "Recuperação de crédito", "Crédito e risco", "R$ milhões"),
    (r"^custo de cr[ée]dito( recorrente)?( 12m)?[1-9]?$", "Custo de crédito recorrente", "Crédito e risco", "%"),
    (r"^[íi]ndice de inadimpl[êe]ncia \(15 a 90 dias\)$", "Índice de inadimplência 15-90 dias", "Crédito e risco", "%"),
    (r"^[íi]ndice de inadimpl[êe]ncia \(acima de 90 dias\)$", "Índice de inadimplência acima de 90 dias", "Crédito e risco", "%"),
    (r"^[íi]ndice de cobertura \(est[áa]gio 3\)$", "Índice de cobertura (Estágio 3)", "Crédito e risco", "%"),
    (r"^npl formation( ex.renegocia[çc][ãa]o)?[1-9]?$", "NPL Formation", "Crédito e risco", "R$ milhões"),

    (r"^roae gerencial.*$|^roae$", "ROAE gerencial", "Rentabilidade", "%"),
    (r"^roaa gerencial.*$|^roaa$", "ROAA gerencial", "Rentabilidade", "%"),
    (r"^[íi]ndice de efici[êe]ncia[1-9]?$", "Índice de eficiência", "Eficiência", "%"),
    (r"^[íi]ndice de recorr[êe]ncia[1-9]?$", "Índice de recorrência", "Eficiência", "%"),

    (r"^ativos totais$|^total do ativo$", "Ativos totais", "Estrutura financeira", "R$ milhões"),
    (r"^total do passivo$", "Passivos totais", "Estrutura financeira", "R$ milhões"),
    (r"^patrim[ôo]nio l[íi]quido$", "Patrimônio líquido", "Estrutura financeira", "R$ milhões"),
    (r"^dep[óo]sitos$", "Depósitos", "Estrutura financeira", "R$ milhões"),
    (r"^capta[çc](õ|o)es de clientes[1-9]?$|^capta[çc][ãa]o de clientes \(a\)$", "Captações de clientes", "Estrutura financeira", "R$ milhões"),
    (r"^total capta[çc](õ|o)es \(b\)$", "Total de captações", "Estrutura financeira", "R$ milhões"),
    (r"^[íi]ndice de basileia( \(bis\))?$", "Índice de Basileia", "Estrutura financeira", "%"),
    (r"^[íi]ndice de capital principal \(cet1\)$|^capital principal \(%\)$", "Índice de capital principal (CET1)", "Estrutura financeira", "%"),
    (r"^ativo ponderado pelo risco \(rwa\)$", "Ativos ponderados pelo risco (RWA)", "Estrutura financeira", "R$ milhões"),

    (r"^despesas gerais$|^total despesas gerais$", "Despesas gerais", "Eficiência", "R$ milhões"),
    (r"^despesas de pessoal[1-9]?$", "Despesas de pessoal", "Eficiência", "R$ milhões"),
    (r"^despesas administrativas$|^total despesas administrativas$", "Despesas administrativas", "Eficiência", "R$ milhões"),
    (r"^despesas tribut[áa]rias$", "Despesas tributárias", "Eficiência", "R$ milhões"),

    (r"^funcion[áa]rios$", "Número de funcionários", "Negócio e escala", "unidades"),
    (r"^lojas$", "Número de lojas", "Negócio e escala", "unidades"),
    (r"^lojas e pabs$", "Lojas e PABs", "Negócio e escala", "unidades"),
    (r"^pabs$", "Número de PABs", "Negócio e escala", "unidades"),
    (r"^caixas eletr[ôo]nicos.*pr[óo]prios$", "Caixas eletrônicos próprios", "Negócio e escala", "unidades"),
    (r"^clientes$", "Número de clientes", "Negócio e escala", "milhões de clientes"),

    (r"^valor de mercado.*$", "Valor de mercado", "Estrutura financeira", "R$ milhões"),
    (r"^lucro l[íi]quido gerencial por unit.*$", "Lucro líquido gerencial por unit", "Desempenho financeiro", "R$"),
    (r"^lucro l[íi]quido societ[áa]rio por unit.*$", "Lucro líquido societário por unit", "Desempenho financeiro", "R$"),
    (r"^valor patrimonial por unit.*$", "Valor patrimonial por unit", "Estrutura financeira", "R$"),
    (r"^quantidade de a[çc](õ|o)es.*$", "Quantidade de ações em circulação", "Estrutura financeira", "milhões de ações"),
    (r"^jcp \+ dividendos.*$", "JCP + Dividendos", "Estrutura financeira", "R$ milhões"),
]

_COMPILED = [(re.compile(pat, flags=re.IGNORECASE), name, cat, unit) for pat, name, cat, unit in INDICATOR_MAP]


def canonicalize(label):
    """
    Retorna (nome_canonico, categoria, unidade_padrao) se o rótulo bater
    com o catálogo; caso contrário retorna (rotulo_limpo, 'Outros', None).
    """
    norm = re.sub(r"\s+", " ", label.strip().lower())
    norm = norm.rstrip("0123456789").strip()  # remove marcadores de nota de rodapé tipo "carteira ampliada4"
    for regex, name, cat, unit in _COMPILED:
        if regex.match(norm):
            return name, cat, unit
    return label.strip(), "Outros", None
