"""Exporta os gráficos do painel como páginas HTML interativas para a documentação.

Uso:
    python scripts/exportar_graficos.py

Os arquivos são gravados em ``docs/graficos/`` e incorporados às páginas do
site (MkDocs). O script também grava ``data/processed/resumo_indicadores.md``
com os indicadores e a análise interpretativa do período completo — os números
citados na documentação saem desse arquivo.
"""

from __future__ import annotations

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


if __name__ == "__main__":
    main()
