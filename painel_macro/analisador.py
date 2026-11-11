"""Processamento e análise da base mensal.

``AnalisadorDados`` encapsula a base tratada e oferece as consultas usadas
pelos indicadores, pelos gráficos e pelo dashboard: filtros, agrupamentos,
ordenações e estatísticas descritivas. A classe não desenha gráficos nem
conhece o Streamlit — sua única responsabilidade é analisar dados.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from painel_macro.config import COLUNAS_GRUPOS, rotulo, tolerancia_do_ano

SITUACAO_ABAIXO = "Abaixo do piso"
SITUACAO_DENTRO = "Dentro do intervalo"
SITUACAO_ACIMA = "Acima do teto"
ORDEM_SITUACOES = [SITUACAO_ABAIXO, SITUACAO_DENTRO, SITUACAO_ACIMA]

COLUNAS_DERIVADAS = (
    "teto_meta",
    "piso_meta",
    "desvio_meta",
    "situacao_meta",
    "juro_real",
    "dolar_var_12m",
    "ibc_br_var_12m",
)

MESES_ABREVIADOS = ["jan", "fev", "mar", "abr", "mai", "jun",
                    "jul", "ago", "set", "out", "nov", "dez"]


def acumular_percentuais(variacoes: pd.Series) -> float:
    """Compõe variações percentuais mensais: Π(1 + v/100) − 1, em %."""
    validos = variacoes.dropna()
    if validos.empty:
        return float("nan")
    return float(((1 + validos / 100).prod() - 1) * 100)


class AnalisadorDados:
    """Realiza as análises sobre a base mensal de indicadores."""

    def __init__(
        self,
        base: pd.DataFrame,
        tolerancia_meta: float | None = None,
    ) -> None:
        """Cria o analisador.

        ``tolerancia_meta`` é o intervalo em torno da meta de inflação, em
        pontos percentuais. Quando omitido, usa-se o intervalo histórico
        de cada ano (ver ``config.TOLERANCIAS_META``).
        """
        if not isinstance(base.index, pd.DatetimeIndex):
            raise TypeError("A base deve ser indexada por datas (DatetimeIndex).")
        if tolerancia_meta is not None and tolerancia_meta < 0:
            raise ValueError("A tolerância da meta não pode ser negativa.")
        self._tolerancia_meta = tolerancia_meta
        ja_enriquecida = set(COLUNAS_DERIVADAS) <= set(base.columns)
        self._dados = base.copy() if ja_enriquecida else self._enriquecer(base)

    # ------------------------------------------------------------------
    # Propriedades (acesso somente leitura ao estado interno)
    # ------------------------------------------------------------------
    @property
    def dados(self) -> pd.DataFrame:
        """Cópia da base analisada — o estado interno não é exposto."""
        return self._dados.copy()

    @property
    def tolerancia_meta(self) -> float | None:
        """Tolerância fixa informada no construtor (``None`` = histórica)."""
        return self._tolerancia_meta

    @property
    def vazio(self) -> bool:
        return self._dados.empty

    @property
    def periodo(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        """Primeiro e último mês presentes na base."""
        return self._dados.index.min(), self._dados.index.max()

    @property
    def grupos_disponiveis(self) -> list[str]:
        """Colunas dos grupos do IPCA presentes na base."""
        return [coluna for coluna in COLUNAS_GRUPOS if coluna in self._dados.columns]

    def __len__(self) -> int:
        return len(self._dados)

    # ------------------------------------------------------------------
    # Seleção e filtragem
    # ------------------------------------------------------------------
    def filtrar_periodo(self, inicio, fim) -> "AnalisadorDados":
        """Devolve um novo analisador restrito ao período informado."""
        inicio, fim = pd.Timestamp(inicio), pd.Timestamp(fim)
        if inicio > fim:
            raise ValueError("A data inicial não pode ser posterior à data final.")
        recorte = self._dados.loc[(self._dados.index >= inicio) & (self._dados.index <= fim)]
        return AnalisadorDados(recorte, self._tolerancia_meta)

    def ultimo_valor(self, coluna: str) -> tuple[pd.Timestamp | None, float]:
        """Último valor disponível de uma coluna e a data a que se refere."""
        serie = self._dados[coluna].dropna()
        if serie.empty:
            return None, float("nan")
        return serie.index[-1], float(serie.iloc[-1])

    def primeiro_valor(self, coluna: str) -> tuple[pd.Timestamp | None, float]:
        """Primeiro valor disponível de uma coluna e a data a que se refere."""
        serie = self._dados[coluna].dropna()
        if serie.empty:
            return None, float("nan")
        return serie.index[0], float(serie.iloc[0])

    def periodo_da_coluna(self, coluna: str) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
        """Primeiro e último mês em que a coluna possui valor."""
        serie = self._dados[coluna].dropna()
        if serie.empty:
            return None, None
        return serie.index[0], serie.index[-1]

    def acumulado(self, coluna: str) -> float:
        """Variação percentual acumulada (composta) de uma coluna no período."""
        return acumular_percentuais(self._dados[coluna])

    # ------------------------------------------------------------------
    # Estatísticas descritivas
    # ------------------------------------------------------------------
    def estatisticas_descritivas(self, colunas: list[str]) -> pd.DataFrame:
        """Estatísticas descritivas das colunas pedidas (uma linha por variável)."""
        resumo = self._dados[colunas].describe().T
        resumo = resumo.rename(columns={
            "count": "observacoes", "mean": "media", "std": "desvio_padrao",
            "min": "minimo", "25%": "q1", "50%": "mediana", "75%": "q3", "max": "maximo",
        })
        resumo["coef_variacao"] = resumo["desvio_padrao"] / resumo["media"].abs()
        resumo.insert(0, "variavel", [rotulo(coluna) for coluna in resumo.index])
        return resumo.reset_index(drop=True)

    def correlacoes(self, colunas: list[str]) -> pd.DataFrame:
        """Matriz de correlação de Pearson entre as colunas pedidas."""
        matriz = self._dados[colunas].corr()
        nomes = [rotulo(coluna) for coluna in colunas]
        matriz.index, matriz.columns = nomes, nomes
        return matriz

    def tendencia_linear(self, x: str, y: str) -> dict[str, float]:
        """Ajusta ``y = a·x + b`` por mínimos quadrados e devolve a, b, r e n."""
        pares = self._dados[[x, y]].dropna()
        if len(pares) < 3 or pares[x].nunique() < 2:
            return {"inclinacao": float("nan"), "intercepto": float("nan"),
                    "correlacao": float("nan"), "observacoes": len(pares)}
        inclinacao, intercepto = np.polyfit(pares[x], pares[y], deg=1)
        return {
            "inclinacao": float(inclinacao),
            "intercepto": float(intercepto),
            "correlacao": float(pares[x].corr(pares[y])),
            "observacoes": len(pares),
        }

    # ------------------------------------------------------------------
    # Agrupamentos
    # ------------------------------------------------------------------
    def inflacao_por_ano(self) -> pd.DataFrame:
        """IPCA acumulado em cada ano, comparado com a meta e seu intervalo."""
        dados = self._dados.dropna(subset=["ipca"])
        por_ano = dados.groupby(dados.index.year).agg(
            ipca_ano=("ipca", acumular_percentuais),
            meta=("meta_inflacao", "first"),
            piso=("piso_meta", "first"),
            teto=("teto_meta", "first"),
            meses=("ipca", "count"),
        )
        por_ano.index.name = "ano"
        por_ano["ano_completo"] = por_ano["meses"] == 12
        por_ano["rotulo_ano"] = por_ano.index.astype(str) + np.where(
            por_ano["ano_completo"], "", "*"
        )
        por_ano["situacao"] = self._classificar(por_ano["ipca_ano"], por_ano["piso"],
                                                 por_ano["teto"])
        return por_ano.reset_index()

    def inflacao_por_grupo(self, grupos: list[str] | None = None) -> pd.DataFrame:
        """Inflação acumulada, média e volatilidade de cada grupo do IPCA.

        O resultado vem ordenado do grupo que mais encareceu para o que
        menos encareceu no período.
        """
        grupos = self._validar_grupos(grupos)
        variacoes = self._dados[grupos].dropna(how="all")
        resumo = pd.DataFrame({
            "coluna": grupos,
            "grupo": [rotulo(grupo) for grupo in grupos],
            "acumulado": [acumular_percentuais(variacoes[grupo]) for grupo in grupos],
            "media_mensal": variacoes.mean().to_numpy(),
            "volatilidade": variacoes.std().to_numpy(),
            "maior_alta": variacoes.max().to_numpy(),
            "maior_queda": variacoes.min().to_numpy(),
        })
        return resumo.sort_values("acumulado", ascending=False).reset_index(drop=True)

    def variacoes_por_grupo(self, grupos: list[str] | None = None) -> pd.DataFrame:
        """Variações mensais dos grupos no formato longo (data, grupo, variacao)."""
        grupos = self._validar_grupos(grupos)
        longo = (
            self._dados[grupos]
            .rename(columns=rotulo)
            .rename_axis(columns="grupo")
            .stack()
            .rename("variacao")
            .reset_index()
        )
        return longo.dropna(subset=["variacao"])

    def distribuicao_situacao_meta(self) -> pd.DataFrame:
        """Quantidade e percentual de meses em cada situação frente à meta."""
        situacoes = self._dados["situacao_meta"].dropna()
        contagem = situacoes.value_counts().reindex(ORDEM_SITUACOES, fill_value=0)
        total = int(contagem.sum())
        distribuicao = pd.DataFrame({
            "situacao": contagem.index,
            "meses": contagem.to_numpy(),
        })
        distribuicao["percentual"] = (
            distribuicao["meses"] / total * 100 if total else float("nan")
        )
        return distribuicao

    def sazonalidade(self, coluna: str = "ipca") -> pd.DataFrame:
        """Tabela ano × mês com os valores mensais de uma coluna."""
        serie = self._dados[coluna].dropna()
        tabela = pd.DataFrame({
            "ano": serie.index.year, "mes": serie.index.month, "valor": serie.to_numpy(),
        }).pivot(index="ano", columns="mes", values="valor")
        tabela = tabela.reindex(columns=range(1, 13))
        tabela.columns = MESES_ABREVIADOS
        return tabela

    def media_por_mes_do_ano(self, coluna: str = "ipca") -> pd.DataFrame:
        """Média histórica de uma coluna em cada mês do calendário."""
        serie = self._dados[coluna].dropna()
        medias = serie.groupby(serie.index.month).mean().reindex(range(1, 13))
        return pd.DataFrame({"mes": MESES_ABREVIADOS, "media": medias.to_numpy()})

    # ------------------------------------------------------------------
    # Ordenação
    # ------------------------------------------------------------------
    def maiores_valores(self, coluna: str, quantidade: int = 5) -> pd.DataFrame:
        """Os meses com os maiores valores de uma coluna, em ordem decrescente."""
        ordenado = self._dados[[coluna]].dropna().sort_values(coluna, ascending=False)
        return ordenado.head(quantidade).reset_index()

    def tabela(
        self,
        colunas: list[str] | None = None,
        ordenar_por: str = "data",
        crescente: bool = False,
    ) -> pd.DataFrame:
        """Tabela de dados para exibição, com as colunas e a ordenação pedidas."""
        colunas = colunas or list(self._dados.columns)
        tabela = self._dados[colunas].reset_index()
        return tabela.sort_values(ordenar_por, ascending=crescente).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------
    def _enriquecer(self, base: pd.DataFrame) -> pd.DataFrame:
        """Acrescenta as variáveis derivadas usadas nas análises."""
        dados = base.copy()
        tolerancia = self._tolerancia_por_mes(dados.index)
        dados["teto_meta"] = dados["meta_inflacao"] + tolerancia
        dados["piso_meta"] = dados["meta_inflacao"] - tolerancia
        dados["desvio_meta"] = dados["ipca_12m"] - dados["meta_inflacao"]
        dados["situacao_meta"] = self._classificar(
            dados["ipca_12m"], dados["piso_meta"], dados["teto_meta"]
        )
        dados["juro_real"] = (
            (1 + dados["selic"] / 100) / (1 + dados["ipca_12m"] / 100) - 1
        ) * 100
        dados["dolar_var_12m"] = dados["dolar"].pct_change(12, fill_method=None) * 100
        dados["ibc_br_var_12m"] = dados["ibc_br"].pct_change(12, fill_method=None) * 100
        return dados

    def _tolerancia_por_mes(self, indice: pd.DatetimeIndex) -> pd.Series:
        """Tolerância da meta aplicável a cada mês da base."""
        if self._tolerancia_meta is not None:
            return pd.Series(self._tolerancia_meta, index=indice)
        return pd.Series([tolerancia_do_ano(ano) for ano in indice.year], index=indice)

    @staticmethod
    def _classificar(valor: pd.Series, piso: pd.Series, teto: pd.Series) -> pd.Series:
        """Classifica cada observação como abaixo, dentro ou acima do intervalo."""
        # A comparação usa duas casas decimais, como na divulgação oficial:
        # 6,503% é divulgado como 6,50% e, portanto, não ultrapassa um teto de 6,50%.
        valor = valor.round(2)
        situacao = pd.Series(SITUACAO_DENTRO, index=valor.index, dtype="object")
        situacao[valor > teto] = SITUACAO_ACIMA
        situacao[valor < piso] = SITUACAO_ABAIXO
        situacao[valor.isna() | piso.isna() | teto.isna()] = None
        return situacao

    def _validar_grupos(self, grupos: list[str] | None) -> list[str]:
        disponiveis = self.grupos_disponiveis
        if grupos is None:
            return disponiveis
        desconhecidos = [grupo for grupo in grupos if grupo not in disponiveis]
        if desconhecidos:
            raise KeyError(f"Grupos inexistentes na base: {desconhecidos}")
        return list(grupos)
