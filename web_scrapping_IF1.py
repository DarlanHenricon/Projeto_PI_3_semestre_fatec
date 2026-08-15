# -*- coding: utf-8 -*-
"""
Raspagem de dados financeiros - Santander Brasil
Fonte: Informe de Resultados (BRGAAP) - Relações com Investidores

Fluxo: acessar fonte -> achar documento -> baixar -> extrair tabelas do PDF
       -> tratar os dados -> validar -> gerar CSV com histórico.

Feito para Projeto Integrador - Análise Financeira Santander Brasil
"""
import os
import re
import sys
import csv
import json
import datetime
import argparse
import urllib.request
import urllib.error

import pdfplumber

from normalize import parse_br_number, clean_text, is_percentage, is_pp
from indicators import canonicalize

# ----------------------------------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# ----------------------------------------------------------------------------

# URL padrão do documento (pode mudar, então fique de olho)
DEFAULT_SOURCE_URL = (
    "https://api.mziq.com/mzfilemanager/v2/d/a2595886-9fbb-4339-8a38-71d6ce7c7d36/"
    "118f8091-12e1-8f80-bee8-c6a1f3f1660e?origin=2"
)
DOCUMENT_NAME = "Informe de Resultados 1T25 (BRGAAP) - Santander Brasil"
OUTPUT_DIR = "output"  # Pasta onde os arquivos vão ser salvos
RAW_PDF_PATH = os.path.join(OUTPUT_DIR, "informe_resultados_raw.pdf")
RAW_CSV_PATH = os.path.join(OUTPUT_DIR, "santander_dados_brutos.csv")
FINAL_CSV_PATH = os.path.join(OUTPUT_DIR, "santander_serie_historica.csv")
LOG_PATH = os.path.join(OUTPUT_DIR, "log_extracao.txt")

# Padrões pra reconhecer períodos (ex: 1T25, Mar/25) e valores numéricos
PERIOD_TOKEN_RE = re.compile(r"^([1-4]T\d{2}|[A-Za-zçÇ]{3}/\d{2})$")
VALUE_TOKEN_RE = re.compile(
    r"^\(?-?\d{1,3}(\.\d{3})*(,\d+)?\)?%?(pp)?$|^n\.a\.$|^-$"
)

# Rótulos que provavelmente são lixo (notas de rodapé, textos genéricos) e devem ser ignorados
LABEL_BLOCKLIST_RE = re.compile(
    r"^(resultados|estrat[ée]gia|reconcilia[çc][ãa]o|santander brasil|"
    r"\(\d+\)|nota|p[áa]gina \d+|r\$ milh[õo]es|em r\$|www\.)",
    re.IGNORECASE,
)

# Tópicos esperados nas tabelas (só pra referência, não usamos como filtro rígido)
EXPECTED_TABLE_TOPICS = [
    "Sumário Executivo", "Demonstração de Resultado Gerencial", "Margem Financeira",
    "Comissões", "Resultado de PDD", "Qualidade de crédito", "Despesas",
    "Balanço Patrimonial", "Carteira de Crédito", "Captações", "Capital",
]


def log(message, logfile=None):
    """Printa a mensagem no terminal e salva no arquivo de log."""
    print(message)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(message + "\n")


# ----------------------------------------------------------------------------
# ETAPA 1: ACESSAR E BAIXAR O PDF
# ----------------------------------------------------------------------------

def check_source_accessible(url):
    """Verifica se a URL tá no ar antes de baixar o PDF inteiro."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        # Se não aceitar HEAD, tenta com GET parcial
        if e.code in (403, 405):
            return check_source_accessible_get_fallback(url)
        return False, e.code, {}
    except Exception as e:
        return False, str(e), {}


def check_source_accessible_get_fallback(url):
    """Fallback: tenta baixar só o começo do arquivo pra ver se existe."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1024"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, resp.status, dict(resp.headers)
    except Exception as e:
        return False, str(e), {}


def download_pdf(url, dest_path, logfile=None):
    """Baixa o PDF e confere se é realmente um PDF (checa a assinatura %PDF-)."""
    log(f"[1/6] Verificando se a fonte tá acessível: {url}", logfile)
    ok, status, headers = check_source_accessible(url)
    if not ok:
        raise ConnectionError(f"Fonte inacessível. Detalhe: {status}")
    log(f"      Fonte OK (status={status}).", logfile)

    log("[2/6] Baixando o documento...", logfile)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        raise ConnectionError(f"Falha no download: {e}")

    # Segurança: se veio muito pequeno, provavelmente é página de erro
    if len(data) < 1024:
        raise ValueError(
            "Arquivo baixado é muito pequeno (<1KB). Deve ser página de erro, não o PDF."
        )

    # Verifica se é PDF de verdade
    if not data[:5] == b"%PDF-":
        preview = data[:200]
        raise ValueError(
            "Não é um PDF válido (assinatura %PDF- não encontrada). "
            f"Prévia: {preview!r}"
        )

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)

    size_kb = len(data) / 1024
    log(f"      Download concluído: {dest_path} ({size_kb:.1f} KB)", logfile)
    return dest_path


# ----------------------------------------------------------------------------
# ETAPA 2: EXTRAIR TEXTO DO PDF (MANTENDO A POSIÇÃO DAS PALAVRAS)
# ----------------------------------------------------------------------------

def extract_pages_layout_text(pdf_path, logfile=None):
    """
    Extrai o texto de cada página mantendo o alinhamento (layout=True).
    Isso ajuda a identificar colunas mesmo quando não têm linhas de grade.
    Retorna uma lista com o texto de cada página e uma dica do tópico.
    """
    log("[3/6] Extraindo texto com layout preservado (pdfplumber)...", logfile)
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        log(f"      PDF tem {n_pages} páginas.", logfile)
        for page_number, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text(layout=True) or ""
            except Exception as e:
                log(f"      [aviso] Erro na página {page_number}: {e}", logfile)
                text = ""
            plain_text = page.extract_text() or ""
            topic_hint = _guess_topic(plain_text)
            pages_data.append({"page": page_number, "text": text, "topic_hint": topic_hint})
    return pages_data, n_pages


def _guess_topic(page_text):
    """Tenta adivinhar o assunto da página batendo com os tópicos esperados."""
    for topic in EXPECTED_TABLE_TOPICS:
        if topic.lower() in page_text.lower():
            return topic
    return None


# ----------------------------------------------------------------------------
# ETAPA 3: PARSING LINHA A LINHA -> EXTRAIR DADOS
# ----------------------------------------------------------------------------

def _merge_pp_tokens(line):
    """Transforma 'N p.p.' em 'Npp' pra não atrapalhar a separação por espaços."""
    return re.sub(r"(-?\d[\d\.,]*)\s+p\.\s?p\.", r"\1pp", line, flags=re.IGNORECASE)


def _tokenize(line):
    """Divide a linha em tokens (palavras), tratando os pp primeiro."""
    line = _merge_pp_tokens(line)
    return [t for t in line.strip().split() if t]


def _extract_period_sequence(tokens):
    """
    Pega a sequência de períodos que aparecem no cabeçalho da tabela.
    Exemplo: ['1T24', '1T25', '1T24', 'x', '1T25', '1T25', '1T24', 'x', '1T25']
    Vai retornar ['1T24', '1T25'] (ordem de aparição, sem repetir).
    """
    seen = []
    for tok in tokens:
        if tok.lower() == "x":
            continue
        if PERIOD_TOKEN_RE.match(tok) and tok not in seen:
            seen.append(tok)
    return seen


def _is_header_line(tokens):
    """Diz se uma linha parece ser cabeçalho (tem pelo menos 2 períodos)."""
    periods = _extract_period_sequence(tokens)
    return len(periods) >= 2


def _extract_value_tokens(tokens):
    """Pega os tokens que parecem valores numéricos, começando do final da linha."""
    values = []
    for tok in reversed(tokens):
        if VALUE_TOKEN_RE.match(tok):
            values.insert(0, tok)
        else:
            break
    return values


def map_values_to_periods(value_tokens, periods):
    """
    Faz a correspondência entre os valores e os períodos.
    A lógica é baseada no padrão do relatório:
      - 5 valores  -> [P1, P2, ΔQoQ, P3, ΔYoY] => pega posições 0,1,3
      - 3 valores  -> [P1, P2, P3]
      - 2 períodos e 2 valores -> [P1, P2]
    Se não encaixar em nenhum padrão, retorna vazio.
    """
    n_periods = len(periods)
    n_values = len(value_tokens)

    if n_periods == 3 and n_values == 5:
        return {periods[0]: value_tokens[0], periods[1]: value_tokens[1], periods[2]: value_tokens[3]}
    if n_periods == 3 and n_values == 3:
        return {periods[0]: value_tokens[0], periods[1]: value_tokens[1], periods[2]: value_tokens[2]}
    if n_periods == 2 and n_values >= 2:
        return {periods[0]: value_tokens[0], periods[1]: value_tokens[1]}
    if n_periods >= 1 and n_values == n_periods:
        return dict(zip(periods, value_tokens))
    return {}


def infer_unit(canonical_unit, raw_value_str):
    """Decide qual unidade usar: % se tiver %, senão usa a unit canônica, ou 'número'."""
    if is_percentage(raw_value_str):
        return "%"
    if canonical_unit:
        return canonical_unit
    return "número"


def parse_page_into_records(page_entry, document_name, source_url, collection_date, logfile=None):
    """
    Analisa o texto de uma página, procurando tabelas no formato:
    cabeçalho com períodos -> linhas com rótulo + valores.
    Retorna os registros encontrados, quantas tabelas achou e eventuais anotações.
    """
    page = page_entry["page"]
    topic_hint = page_entry["topic_hint"]
    lines = page_entry["text"].split("\n")

    records = []
    tables_found = 0
    unparsed_notes = []

    current_periods = None
    rows_since_header = 0

    for raw_line in lines:
        if not raw_line.strip():
            continue
        tokens = _tokenize(raw_line)
        if not tokens:
            continue

        # Se achou um cabeçalho, atualiza os períodos atuais
        if _is_header_line(tokens):
            current_periods = _extract_period_sequence(tokens)
            rows_since_header = 0
            tables_found += 1
            continue

        if current_periods is None:
            continue  # Ainda não vimos cabeçalho nesta página

        # Separa rótulo (indicador) dos valores
        value_tokens = _extract_value_tokens(tokens)
        label_tokens = tokens[: len(tokens) - len(value_tokens)]
        label_raw = clean_text(" ".join(label_tokens))

        if not value_tokens or not label_raw:
            rows_since_header += 1
            if rows_since_header > 8:
                current_periods = None  # Sai do bloco da tabela
            continue

        # Filtra rótulos que são lixo (notas, rodapé, etc)
        if LABEL_BLOCKLIST_RE.match(label_raw):
            continue
        if len(label_tokens) > 14:
            continue  # Rótulo muito longo, provavelmente é texto narrativo

        # Mapeia valores para períodos
        mapping = map_values_to_periods(value_tokens, current_periods)
        if not mapping:
            unparsed_notes.append(
                f"pagina {page}: '{label_raw[:60]}' com {len(value_tokens)} valor(es) "
                f"pra {len(current_periods)} período(s) - padrão não reconhecido, ignorado"
            )
            continue

        # Padroniza o nome do indicador
        canonical_name, category, canonical_unit = canonicalize(label_raw)

        for period_label, raw_value in mapping.items():
            value = parse_br_number(raw_value)
            if value is None:
                continue
            unit = infer_unit(canonical_unit, raw_value)
            records.append({
                "periodo": period_label,
                "indicador": canonical_name,
                "valor": value,
                "unidade": unit,
                "categoria": category,
                "documento": document_name,
                "url_origem": source_url,
                "pagina": page,
                "data_coleta": collection_date,
            })
        rows_since_header = 0

    return records, tables_found, unparsed_notes


# ----------------------------------------------------------------------------
# ETAPA 4: LIMPEZA E DEDUPLICAÇÃO
# ----------------------------------------------------------------------------

def deduplicate_records(records, logfile=None):
    """
    Remove duplicatas exatas (mesmo período+indicador+valor+página).
    Se o mesmo indicador/período aparece com valores diferentes em tabelas diferentes,
    mantém o primeiro e registra o conflito no log.
    """
    seen_exact = set()
    best = {}
    conflicts = []

    for r in records:
        key_exact = (r["periodo"], r["indicador"], r["valor"], r["unidade"])
        if key_exact in seen_exact:
            continue
        seen_exact.add(key_exact)

        key_indicator = (r["periodo"], r["indicador"], r["unidade"])
        if key_indicator in best and best[key_indicator]["valor"] != r["valor"]:
            conflicts.append(
                f"Conflito: {r['periodo']} / {r['indicador']} ({r['unidade']}): "
                f"{best[key_indicator]['valor']} (pág. {best[key_indicator]['pagina']}) "
                f"vs {r['valor']} (pág. {r['pagina']}) -> mantendo o primeiro"
            )
            continue
        if key_indicator not in best:
            best[key_indicator] = r

    for c in conflicts:
        log(f"      [aviso] {c}", logfile)

    return list(best.values())


def validate_records(records, logfile=None):
    """Faz umas verificações básicas pra ver se os dados fazem sentido."""
    issues = []
    if not records:
        issues.append("Nenhum registro foi extraído do documento.")

    # Percentuais fora do intervalo plausível
    percent_out_of_range = [
        r for r in records
        if r["unidade"] == "%" and not (-100 <= r["valor"] <= 200)
    ]
    if percent_out_of_range:
        issues.append(
            f"{len(percent_out_of_range)} percentual(is) fora do esperado (-100% a 200%) - "
            f"vale revisar."
        )

    for r in percent_out_of_range[:5]:
        log(f"      [validação] Valor suspeito: {r['periodo']} / {r['indicador']} = {r['valor']}%", logfile)

    n_periods = len(set(r["periodo"] for r in records))
    n_indicators = len(set(r["indicador"] for r in records))
    log(f"      Validação: {n_periods} período(s), {n_indicators} indicador(es) distintos.", logfile)

    return issues


# ----------------------------------------------------------------------------
# ETAPA 5: SALVAR CSV
# ----------------------------------------------------------------------------

CSV_FIELDS = ["periodo", "indicador", "valor", "unidade", "categoria",
              "documento", "url_origem", "pagina", "data_coleta"]


def write_csv(records, path):
    """Salva os registros num arquivo CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    records_sorted = sorted(records, key=lambda r: (r["categoria"], r["indicador"], r["periodo"]))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in records_sorted:
            writer.writerow(r)


# ----------------------------------------------------------------------------
# ETAPA 6: RELATÓRIO FINAL
# ----------------------------------------------------------------------------

def print_summary_report(n_tables, n_records_raw, n_records_final, periods, indicators, issues, logfile=None):
    """Mostra um resumo do que foi extraído."""
    log("\n" + "=" * 70, logfile)
    log("RELATÓRIO DE EXTRAÇÃO - Santander Brasil (Informe de Resultados)", logfile)
    log("=" * 70, logfile)
    log(f"Documentos processados:             1", logfile)
    log(f"Tabelas extraídas:                   {n_tables}", logfile)
    log(f"Registros brutos:                    {n_records_raw}", logfile)
    log(f"Registros finais (pós-tratamento):   {n_records_final}", logfile)
    log(f"Indicadores distintos:               {len(indicators)}", logfile)
    log(f"Períodos encontrados:                {', '.join(sorted(periods))}", logfile)
    if issues:
        log("\nAvisos / limitações:", logfile)
        for issue in issues:
            log(f"  - {issue}", logfile)
    else:
        log("\nNenhuma inconsistência crítica na validação básica.", logfile)
    log("=" * 70, logfile)


# ----------------------------------------------------------------------------
# ORQUESTRAÇÃO - MAIN
# ----------------------------------------------------------------------------

def run(source_url=DEFAULT_SOURCE_URL, keep_raw=True):
    """Executa o pipeline completo de raspagem e processamento dos dados."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    collection_date = datetime.date.today().isoformat()

    # Passo 1: Baixar o PDF
    try:
        download_pdf(source_url, RAW_PDF_PATH, logfile=LOG_PATH)
    except Exception as e:
        log(f"\n[ERRO FATAL] Não foi possível baixar o documento: {e}", LOG_PATH)
        log("Verifique sua conexão e se a URL ainda é válida. "
            "Consulte https://www.santander.com.br/ri/ para o documento atualizado.", LOG_PATH)
        sys.exit(1)

    # Passo 2: Extrair texto do PDF
    pages_data, n_pages = extract_pages_layout_text(RAW_PDF_PATH, logfile=LOG_PATH)

    # Passo 3: Parsear as páginas e extrair registros
    log("[4/6] Interpretando tabelas e convertendo pra registros...", LOG_PATH)
    all_records = []
    unparsed_tables = []
    total_tables_found = 0
    for page_entry in pages_data:
        records, n_tables, notes = parse_page_into_records(
            page_entry, DOCUMENT_NAME, source_url, collection_date, logfile=LOG_PATH
        )
        all_records.extend(records)
        total_tables_found += n_tables
        unparsed_tables.extend(notes)

    if total_tables_found == 0:
        log("[ERRO] Nenhuma tabela com cabeçalho de período foi encontrada. "
            "O layout do PDF deve ter mudado. Extração interrompida.", LOG_PATH)
        sys.exit(1)

    log(f"      Tabelas identificadas: {total_tables_found}", LOG_PATH)
    log(f"      Registros brutos: {len(all_records)}", LOG_PATH)
    if unparsed_tables:
        log(f"      Linhas ignoradas: {len(unparsed_tables)}", LOG_PATH)
        for u in unparsed_tables[:10]:
            log(f"        - {u}", LOG_PATH)

    # Salva CSV bruto se pediu
    if keep_raw and all_records:
        write_csv(all_records, RAW_CSV_PATH)
        log(f"      CSV bruto salvo em: {RAW_CSV_PATH}", LOG_PATH)

    # Passo 4: Tratar, deduplicar e validar
    log("[5/6] Tratando, deduplicando e validando...", LOG_PATH)
    final_records = deduplicate_records(all_records, logfile=LOG_PATH)
    issues = validate_records(final_records, logfile=LOG_PATH)

    # Passo 5: Gerar CSV final
    log("[6/6] Gerando CSV final...", LOG_PATH)
    write_csv(final_records, FINAL_CSV_PATH)
    log(f"      CSV final salvo em: {FINAL_CSV_PATH}", LOG_PATH)

    periods = set(r["periodo"] for r in final_records)
    indicators = set(r["indicador"] for r in final_records)

    print_summary_report(
        n_tables=total_tables_found,
        n_records_raw=len(all_records),
        n_records_final=len(final_records),
        periods=periods,
        indicators=indicators,
        issues=issues + [u for u in unparsed_tables[:5]],
        logfile=LOG_PATH,
    )

    return final_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Raspador de dados financeiros do Santander Brasil (Informe de Resultados)."
    )
    parser.add_argument("--url", default=DEFAULT_SOURCE_URL, help="URL do PDF a processar.")
    parser.add_argument("--no-raw", action="store_true", help="Não salvar o CSV bruto.")
    args = parser.parse_args()

    run(source_url=args.url, keep_raw=not args.no_raw)