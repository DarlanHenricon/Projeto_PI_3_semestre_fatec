# 📊 Projeto Integrador — Web Scraping e Análise de Dados

Projeto acadêmico desenvolvido no curso de **Ciência de Dados para Negócios — FATEC Sebrae**, com o objetivo de aplicar conceitos de **Web Scraping, Engenharia de Dados, Python, tratamento de dados e análise de indicadores financeiros** em um problema real.

O projeto tem como foco a coleta, extração, padronização e organização de informações presentes em documentos financeiros públicos, transformando dados originalmente disponibilizados em documentos PDF em uma estrutura adequada para análise.

---

## 🎯 Objetivo do projeto

O principal objetivo é desenvolver um processo automatizado capaz de:

1. Localizar documentos financeiros públicos;
2. Baixar e processar arquivos PDF;
3. Extrair informações relevantes dos documentos;
4. Identificar indicadores financeiros;
5. Normalizar números, percentuais e unidades;
6. Padronizar diferentes formas de escrita dos mesmos indicadores;
7. Organizar os dados em uma estrutura tabular;
8. Preparar os dados para análises posteriores;
9. Documentar todo o processo de coleta e tratamento.

A ideia central é demonstrar como técnicas de **Data Science e programação podem transformar informações não estruturadas em dados prontos para análise**.

---

## 🧠 Contexto acadêmico

Este projeto faz parte das atividades acadêmicas do curso de:

**Ciência de Dados para Negócios**
**FATEC Sebrae — São Paulo**

O desenvolvimento do projeto busca integrar conhecimentos de programação, análise de dados e negócios, utilizando uma situação próxima de um cenário profissional de dados.

Além do resultado final, o projeto documenta o processo de desenvolvimento, permitindo compreender como os dados foram obtidos, tratados e estruturados.

---

## 🏦 Fonte dos dados

Os dados utilizados são provenientes de **documentos financeiros públicos disponibilizados pela instituição analisada**, incluindo documentos como:

* Demonstrações Financeiras;
* Informes de Resultados;
* Apresentações de Resultados;
* Outros documentos financeiros públicos relevantes.

Os documentos são disponibilizados originalmente em formato **PDF**, o que torna necessária uma etapa de extração e tratamento antes que os dados possam ser utilizados em análises estruturadas.

> **Importante:** os documentos e informações de terceiros permanecem sujeitos aos respectivos direitos autorais, termos de uso e condições de disponibilização de seus proprietários. Este projeto não reivindica propriedade sobre esses dados ou documentos.

---

# 🔎 Processo de desenvolvimento

O projeto foi estruturado em diferentes etapas de um pipeline de dados.

```text
Documentos públicos
        ↓
Download dos PDFs
        ↓
Extração do texto
        ↓
Localização dos indicadores
        ↓
Limpeza dos dados
        ↓
Normalização dos valores
        ↓
Padronização dos indicadores
        ↓
Validação
        ↓
Dados estruturados
        ↓
Análise
```

---

## 1. 📥 Coleta dos documentos

A primeira etapa consiste em obter os documentos financeiros disponibilizados publicamente.

Os arquivos são organizados de acordo com período, tipo de documento e instituição analisada.

Essa etapa permite criar uma base histórica que posteriormente pode ser utilizada para comparar diferentes períodos.

---

## 2. 🕷️ Web Scraping

Foi desenvolvido um processo automatizado em **Python** para auxiliar na coleta e processamento das informações.

Entre as tecnologias utilizadas estão:

* Python
* `urllib`
* `pdfplumber`
* Expressões regulares (`re`)
* Estruturas de dados nativas do Python

O objetivo do scraping não é simplesmente baixar páginas ou arquivos, mas construir um processo reproduzível de coleta de dados.

---

## 3. 📄 Extração dos PDFs

Como grande parte das informações está disponível em documentos PDF, uma das etapas mais importantes é transformar o conteúdo desses documentos em texto processável.

Para isso, foi utilizada a biblioteca:

```python
import pdfplumber
```

O processo permite acessar as páginas dos documentos e extrair seu conteúdo textual para posterior processamento.

---

## 4. 🧹 Tratamento e limpeza

Os dados extraídos dos PDFs não estão necessariamente prontos para utilização.

Podem existir diferenças como:

* Separadores decimais;
* Separadores de milhares;
* Símbolos de porcentagem;
* Unidades diferentes;
* Espaços desnecessários;
* Quebras de linha;
* Variações na escrita dos indicadores;
* Informações adicionais presentes no texto.

Por isso, foi criada uma etapa específica de limpeza e normalização.

---

## 5. 🔢 Normalização de números

Um dos problemas encontrados é que números financeiros podem aparecer em diferentes formatos.

Por exemplo:

```text
33,67%
33.67%
1.234,56
1,234.56
```

Para evitar que essas diferenças prejudiquem a análise, o projeto possui funções responsáveis pela interpretação e padronização dos valores.

Exemplo:

```python
from normalize import parse_br_number
```

Dessa forma, diferentes representações podem ser convertidas para um formato consistente.

---

## 6. 📊 Identificação de percentuais e pontos percentuais

Também foram implementadas funções para identificar diferentes tipos de informação percentual.

Exemplo:

```python
from normalize import is_percentage
from normalize import is_pp
```

Isso permite diferenciar situações como:

```text
+5,2%
+5,2 p.p.
```

Essa distinção é importante porque **percentual (%) e ponto percentual (p.p.) não representam a mesma coisa**.

---

## 7. 🏷️ Padronização dos indicadores

Outro desafio encontrado foi a existência de diferentes formas de representar um mesmo indicador.

Para resolver esse problema, foi criada uma camada de padronização utilizando:

```python
from indicators import canonicalize
```

A função transforma diferentes nomenclaturas em uma representação padronizada.

Isso facilita posteriormente:

* Comparações entre períodos;
* Criação de tabelas;
* Análises estatísticas;
* Visualizações;
* Construção de dashboards;
* Automação do processo.

---

# 🗂️ Estrutura do projeto

A estrutura do repositório foi pensada para separar código, dados e documentação.

```text
.
├── README.md
├── LICENSE
│
├── src/
│   ├── scraper.py
│   ├── normalize.py
│   ├── indicators.py
│   └── ...
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   └── ...
│
└── docs/
    └── ...
```

> A estrutura pode ser adaptada conforme o desenvolvimento do projeto.

### `src/`

Contém os códigos responsáveis pela coleta, processamento e transformação dos dados.

### `data/raw/`

Destinado aos dados/documentos em seu formato original, quando sua redistribuição for permitida.

### `data/processed/`

Contém os dados após as etapas de tratamento e padronização, quando aplicável.

### `notebooks/`

Área destinada à exploração, análise e visualização dos dados.

### `docs/`

Documentação complementar sobre o projeto e sua metodologia.

---

# 🛠️ Tecnologias utilizadas

### Linguagem

* 🐍 Python

### Bibliotecas

* `urllib`
* `pdfplumber`
* `re`
* Outras bibliotecas utilizadas durante as etapas de análise e processamento

### Conceitos aplicados

* Web Scraping
* Extração de dados de PDF
* ETL
* Limpeza de dados
* Normalização
* Padronização de dados
* Expressões regulares
* Análise exploratória
* Indicadores financeiros
* Automação de processos

---

# 📈 Próximas etapas

O projeto pode evoluir para uma estrutura mais completa de análise de dados.

Entre as possibilidades estão:

* [ ] Automatizar completamente a coleta dos documentos;
* [ ] Aumentar a quantidade de períodos analisados;
* [ ] Criar uma base histórica estruturada;
* [ ] Implementar validações automáticas;
* [ ] Criar análises exploratórias;
* [ ] Criar visualizações dos indicadores;
* [ ] Desenvolver um dashboard;
* [ ] Automatizar a atualização da base;
* [ ] Comparar indicadores entre diferentes períodos;
* [ ] Criar métricas para análise da evolução financeira.

---

# 🎓 Objetivo de aprendizado

Mais do que obter um conjunto de dados final, este projeto tem como objetivo demonstrar o processo completo de transformação de dados:

> **Dados não estruturados → dados tratados → dados estruturados → informação → análise.**

O desenvolvimento também busca consolidar conhecimentos de programação e análise de dados aplicados a um problema relacionado ao contexto empresarial e financeiro.

---

# 👨‍💻 Autor

**Darlan Henricon**

Estudante de **Ciência de Dados para Negócios — FATEC Sebrae**

GitHub:
https://github.com/DarlanHenricon

---

# ⚖️ Licença e uso

Este projeto foi desenvolvido para **fins acadêmicos, educacionais e de portfólio**.

O código disponibilizado neste repositório é de autoria de **Darlan Henricon**, salvo quando indicado de outra forma.

É permitido consultar e estudar o código para fins educacionais, desde que a autoria seja devidamente reconhecida.

**Não é autorizada a utilização deste projeto, total ou parcialmente, para fins comerciais sem autorização prévia do autor.**

A utilização de trechos do projeto em trabalhos acadêmicos, estudos ou projetos educacionais deve manter a referência ao autor e ao repositório original.

Os documentos, dados e informações obtidos de fontes externas permanecem sujeitos às respectivas licenças, direitos autorais e termos de uso.

Para detalhes completos sobre as condições de utilização do código, consulte o arquivo [`LICENSE`](LICENSE).

---

## 📌 Observação

Este projeto possui finalidade **acadêmica e educacional** e não representa, necessariamente, qualquer posição, recomendação ou análise oficial da instituição cujos documentos são utilizados como fonte.

O projeto tem como finalidade demonstrar técnicas de **coleta, tratamento, organização e análise de dados** aplicadas a informações públicas.

---

⭐ Se este projeto foi útil para seus estudos, considere deixar uma estrela no repositório.

**Desenvolvido por Darlan Henricon — Ciência de Dados para Negócios | FATEC Sebrae**
