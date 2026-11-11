"""Fontes de dados do projeto.

Este módulo concentra tudo o que diz respeito à *origem* dos dados:

* ``FonteDados`` – classe abstrata que define o contrato de qualquer fonte;
* ``FonteDadosSGS`` – consulta a API pública de séries temporais do BCB;
* ``FonteDadosCSV`` – lê e grava as séries em arquivos CSV locais;
* ``FonteDadosComCache`` – combina duas fontes: tenta a principal e, se ela
  falhar, usa a reserva (padrão de projeto *Decorator*).

As três classes concretas são intercambiáveis (princípio da substituição
de Liskov): o restante do sistema conhece apenas a abstração ``FonteDados``.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd
import requests

from painel_macro.config import SerieConfig

COLUNAS_BRUTAS = ["data", "valor"]
COLUNAS_LONGAS = ["serie", "data", "valor"]


class ErroFonteDados(Exception):
    """Erro levantado quando uma fonte não consegue entregar os dados."""


class ClienteHTTP(Protocol):
    """Interface mínima de um cliente HTTP (princípio da segregação de interfaces)."""

    def obter_json(self, url: str, parametros: dict[str, str]) -> list[dict]:
        """Faz uma requisição GET e devolve o corpo JSON já decodificado."""
        ...


class ClienteRequests:
    """Implementação de ``ClienteHTTP`` baseada na biblioteca ``requests``."""

    def __init__(
        self, tempo_limite: float = 30.0, tentativas: int = 4, espera_inicial: float = 1.0
    ) -> None:
        if tentativas < 1:
            raise ValueError("É preciso permitir pelo menos uma tentativa.")
        self._tempo_limite = tempo_limite
        self._tentativas = tentativas
        self._espera_inicial = espera_inicial
        self._sessao = requests.Session()
        self._sessao.headers.update({"Accept": "application/json"})

    def obter_json(self, url: str, parametros: dict[str, str]) -> list[dict]:
        """Consulta a URL, repetindo a tentativa em caso de falha passageira."""
        ultimo_erro: Exception | None = None
        for tentativa in range(self._tentativas):
            if tentativa:
                time.sleep(self._espera_inicial * 2 ** (tentativa - 1))
            try:
                resposta = self._sessao.get(url, params=parametros, timeout=self._tempo_limite)
                resposta.raise_for_status()
                return resposta.json()
            except (requests.RequestException, ValueError) as erro:
                ultimo_erro = erro
                if not self._vale_repetir(erro):
                    break
        raise ErroFonteDados(f"Falha ao consultar {url}: {ultimo_erro}") from ultimo_erro

    @staticmethod
    def _vale_repetir(erro: Exception) -> bool:
        """Erros do cliente (4xx) são definitivos; os demais podem ser passageiros."""
        resposta = getattr(erro, "response", None)
        return resposta is None or resposta.status_code >= 500


class FonteDados(ABC):
    """Contrato comum a todas as origens de dados."""

    def __init__(self, nome: str) -> None:
        self._nome = nome

    @property
    def nome(self) -> str:
        """Nome legível da fonte (somente leitura)."""
        return self._nome

    @abstractmethod
    def carregar(self, serie: SerieConfig, inicio: date, fim: date) -> pd.DataFrame:
        """Devolve os dados brutos de uma série com as colunas ``data`` e ``valor``."""

    def carregar_varias(
        self, series: Iterable[SerieConfig], inicio: date, fim: date
    ) -> pd.DataFrame:
        """Carrega várias séries e as empilha no formato longo (serie, data, valor)."""
        partes = []
        for serie in series:
            bruto = self.carregar(serie, inicio, fim)
            partes.append(bruto.assign(serie=serie.nome)[COLUNAS_LONGAS])
        if not partes:
            return pd.DataFrame(columns=COLUNAS_LONGAS)
        return pd.concat(partes, ignore_index=True)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(nome={self._nome!r})"


class FonteDadosSGS(FonteDados):
    """Consulta a API do Sistema Gerenciador de Séries Temporais (SGS) do BCB.

    A API limita as consultas de séries diárias a janelas de dez anos. Para
    funcionar com qualquer periodicidade, o período pedido é dividido em
    janelas e os resultados são concatenados.
    """

    URL_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    FORMATO_DATA = "%d/%m/%Y"

    def __init__(self, cliente: ClienteHTTP | None = None, janela_anos: int = 10) -> None:
        super().__init__("API SGS – Banco Central do Brasil")
        if janela_anos < 1:
            raise ValueError("A janela de consulta deve ter pelo menos um ano.")
        self._cliente = cliente or ClienteRequests()
        self._janela_anos = janela_anos

    def carregar(self, serie: SerieConfig, inicio: date, fim: date) -> pd.DataFrame:
        if inicio > fim:
            raise ValueError("A data inicial não pode ser posterior à data final.")
        registros: list[dict] = []
        for inicio_janela, fim_janela in self._janelas(serie, inicio, fim):
            parametros = {
                "formato": "json",
                "dataInicial": inicio_janela.strftime(self.FORMATO_DATA),
                "dataFinal": fim_janela.strftime(self.FORMATO_DATA),
            }
            resposta = self._cliente.obter_json(self._url(serie), parametros)
            if not isinstance(resposta, list):
                raise ErroFonteDados(
                    f"Resposta inesperada da API para a série {serie.codigo}: {resposta!r}"
                )
            registros.extend(resposta)
        if not registros:
            raise ErroFonteDados(f"A série {serie.codigo} não retornou nenhum registro.")
        return pd.DataFrame(registros, columns=COLUNAS_BRUTAS)

    def _url(self, serie: SerieConfig) -> str:
        return self.URL_BASE.format(codigo=serie.codigo)

    def _janelas(self, serie: SerieConfig, inicio: date, fim: date) -> list[tuple[date, date]]:
        """Divide o período em janelas aceitas pela API."""
        if serie.periodicidade != "diaria":
            return [(inicio, fim)]
        janelas = []
        atual = inicio
        while atual <= fim:
            limite = date(atual.year + self._janela_anos, atual.month, min(atual.day, 28))
            fim_janela = min(fim, limite - timedelta(days=1))
            janelas.append((atual, fim_janela))
            atual = fim_janela + timedelta(days=1)
        return janelas


class FonteDadosCSV(FonteDados):
    """Lê e grava as séries em arquivos CSV (um arquivo por série)."""

    def __init__(self, diretorio: Path | str) -> None:
        super().__init__("Arquivos CSV locais")
        self._diretorio = Path(diretorio)

    @property
    def diretorio(self) -> Path:
        return self._diretorio

    def carregar(self, serie: SerieConfig, inicio: date, fim: date) -> pd.DataFrame:
        caminho = self._caminho(serie)
        if not caminho.exists():
            raise ErroFonteDados(f"Arquivo não encontrado: {caminho}")
        # Os valores são lidos como texto para preservar o dado bruto;
        # a conversão de tipos é responsabilidade do TratadorDados.
        bruto = pd.read_csv(caminho, dtype=str)
        if list(bruto.columns) != COLUNAS_BRUTAS:
            raise ErroFonteDados(f"Colunas inesperadas em {caminho}: {list(bruto.columns)}")
        datas = pd.to_datetime(bruto["data"], format="%d/%m/%Y", errors="coerce")
        no_periodo = datas.isna() | datas.between(pd.Timestamp(inicio), pd.Timestamp(fim))
        return bruto[no_periodo].reset_index(drop=True)

    def salvar(self, serie: SerieConfig, dados: pd.DataFrame) -> Path:
        """Grava os dados brutos de uma série e devolve o caminho do arquivo."""
        self._diretorio.mkdir(parents=True, exist_ok=True)
        caminho = self._caminho(serie)
        dados[COLUNAS_BRUTAS].to_csv(caminho, index=False)
        return caminho

    def possui(self, serie: SerieConfig) -> bool:
        return self._caminho(serie).exists()

    def _caminho(self, serie: SerieConfig) -> Path:
        return self._diretorio / serie.nome_arquivo


class FonteDadosComCache(FonteDados):
    """Tenta a fonte principal e recorre à reserva em caso de falha.

    Quando a fonte principal responde, os dados são gravados na reserva
    (se ``atualizar_reserva`` for verdadeiro), de modo que o painel continue
    funcionando mesmo sem acesso à internet.
    """

    def __init__(
        self,
        principal: FonteDados,
        reserva: FonteDadosCSV,
        atualizar_reserva: bool = True,
    ) -> None:
        super().__init__(f"{principal.nome} (com cópia local)")
        self._principal = principal
        self._reserva = reserva
        self._atualizar_reserva = atualizar_reserva
        self._series_da_reserva: list[str] = []

    @property
    def series_da_reserva(self) -> tuple[str, ...]:
        """Séries que precisaram ser lidas da cópia local na última carga."""
        return tuple(self._series_da_reserva)

    @property
    def usou_reserva(self) -> bool:
        return bool(self._series_da_reserva)

    def carregar(self, serie: SerieConfig, inicio: date, fim: date) -> pd.DataFrame:
        try:
            dados = self._principal.carregar(serie, inicio, fim)
        except ErroFonteDados:
            dados = self._reserva.carregar(serie, inicio, fim)
            self._series_da_reserva.append(serie.nome)
            return dados
        if self._atualizar_reserva:
            self._reserva.salvar(serie, dados)
        return dados
