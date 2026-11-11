"""Catálogo das séries temporais utilizadas no projeto.

Todas as séries vêm do Sistema Gerenciador de Séries Temporais (SGS) do
Banco Central do Brasil. Cada série é descrita por um objeto imutável
``SerieConfig``; para acrescentar uma nova série ao painel basta incluir
um item no catálogo, sem alterar nenhuma outra classe (princípio
aberto/fechado).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
DIRETORIO_DADOS_BRUTOS = RAIZ_PROJETO / "data" / "raw"
DIRETORIO_DADOS_TRATADOS = RAIZ_PROJETO / "data" / "processed"

DATA_INICIAL_PADRAO = date(2000, 1, 1)

#: Intervalo de tolerância da meta de inflação, em pontos percentuais para
#: cima e para baixo, conforme o ano a partir do qual passou a valer.
#: Valores transcritos do histórico de metas publicado pelo Banco Central.
TOLERANCIAS_META: tuple[tuple[int, float], ...] = (
    (1999, 2.0),
    (2003, 2.5),
    (2006, 2.0),
    (2017, 1.5),
)


def tolerancia_do_ano(ano: int) -> float:
    """Intervalo de tolerância da meta (em p.p.) vigente no ano informado."""
    vigente = TOLERANCIAS_META[0][1]
    for ano_inicial, tolerancia in TOLERANCIAS_META:
        if ano >= ano_inicial:
            vigente = tolerancia
    return vigente


@dataclass(frozen=True)
class SerieConfig:
    """Metadados de uma série temporal do SGS/BCB."""

    codigo: int
    nome: str
    rotulo: str
    unidade: str
    periodicidade: str
    categoria: str
    descricao: str

    @property
    def nome_arquivo(self) -> str:
        """Nome do arquivo CSV usado para guardar a série em disco."""
        return f"sgs_{self.codigo}_{self.nome}.csv"


CATEGORIA_MACRO = "macro"
CATEGORIA_GRUPO = "grupo_ipca"
CATEGORIA_META = "meta"

SERIES_MACRO: tuple[SerieConfig, ...] = (
    SerieConfig(
        433, "ipca", "IPCA mensal", "% a.m.", "mensal", CATEGORIA_MACRO,
        "Variação mensal do Índice Nacional de Preços ao Consumidor Amplo (IBGE).",
    ),
    SerieConfig(
        13522, "ipca_12m", "IPCA em 12 meses", "% em 12 meses", "mensal", CATEGORIA_MACRO,
        "Variação do IPCA acumulada nos últimos 12 meses.",
    ),
    SerieConfig(
        4189, "selic", "Taxa Selic", "% a.a.", "mensal", CATEGORIA_MACRO,
        "Taxa de juros Selic acumulada no mês, anualizada (base 252 dias úteis).",
    ),
    SerieConfig(
        3698, "dolar", "Dólar (venda)", "R$/US$", "mensal", CATEGORIA_MACRO,
        "Taxa de câmbio livre do dólar americano (venda), média mensal.",
    ),
    SerieConfig(
        24369, "desocupacao", "Taxa de desocupação", "%", "mensal", CATEGORIA_MACRO,
        "Taxa de desocupação da PNAD Contínua (IBGE), trimestre móvel.",
    ),
    SerieConfig(
        24363, "ibc_br", "IBC-Br", "índice", "mensal", CATEGORIA_MACRO,
        "Índice de Atividade Econômica do Banco Central (IBC-Br), sem ajuste sazonal.",
    ),
)

SERIES_GRUPOS: tuple[SerieConfig, ...] = (
    SerieConfig(
        1635, "alimentacao_bebidas", "Alimentação e bebidas", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Alimentação e bebidas.",
    ),
    SerieConfig(
        1636, "habitacao", "Habitação", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Habitação.",
    ),
    SerieConfig(
        1637, "artigos_residencia", "Artigos de residência", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Artigos de residência.",
    ),
    SerieConfig(
        1638, "vestuario", "Vestuário", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Vestuário.",
    ),
    SerieConfig(
        1639, "transportes", "Transportes", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Transportes.",
    ),
    SerieConfig(
        1640, "comunicacao", "Comunicação", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Comunicação.",
    ),
    SerieConfig(
        1641, "saude_cuidados", "Saúde e cuidados pessoais", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Saúde e cuidados pessoais.",
    ),
    SerieConfig(
        1642, "despesas_pessoais", "Despesas pessoais", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Despesas pessoais.",
    ),
    SerieConfig(
        1643, "educacao", "Educação", "% a.m.", "mensal",
        CATEGORIA_GRUPO, "IPCA – grupo Educação.",
    ),
)

SERIES_META: tuple[SerieConfig, ...] = (
    SerieConfig(
        13521, "meta_inflacao", "Meta de inflação", "% a.a.", "anual", CATEGORIA_META,
        "Centro da meta para a inflação definida pelo Conselho Monetário Nacional.",
    ),
)

CATALOGO: tuple[SerieConfig, ...] = SERIES_MACRO + SERIES_GRUPOS + SERIES_META

COLUNAS_GRUPOS: tuple[str, ...] = tuple(serie.nome for serie in SERIES_GRUPOS)

ROTULOS: dict[str, str] = {serie.nome: serie.rotulo for serie in CATALOGO} | {
    "juro_real": "Juro real (ex-post)",
    "dolar_var_12m": "Variação do dólar em 12 meses",
    "ibc_br_var_12m": "Variação do IBC-Br em 12 meses",
    "desvio_meta": "Desvio em relação à meta",
    "teto_meta": "Teto da meta",
    "piso_meta": "Piso da meta",
    "situacao_meta": "Situação frente à meta",
}

UNIDADES: dict[str, str] = {serie.nome: serie.unidade for serie in CATALOGO} | {
    "juro_real": "% a.a.",
    "dolar_var_12m": "% em 12 meses",
    "ibc_br_var_12m": "% em 12 meses",
    "desvio_meta": "p.p.",
    "teto_meta": "% a.a.",
    "piso_meta": "% a.a.",
}


def rotulo(coluna: str) -> str:
    """Devolve o rótulo legível de uma coluna (ou o próprio nome, se desconhecida)."""
    return ROTULOS.get(coluna, coluna)


def unidade(coluna: str) -> str:
    """Devolve a unidade de medida de uma coluna (texto vazio se desconhecida)."""
    return UNIDADES.get(coluna, "")
