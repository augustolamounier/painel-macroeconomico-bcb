"""Gera e executa o notebook de exploração dos dados (Etapa 2 do projeto).

Uso:
    python scripts/gerar_notebook.py
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "notebooks" / "01_exploracao_dos_dados.ipynb"

CELULAS: list[tuple[str, str]] = [
    ("md", """# Etapa 2 — Obtenção e exploração dos dados

**Projeto:** Inflação, juros e câmbio no Brasil — painel com dados abertos do Banco Central.

Este notebook documenta a análise exploratória inicial: de onde vêm os dados, como são
carregados com Pandas, quais são as variáveis e seus tipos, e que problemas de qualidade
(valores ausentes, duplicidades e inconsistências) foram encontrados.

Os dados brutos ficam em `data/raw/` (um CSV por série, exatamente como a API devolve) e são
atualizados com `python scripts/atualizar_dados.py`."""),
    ("code", """import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.io as pio

sys.path.insert(0, str(Path.cwd().parent))
pio.renderers.default = "notebook_connected"
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", "{:,.3f}".format)

from painel_macro.config import CATALOGO, DATA_INICIAL_PADRAO, DIRETORIO_DADOS_BRUTOS
from painel_macro.fontes import FonteDadosCSV
from painel_macro.tratamento import TratadorDados"""),
    ("md", """## 1. Fonte de dados

Os dados vêm do **Sistema Gerenciador de Séries Temporais (SGS)** do Banco Central do Brasil,
consultado pela API pública `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados`.
Cada série é identificada por um código numérico. O catálogo do projeto reúne 16 séries:"""),
    ("code", """catalogo = pd.DataFrame(
    [(s.codigo, s.nome, s.rotulo, s.unidade, s.periodicidade, s.categoria) for s in CATALOGO],
    columns=["codigo_sgs", "coluna", "descricao", "unidade", "periodicidade", "categoria"],
)
catalogo"""),
    ("md", """## 2. Carga dos dados brutos com Pandas

A classe `FonteDadosCSV` lê a cópia local das séries. Os valores chegam **como texto**, do
mesmo jeito que a API os entrega (data no formato `dd/mm/aaaa` e número com ponto decimal)."""),
    ("code", """fonte = FonteDadosCSV(DIRETORIO_DADOS_BRUTOS)
bruto = fonte.carregar_varias(CATALOGO, DATA_INICIAL_PADRAO, date.today())
print(f"{len(bruto):,} registros brutos, {bruto['serie'].nunique()} séries")
bruto.head()"""),
    ("code", """bruto.info()"""),
    ("md", """### Cobertura de cada série

Nem todas as séries começam em 2000 e nem todas são divulgadas com a mesma defasagem."""),
    ("code", """datas = pd.to_datetime(bruto["data"], format="%d/%m/%Y")
cobertura = (
    bruto.assign(data=datas)
    .groupby("serie")["data"]
    .agg(registros="count", inicio="min", fim="max")
    .sort_values("inicio")
)
cobertura"""),
    ("md", """## 3. Verificações de qualidade nos dados brutos

### 3.1 Valores ausentes e não numéricos"""),
    ("code", """valores = pd.to_numeric(bruto["valor"], errors="coerce")
print("Células vazias:", int(bruto.isna().sum().sum()))
print("Valores não numéricos:", int(valores.isna().sum()))
print("Datas inválidas:", int(datas.isna().sum()))"""),
    ("md", "### 3.2 Duplicidades"),
    ("code", """print("Linhas totalmente duplicadas:", int(bruto.duplicated().sum()))
print("Mesma série e mesma data repetidas:", int(bruto.duplicated(subset=['serie', 'data']).sum()))"""),
    ("md", """### 3.3 Inconsistências

Três verificações: datas no futuro, valores fora de faixas plausíveis e coerência entre séries
relacionadas."""),
    ("code", """hoje = pd.Timestamp.today().normalize()
print("Registros com data futura:", int((datas > hoje).sum()))

faixas = bruto.assign(valor=valores).groupby("serie")["valor"].agg(["min", "max"])
faixas"""),
    ("md", """**Coerência entre séries.** O IPCA em 12 meses (série 13522) deve ser igual à composição
das doze últimas variações mensais do IPCA (série 433). A diferença máxima encontrada é só de
arredondamento, o que confirma que as duas séries são consistentes entre si."""),
    ("code", """tratador = TratadorDados()
base = tratador.tratar(bruto)

recalculado = ((1 + base["ipca"] / 100).rolling(12).apply(lambda x: x.prod(), raw=True) - 1) * 100
diferenca = (recalculado - base["ipca_12m"]).abs()
print(f"Diferença máxima entre o IPCA 12m publicado e o recalculado: {diferenca.max():.4f} p.p.")"""),
    ("md", """## 4. Base tratada: variáveis e tipos

O `TratadorDados` converte os tipos, remove duplicidades e datas futuras, organiza tudo em uma
tabela mensal (uma linha por mês, uma coluna por série) e repete a meta anual de inflação em
todos os meses do ano."""),
    ("code", """base.info()"""),
    ("code", """tratador.relatorio.como_tabela()"""),
    ("code", """base.tail(6).T"""),
    ("md", """### Valores ausentes na base tratada

Os valores ausentes que restam têm explicação e **não são preenchidos**, porque isso
significaria inventar dados:

* `desocupacao`: a PNAD Contínua só existe a partir de março de 2012;
* `ibc_br`: a série começa em janeiro de 2003 e é divulgada com cerca de dois meses de defasagem;
* demais séries: os últimos meses ainda não foram divulgados."""),
    ("code", """ausentes = pd.DataFrame({
    "meses_sem_valor": base.isna().sum(),
    "percentual": (base.isna().mean() * 100).round(1),
    "primeiro_mes_com_valor": base.apply(lambda coluna: coluna.first_valid_index()),
    "ultimo_mes_com_valor": base.apply(lambda coluna: coluna.last_valid_index()),
})
ausentes"""),
    ("md", "## 5. Análise exploratória inicial\n\n### 5.1 Estatísticas descritivas"),
    ("code", """base.describe().T"""),
    ("md", "### 5.2 Evolução das principais variáveis"),
    ("code", """import plotly.express as px

principais = base[["ipca_12m", "selic", "meta_inflacao"]].rename(columns={
    "ipca_12m": "IPCA em 12 meses", "selic": "Taxa Selic", "meta_inflacao": "Meta de inflação",
})
figura = px.line(principais, labels={"value": "% ao ano", "data": "", "variable": ""},
                 title="Inflação, juros e meta (2000 em diante)")
figura.update_layout(height=380, hovermode="x unified")
figura.show()"""),
    ("md", "### 5.3 Distribuição da inflação mensal"),
    ("code", """figura = px.histogram(base, x="ipca", nbins=40,
                      labels={"ipca": "IPCA mensal (%)"},
                      title="Distribuição das variações mensais do IPCA")
figura.update_layout(height=340, yaxis_title="meses", bargap=0.05)
figura.show()

print(f"Assimetria: {base['ipca'].skew():.2f} | Meses com deflação: {(base['ipca'] < 0).sum()}")"""),
    ("md", "### 5.4 Correlações entre as variáveis macroeconômicas"),
    ("code", """base[["ipca_12m", "selic", "dolar", "desocupacao", "ibc_br"]].corr().round(2)"""),
    ("md", """### 5.5 Um primeiro olhar sobre os grupos do IPCA

A média mensal de fevereiro do grupo Educação é muito maior que a dos outros meses: é quando
entram os reajustes das mensalidades escolares. Esse padrão conhecido serve como mais uma
confirmação de que os códigos das séries dos grupos estão corretos."""),
    ("code", """educacao = base["educacao"].groupby(base.index.month).mean().round(2)
educacao.index.name = "mes"
educacao.to_frame("variacao_media_educacao").T"""),
    ("md", """## 6. Conclusões da exploração

* Os dados brutos chegam limpos: **sem valores não numéricos, sem duplicidades e sem datas
  futuras** nas séries usadas. Ainda assim, o `TratadorDados` trata esses casos, porque a API
  pode mudar e outras séries (como a meta diária da Selic) trazem datas futuras.
* O principal cuidado é com os **valores ausentes estruturais**: séries que começam depois de
  2000 e meses recentes ainda não divulgados. Eles são mantidos como ausentes.
* As séries são coerentes entre si (o IPCA em 12 meses bate com a composição do IPCA mensal).
* A inflação mensal é assimétrica à direita: a maior parte dos meses fica entre 0,2% e 0,7%,
  com poucos meses de alta muito forte.

As perguntas do projeto são respondidas no dashboard (`streamlit run app.py`) e na
documentação."""),
]


def main() -> None:
    notebook = nbformat.v4.new_notebook()
    notebook.metadata["kernelspec"] = {
        "display_name": "Python 3", "language": "python", "name": "python3",
    }
    for tipo, conteudo in CELULAS:
        criar = nbformat.v4.new_markdown_cell if tipo == "md" else nbformat.v4.new_code_cell
        notebook.cells.append(criar(conteudo))

    executor = ExecutePreprocessor(timeout=180, kernel_name="python3")
    executor.preprocess(notebook, {"metadata": {"path": str(DESTINO.parent)}})

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, DESTINO)
    print(f"Notebook gravado em {DESTINO}")


if __name__ == "__main__":
    main()
