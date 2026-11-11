# 4. Indicadores

O enunciado pede ao menos cinco indicadores relevantes para o problema. O painel calcula
**dez**, todos recalculados sempre que o usuário muda o período no filtro.

Cada indicador é um objeto de uma subclasse de `Indicador`. O método `calcular` recebe o
`AnalisadorDados` do período filtrado e devolve um `ResultadoIndicador` (valor, unidade, mês
de referência e texto de apoio).

## Quadro dos indicadores

Valores do período completo da base (01/2000 a 09/2026; coleta em 10/11/2026).

| # | Indicador | Classe | Fórmula | Valor | Para que serve |
|---|---|---|---|---|---|
| 1 | **IPCA em 12 meses** | `IndicadorUltimoValor` | último valor de `ipca_12m` | 4,58% (09/2026) | Medida oficial da inflação corrente |
| 2 | **Desvio da meta** | `IndicadorDesvioMeta` | `ipca_12m − meta` | +1,58 p.p. | Mostra se a inflação está acima ou abaixo do objetivo |
| 3 | **Taxa Selic** | `IndicadorUltimoValor` | último valor de `selic` | 13,65% a.a. (11/2026) | Custo básico do dinheiro na economia |
| 4 | **Juro real (ex-post)** | `IndicadorUltimoValor` | `(1+selic)/(1+ipca_12m) − 1` | 8,80% a.a. | Quanto o juro rende acima da inflação |
| 5 | **Inflação no período** | `IndicadorInflacaoAcumulada` | `Π(1 + ipca/100) − 1` | 384,46% | Alta total dos preços no período |
| 6 | **Poder de compra** | `IndicadorPoderDeCompra` | `100 / (1 + inflação acumulada)` | R$ 20,64 | Tradução da inflação para o bolso |
| 7 | **Meses acima do teto** | `IndicadorMesesAcimaDoTeto` | meses com `ipca_12m > teto` ÷ total | 38,3% (123 de 321) | Frequência com que a meta foi descumprida |
| 8 | **Dólar no período** | `IndicadorVariacaoNoPeriodo` | `dólar final / dólar inicial − 1` | +184,38% (R$ 1,80 → R$ 5,13) | Desvalorização do real frente ao dólar |
| 9 | **Desocupação** | `IndicadorUltimoValor` | último valor de `desocupacao` | 5,2% (09/2026) | Situação do mercado de trabalho |
| 10 | **Grupo que mais subiu** | `IndicadorGrupoMaiorInflacao` | maior inflação acumulada entre os grupos | Alimentação e bebidas (539,76%) | Onde a inflação pesou mais |

## Observações sobre as fórmulas

**Inflação acumulada.** Variações percentuais não se somam: compõem-se. Duas altas de 10%
resultam em 21%, não em 20%. Por isso o acumulado é o produto dos fatores `(1 + v/100)`:

```python
def acumular_percentuais(variacoes: pd.Series) -> float:
    validos = variacoes.dropna()
    return float(((1 + validos / 100).prod() - 1) * 100)
```

A taxa média anual equivalente é `(1 + acumulado)^(12/meses) − 1`: 384,46% em 321 meses
correspondem a 6,08% ao ano.

**Juro real ex-post.** Usa a fórmula de Fisher, `(1 + i) / (1 + π) − 1`, e não a simples
subtração `i − π`, que superestima o resultado quando as taxas são altas. É "ex-post" porque
desconta a inflação que **já ocorreu** nos últimos 12 meses.

**Desvio e situação frente à meta.** A comparação é feita com duas casas decimais, como na
divulgação oficial. Em 2011, por exemplo, a composição das variações mensais dá 6,503%, que é
divulgado como 6,50% e, portanto, não ultrapassa o teto de 6,50% daquele ano.

**Variação em 12 meses nos cartões.** Os indicadores de "último valor" mostram também a
diferença em relação ao mesmo mês do ano anterior, em pontos percentuais. A cor indica se a
mudança é boa ou ruim: inflação e desemprego em queda aparecem em verde.

## Como acrescentar um indicador

Basta criar uma subclasse e adicioná-la ao painel — nenhuma classe existente é alterada:

```python
from painel_macro.indicadores import Indicador, PainelIndicadores

class IndicadorSelicMaxima(Indicador):
    def __init__(self):
        super().__init__("Selic máxima", "Maior taxa Selic do período.")

    def calcular(self, analisador):
        return self._resultado(float(analisador.dados["selic"].max()))

painel = PainelIndicadores.padrao()
painel.adicionar(IndicadorSelicMaxima())
```
