"""Orquestração da carga: fonte de dados → tratamento → base analítica."""

from __future__ import annotations

from datetime import date

import pandas as pd

from painel_macro.config import CATALOGO, DATA_INICIAL_PADRAO, SerieConfig
from painel_macro.fontes import FonteDados
from painel_macro.tratamento import RelatorioQualidade, TratadorDados


class PipelineDados:
    """Liga uma ``FonteDados`` a um ``TratadorDados``.

    A classe depende apenas das abstrações recebidas no construtor
    (inversão de dependência): trocar a API por arquivos locais, ou por uma
    fonte falsa nos testes, não exige alterar o pipeline.
    """

    def __init__(
        self,
        fonte: FonteDados,
        tratador: TratadorDados | None = None,
        catalogo: tuple[SerieConfig, ...] = CATALOGO,
    ) -> None:
        self._fonte = fonte
        self._catalogo = catalogo
        self._tratador = tratador or TratadorDados(catalogo)
        self._bruto: pd.DataFrame | None = None

    @property
    def fonte(self) -> FonteDados:
        return self._fonte

    @property
    def relatorio(self) -> RelatorioQualidade:
        """Relatório de qualidade da última execução."""
        return self._tratador.relatorio

    @property
    def dados_brutos(self) -> pd.DataFrame | None:
        """Dados brutos (formato longo) da última execução."""
        return None if self._bruto is None else self._bruto.copy()

    def executar(
        self, inicio: date = DATA_INICIAL_PADRAO, fim: date | None = None
    ) -> pd.DataFrame:
        """Carrega todas as séries do catálogo e devolve a base mensal tratada."""
        fim = fim or date.today()
        self._bruto = self._fonte.carregar_varias(self._catalogo, inicio, fim)
        return self._tratador.tratar(self._bruto)
