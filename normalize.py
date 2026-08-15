# -*- coding: utf-8 -*-
"""
Funções de normalização e limpeza de valores extraídos do PDF do Santander.
Trata especificamente o formato numérico brasileiro (1.234,56) e as
convenções usadas nos relatórios financeiros (parênteses = negativo,
'n.a.' = não aplicável, 'p.p.' = pontos percentuais, etc.).
"""
import re

# Padrão de número em formato BR, com sinal opcional, parênteses opcionais
# (indicando negativo), milhar com ponto e decimal com vírgula.
_NUM_RE = re.compile(
    r"^\(?\s*-?\s*R?\$?\s*(\d{1,3}(?:\.\d{3})*|\d+)(,\d+)?\s*%?\s*\)?$"
)

NA_TOKENS = {"n.a.", "n/a", "na", "-", "—", "–", "", "nd", "n.d."}


def clean_text(s):
    """Remove espaços duplicados, quebras de linha e caracteres de controle."""
    if s is None:
        return ""
    s = str(s).replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def is_percentage(raw):
    return "%" in raw


def is_pp(raw):
    """Detecta 'pontos percentuais' (p.p.), que representam variação, não valor absoluto."""
    return bool(re.search(r"p\.?\s?p\.?", raw, flags=re.IGNORECASE))


def parse_br_number(raw):
    """
    Converte uma string em formato numérico brasileiro para float.
    Retorna None se não for possível interpretar como número
    (ex.: 'n.a.', texto narrativo, célula vazia).

    Trata:
      - separador de milhar '.' e decimal ','
      - parênteses como negativo: (823) -> -823
      - sinal de % (removido, mas sinalizado por is_percentage)
      - espaços e o símbolo R$
    """
    if raw is None:
        return None
    original = raw
    s = clean_text(raw)
    if s.lower() in NA_TOKENS:
        return None

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    if s.startswith("-"):
        negative = True
        s = s[1:].strip()

    s = s.replace("R$", "").replace("%", "").strip()
    s = re.sub(r"p\.?\s?p\.?", "", s, flags=re.IGNORECASE).strip()

    if s == "" or s.lower() in NA_TOKENS:
        return None

    # remove separador de milhar '.', troca decimal ',' por '.'
    # cuidado: só troca se o padrão realmente parecer BR (não confundir com números já em formato US)
    if re.match(r"^\d{1,3}(\.\d{3})*(,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.match(r"^\d+,\d+$", s):
        s = s.replace(",", ".")
    elif re.match(r"^\d+$", s):
        pass  # já é inteiro puro
    else:
        # não bate com nenhum padrão numérico esperado -> não é um número confiável
        return None

    try:
        value = float(s)
    except ValueError:
        return None

    if negative:
        value = -value
    return value


def looks_like_period_header(token):
    """
    Detecta se uma célula de cabeçalho representa um período
    (trimestre 1T25, mês/ano Mar/25, ou variação 1T25 x 4T24).
    """
    token = clean_text(token)
    if re.match(r"^[1-4]T\d{2}$", token):
        return "trimestre"
    if re.match(r"^[A-Za-zç]{3}/\d{2}$", token):
        return "data"
    if re.search(r"\bx\b", token) or "1T25 x" in token or "x " in token:
        return "variacao"
    return None


def is_variation_column(header_text):
    """Colunas de variação percentual/p.p. entre períodos (não representam um período em si)."""
    header_text = clean_text(header_text)
    return bool(re.search(r"\bx\b", header_text)) or "var" in header_text.lower()
