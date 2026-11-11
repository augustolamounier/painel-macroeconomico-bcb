"""Objetos compartilhados pelos testes (fontes falsas e bases sintéticas)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from painel_macro.analisador import AnalisadorDados
from painel_macro.config import CATALOGO, COLUNAS_GRUPOS, SerieConfig
from painel_macro.fontes import COLUNAS_BRUTAS, ErroFonteDados, FonteDados


class FonteFalsa(FonteDados):
    """Fonte em memória: devolve dados pré-definidos sem acessar a rede."""

    def __init__(self, dados: dict[str, pd.DataFrame] | None = None, falhar: bool = False):
        super().__init__("Fonte falsa")
        self._dados = dados or {}
        self._falhar = falhar
        self.chamadas: list[str] = []

    def carregar(self, serie: SerieConfig, inicio: date, fim: date) -> pd.DataFrame:
        self.chamadas.append(serie.nome)
        if self._falhar or serie.nome not in self._dados:
            raise ErroFonteDados(f"Série indisponível: {serie.nome}")
        return self._dados[serie.nome].copy()


class ClienteFalso:
    """Cliente HTTP falso que registra as requisições recebidas."""

    def __init__(self, resposta=None):
        self.resposta = resposta if resposta is not None else [
            {"data": "01/01/2024", "valor": "0.42"},
            {"data": "01/02/2024", "valor": "0.83"},
        ]
        self.requisicoes: list[tuple[str, dict]] = []

    def obter_json(self, url, parametros):
        self.requisicoes.append((url, parametros))
        return self.resposta


def bruto(datas: list[str], valores: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"data": datas, "valor": valores}, columns=COLUNAS_BRUTAS)


@pytest.fixture
def serie_ipca() -> SerieConfig:
    return next(serie for serie in CATALOGO if serie.nome == "ipca")


@pytest.fixture
def base_sintetica() -> pd.DataFrame:
    """Base mensal de 2019 a 2023 com valores simples e previsíveis."""
    indice = pd.date_range("2019-01-01", "2023-12-01", freq="MS", name="data")
    meses = len(indice)
    gerador = np.random.default_rng(42)
    base = pd.DataFrame(index=indice)
    base["ipca"] = 0.3
    # Em 2021 a inflação mensal dobra, para estourar o teto da meta.
    base.loc["2021", "ipca"] = 1.0
    fator = (1 + base["ipca"] / 100)
    base["ipca_12m"] = (fator.rolling(12).apply(np.prod, raw=True) - 1) * 100
    base["selic"] = np.linspace(6.0, 12.0, meses)
    base["dolar"] = np.linspace(4.0, 5.0, meses)
    base["desocupacao"] = np.linspace(12.0, 8.0, meses)
    base["ibc_br"] = np.linspace(100.0, 110.0, meses)
    for posicao, grupo in enumerate(COLUNAS_GRUPOS):
        base[grupo] = 0.1 * (posicao + 1) + gerador.normal(0, 0.05, meses)
    base["meta_inflacao"] = 4.0
    return base


@pytest.fixture
def analisador(base_sintetica) -> AnalisadorDados:
    return AnalisadorDados(base_sintetica, tolerancia_meta=1.5)
