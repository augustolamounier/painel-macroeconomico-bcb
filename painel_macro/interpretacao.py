"""Análise interpretativa gerada a partir dos dados.

``GeradorInterpretacao`` transforma os resultados numéricos do
``AnalisadorDados`` em frases em português. Como o texto é montado a partir
dos números do período filtrado, ele acompanha os filtros do dashboard e
nunca fica desatualizado em relação aos gráficos.
"""

from __future__ import annotations

import math

from painel_macro.analisador import SITUACAO_ABAIXO, SITUACAO_ACIMA, AnalisadorDados
from painel_macro.config import rotulo
from painel_macro.indicadores import formatar_mes
from painel_macro.indicadores import formatar_numero as num

SEM_DADOS = "Não há dados suficientes no período selecionado para esta análise."

NOMES_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
               "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _listar(itens: list[str]) -> str:
    """Junta itens em uma enumeração: 'a, b e c'."""
    itens = [str(item) for item in itens]
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def _intensidade(correlacao: float) -> str:
    """Descreve em palavras a força de uma correlação."""
    forca = abs(correlacao)
    if forca < 0.3:
        return "fraca"
    if forca < 0.6:
        return "moderada"
    return "forte"


class GeradorInterpretacao:
    """Escreve a leitura dos indicadores e gráficos do período analisado."""

    def __init__(self, analisador: AnalisadorDados, grupos: list[str] | None = None) -> None:
        self._analisador = analisador
        self._grupos = grupos
        self._dados = analisador.dados

    # ------------------------------------------------------------------
    # Leituras por tema
    # ------------------------------------------------------------------
    def inflacao_e_meta(self) -> str:
        data, ipca_12m = self._analisador.ultimo_valor("ipca_12m")
        if data is None:
            return SEM_DADOS
        linha = self._dados.loc[data]
        desvio = linha["desvio_meta"]
        texto = (
            f"Em {formatar_mes(data)}, o IPCA acumulado em 12 meses estava em "
            f"**{num(ipca_12m)}%**"
        )
        if not math.isnan(desvio):
            posicao = "acima" if desvio >= 0 else "abaixo"
            texto += (
                f", {num(abs(desvio))} p.p. {posicao} do centro da meta "
                f"({num(linha['meta_inflacao'])}%) e "
                f"**{str(linha['situacao_meta']).lower()}** de tolerância, que vai de "
                f"{num(linha['piso_meta'])}% a {num(linha['teto_meta'])}%"
            )
        texto += ". "

        distribuicao = self._analisador.distribuicao_situacao_meta().set_index("situacao")
        total = int(distribuicao["meses"].sum())
        if total:
            acima = distribuicao.loc[SITUACAO_ACIMA]
            abaixo = distribuicao.loc[SITUACAO_ABAIXO]
            texto += (
                f"No período, a inflação em 12 meses ficou acima do teto em "
                f"**{int(acima['meses'])} de {total} meses** ({num(acima['percentual'], 1)}%) "
                f"e abaixo do piso em {int(abaixo['meses'])} ({num(abaixo['percentual'], 1)}%). "
            )
        pico = self._analisador.maiores_valores("ipca_12m", 1)
        if not pico.empty:
            texto += (
                f"O pico foi de {num(pico.loc[0, 'ipca_12m'])}% em "
                f"{formatar_mes(pico.loc[0, 'data'])}."
            )
        return texto

    def inflacao_anual(self) -> str:
        por_ano = self._analisador.inflacao_por_ano()
        completos = por_ano[por_ano["ano_completo"]].dropna(subset=["situacao"])
        if completos.empty:
            return "O período selecionado não contém nenhum ano completo para comparar com a meta."
        acima = completos[completos["situacao"] == SITUACAO_ACIMA]
        abaixo = completos[completos["situacao"] == SITUACAO_ABAIXO]
        maior = completos.loc[completos["ipca_ano"].idxmax()]
        menor = completos.loc[completos["ipca_ano"].idxmin()]
        texto = (
            f"Dos {len(completos)} anos completos do período, **{len(acima)} terminaram com "
            f"inflação acima do teto da meta**"
        )
        if len(acima):
            texto += f" ({_listar(acima['ano'].tolist())})"
        texto += f" e {len(abaixo)} abaixo do piso"
        if len(abaixo):
            texto += f" ({_listar(abaixo['ano'].tolist())})"
        texto += (
            f". A maior inflação anual foi a de {int(maior['ano'])} ({num(maior['ipca_ano'])}%) "
            f"e a menor, a de {int(menor['ano'])} ({num(menor['ipca_ano'])}%)."
        )
        return texto

    def grupos(self) -> str:
        ranking = self._analisador.inflacao_por_grupo(self._grupos).dropna(subset=["acumulado"])
        if ranking.empty:
            return SEM_DADOS
        geral = self._analisador.acumulado("ipca")
        primeiro, ultimo = ranking.iloc[0], ranking.iloc[-1]
        acima_do_geral = ranking[ranking["acumulado"] > geral]["grupo"].tolist()
        mais_volatil = ranking.loc[ranking["volatilidade"].idxmax()]
        texto = (
            f"**{primeiro['grupo']}** foi o grupo que mais encareceu no período "
            f"({num(primeiro['acumulado'], 1)}%)"
        )
        if len(ranking) > 1:
            texto += (
                f", enquanto **{ultimo['grupo']}** teve a menor alta "
                f"({num(ultimo['acumulado'], 1)}%)"
            )
        texto += f". O IPCA geral acumulou {num(geral, 1)}% no mesmo período"
        if acima_do_geral:
            texto += (
                f"; ficaram acima dele: {_listar(acima_do_geral)}"
            )
        texto += (
            f". O grupo com preços mais instáveis foi **{mais_volatil['grupo']}** "
            f"(desvio-padrão de {num(mais_volatil['volatilidade'])} p.p. nas variações mensais)."
        )
        return texto

    def juros(self) -> str:
        data_selic, selic = self._analisador.ultimo_valor("selic")
        data_real, juro_real = self._analisador.ultimo_valor("juro_real")
        if data_selic is None or data_real is None:
            return SEM_DADOS
        serie = self._dados["juro_real"].dropna()
        negativos = int((serie < 0).sum())
        texto = (
            f"A Selic estava em **{num(selic)}% ao ano** em {formatar_mes(data_selic)}. "
            f"Descontada a inflação de 12 meses, o juro real era de **{num(juro_real)}%** "
            f"em {formatar_mes(data_real)}, contra uma média de {num(serie.mean())}% no período. "
        )
        if negativos:
            texto += (
                f"Em {negativos} dos {len(serie)} meses o juro real foi negativo, isto é, "
                f"a taxa básica rendeu menos do que a inflação. "
            )
        else:
            texto += "Em nenhum mês do período o juro real foi negativo. "
        tendencia = self._analisador.tendencia_linear("ipca_12m", "selic")
        if not math.isnan(tendencia["correlacao"]):
            texto += (
                f"A correlação entre a Selic e o IPCA em 12 meses é "
                f"{_intensidade(tendencia['correlacao'])} (r = {num(tendencia['correlacao'])})."
            )
        return texto

    def cambio(self) -> str:
        data_inicial, inicial = self._analisador.primeiro_valor("dolar")
        data_final, final = self._analisador.ultimo_valor("dolar")
        if data_inicial is None:
            return SEM_DADOS
        variacao = (final / inicial - 1) * 100
        verbo = "subiu" if variacao >= 0 else "caiu"
        maximo = self._analisador.maiores_valores("dolar", 1)
        return (
            f"O dólar {verbo} **{num(abs(variacao), 1)}%** no período: de R$ {num(inicial)} em "
            f"{formatar_mes(data_inicial)} para R$ {num(final)} em {formatar_mes(data_final)}. "
            f"A maior cotação média mensal foi de R$ {num(maximo.loc[0, 'dolar'])}, em "
            f"{formatar_mes(maximo.loc[0, 'data'])}."
        )

    def dispersao(self, variavel: str = "dolar_var_12m") -> str:
        tendencia = self._analisador.tendencia_linear(variavel, "ipca_12m")
        correlacao = tendencia["correlacao"]
        if math.isnan(correlacao):
            return SEM_DADOS
        sentido = "positiva" if correlacao >= 0 else "negativa"
        return (
            f"A relação entre **{rotulo(variavel).lower()}** e o IPCA em 12 meses é "
            f"**{sentido} e {_intensidade(correlacao)}** (r = {num(correlacao)}, "
            f"{tendencia['observacoes']} meses). Pela reta de tendência, cada unidade a mais "
            f"na variável está associada a {num(tendencia['inclinacao'], 3)} ponto percentual "
            f"de inflação. Correlação não significa causalidade: outros fatores, como "
            f"choques de oferta e a própria política de juros, atuam ao mesmo tempo."
        )

    def sazonalidade(self) -> str:
        medias = self._analisador.media_por_mes_do_ano("ipca").dropna(subset=["media"])
        if len(medias) < 12 or len(self._dados["ipca"].dropna()) < 24:
            return "Selecione pelo menos dois anos completos para avaliar o padrão sazonal."
        maior = medias["media"].idxmax()
        menor = medias["media"].idxmin()
        texto = (
            f"Em média, **{NOMES_MESES[maior]}** é o mês de inflação mais alta no período "
            f"({num(medias.loc[maior, 'media'])}%) e **{NOMES_MESES[menor]}**, o de inflação "
            f"mais baixa ({num(medias.loc[menor, 'media'])}%)."
        )
        virada_do_ano, meio_do_ano = (10, 11, 0, 1, 2), (4, 5, 6, 7)
        if maior in virada_do_ano and menor in meio_do_ano:
            texto += (
                " Isso sugere um padrão sazonal: os preços tendem a subir mais na virada "
                "do ano e menos no meio do ano."
            )
        return texto

    def poder_de_compra(self) -> str:
        acumulado = self._analisador.acumulado("ipca")
        inicio, fim = self._analisador.periodo_da_coluna("ipca")
        if inicio is None or math.isnan(acumulado):
            return SEM_DADOS
        valor_real = 100 / (1 + acumulado / 100)
        necessario = 100 * (1 + acumulado / 100)
        return (
            f"Entre {formatar_mes(inicio)} e {formatar_mes(fim)}, os preços subiram "
            f"**{num(acumulado, 1)}%**. Quem guardou R$ 100,00 sem nenhuma correção ficou com o "
            f"equivalente a **R$ {num(valor_real)}** em poder de compra; para comprar o que "
            f"R$ 100,00 compravam no início, seriam necessários R$ {num(necessario)}."
        )

    def mercado_de_trabalho(self) -> str:
        data, taxa = self._analisador.ultimo_valor("desocupacao")
        if data is None:
            return (
                "A taxa de desocupação da PNAD Contínua só existe a partir de março de 2012; "
                "não há observações no período selecionado."
            )
        serie = self._dados["desocupacao"].dropna()
        pico_data = serie.idxmax()
        return (
            f"A taxa de desocupação era de **{num(taxa, 1)}%** em {formatar_mes(data)}. "
            f"No período, variou entre {num(serie.min(), 1)}% "
            f"({formatar_mes(serie.idxmin())}) e {num(serie.max(), 1)}% "
            f"({formatar_mes(pico_data)})."
        )

    # ------------------------------------------------------------------
    # Síntese
    # ------------------------------------------------------------------
    def secoes(self, variavel_dispersao: str = "dolar_var_12m") -> list[tuple[str, str]]:
        """Análise completa, como lista de (título, texto)."""
        if self._analisador.vazio:
            return [("Sem dados", SEM_DADOS)]
        return [
            ("A inflação cumpre a meta?", self.inflacao_e_meta() + " " + self.inflacao_anual()),
            ("O que mais pesou no bolso?", self.grupos()),
            ("Como os juros reagiram?", self.juros()),
            ("Câmbio e inflação", self.cambio() + " " + self.dispersao(variavel_dispersao)),
            ("Sazonalidade", self.sazonalidade()),
            ("Poder de compra", self.poder_de_compra()),
            ("Mercado de trabalho", self.mercado_de_trabalho()),
        ]

    def como_markdown(self, variavel_dispersao: str = "dolar_var_12m") -> str:
        """Análise completa em Markdown."""
        return "\n\n".join(
            f"**{titulo}** — {texto}" for titulo, texto in self.secoes(variavel_dispersao)
        )

