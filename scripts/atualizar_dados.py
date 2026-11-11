"""Baixa as séries do Banco Central e atualiza os arquivos da pasta ``data/``.

Uso:
    python scripts/atualizar_dados.py

* ``data/raw/``       – um CSV por série, exatamente como a API devolve;
* ``data/processed/`` – base mensal tratada, pronta para análise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from painel_macro.config import (  # noqa: E402
    DIRETORIO_DADOS_BRUTOS,
    DIRETORIO_DADOS_TRATADOS,
)
from painel_macro.fontes import FonteDadosComCache, FonteDadosCSV, FonteDadosSGS  # noqa: E402
from painel_macro.pipeline import PipelineDados  # noqa: E402


def main() -> None:
    fonte = FonteDadosComCache(FonteDadosSGS(), FonteDadosCSV(DIRETORIO_DADOS_BRUTOS))
    pipeline = PipelineDados(fonte)
    base = pipeline.executar()

    if fonte.usou_reserva:
        print("Atenção: a API não respondeu para:", ", ".join(fonte.series_da_reserva))

    DIRETORIO_DADOS_TRATADOS.mkdir(parents=True, exist_ok=True)
    destino = DIRETORIO_DADOS_TRATADOS / "base_mensal.csv"
    base.to_csv(destino, float_format="%.6g")

    inicio, fim = pipeline.relatorio.periodo
    print(f"Base atualizada: {len(base)} meses ({inicio:%m/%Y} a {fim:%m/%Y}).")
    print(pipeline.relatorio.como_tabela().to_string(index=False))
    print(f"Arquivo gravado em {destino}")


if __name__ == "__main__":
    main()
