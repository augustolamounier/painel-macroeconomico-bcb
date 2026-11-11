import pandas as pd
import plotly.graph_objects as go
import pytest

from painel_macro.galeria import GaleriaGraficos
from painel_macro.visualizadores import (
    GraficoBarras,
    GraficoBoxplot,
    GraficoDispersao,
    GraficoLinhas,
    GraficoMapaCalor,
    GraficoSetores,
    Visualizador,
)


def tipos(figura: go.Figure) -> set[str]:
    return {traco.type for traco in figura.data}


def test_visualizador_e_abstrato():
    with pytest.raises(TypeError):
        Visualizador("título")  # type: ignore[abstract]


def test_grafico_de_linhas(analisador):
    grafico = GraficoLinhas(
        "Inflação", {"ipca_12m": "IPCA em 12 meses"},
        faixa=("piso_meta", "teto_meta", "Intervalo"),
        linha_referencia=("meta_inflacao", "Meta"),
    )
    figura = grafico.gerar(analisador.dados)

    assert tipos(figura) == {"scatter"}
    assert "IPCA em 12 meses" in [traco.name for traco in figura.data]
    assert figura.layout.title.text == "Inflação"
    assert grafico.tipo == "GraficoLinhas"


def test_grafico_de_linhas_valida_as_series():
    with pytest.raises(ValueError):
        GraficoLinhas("x", {})
    with pytest.raises(ValueError):
        GraficoLinhas("x", {str(numero): str(numero) for numero in range(5)})


def test_grafico_de_barras_com_cores_por_categoria():
    dados = pd.DataFrame({
        "ano": ["2020", "2021"], "valor": [4.5, 10.1],
        "situacao": ["Dentro", "Acima"], "meta": [4.0, 3.75],
    })
    figura = GraficoBarras(
        "Barras", "ano", "valor", coluna_cor="situacao",
        mapa_cores={"Dentro": "#888888", "Acima": "#cc0000"}, marcador=("meta", "Meta"),
    ).gerar(dados)

    barras = [traco for traco in figura.data if traco.type == "bar"]
    assert [barra.name for barra in barras] == ["Dentro", "Acima"]
    assert barras[1].marker.color == "#cc0000"
    assert "scatter" in tipos(figura)       # a meta é desenhada sobre as barras


def test_grafico_de_barras_horizontal_com_referencia():
    dados = pd.DataFrame({"grupo": ["A", "B"], "acumulado": [50.0, 20.0]})
    figura = GraficoBarras("Barras", "grupo", "acumulado", horizontal=True,
                           referencia=(30.0, "Geral")).gerar(dados)

    assert figura.data[0].orientation == "h"
    assert list(figura.data[0].x) == [50.0, 20.0]
    assert len(figura.layout.shapes) == 1


def test_grafico_de_setores_ignora_fatias_vazias():
    dados = pd.DataFrame({"situacao": ["A", "B", "C"], "meses": [10, 0, 30]})
    figura = GraficoSetores("Setores", "situacao", "meses").gerar(dados)

    assert tipos(figura) == {"pie"}
    assert list(figura.data[0].labels) == ["A", "C"]


def test_grafico_de_dispersao_com_tendencia(analisador):
    figura = GraficoDispersao("Dispersão", "selic", "dolar", "Selic", "Dólar").gerar(
        analisador.dados
    )
    assert len(figura.data) == 2
    assert figura.data[0].mode == "markers"
    assert "Tendência linear" in figura.data[1].name


def test_boxplot_e_mapa_de_calor(analisador):
    caixa = GraficoBoxplot("Box", "grupo", "variacao").gerar(analisador.variacoes_por_grupo())
    calor = GraficoMapaCalor("Calor").gerar(analisador.sazonalidade())

    assert tipos(caixa) == {"box"}
    assert tipos(calor) == {"heatmap"}
    assert calor.data[0].zmid == 0


@pytest.mark.parametrize("grafico", [
    GraficoLinhas("Linhas", {"a": "A"}),
    GraficoBarras("Barras", "a", "b"),
    GraficoSetores("Setores", "a", "b"),
    GraficoDispersao("Dispersão", "a", "b", "A", "B"),
    GraficoBoxplot("Box", "a", "b"),
    GraficoMapaCalor("Calor"),
])
def test_todo_visualizador_lida_com_dados_vazios(grafico):
    """Polimorfismo + Liskov: qualquer subclasse responde a gerar() da mesma forma."""
    figura = grafico.gerar(pd.DataFrame(columns=["a", "b"]))

    assert isinstance(figura, go.Figure)
    assert len(figura.data) == 0
    assert "Não há dados" in figura.layout.annotations[0].text


def test_galeria_gera_os_tipos_de_grafico_exigidos(analisador):
    figuras = GaleriaGraficos(analisador).gerar_todos()

    assert set(figuras) == set(GaleriaGraficos(analisador).nomes)
    encontrados = set().union(*(tipos(figura) for figura in figuras.values()))
    assert {"bar", "scatter", "pie", "box", "heatmap"} <= encontrados
    with pytest.raises(KeyError):
        GaleriaGraficos(analisador).gerar("inexistente")


def test_galeria_respeita_os_grupos_selecionados(analisador):
    figura = GaleriaGraficos(analisador).inflacao_por_grupo(["habitacao", "educacao"])
    assert sorted(figura.data[0].y) == ["Educação", "Habitação"]


def test_galeria_com_periodo_sem_dados(analisador):
    vazio = analisador.filtrar_periodo("1990-01-01", "1990-12-01")
    for figura in GaleriaGraficos(vazio).gerar_todos().values():
        assert isinstance(figura, go.Figure)
