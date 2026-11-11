import pandas as pd
import pytest

from painel_macro.config import CATALOGO
from painel_macro.pipeline import PipelineDados
from painel_macro.tratamento import TratadorDados
from tests.conftest import FonteFalsa, bruto

REFERENCIA = pd.Timestamp("2024-06-30")


def longo(linhas: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(linhas, columns=["serie", "data", "valor"])


@pytest.fixture
def tratador() -> TratadorDados:
    return TratadorDados(data_referencia=REFERENCIA)


def test_converte_tipos_e_monta_base_mensal(tratador):
    base = tratador.tratar(longo([
        ("ipca", "01/01/2024", "0.42"),
        ("ipca", "01/02/2024", "0,83"),   # vírgula decimal também é aceita
        ("selic", "01/01/2024", "11.75"),
        ("selic", "01/02/2024", "11.25"),
    ]))

    assert isinstance(base.index, pd.DatetimeIndex)
    assert list(base.columns) == ["ipca", "selic"]
    assert base["ipca"].tolist() == [0.42, 0.83]
    assert base.dtypes.eq("float64").all()


def test_descarta_valores_e_datas_invalidos(tratador):
    base = tratador.tratar(longo([
        ("ipca", "01/01/2024", "0.42"),
        ("ipca", "01/02/2024", "n/d"),
        ("ipca", "31/02/2024", "0.50"),
    ]))

    assert len(base) == 1
    assert tratador.relatorio.valores_invalidos == 1
    assert tratador.relatorio.datas_invalidas == 1


def test_remove_duplicidades_mantendo_o_ultimo_registro(tratador):
    base = tratador.tratar(longo([
        ("ipca", "01/01/2024", "0.40"),
        ("ipca", "01/01/2024", "0.42"),
    ]))

    assert base.loc["2024-01-01", "ipca"] == 0.42
    assert tratador.relatorio.duplicados_removidos == 1


def test_remove_datas_futuras(tratador):
    base = tratador.tratar(longo([
        ("selic", "01/06/2024", "10.50"),
        ("selic", "01/12/2024", "13.75"),
    ]))

    assert base.index.max() == pd.Timestamp("2024-06-01")
    assert tratador.relatorio.datas_futuras_removidas == 1


def test_propaga_serie_anual_para_todos_os_meses_do_ano(tratador):
    base = tratador.tratar(longo([
        ("ipca", "01/01/2024", "0.42"),
        ("ipca", "01/02/2024", "0.83"),
        ("ipca", "01/03/2024", "0.16"),
        ("meta_inflacao", "01/01/2024", "3.00"),
    ]))

    assert base["meta_inflacao"].tolist() == [3.0, 3.0, 3.0]


def test_interpola_apenas_lacunas_internas(tratador):
    base = tratador.tratar(longo([
        ("ipca", "01/01/2024", "0.40"),
        ("ipca", "01/03/2024", "0.60"),
        ("ipca", "01/04/2024", "0.30"),
        ("selic", "01/02/2024", "11.00"),
        ("selic", "01/03/2024", "10.75"),
    ]))

    assert base.loc["2024-02-01", "ipca"] == pytest.approx(0.50)
    assert pd.isna(base.loc["2024-01-01", "selic"])   # início ausente não é inventado
    assert pd.isna(base.loc["2024-04-01", "selic"])   # fim ausente também não
    assert tratador.relatorio.lacunas_interpoladas == 1
    assert tratador.relatorio.ausentes_por_coluna == {"ipca": 0, "selic": 2}


def test_relatorio_vira_tabela(tratador):
    tratador.tratar(longo([("ipca", "01/01/2024", "0.42")]))
    tabela = tratador.relatorio.como_tabela()

    assert list(tabela.columns) == ["verificacao", "quantidade"]
    assert tabela["quantidade"].iloc[0] == 1


def test_pipeline_liga_fonte_e_tratador():
    dados = {serie.nome: bruto(["01/01/2024", "01/02/2024"], ["1.0", "2.0"])
             for serie in CATALOGO}
    fonte = FonteFalsa(dados)
    pipeline = PipelineDados(fonte, TratadorDados(data_referencia=REFERENCIA))

    base = pipeline.executar()

    assert fonte.chamadas == [serie.nome for serie in CATALOGO]
    assert list(base.columns) == [serie.nome for serie in CATALOGO]
    assert len(base) == 2
    assert pipeline.relatorio.registros_brutos == 2 * len(CATALOGO)
    assert len(pipeline.dados_brutos) == 2 * len(CATALOGO)
