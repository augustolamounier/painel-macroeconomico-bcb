"""Exporta os gráficos do painel como páginas HTML interativas para a documentação.

Uso:
    python scripts/exportar_graficos.py

Os arquivos são gravados em ``docs/graficos/`` e incorporados às páginas do
site (MkDocs). O script também grava ``data/processed/resumo_indicadores.md``
com os indicadores e a análise interpretativa do período completo — os números
citados na documentação saem desse arquivo — e ``docs/apresentacao/dados.js``,
com as séries usadas pelos gráficos interativos dos slides.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from painel_macro.analisador import AnalisadorDados  # noqa: E402
from painel_macro.config import (  # noqa: E402
    DIRETORIO_DADOS_BRUTOS,
    DIRETORIO_DADOS_TRATADOS,
    RAIZ_PROJETO,
)
from painel_macro.fontes import FonteDadosCSV  # noqa: E402
from painel_macro.galeria import GaleriaGraficos  # noqa: E402
from painel_macro.indicadores import PainelIndicadores  # noqa: E402
from painel_macro.interpretacao import GeradorInterpretacao  # noqa: E402
from painel_macro.pipeline import PipelineDados  # noqa: E402

DESTINO = RAIZ_PROJETO / "docs" / "graficos"
DADOS_APRESENTACAO = RAIZ_PROJETO / "docs" / "apresentacao" / "dados.js"


def exportar_dados_apresentacao(analisador: AnalisadorDados) -> None:
    """Grava as séries que os slides usam, no formato que o navegador lê direto."""
    dados = analisador.dados.dropna(subset=["ipca_12m"])
    serie = [
        [f"{data:%Y-%m}", round(linha.ipca_12m, 2), round(linha.meta_inflacao, 2),
         round(linha.piso_meta, 2), round(linha.teto_meta, 2), round(linha.selic, 2)]
        for data, linha in dados.iterrows()
    ]
    ranking = analisador.inflacao_por_grupo()
    grupos = [[linha.grupo, round(linha.acumulado, 1)] for linha in ranking.itertuples()]
    conteudo = (
        "// Gerado por scripts/exportar_graficos.py a partir dos dados do Banco Central.\n"
        "// SERIE: [mês, IPCA 12 meses, centro da meta, piso, teto, Selic]\n"
        f"window.SERIE = {json.dumps(serie, separators=(',', ':'))};\n"
        f"window.GRUPOS = {json.dumps(grupos, ensure_ascii=False, separators=(',', ':'))};\n"
        f"window.IPCA_GERAL = {round(analisador.acumulado('ipca'), 1)};\n"
    )
    DADOS_APRESENTACAO.write_text(conteudo, encoding="utf-8")
    print(f"dados da apresentação gravados: {DADOS_APRESENTACAO.name}")


def main() -> None:
    base = PipelineDados(FonteDadosCSV(DIRETORIO_DADOS_BRUTOS)).executar()
    analisador = AnalisadorDados(base)
    DESTINO.mkdir(parents=True, exist_ok=True)

    for nome, figura in GaleriaGraficos(analisador).gerar_todos().items():
        figura.write_html(
            DESTINO / f"{nome}.html", include_plotlyjs="directory", full_html=True,
            config={"displaylogo": False, "responsive": True},
        )
        print(f"gráfico exportado: {nome}.html")

    indicadores = PainelIndicadores.padrao().como_tabela(analisador)
    interpretacao = GeradorInterpretacao(analisador).como_markdown()
    resumo = (
        "# Resumo gerado automaticamente\n\n"
        + indicadores.to_markdown(index=False)
        + "\n\n"
        + interpretacao
        + "\n"
    )
    arquivo_resumo = DIRETORIO_DADOS_TRATADOS / "resumo_indicadores.md"
    arquivo_resumo.write_text(resumo, encoding="utf-8")
    print(f"resumo gravado: {arquivo_resumo.name}")

    exportar_dados_apresentacao(analisador)


if __name__ == "__main__":
    main()
