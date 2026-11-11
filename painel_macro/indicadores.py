"""Indicadores calculados a partir da base analisada.

A classe abstrata ``Indicador`` define o contrato: todo indicador sabe
``calcular`` a si mesmo a partir de um ``AnalisadorDados`` e devolve um
``ResultadoIndicador``. As subclasses implementam regras de cálculo
diferentes, e o ``PainelIndicadores`` trata todas da mesma forma
(polimorfismo).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from painel_macro.analisador import SITUACAO_ACIMA, AnalisadorDados
from painel_macro.config import rotulo, unidade


def formatar_numero(valor: float, casas: int = 2) -> str:
    """Formata um número no padrão brasileiro (1.234,56)."""
    if valor is None or math.isnan(valor):
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_mes(data: pd.Timestamp | None) -> str:
    """Formata uma data como mês/ano (ex.: 09/2026)."""
    return "—" if data is None or pd.isna(data) else f"{data:%m/%Y}"


@dataclass(frozen=True)
class ResultadoIndicador:
    """Valor de um indicador, pronto para ser exibido."""

    nome: str
    valor: float
    unidade: str
    descricao: str
    referencia: str = ""
    variacao: float | None = None
    rotulo_variacao: str = ""
    detalhe: str = ""
    casas: int = 2
    prefixo: str = ""
    #: Indica se uma variação positiva é uma notícia ruim (ex.: inflação subindo).
    alta_e_ruim: bool = True

    @property
    def disponivel(self) -> bool:
        return not math.isnan(self.valor)

    @property
    def valor_formatado(self) -> str:
        if not self.disponivel:
            return "—"
        numero = formatar_numero(self.valor, self.casas)
        if self.prefixo:
            return f"{self.prefixo} {numero}"
        sufixo = self.unidade if self.unidade in ("%", "p.p.") else ""
        separador = " " if sufixo == "p.p." else ""
        return f"{numero}{separador}{sufixo}"

    @property
    def legenda(self) -> str:
        """Texto curto de apoio: o detalhe do indicador ou, na falta dele, a referência."""
        return self.detalhe or self.referencia

    @property
    def variacao_formatada(self) -> str | None:
        if self.variacao is None or math.isnan(self.variacao):
            return None
        separador = "" if self.rotulo_variacao.startswith("%") else " "
        numero = formatar_numero(self.variacao, self.casas)
        return f"{numero}{separador}{self.rotulo_variacao}".strip()


class Indicador(ABC):
    """Classe base de todos os indicadores."""

    def __init__(self, nome: str, descricao: str, unidade: str = "%") -> None:
        self._nome = nome
        self._descricao = descricao
        self._unidade = unidade

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def descricao(self) -> str:
        return self._descricao

    @property
    def unidade(self) -> str:
        return self._unidade

    @abstractmethod
    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        """Calcula o indicador para o período coberto pelo analisador."""

    def _resultado(self, valor: float, **extras) -> ResultadoIndicador:
        """Monta o resultado preenchendo os campos comuns a todo indicador."""
        return ResultadoIndicador(
            nome=self._nome, valor=valor, unidade=self._unidade,
            descricao=self._descricao, **extras,
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(nome={self._nome!r})"


class IndicadorUltimoValor(Indicador):
    """Último valor disponível de uma variável, comparado com 12 meses antes."""

    def __init__(
        self,
        coluna: str,
        nome: str | None = None,
        descricao: str | None = None,
        unidade_medida: str | None = None,
        rotulo_variacao: str = "p.p. em 12m",
        alta_e_ruim: bool = True,
        casas: int = 2,
    ) -> None:
        super().__init__(
            nome or rotulo(coluna),
            descricao or f"Último valor disponível de {rotulo(coluna)}.",
            unidade_medida or unidade(coluna),
        )
        self._coluna = coluna
        self._rotulo_variacao = rotulo_variacao
        self._alta_e_ruim = alta_e_ruim
        self._casas = casas

    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        data, valor = analisador.ultimo_valor(self._coluna)
        return self._resultado(
            valor,
            referencia=formatar_mes(data),
            variacao=self._variacao_em_12_meses(analisador, data, valor),
            rotulo_variacao=self._rotulo_variacao,
            alta_e_ruim=self._alta_e_ruim,
            casas=self._casas,
        )

    def _variacao_em_12_meses(
        self, analisador: AnalisadorDados, data: pd.Timestamp | None, valor: float
    ) -> float | None:
        if data is None:
            return None
        serie = analisador.dados[self._coluna]
        anterior = serie.get(data - pd.DateOffset(years=1))
        if anterior is None or pd.isna(anterior):
            return None
        return float(valor - anterior)


class IndicadorInflacaoAcumulada(Indicador):
    """Inflação (IPCA) acumulada em todo o período analisado."""

    def __init__(self) -> None:
        super().__init__(
            "Inflação no período",
            "Variação composta do IPCA entre o primeiro e o último mês do período.",
        )

    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        acumulado = analisador.acumulado("ipca")
        meses = int(analisador.dados["ipca"].notna().sum())
        media_anual = float("nan")
        if meses:
            media_anual = ((1 + acumulado / 100) ** (12 / meses) - 1) * 100
        return self._resultado(
            acumulado,
            referencia=_periodo_da_coluna(analisador, "ipca"),
            detalhe=f"{formatar_numero(media_anual)}% ao ano, em média",
        )


class IndicadorPoderDeCompra(Indicador):
    """Quanto valem hoje R$ 100,00 do início do período, descontada a inflação."""

    def __init__(self, valor_inicial: float = 100.0) -> None:
        super().__init__(
            "Poder de compra",
            "Valor real, ao final do período, de uma quantia guardada sem correção "
            "desde o início do período.",
            "R$",
        )
        self._valor_inicial = valor_inicial

    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        acumulado = analisador.acumulado("ipca")
        valor_real = self._valor_inicial / (1 + acumulado / 100)
        perda = (valor_real / self._valor_inicial - 1) * 100
        return self._resultado(
            valor_real,
            prefixo="R$",
            referencia=_periodo_da_coluna(analisador, "ipca"),
            variacao=perda,
            rotulo_variacao="%",
            detalhe=f"de R$ {formatar_numero(self._valor_inicial, 0)} do início do período",
            alta_e_ruim=False,
        )


class IndicadorDesvioMeta(Indicador):
    """Distância entre o IPCA em 12 meses e o centro da meta de inflação."""

    def __init__(self) -> None:
        super().__init__(
            "Desvio da meta",
            "IPCA acumulado em 12 meses menos o centro da meta de inflação.",
            "p.p.",
        )

    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        data, desvio = analisador.ultimo_valor("desvio_meta")
        detalhe = ""
        if data is not None:
            linha = analisador.dados.loc[data]
            detalhe = (
                f"meta de {formatar_numero(linha['meta_inflacao'])}% · "
                f"{str(linha['situacao_meta']).lower()}"
            )
        return self._resultado(desvio, referencia=formatar_mes(data), detalhe=detalhe)


class IndicadorMesesAcimaDoTeto(Indicador):
    """Percentual de meses em que o IPCA em 12 meses superou o teto da meta."""

    def __init__(self) -> None:
        super().__init__(
            "Meses acima do teto",
            "Parcela dos meses do período em que o IPCA em 12 meses ficou acima "
            "do limite superior do intervalo de tolerância.",
        )

    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        distribuicao = analisador.distribuicao_situacao_meta().set_index("situacao")
        total = int(distribuicao["meses"].sum())
        acima = int(distribuicao.loc[SITUACAO_ACIMA, "meses"])
        percentual = acima / total * 100 if total else float("nan")
        return self._resultado(
            percentual,
            referencia=_periodo_da_coluna(analisador, "situacao_meta"),
            detalhe=f"{acima} de {total} meses",
            casas=1,
        )


class IndicadorVariacaoNoPeriodo(Indicador):
    """Variação percentual de uma variável entre o início e o fim do período."""

    def __init__(self, coluna: str, nome: str | None = None, descricao: str | None = None) -> None:
        super().__init__(
            nome or f"Variação de {rotulo(coluna)}",
            descricao or f"Variação percentual de {rotulo(coluna)} entre o primeiro "
                         "e o último mês do período.",
        )
        self._coluna = coluna

    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        data_inicial, inicial = analisador.primeiro_valor(self._coluna)
        data_final, final = analisador.ultimo_valor(self._coluna)
        variacao = (final / inicial - 1) * 100 if inicial else float("nan")
        detalhe = ""
        if data_inicial is not None:
            detalhe = f"de {formatar_numero(inicial)} para {formatar_numero(final)}"
        return self._resultado(
            variacao,
            referencia=f"{formatar_mes(data_inicial)} a {formatar_mes(data_final)}",
            detalhe=detalhe,
        )


class IndicadorGrupoMaiorInflacao(Indicador):
    """Grupo de consumo do IPCA com a maior inflação acumulada no período."""

    def __init__(self, grupos: list[str] | None = None) -> None:
        super().__init__(
            "Grupo que mais subiu",
            "Grupo do IPCA com a maior variação acumulada de preços no período.",
        )
        self._grupos = grupos

    def calcular(self, analisador: AnalisadorDados) -> ResultadoIndicador:
        ranking = analisador.inflacao_por_grupo(self._grupos).dropna(subset=["acumulado"])
        if ranking.empty:
            return self._resultado(float("nan"))
        lider = ranking.iloc[0]
        return self._resultado(
            float(lider["acumulado"]),
            referencia=_periodo_da_coluna(analisador, lider["coluna"]),
            detalhe=str(lider["grupo"]),
        )


class PainelIndicadores:
    """Coleção de indicadores calculados em conjunto.

    O painel não sabe *como* cada indicador é calculado: ele apenas chama
    ``calcular`` em cada objeto da lista. Para incluir um novo indicador,
    cria-se uma nova subclasse de ``Indicador`` — nada aqui muda.
    """

    def __init__(self, indicadores: list[Indicador] | None = None) -> None:
        self._indicadores: list[Indicador] = list(indicadores or [])

    @classmethod
    def padrao(cls) -> "PainelIndicadores":
        """Painel com os indicadores usados no dashboard."""
        return cls([
            IndicadorUltimoValor(
                "ipca_12m", "IPCA em 12 meses",
                "Inflação oficial acumulada nos últimos 12 meses.", "%",
            ),
            IndicadorDesvioMeta(),
            IndicadorUltimoValor(
                "selic", "Taxa Selic",
                "Taxa básica de juros (Selic acumulada no mês, anualizada).", "%",
                alta_e_ruim=False,
            ),
            IndicadorUltimoValor(
                "juro_real", "Juro real (ex-post)",
                "Selic descontada a inflação dos últimos 12 meses.", "%",
                alta_e_ruim=False,
            ),
            IndicadorInflacaoAcumulada(),
            IndicadorPoderDeCompra(),
            IndicadorMesesAcimaDoTeto(),
            IndicadorVariacaoNoPeriodo(
                "dolar", "Dólar no período",
                "Variação da cotação média mensal do dólar entre o início e o fim do período.",
            ),
            IndicadorUltimoValor(
                "desocupacao", "Desocupação",
                "Percentual da força de trabalho sem ocupação (PNAD Contínua).", "%",
                casas=1,
            ),
            IndicadorGrupoMaiorInflacao(),
        ])

    @property
    def indicadores(self) -> tuple[Indicador, ...]:
        return tuple(self._indicadores)

    def adicionar(self, indicador: Indicador) -> None:
        if not isinstance(indicador, Indicador):
            raise TypeError("Só é possível adicionar objetos do tipo Indicador.")
        self._indicadores.append(indicador)

    def calcular_todos(self, analisador: AnalisadorDados) -> list[ResultadoIndicador]:
        """Calcula todos os indicadores para o período do analisador."""
        return [indicador.calcular(analisador) for indicador in self._indicadores]

    def como_tabela(self, analisador: AnalisadorDados) -> pd.DataFrame:
        """Resultados em forma de tabela, útil para relatórios e documentação."""
        resultados = self.calcular_todos(analisador)
        return pd.DataFrame({
            "indicador": [r.nome for r in resultados],
            "valor": [r.valor_formatado for r in resultados],
            "referencia": [r.referencia for r in resultados],
            "detalhe": [r.detalhe for r in resultados],
        })

    def __len__(self) -> int:
        return len(self._indicadores)


def _periodo_da_coluna(analisador: AnalisadorDados, coluna: str) -> str:
    """Texto com o primeiro e o último mês em que a coluna tem valor."""
    data_inicial, data_final = analisador.periodo_da_coluna(coluna)
    return f"{formatar_mes(data_inicial)} a {formatar_mes(data_final)}"
