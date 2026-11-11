"""Tratamento dos dados brutos com Pandas.

``TratadorDados`` recebe os dados no formato longo devolvido por uma
``FonteDados`` (colunas ``serie``, ``data`` e ``valor``, todas em texto) e
entrega uma base mensal limpa, no formato largo (uma coluna por série).

Cada etapa do tratamento é um método pequeno e testável, e tudo o que foi
corrigido fica registrado em um ``RelatorioQualidade``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from painel_macro.config import CATALOGO, SerieConfig


@dataclass
class RelatorioQualidade:
    """Resumo das verificações e correções feitas durante o tratamento."""

    registros_brutos: int = 0
    valores_invalidos: int = 0
    datas_invalidas: int = 0
    duplicados_removidos: int = 0
    datas_futuras_removidas: int = 0
    lacunas_interpoladas: int = 0
    registros_finais: int = 0
    ausentes_por_coluna: dict[str, int] = field(default_factory=dict)
    periodo: tuple[pd.Timestamp | None, pd.Timestamp | None] = (None, None)

    def como_tabela(self) -> pd.DataFrame:
        """Devolve o relatório como tabela (verificação, quantidade)."""
        linhas = [
            ("Registros brutos recebidos", self.registros_brutos),
            ("Valores não numéricos descartados", self.valores_invalidos),
            ("Datas inválidas descartadas", self.datas_invalidas),
            ("Registros duplicados removidos", self.duplicados_removidos),
            ("Registros com data futura removidos", self.datas_futuras_removidas),
            ("Lacunas internas interpoladas", self.lacunas_interpoladas),
            ("Meses na base final", self.registros_finais),
        ]
        return pd.DataFrame(linhas, columns=["verificacao", "quantidade"])


class TratadorDados:
    """Limpa e organiza os dados brutos das séries temporais."""

    def __init__(
        self,
        catalogo: tuple[SerieConfig, ...] = CATALOGO,
        data_referencia: pd.Timestamp | None = None,
        limite_interpolacao: int = 2,
    ) -> None:
        self._catalogo = {serie.nome: serie for serie in catalogo}
        self._data_referencia = data_referencia
        self._limite_interpolacao = limite_interpolacao
        self._relatorio = RelatorioQualidade()

    @property
    def relatorio(self) -> RelatorioQualidade:
        """Relatório de qualidade da última execução de :meth:`tratar`."""
        return self._relatorio

    def tratar(self, bruto: pd.DataFrame) -> pd.DataFrame:
        """Executa o tratamento completo e devolve a base mensal limpa."""
        self._relatorio = RelatorioQualidade(registros_brutos=len(bruto))
        dados = self._padronizar_tipos(bruto)
        dados = self._remover_duplicidades(dados)
        dados = self._remover_datas_futuras(dados)
        base = self._para_formato_largo(dados)
        base = self._propagar_series_anuais(base)
        base = self._interpolar_lacunas_internas(base)
        self._relatorio.registros_finais = len(base)
        self._relatorio.ausentes_por_coluna = base.isna().sum().to_dict()
        if not base.empty:
            self._relatorio.periodo = (base.index.min(), base.index.max())
        return base

    # ------------------------------------------------------------------
    # Etapas do tratamento
    # ------------------------------------------------------------------
    def _padronizar_tipos(self, bruto: pd.DataFrame) -> pd.DataFrame:
        """Converte datas e valores de texto para os tipos corretos."""
        dados = bruto.copy()
        dados["data"] = pd.to_datetime(dados["data"], format="%d/%m/%Y", errors="coerce")
        texto = dados["valor"].astype("string").str.strip().str.replace(",", ".", regex=False)
        dados["valor"] = pd.to_numeric(texto, errors="coerce")

        datas_invalidas = dados["data"].isna()
        valores_invalidos = dados["valor"].isna() & ~datas_invalidas
        self._relatorio.datas_invalidas = int(datas_invalidas.sum())
        self._relatorio.valores_invalidos = int(valores_invalidos.sum())
        return dados[~datas_invalidas & ~valores_invalidos]

    def _remover_duplicidades(self, dados: pd.DataFrame) -> pd.DataFrame:
        """Mantém um único registro por série e data (o mais recente recebido)."""
        sem_duplicados = dados.drop_duplicates(subset=["serie", "data"], keep="last")
        self._relatorio.duplicados_removidos = len(dados) - len(sem_duplicados)
        return sem_duplicados

    def _remover_datas_futuras(self, dados: pd.DataFrame) -> pd.DataFrame:
        """Descarta registros com data posterior à data de referência."""
        referencia = self._data_referencia or pd.Timestamp.today().normalize()
        no_passado = dados["data"] <= referencia
        self._relatorio.datas_futuras_removidas = int((~no_passado).sum())
        return dados[no_passado]

    def _para_formato_largo(self, dados: pd.DataFrame) -> pd.DataFrame:
        """Transforma o formato longo em uma tabela mensal com uma coluna por série."""
        dados = dados.assign(data=dados["data"].dt.to_period("M").dt.to_timestamp())
        base = dados.pivot_table(index="data", columns="serie", values="valor", aggfunc="last")
        base = base.sort_index()
        if not base.empty:
            calendario = pd.date_range(base.index.min(), base.index.max(), freq="MS", name="data")
            base = base.reindex(calendario)
        base.columns.name = None
        ordem = [nome for nome in self._catalogo if nome in base.columns]
        return base[ordem]

    def _propagar_series_anuais(self, base: pd.DataFrame) -> pd.DataFrame:
        """Repete o valor das séries anuais em todos os meses do respectivo ano."""
        base = base.copy()
        for nome, serie in self._catalogo.items():
            if serie.periodicidade == "anual" and nome in base.columns:
                base[nome] = base.groupby(base.index.year)[nome].transform("first")
        return base

    def _interpolar_lacunas_internas(self, base: pd.DataFrame) -> pd.DataFrame:
        """Preenche por interpolação linear apenas lacunas curtas no meio da série.

        Valores ausentes no início (série ainda não existia) ou no fim
        (dado ainda não divulgado) são mantidos como ausentes, pois
        preenchê-los seria inventar informação.
        """
        if base.empty:
            return base
        antes = int(base.isna().sum().sum())
        base = base.interpolate(
            method="linear", limit=self._limite_interpolacao, limit_area="inside"
        )
        self._relatorio.lacunas_interpoladas = antes - int(base.isna().sum().sum())
        return base
