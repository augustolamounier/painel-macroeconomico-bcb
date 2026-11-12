"""Galeria com os gráficos do painel.

``GaleriaGraficos`` decide *quais* gráficos existem e com que dados cada um
é alimentado. Ela conecta o ``AnalisadorDados`` (que calcula) aos
``Visualizador`` (que desenham), e é usada tanto pelo dashboard quanto pelo
script que exporta os gráficos para a documentação.
"""

from __future__ import annotations

from collections.abc import Callable

import plotly.graph_objects as go

from painel_macro.analisador import (
    SITUACAO_ABAIXO,
    SITUACAO_ACIMA,
    SITUACAO_DENTRO,
    AnalisadorDados,
)
from painel_macro.config import rotulo, unidade
from painel_macro.indicadores import formatar_mes, formatar_numero
from painel_macro.visualizadores import (
    ARDOSIA,
    CINZA,
    VINHO,
    GraficoBarras,
    GraficoBoxplot,
    GraficoDispersao,
    GraficoLinhas,
    GraficoMapaCalor,
    GraficoSetores,
    TemaGrafico,
)

CORES_SITUACAO = {
    SITUACAO_ABAIXO: ARDOSIA,
    SITUACAO_DENTRO: CINZA,
    SITUACAO_ACIMA: VINHO,
}

#: Variáveis que podem ser comparadas com a inflação no gráfico de dispersão.
VARIAVEIS_DISPERSAO = ("dolar_var_12m", "selic", "desocupacao", "ibc_br_var_12m")


class GaleriaGraficos:
    """Monta as figuras do painel a partir de um ``AnalisadorDados``."""

    def __init__(self, analisador: AnalisadorDados, tema: TemaGrafico | None = None) -> None:
        self._analisador = analisador
        self._tema = tema or TemaGrafico()
        self._periodo = self._descrever_periodo()

    @property
    def nomes(self) -> tuple[str, ...]:
        """Identificadores dos gráficos disponíveis."""
        return tuple(self._construtores())

    def gerar(self, nome: str) -> go.Figure:
        """Gera um gráfico pelo identificador."""
        construtores = self._construtores()
        if nome not in construtores:
            raise KeyError(f"Gráfico desconhecido: {nome!r}")
        return construtores[nome]()

    def gerar_todos(self) -> dict[str, go.Figure]:
        return {nome: construtor() for nome, construtor in self._construtores().items()}

    # ------------------------------------------------------------------
    # Gráficos
    # ------------------------------------------------------------------
    def inflacao_e_meta(self) -> go.Figure:
        """Linhas: IPCA em 12 meses contra a meta e seu intervalo de tolerância."""
        grafico = GraficoLinhas(
            "Inflação em 12 meses e a meta",
            series={"ipca_12m": "IPCA em 12 meses"},
            subtitulo=f"IPCA acumulado em 12 meses, meta e intervalo de tolerância · "
                      f"{self._periodo}",
            faixa=("piso_meta", "teto_meta", "Intervalo de tolerância"),
            linha_referencia=("meta_inflacao", "Centro da meta"),
            tema=self._tema,
        )
        return grafico.gerar(self._analisador.dados.dropna(subset=["ipca_12m"], how="all"))

    def juros_e_inflacao(self) -> go.Figure:
        """Linhas: Selic, IPCA em 12 meses e juro real."""
        grafico = GraficoLinhas(
            "Juros, inflação e juro real",
            series={
                "selic": "Taxa Selic (% a.a.)",
                "ipca_12m": "IPCA em 12 meses",
                "juro_real": "Juro real (ex-post)",
            },
            subtitulo=f"Juro real = Selic descontada a inflação de 12 meses · {self._periodo}",
            tema=self._tema,
        )
        return grafico.gerar(self._analisador.dados)

    def cambio(self) -> go.Figure:
        """Linhas: cotação média mensal do dólar."""
        grafico = GraficoLinhas(
            "Taxa de câmbio",
            series={"dolar": "Dólar (venda)"},
            subtitulo=f"Cotação média mensal do dólar, em reais · {self._periodo}",
            sufixo="", titulo_eixo_y="R$ por US$",
            tema=self._tema,
        )
        return grafico.gerar(self._analisador.dados.dropna(subset=["dolar"]))

    def inflacao_anual(self) -> go.Figure:
        """Barras: IPCA de cada ano, colorido conforme a situação frente à meta."""
        por_ano = self._analisador.inflacao_por_ano()
        tem_parcial = not por_ano.empty and not por_ano["ano_completo"].all()
        subtitulo = "IPCA acumulado em cada ano e centro da meta"
        if tem_parcial:
            subtitulo += " · * ano com dados parciais"
        grafico = GraficoBarras(
            "Inflação anual frente à meta",
            categoria="rotulo_ano", valor="ipca_ano", subtitulo=subtitulo,
            coluna_cor="situacao", mapa_cores=CORES_SITUACAO,
            marcador=("meta", "Centro da meta"),
            mostrar_valores=len(por_ano) <= 15,
            tema=self._tema,
        )
        return grafico.gerar(por_ano)

    def inflacao_por_grupo(self, grupos: list[str] | None = None) -> go.Figure:
        """Barras: inflação acumulada por grupo de consumo, em ordem decrescente."""
        ranking = self._analisador.inflacao_por_grupo(grupos).dropna(subset=["acumulado"])
        geral = self._analisador.acumulado("ipca")
        grafico = GraficoBarras(
            "Inflação acumulada por grupo de consumo",
            categoria="grupo", valor="acumulado", horizontal=True,
            subtitulo=f"Variação acumulada dos preços de cada grupo do IPCA · {self._periodo}",
            nome_serie="Inflação acumulada",
            referencia=(geral, f"IPCA geral: {formatar_numero(geral, 1)}%"),
            tema=self._tema,
        )
        return grafico.gerar(ranking)

    def situacao_meta(self) -> go.Figure:
        """Setores: parcela dos meses abaixo, dentro e acima do intervalo da meta."""
        grafico = GraficoSetores(
            "Meses dentro e fora da meta",
            rotulos="situacao", valores="meses",
            subtitulo=f"IPCA em 12 meses frente ao intervalo · {self._periodo}",
            mapa_cores=CORES_SITUACAO,
            tema=self._tema,
        )
        return grafico.gerar(self._analisador.distribuicao_situacao_meta())

    def dispersao(self, variavel: str = "dolar_var_12m") -> go.Figure:
        """Dispersão: uma variável macroeconômica contra o IPCA em 12 meses."""
        nome, medida = rotulo(variavel), unidade(variavel)
        grafico = GraficoDispersao(
            f"{nome} × inflação",
            x=variavel, y="ipca_12m",
            rotulo_x=nome, rotulo_y="IPCA em 12 meses",
            sufixo_x="%" if medida.startswith("%") else "",
            subtitulo=f"Cada ponto é um mês · {self._periodo}",
            tema=self._tema,
        )
        return grafico.gerar(self._analisador.dados)

    def distribuicao_por_grupo(self, grupos: list[str] | None = None) -> go.Figure:
        """Boxplot: distribuição das variações mensais de cada grupo."""
        grafico = GraficoBoxplot(
            "Distribuição das variações mensais por grupo",
            categoria="grupo", valor="variacao",
            subtitulo=f"Mediana, quartis e meses atípicos de cada grupo · {self._periodo}",
            tema=self._tema,
        )
        return grafico.gerar(self._analisador.variacoes_por_grupo(grupos))

    def sazonalidade(self) -> go.Figure:
        """Mapa de calor: IPCA mensal por ano e mês."""
        grafico = GraficoMapaCalor(
            "Sazonalidade da inflação",
            subtitulo="IPCA de cada mês, por ano · azul = queda de preços, vinho = alta",
            rotulo_valor="IPCA",
            tema=self._tema,
        )
        return grafico.gerar(self._analisador.sazonalidade("ipca"))

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------
    def _construtores(self) -> dict[str, Callable[[], go.Figure]]:
        return {
            "inflacao_e_meta": self.inflacao_e_meta,
            "inflacao_anual": self.inflacao_anual,
            "situacao_meta": self.situacao_meta,
            "inflacao_por_grupo": self.inflacao_por_grupo,
            "distribuicao_por_grupo": self.distribuicao_por_grupo,
            "sazonalidade": self.sazonalidade,
            "juros_e_inflacao": self.juros_e_inflacao,
            "cambio": self.cambio,
            "dispersao": self.dispersao,
        }

    def _descrever_periodo(self) -> str:
        if self._analisador.vazio:
            return "sem dados"
        inicio, fim = self._analisador.periodo_da_coluna("ipca")
        if inicio is None:
            inicio, fim = self._analisador.periodo
        return f"{formatar_mes(inicio)} a {formatar_mes(fim)}"
