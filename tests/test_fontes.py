from datetime import date

import pandas as pd
import pytest

from painel_macro.config import SerieConfig
from painel_macro.fontes import (
    ErroFonteDados,
    FonteDados,
    FonteDadosComCache,
    FonteDadosCSV,
    FonteDadosSGS,
)
from tests.conftest import ClienteFalso, FonteFalsa, bruto

INICIO, FIM = date(2000, 1, 1), date(2025, 12, 31)


def test_fonte_dados_e_abstrata():
    with pytest.raises(TypeError):
        FonteDados("qualquer")  # type: ignore[abstract]


def test_sgs_monta_requisicao_e_devolve_colunas_brutas(serie_ipca):
    cliente = ClienteFalso()
    dados = FonteDadosSGS(cliente).carregar(serie_ipca, INICIO, FIM)

    assert list(dados.columns) == ["data", "valor"]
    assert len(dados) == 2
    url, parametros = cliente.requisicoes[0]
    assert url.endswith("bcdata.sgs.433/dados")
    assert parametros == {
        "formato": "json", "dataInicial": "01/01/2000", "dataFinal": "31/12/2025",
    }


def test_sgs_divide_series_diarias_em_janelas_de_dez_anos():
    diaria = SerieConfig(1, "dolar_diario", "Dólar", "R$", "diaria", "macro", "")
    cliente = ClienteFalso()
    FonteDadosSGS(cliente).carregar(diaria, INICIO, FIM)

    janelas = [(p["dataInicial"], p["dataFinal"]) for _, p in cliente.requisicoes]
    assert janelas == [
        ("01/01/2000", "31/12/2009"),
        ("01/01/2010", "31/12/2019"),
        ("01/01/2020", "31/12/2025"),
    ]


def test_sgs_rejeita_resposta_vazia_ou_inesperada(serie_ipca):
    with pytest.raises(ErroFonteDados):
        FonteDadosSGS(ClienteFalso(resposta=[])).carregar(serie_ipca, INICIO, FIM)
    with pytest.raises(ErroFonteDados):
        FonteDadosSGS(ClienteFalso(resposta={"error": "x"})).carregar(serie_ipca, INICIO, FIM)


def test_sgs_valida_periodo(serie_ipca):
    with pytest.raises(ValueError):
        FonteDadosSGS(ClienteFalso()).carregar(serie_ipca, FIM, INICIO)


def test_csv_salva_e_carrega_filtrando_o_periodo(tmp_path, serie_ipca):
    fonte = FonteDadosCSV(tmp_path)
    assert not fonte.possui(serie_ipca)
    fonte.salvar(serie_ipca, bruto(["01/12/1999", "01/01/2000", "01/02/2000"],
                                   ["0.60", "0.62", "0.13"]))

    assert fonte.possui(serie_ipca)
    dados = fonte.carregar(serie_ipca, date(2000, 1, 1), date(2000, 12, 31))
    assert dados["data"].tolist() == ["01/01/2000", "01/02/2000"]
    assert dados["valor"].tolist() == ["0.62", "0.13"]  # o dado bruto continua em texto


def test_csv_sem_arquivo_levanta_erro(tmp_path, serie_ipca):
    with pytest.raises(ErroFonteDados):
        FonteDadosCSV(tmp_path).carregar(serie_ipca, INICIO, FIM)


def test_cache_usa_principal_e_atualiza_a_copia_local(tmp_path, serie_ipca):
    principal = FonteFalsa({"ipca": bruto(["01/01/2024"], ["0.42"])})
    reserva = FonteDadosCSV(tmp_path)
    fonte = FonteDadosComCache(principal, reserva)

    dados = fonte.carregar(serie_ipca, INICIO, FIM)

    assert dados["valor"].tolist() == ["0.42"]
    assert reserva.possui(serie_ipca)
    assert not fonte.usou_reserva


def test_cache_recorre_a_copia_local_quando_a_principal_falha(tmp_path, serie_ipca):
    reserva = FonteDadosCSV(tmp_path)
    reserva.salvar(serie_ipca, bruto(["01/01/2024"], ["0.42"]))
    fonte = FonteDadosComCache(FonteFalsa(falhar=True), reserva)

    dados = fonte.carregar(serie_ipca, INICIO, FIM)

    assert dados["valor"].tolist() == ["0.42"]
    assert fonte.series_da_reserva == ("ipca",)


def test_fontes_sao_intercambiaveis(tmp_path, serie_ipca):
    """Polimorfismo: qualquer FonteDados serve para carregar_varias."""
    csv = FonteDadosCSV(tmp_path)
    csv.salvar(serie_ipca, bruto(["01/01/2024"], ["0.42"]))
    fontes = [
        csv,
        FonteDadosSGS(ClienteFalso()),
        FonteFalsa({"ipca": bruto(["01/01/2024"], ["0.42"])}),
    ]
    for fonte in fontes:
        longo = fonte.carregar_varias([serie_ipca], INICIO, FIM)
        assert isinstance(longo, pd.DataFrame)
        assert list(longo.columns) == ["serie", "data", "valor"]
        assert set(longo["serie"]) == {"ipca"}


class _RespostaFalsa:
    def __init__(self, status: int, corpo=None):
        self.status_code = status
        self._corpo = corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"erro {self.status_code}", response=self)

    def json(self):
        return self._corpo


def _cliente_com_respostas(monkeypatch, respostas):
    from painel_macro.fontes import ClienteRequests

    cliente = ClienteRequests(tentativas=3, espera_inicial=0)
    fila = list(respostas)
    chamadas = []

    def get_falso(url, params=None, timeout=None):
        chamadas.append(url)
        return fila.pop(0)

    monkeypatch.setattr(cliente._sessao, "get", get_falso)
    return cliente, chamadas


def test_cliente_repete_a_consulta_apos_erro_passageiro(monkeypatch):
    cliente, chamadas = _cliente_com_respostas(
        monkeypatch, [_RespostaFalsa(502), _RespostaFalsa(200, [{"data": "x", "valor": "1"}])]
    )
    assert cliente.obter_json("https://exemplo", {}) == [{"data": "x", "valor": "1"}]
    assert len(chamadas) == 2


def test_cliente_nao_repete_erro_definitivo(monkeypatch):
    cliente, chamadas = _cliente_com_respostas(monkeypatch, [_RespostaFalsa(404)] * 3)
    with pytest.raises(ErroFonteDados):
        cliente.obter_json("https://exemplo", {})
    assert len(chamadas) == 1


def test_cliente_desiste_apos_esgotar_as_tentativas(monkeypatch):
    cliente, chamadas = _cliente_com_respostas(monkeypatch, [_RespostaFalsa(503)] * 3)
    with pytest.raises(ErroFonteDados):
        cliente.obter_json("https://exemplo", {})
    assert len(chamadas) == 3
