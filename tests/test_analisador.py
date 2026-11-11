import pandas as pd
import pytest

from painel_macro.analisador import (
    COLUNAS_DERIVADAS,
    SITUACAO_ACIMA,
    SITUACAO_DENTRO,
    AnalisadorDados,
    acumular_percentuais,
)
from painel_macro.config import COLUNAS_GRUPOS, tolerancia_do_ano


def test_acumular_percentuais_compoe_as_variacoes():
    assert acumular_percentuais(pd.Series([10.0, 10.0])) == pytest.approx(21.0)
    assert pd.isna(acumular_percentuais(pd.Series([], dtype=float)))


def test_tolerancia_historica_da_meta():
    assert tolerancia_do_ano(2000) == 2.0
    assert tolerancia_do_ano(2004) == 2.5
    assert tolerancia_do_ano(2010) == 2.0
    assert tolerancia_do_ano(2024) == 1.5


def test_exige_indice_de_datas_e_tolerancia_valida(base_sintetica):
    with pytest.raises(TypeError):
        AnalisadorDados(base_sintetica.reset_index(drop=True))
    with pytest.raises(ValueError):
        AnalisadorDados(base_sintetica, tolerancia_meta=-1)


def test_cria_variaveis_derivadas(analisador):
    dados = analisador.dados
    assert set(COLUNAS_DERIVADAS) <= set(dados.columns)
    linha = dados.loc["2023-12-01"]
    assert linha["teto_meta"] == 5.5 and linha["piso_meta"] == 2.5
    assert linha["desvio_meta"] == pytest.approx(linha["ipca_12m"] - 4.0)
    esperado = ((1 + linha["selic"] / 100) / (1 + linha["ipca_12m"] / 100) - 1) * 100
    assert linha["juro_real"] == pytest.approx(esperado)


def test_encapsulamento_dados_devolve_copia(analisador):
    copia = analisador.dados
    copia["ipca"] = 999.0
    assert (analisador.dados["ipca"] != 999.0).all()


def test_filtrar_periodo_devolve_novo_analisador(analisador):
    recorte = analisador.filtrar_periodo("2021-01-01", "2021-12-01")

    assert len(recorte) == 12
    assert len(analisador) == 60          # o original não muda
    assert recorte.periodo == (pd.Timestamp("2021-01-01"), pd.Timestamp("2021-12-01"))
    # a variação em 12 meses usa o histórico anterior ao filtro
    assert recorte.dados["dolar_var_12m"].notna().all()
    with pytest.raises(ValueError):
        analisador.filtrar_periodo("2022-01-01", "2021-01-01")


def test_filtro_sem_dados_resulta_em_analisador_vazio(analisador):
    assert analisador.filtrar_periodo("1990-01-01", "1990-12-01").vazio


def test_inflacao_por_ano_compara_com_a_meta(analisador):
    por_ano = analisador.inflacao_por_ano().set_index("ano")

    assert por_ano.loc[2019, "ipca_ano"] == pytest.approx((1.003 ** 12 - 1) * 100)
    assert por_ano.loc[2019, "situacao"] == SITUACAO_DENTRO
    assert por_ano.loc[2021, "ipca_ano"] == pytest.approx((1.01 ** 12 - 1) * 100)
    assert por_ano.loc[2021, "situacao"] == SITUACAO_ACIMA
    assert por_ano["ano_completo"].all()


def test_ano_incompleto_e_sinalizado(analisador):
    por_ano = analisador.filtrar_periodo("2023-01-01", "2023-06-01").inflacao_por_ano()
    assert not por_ano.loc[0, "ano_completo"]
    assert por_ano.loc[0, "rotulo_ano"] == "2023*"


def test_inflacao_por_grupo_vem_ordenada(analisador):
    ranking = analisador.inflacao_por_grupo()

    assert len(ranking) == len(COLUNAS_GRUPOS)
    assert ranking["acumulado"].is_monotonic_decreasing
    assert ranking.loc[0, "coluna"] == COLUNAS_GRUPOS[-1]   # maior média na base sintética
    with pytest.raises(KeyError):
        analisador.inflacao_por_grupo(["grupo_inexistente"])


def test_variacoes_por_grupo_em_formato_longo(analisador):
    longo = analisador.variacoes_por_grupo(["habitacao", "transportes"])
    assert list(longo.columns) == ["data", "grupo", "variacao"]
    assert set(longo["grupo"]) == {"Habitação", "Transportes"}
    assert len(longo) == 120


def test_distribuicao_da_situacao_frente_a_meta(analisador):
    distribuicao = analisador.distribuicao_situacao_meta()
    assert distribuicao["meses"].sum() == analisador.dados["ipca_12m"].notna().sum()
    assert distribuicao["percentual"].sum() == pytest.approx(100.0)
    assert distribuicao.set_index("situacao").loc[SITUACAO_ACIMA, "meses"] > 0


def test_classificacao_usa_duas_casas_decimais():
    valor = pd.Series([6.503, 6.51, 2.494])
    piso, teto = pd.Series([2.5] * 3), pd.Series([6.5] * 3)
    situacoes = AnalisadorDados._classificar(valor, piso, teto).tolist()
    assert situacoes == [SITUACAO_DENTRO, SITUACAO_ACIMA, "Abaixo do piso"]


def test_sazonalidade_e_media_por_mes(analisador):
    tabela = analisador.sazonalidade("ipca")
    assert tabela.shape == (5, 12)
    assert tabela.loc[2021, "jan"] == 1.0
    medias = analisador.media_por_mes_do_ano("ipca")
    assert medias["media"].tolist() == pytest.approx([0.44] * 12)


def test_estatisticas_descritivas(analisador):
    resumo = analisador.estatisticas_descritivas(["ipca", "selic"])
    assert resumo["variavel"].tolist() == ["IPCA mensal", "Taxa Selic"]
    assert resumo.loc[0, "media"] == pytest.approx(0.44)
    assert resumo.loc[1, "minimo"] == 6.0 and resumo.loc[1, "maximo"] == 12.0
    assert {"mediana", "desvio_padrao", "coef_variacao"} <= set(resumo.columns)


def test_tendencia_linear_e_correlacoes(analisador):
    tendencia = analisador.tendencia_linear("selic", "dolar")
    assert tendencia["correlacao"] == pytest.approx(1.0)
    assert tendencia["inclinacao"] == pytest.approx(1 / 6)
    matriz = analisador.correlacoes(["selic", "dolar", "desocupacao"])
    assert matriz.loc["Taxa Selic", "Taxa de desocupação"] == pytest.approx(-1.0)


def test_ordenacao_e_tabela(analisador):
    maiores = analisador.maiores_valores("selic", 3)
    assert maiores["selic"].is_monotonic_decreasing and len(maiores) == 3

    tabela = analisador.tabela(["ipca", "selic"], ordenar_por="selic", crescente=True)
    assert list(tabela.columns) == ["data", "ipca", "selic"]
    assert tabela["selic"].is_monotonic_increasing


def test_primeiro_ultimo_valor_e_acumulado(analisador):
    data, valor = analisador.ultimo_valor("dolar")
    assert data == pd.Timestamp("2023-12-01") and valor == 5.0
    data, valor = analisador.primeiro_valor("ipca_12m")
    assert data == pd.Timestamp("2019-12-01")       # precisa de 12 meses de histórico
    esperado = (1.003 ** 48 * 1.01 ** 12 - 1) * 100
    assert analisador.acumulado("ipca") == pytest.approx(esperado)
