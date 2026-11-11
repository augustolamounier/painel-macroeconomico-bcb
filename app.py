"""Ponto de entrada do dashboard.

Execute com:
    streamlit run app.py

Este arquivo é a "raiz de composição" do sistema: é o único lugar em que as
classes concretas são escolhidas e ligadas umas às outras.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from painel_macro.analisador import AnalisadorDados
from painel_macro.config import DIRETORIO_DADOS_BRUTOS
from painel_macro.dashboard import Dashboard, InformacoesCarga
from painel_macro.fontes import (
    ClienteRequests,
    FonteDados,
    FonteDadosComCache,
    FonteDadosCSV,
    FonteDadosSGS,
)
from painel_macro.indicadores import PainelIndicadores
from painel_macro.pipeline import PipelineDados

FUSO_HORARIO = "America/Sao_Paulo"

st.set_page_config(
    page_title="Inflação, juros e câmbio no Brasil",
    page_icon=":material/monitoring:",
    layout="wide",
)


def criar_fonte() -> FonteDados:
    """Escolhe a fonte de dados.

    Por padrão o painel consulta a API do Banco Central e, se ela falhar,
    usa a cópia local em ``data/raw``. Defina a variável de ambiente
    ``PAINEL_FONTE=csv`` para trabalhar somente com a cópia local.
    """
    copia_local = FonteDadosCSV(DIRETORIO_DADOS_BRUTOS)
    if os.environ.get("PAINEL_FONTE", "api").lower() == "csv":
        return copia_local
    api = FonteDadosSGS(ClienteRequests(tempo_limite=15, tentativas=2))
    return FonteDadosComCache(api, copia_local, atualizar_reserva=False)


@st.cache_data(ttl=6 * 60 * 60, show_spinner="Consultando o Banco Central do Brasil…")
def carregar_base() -> tuple[pd.DataFrame, InformacoesCarga]:
    """Carrega e trata os dados (resultado guardado em cache por seis horas)."""
    fonte = criar_fonte()
    pipeline = PipelineDados(fonte)
    base = pipeline.executar()
    informacoes = InformacoesCarga(
        fonte=fonte.nome,
        carregado_em=pd.Timestamp.now(tz=FUSO_HORARIO),
        relatorio=pipeline.relatorio,
        series_da_copia_local=getattr(fonte, "series_da_reserva", ()),
    )
    return base, informacoes


def main() -> None:
    base, informacoes = carregar_base()
    dashboard = Dashboard(
        analisador=AnalisadorDados(base),
        painel_indicadores=PainelIndicadores.padrao(),
        informacoes=informacoes,
    )
    dashboard.renderizar()


main()
