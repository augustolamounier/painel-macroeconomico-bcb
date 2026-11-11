import math

import pytest

from painel_macro.indicadores import (
    Indicador,
    IndicadorDesvioMeta,
    IndicadorGrupoMaiorInflacao,
    IndicadorInflacaoAcumulada,
    IndicadorMesesAcimaDoTeto,
    IndicadorPoderDeCompra,
    IndicadorUltimoValor,
    IndicadorVariacaoNoPeriodo,
    PainelIndicadores,
    ResultadoIndicador,
    formatar_mes,
    formatar_numero,
)


def test_formatacao_brasileira():
    assert formatar_numero(1234.567) == "1.234,57"
    assert formatar_numero(-0.5, 1) == "-0,5"
    assert formatar_numero(float("nan")) == "—"
    assert formatar_mes(None) == "—"


def test_indicador_e_abstrato():
    with pytest.raises(TypeError):
        Indicador("x", "y")  # type: ignore[abstract]


def test_ultimo_valor_com_variacao_em_12_meses(analisador):
    resultado = IndicadorUltimoValor("selic", "Taxa Selic", unidade_medida="%").calcular(analisador)

    assert resultado.valor == 12.0
    assert resultado.referencia == "12/2023"
    assert resultado.variacao == pytest.approx(12.0 - analisador.dados.loc["2022-12-01", "selic"])
    assert resultado.valor_formatado == "12,00%"
    assert resultado.variacao_formatada.endswith("p.p. em 12m")


def test_inflacao_acumulada_e_poder_de_compra(analisador):
    esperado = (1.003 ** 48 * 1.01 ** 12 - 1) * 100
    inflacao = IndicadorInflacaoAcumulada().calcular(analisador)
    poder = IndicadorPoderDeCompra().calcular(analisador)

    assert inflacao.valor == pytest.approx(esperado)
    assert inflacao.referencia == "01/2019 a 12/2023"
    assert poder.valor == pytest.approx(100 / (1 + esperado / 100))
    assert poder.valor_formatado.startswith("R$ ")
    assert poder.variacao < 0


def test_desvio_da_meta(analisador):
    resultado = IndicadorDesvioMeta().calcular(analisador)
    ultimo = analisador.dados.loc["2023-12-01"]

    assert resultado.valor == pytest.approx(ultimo["ipca_12m"] - 4.0)
    assert resultado.unidade == "p.p."
    assert "meta de 4,00%" in resultado.detalhe


def test_meses_acima_do_teto(analisador):
    resultado = IndicadorMesesAcimaDoTeto().calcular(analisador)
    dados = analisador.dados
    acima = (dados["ipca_12m"].round(2) > dados["teto_meta"]).sum()
    total = dados["ipca_12m"].notna().sum()

    assert resultado.valor == pytest.approx(acima / total * 100)
    assert resultado.detalhe == f"{acima} de {total} meses"


def test_variacao_no_periodo(analisador):
    resultado = IndicadorVariacaoNoPeriodo("dolar").calcular(analisador)
    assert resultado.valor == pytest.approx(25.0)
    assert resultado.detalhe == "de 4,00 para 5,00"


def test_grupo_com_maior_inflacao(analisador):
    resultado = IndicadorGrupoMaiorInflacao().calcular(analisador)
    assert resultado.detalhe == "Educação"
    restrito = IndicadorGrupoMaiorInflacao(["habitacao", "vestuario"]).calcular(analisador)
    assert restrito.detalhe == "Vestuário"


def test_indicadores_sem_dados_nao_quebram(analisador):
    vazio = analisador.filtrar_periodo("2019-01-01", "2019-06-01")  # sem IPCA em 12 meses
    resultado = IndicadorUltimoValor("ipca_12m").calcular(vazio)

    assert not resultado.disponivel
    assert resultado.valor_formatado == "—"
    assert resultado.variacao_formatada is None


def test_painel_trata_todos_os_indicadores_da_mesma_forma(analisador):
    """Polimorfismo: o painel só conhece a interface Indicador."""
    painel = PainelIndicadores.padrao()
    resultados = painel.calcular_todos(analisador)

    assert len(painel) >= 5
    assert len(resultados) == len(painel)
    assert all(isinstance(resultado, ResultadoIndicador) for resultado in resultados)
    assert all(not math.isnan(resultado.valor) for resultado in resultados)
    assert len({resultado.nome for resultado in resultados}) == len(resultados)


def test_painel_aceita_novos_indicadores_sem_modificacao(analisador):
    """Aberto/fechado: um indicador novo entra sem alterar o painel."""

    class IndicadorSelicMaxima(Indicador):
        def __init__(self):
            super().__init__("Selic máxima", "Maior Selic do período.")

        def calcular(self, analisador):
            return self._resultado(float(analisador.dados["selic"].max()))

    painel = PainelIndicadores()
    painel.adicionar(IndicadorSelicMaxima())

    assert painel.calcular_todos(analisador)[0].valor == 12.0
    with pytest.raises(TypeError):
        painel.adicionar("não é indicador")  # type: ignore[arg-type]


def test_painel_como_tabela(analisador):
    tabela = PainelIndicadores.padrao().como_tabela(analisador)
    assert list(tabela.columns) == ["indicador", "valor", "referencia", "detalhe"]
    assert len(tabela) == len(PainelIndicadores.padrao())
