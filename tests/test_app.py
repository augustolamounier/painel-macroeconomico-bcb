"""Testes de integração: executam o dashboard inteiro com a cópia local dos dados."""

import pytest
from streamlit.testing.v1 import AppTest

from painel_macro.config import CATALOGO, DIRETORIO_DADOS_BRUTOS, RAIZ_PROJETO
from painel_macro.fontes import FonteDadosCSV
from painel_macro.pipeline import PipelineDados


@pytest.fixture
def app(monkeypatch) -> AppTest:
    monkeypatch.setenv("PAINEL_FONTE", "csv")
    return AppTest.from_file(str(RAIZ_PROJETO / "app.py"), default_timeout=120).run()


def test_copia_local_dos_dados_esta_completa():
    fonte = FonteDadosCSV(DIRETORIO_DADOS_BRUTOS)
    assert all(fonte.possui(serie) for serie in CATALOGO)

    base = PipelineDados(fonte).executar()
    assert len(base) >= 300
    assert base.index.is_monotonic_increasing and base.index.is_unique
    assert base["ipca"].between(-2, 5).all() or base["ipca"].isna().any()


def test_dashboard_renderiza_todos_os_componentes(app):
    assert not app.exception
    assert app.title[0].value == "Inflação, juros e câmbio no Brasil"       # cabeçalho
    assert len(app.metric) == 10                                             # KPIs
    assert all(metrica.value != "—" for metrica in app.metric)
    assert len(app.sidebar.slider) == 1 and len(app.sidebar.multiselect) == 1  # filtros
    assert len(app.tabs) == 6
    assert len(app.dataframe) >= 1                                           # tabela
    textos = " ".join(elemento.value for elemento in app.markdown)
    assert "Leitura:" in textos and "Limitações" in textos                   # interpretação


def test_filtro_de_periodo_recalcula_os_indicadores(app):
    antes = [metrica.value for metrica in app.metric]
    app.sidebar.slider[0].set_value((2010, 2015)).run()

    assert not app.exception
    depois = [metrica.value for metrica in app.metric]
    assert antes != depois
    assert any("12/2015" in legenda.value for legenda in app.caption)


def test_filtro_de_grupos_e_variavel_de_dispersao(app):
    app.sidebar.multiselect[0].set_value(["habitacao", "transportes"])
    app.sidebar.selectbox[0].set_value("selic")
    app.run()

    assert not app.exception
    textos = " ".join(elemento.value for elemento in app.markdown)
    assert "taxa selic" in textos


def test_sem_grupos_selecionados_exibe_aviso(app):
    app.sidebar.multiselect[0].set_value([]).run()

    assert not app.exception
    assert any("Nenhum grupo selecionado" in aviso.value for aviso in app.warning)
