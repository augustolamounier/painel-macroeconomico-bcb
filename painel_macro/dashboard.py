"""Dashboard interativo (Streamlit).

``Dashboard`` organiza os componentes do painel: cabeçalho, filtros,
indicadores (KPIs), gráficos, tabela de dados e análise interpretativa.
A classe não calcula nem desenha nada por conta própria — ela coordena os
objetos que recebe (``AnalisadorDados`` e ``PainelIndicadores``) e os que
cria a cada interação (``GaleriaGraficos`` e ``GeradorInterpretacao``).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from painel_macro.analisador import AnalisadorDados
from painel_macro.config import COLUNAS_GRUPOS, SERIES_MACRO, rotulo, unidade
from painel_macro.galeria import VARIAVEIS_DISPERSAO, GaleriaGraficos
from painel_macro.indicadores import (
    PainelIndicadores,
    ResultadoIndicador,
    formatar_mes,
    formatar_numero,
)
from painel_macro.interpretacao import GeradorInterpretacao
from painel_macro.tratamento import RelatorioQualidade

CONFIG_PLOTLY = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}

COLUNAS_TABELA_PADRAO = ["ipca", "ipca_12m", "meta_inflacao", "selic", "juro_real", "dolar"]


@dataclass(frozen=True)
class InformacoesCarga:
    """Dados sobre a origem e a qualidade da base exibida."""

    fonte: str
    carregado_em: pd.Timestamp
    relatorio: RelatorioQualidade
    series_da_copia_local: tuple[str, ...] = ()


@dataclass(frozen=True)
class Filtros:
    """Escolhas feitas pelo usuário na barra lateral."""

    ano_inicial: int
    ano_final: int
    grupos: list[str]
    variavel_dispersao: str

    @property
    def inicio(self) -> pd.Timestamp:
        return pd.Timestamp(year=self.ano_inicial, month=1, day=1)

    @property
    def fim(self) -> pd.Timestamp:
        return pd.Timestamp(year=self.ano_final, month=12, day=1)


class Dashboard:
    """Monta a página do painel a partir dos componentes de análise."""

    TITULO = "Inflação, juros e câmbio no Brasil"
    SUBTITULO = (
        "Painel de conjuntura macroeconômica com dados abertos do Banco Central do Brasil"
    )

    def __init__(
        self,
        analisador: AnalisadorDados,
        painel_indicadores: PainelIndicadores,
        informacoes: InformacoesCarga,
    ) -> None:
        self._analisador = analisador
        self._painel_indicadores = painel_indicadores
        self._informacoes = informacoes

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------
    def renderizar(self) -> None:
        """Desenha a página inteira. Chamado a cada interação do usuário."""
        self._cabecalho()
        filtros = self._filtros()
        recorte = self._analisador.filtrar_periodo(filtros.inicio, filtros.fim)
        if recorte.vazio:
            st.warning("Não há dados para o período selecionado. Ajuste os filtros.")
            return

        galeria = GaleriaGraficos(recorte)
        interpretacao = GeradorInterpretacao(recorte, filtros.grupos)

        self._indicadores(recorte)
        abas = st.tabs([
            "Inflação e meta", "Grupos de consumo", "Juros e câmbio",
            "Tabela de dados", "Análise interpretativa", "Sobre o painel",
        ])
        with abas[0]:
            self._aba_inflacao(galeria, interpretacao)
        with abas[1]:
            self._aba_grupos(galeria, interpretacao, filtros)
        with abas[2]:
            self._aba_juros_cambio(galeria, interpretacao, filtros)
        with abas[3]:
            self._aba_tabela(recorte)
        with abas[4]:
            self._aba_interpretacao(interpretacao, filtros, recorte)
        with abas[5]:
            self._aba_sobre()

    # ------------------------------------------------------------------
    # Componentes
    # ------------------------------------------------------------------
    def _cabecalho(self) -> None:
        st.title(self.TITULO)
        st.markdown(self.SUBTITULO)
        inicio, fim = self._analisador.periodo_da_coluna("ipca")
        st.caption(
            f"Fonte: {self._informacoes.fonte} · dados de {formatar_mes(inicio)} a "
            f"{formatar_mes(fim)} · atualizado em "
            f"{self._informacoes.carregado_em:%d/%m/%Y às %H:%M}"
        )
        if self._informacoes.series_da_copia_local:
            st.info(
                "A API do Banco Central não respondeu para "
                f"{len(self._informacoes.series_da_copia_local)} série(s); nesses casos o "
                "painel está usando a cópia local dos dados, que pode estar desatualizada.",
                icon=":material/cloud_off:",
            )

    def _filtros(self) -> Filtros:
        ano_minimo = int(self._analisador.periodo[0].year)
        ano_maximo = int(self._analisador.periodo[1].year)
        with st.sidebar:
            st.header("Filtros")
            ano_inicial, ano_final = st.slider(
                "Período (anos)", min_value=ano_minimo, max_value=ano_maximo,
                value=(ano_minimo, ano_maximo),
                help="Todos os indicadores, gráficos e textos são recalculados para o "
                     "período escolhido.",
            )
            grupos = st.multiselect(
                "Grupos de consumo do IPCA", options=list(COLUNAS_GRUPOS),
                default=list(COLUNAS_GRUPOS), format_func=rotulo,
                help="Grupos exibidos nos gráficos da aba “Grupos de consumo”.",
            )
            variavel = st.selectbox(
                "Variável comparada à inflação", options=list(VARIAVEIS_DISPERSAO),
                format_func=rotulo,
                help="Variável do eixo horizontal no gráfico de dispersão.",
            )
            st.divider()
            st.caption(
                "Dados: Sistema Gerenciador de Séries Temporais (SGS) do Banco Central "
                "do Brasil. As séries de preços e emprego são produzidas pelo IBGE."
            )
        if not grupos:
            st.warning("Nenhum grupo selecionado — exibindo todos os grupos.")
            grupos = list(COLUNAS_GRUPOS)
        return Filtros(ano_inicial, ano_final, grupos, variavel)

    def _indicadores(self, recorte: AnalisadorDados) -> None:
        st.subheader("Indicadores principais")
        resultados = self._painel_indicadores.calcular_todos(recorte)
        por_linha = 5
        for inicio in range(0, len(resultados), por_linha):
            colunas = st.columns(por_linha)
            for coluna, resultado in zip(colunas, resultados[inicio:inicio + por_linha]):
                with coluna:
                    self._cartao_indicador(resultado)

    @staticmethod
    def _cartao_indicador(resultado: ResultadoIndicador) -> None:
        variacao = resultado.variacao_formatada
        if variacao and not variacao.startswith("-"):
            variacao = f"+{variacao}"
        ajuda = resultado.descricao
        if resultado.referencia:
            ajuda += f" Referência: {resultado.referencia}."
        with st.container(border=True, height="stretch"):
            st.metric(
                resultado.nome, resultado.valor_formatado, variacao,
                delta_color="inverse" if resultado.alta_e_ruim else "normal",
                help=ajuda,
            )
            st.caption(resultado.legenda or " ")

    def _aba_inflacao(self, galeria: GaleriaGraficos, interpretacao: GeradorInterpretacao) -> None:
        self._grafico(galeria.inflacao_e_meta(), "inflacao_e_meta")
        self._leitura(interpretacao.inflacao_e_meta())
        self._grafico(galeria.inflacao_anual(), "inflacao_anual")
        self._leitura(interpretacao.inflacao_anual())
        esquerda, direita = st.columns([2, 3])
        with esquerda:
            self._grafico(galeria.situacao_meta(), "situacao_meta")
        with direita:
            self._grafico(galeria.sazonalidade(), "sazonalidade")
        self._leitura(interpretacao.sazonalidade())

    def _aba_grupos(
        self, galeria: GaleriaGraficos, interpretacao: GeradorInterpretacao, filtros: Filtros
    ) -> None:
        self._grafico(galeria.inflacao_por_grupo(filtros.grupos), "inflacao_por_grupo")
        self._leitura(interpretacao.grupos())
        self._grafico(galeria.distribuicao_por_grupo(filtros.grupos), "distribuicao_por_grupo")
        st.caption(
            "Cada caixa reúne a metade central das variações mensais do grupo; a linha "
            "interna é a mediana e os pontos são meses atípicos."
        )

    def _aba_juros_cambio(
        self, galeria: GaleriaGraficos, interpretacao: GeradorInterpretacao, filtros: Filtros
    ) -> None:
        self._grafico(galeria.juros_e_inflacao(), "juros_e_inflacao")
        self._leitura(interpretacao.juros())
        esquerda, direita = st.columns(2)
        with esquerda:
            self._grafico(galeria.cambio(), "cambio")
            self._leitura(interpretacao.cambio())
        with direita:
            self._grafico(galeria.dispersao(filtros.variavel_dispersao), "dispersao")
            self._leitura(interpretacao.dispersao(filtros.variavel_dispersao))

    def _aba_tabela(self, recorte: AnalisadorDados) -> None:
        dados = recorte.dados
        numericas = [coluna for coluna in dados.columns if coluna != "situacao_meta"]
        opcoes = numericas + ["situacao_meta"]
        colunas_controles = st.columns([3, 1, 1])
        with colunas_controles[0]:
            colunas = st.multiselect(
                "Variáveis", options=opcoes, format_func=rotulo,
                default=[coluna for coluna in COLUNAS_TABELA_PADRAO if coluna in opcoes],
            )
        with colunas_controles[1]:
            ordenar_por = st.selectbox(
                "Ordenar por", options=["data"] + colunas,
                format_func=lambda coluna: "Mês" if coluna == "data" else rotulo(coluna),
            )
        with colunas_controles[2]:
            ordem = st.radio("Ordem", options=["Decrescente", "Crescente"], horizontal=True)
        if not colunas:
            st.info("Selecione ao menos uma variável para montar a tabela.")
            return

        tabela = recorte.tabela(colunas, ordenar_por, crescente=ordem == "Crescente")
        st.dataframe(
            self._formatar_tabela(tabela), hide_index=True, height=420,
            column_config=self._configurar_colunas(colunas),
        )
        st.download_button(
            "Baixar tabela (CSV)",
            data=tabela.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name="painel_macro_bcb.csv", mime="text/csv",
            icon=":material/download:",
        )

        with st.expander("Estatísticas descritivas das variáveis selecionadas"):
            selecionadas = [coluna for coluna in colunas if coluna in numericas]
            if selecionadas:
                estatisticas = recorte.estatisticas_descritivas(selecionadas)
                st.dataframe(self._formatar_tabela(estatisticas), hide_index=True)
            else:
                st.caption("Selecione ao menos uma variável numérica.")
        with st.expander("Qualidade dos dados (verificações do tratamento)"):
            relatorio = self._informacoes.relatorio
            st.dataframe(relatorio.como_tabela(), hide_index=True)
            ausentes = pd.DataFrame({
                "variavel": [rotulo(coluna) for coluna in relatorio.ausentes_por_coluna],
                "meses_sem_valor": list(relatorio.ausentes_por_coluna.values()),
            })
            st.caption(
                "Meses sem valor por variável na base completa (séries que começaram depois "
                "de 2000 ou cujo dado mais recente ainda não foi divulgado):"
            )
            st.dataframe(ausentes[ausentes["meses_sem_valor"] > 0], hide_index=True)

    @staticmethod
    def _formatar_tabela(tabela: pd.DataFrame) -> pd.DataFrame:
        """Converte a tabela para texto no formato brasileiro de números e datas.

        A ordenação é feita antes, pelo ``AnalisadorDados``; aqui os valores
        já são apenas apresentação (valores ausentes aparecem como "—").
        """
        exibicao = pd.DataFrame(index=tabela.index)
        for coluna in tabela.columns:
            valores = tabela[coluna]
            if pd.api.types.is_datetime64_any_dtype(valores):
                exibicao[coluna] = valores.map(formatar_mes)
            elif coluna == "observacoes":
                exibicao[coluna] = valores.map(lambda valor: formatar_numero(valor, 0))
            elif pd.api.types.is_numeric_dtype(valores):
                exibicao[coluna] = valores.map(formatar_numero)
            else:
                exibicao[coluna] = valores.fillna("—").astype(str)
        return exibicao

    @staticmethod
    def _configurar_colunas(colunas: list[str]) -> dict:
        configuracao = {"data": st.column_config.Column("Mês")}
        for coluna in colunas:
            medida = unidade(coluna)
            titulo = f"{rotulo(coluna)} ({medida})" if medida else rotulo(coluna)
            configuracao[coluna] = st.column_config.Column(titulo)
        return configuracao

    def _aba_interpretacao(
        self, interpretacao: GeradorInterpretacao, filtros: Filtros, recorte: AnalisadorDados
    ) -> None:
        inicio, fim = recorte.periodo_da_coluna("ipca")
        st.caption(
            f"Texto gerado automaticamente a partir dos dados de {formatar_mes(inicio)} a "
            f"{formatar_mes(fim)}. Ele muda conforme os filtros da barra lateral."
        )
        for titulo, texto in interpretacao.secoes(filtros.variavel_dispersao):
            st.markdown(f"#### {titulo}")
            st.markdown(texto)
        st.markdown("#### Limitações")
        st.markdown(
            "- O painel é descritivo: mostra associações entre as variáveis, não relações "
            "de causa e efeito.\n"
            "- O juro real é calculado *ex-post* (Selic menos a inflação já ocorrida), e não "
            "com a inflação esperada pelo mercado.\n"
            "- Até 2024 o cumprimento oficial da meta era avaliado pelo IPCA do ano-calendário; "
            "a comparação mês a mês do IPCA em 12 meses é uma aproximação.\n"
            "- Os grupos do IPCA têm pesos diferentes no índice; a inflação acumulada de um "
            "grupo não indica, sozinha, quanto ele contribuiu para o índice geral."
        )

    def _aba_sobre(self) -> None:
        st.markdown(
            "Este painel foi desenvolvido como projeto final da disciplina de Programação "
            "Orientada a Objetos (Ciência de Dados e Inteligência Artificial). Ele consulta "
            "a API pública do Banco Central, trata os dados com Pandas e apresenta os "
            "resultados com Plotly e Streamlit."
        )
        st.markdown("#### Variáveis")
        variaveis = pd.DataFrame({
            "Variável": [serie.rotulo for serie in SERIES_MACRO],
            "Unidade": [serie.unidade for serie in SERIES_MACRO],
            "Código SGS": [serie.codigo for serie in SERIES_MACRO],
            "Descrição": [serie.descricao for serie in SERIES_MACRO],
        })
        st.dataframe(variaveis, hide_index=True)
        st.markdown(
            "Além dessas, o painel usa as nove séries de variação mensal dos grupos do IPCA "
            "(códigos SGS 1635 a 1643) e a meta de inflação (código 13521).\n\n"
            "#### Como ler os indicadores\n"
            "- **IPCA em 12 meses**: inflação oficial acumulada nos últimos 12 meses.\n"
            "- **Desvio em relação à meta**: IPCA em 12 meses menos o centro da meta.\n"
            "- **Juro real (ex-post)**: (1 + Selic) ÷ (1 + IPCA em 12 meses) − 1.\n"
            "- **Inflação acumulada**: composição das variações mensais do IPCA no período.\n"
            "- **Poder de compra**: quanto valem R$ 100,00 do início do período, "
            "descontada a inflação.\n"
            "- **Meses acima do teto**: parcela dos meses em que o IPCA em 12 meses superou "
            "o limite superior do intervalo de tolerância da meta."
        )

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------
    @staticmethod
    def _grafico(figura, chave: str) -> None:
        st.plotly_chart(figura, theme=None, key=f"grafico_{chave}", config=CONFIG_PLOTLY)

    @staticmethod
    def _leitura(texto: str) -> None:
        st.markdown(f"**Leitura:** {texto}")
