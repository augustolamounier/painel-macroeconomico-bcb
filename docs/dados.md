# 2. Dados e tratamento

## Fonte pública de dados

| Item | Descrição |
|---|---|
| **Instituição** | Banco Central do Brasil (BCB) |
| **Sistema** | SGS — Sistema Gerenciador de Séries Temporais |
| **Portal** | [dadosabertos.bcb.gov.br](https://dadosabertos.bcb.gov.br/) |
| **Forma de acesso** | API pública REST, sem cadastro nem chave de acesso |
| **Endereço da API** | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados?formato=json&dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa` |
| **Formato** | JSON — lista de registros `{"data": "01/09/2026", "valor": "0.82"}` |
| **Período usado** | janeiro de 2000 até o último mês divulgado |
| **Data da coleta registrada no repositório** | 10/11/2026 |

O SGS reúne séries produzidas pelo próprio Banco Central (Selic, câmbio, IBC-Br, meta de
inflação) e séries de outros órgãos que o BCB redistribui — é o caso do IPCA e da taxa de
desocupação, calculados pelo **IBGE**.

Cada série tem um código numérico. A classe `FonteDadosSGS` monta a URL a partir do código,
faz a requisição e devolve os registros em um `DataFrame`. Uma cópia dos dados brutos é mantida
em `data/raw/` (um arquivo CSV por série), para que o projeto seja reproduzível e o painel
funcione mesmo sem internet.

!!! info "Particularidades da API tratadas no código"
    - Consultas a séries **diárias** são limitadas a janelas de dez anos; `FonteDadosSGS`
      divide o período pedido em janelas e concatena os resultados.
    - A API ocasionalmente devolve erros passageiros (HTTP 502/503); `ClienteRequests` repete
      a consulta com espera crescente antes de desistir.
    - Se a API estiver fora do ar, `FonteDadosComCache` usa automaticamente a cópia local.

## Variáveis utilizadas

### Séries macroeconômicas

| Coluna | Código SGS | Descrição | Unidade | Início na base |
|---|---|---|---|---|
| `ipca` | 433 | Variação mensal do IPCA, índice oficial de inflação (IBGE) | % ao mês | 01/2000 |
| `ipca_12m` | 13522 | IPCA acumulado em 12 meses | % em 12 meses | 01/2000 |
| `selic` | 4189 | Taxa Selic acumulada no mês, anualizada (base 252 dias úteis) | % ao ano | 01/2000 |
| `dolar` | 3698 | Taxa de câmbio livre, dólar americano (venda), média mensal | R$/US$ | 01/2000 |
| `desocupacao` | 24369 | Taxa de desocupação — PNAD Contínua (IBGE) | % | 03/2012 |
| `ibc_br` | 24363 | Índice de Atividade Econômica do Banco Central | índice | 01/2003 |
| `meta_inflacao` | 13521 | Centro da meta de inflação fixada pelo CMN | % ao ano | 2000 (anual) |

### Grupos do IPCA (variação mensal, em %)

| Coluna | Código SGS | Grupo |
|---|---|---|
| `alimentacao_bebidas` | 1635 | Alimentação e bebidas |
| `habitacao` | 1636 | Habitação |
| `artigos_residencia` | 1637 | Artigos de residência |
| `vestuario` | 1638 | Vestuário |
| `transportes` | 1639 | Transportes |
| `comunicacao` | 1640 | Comunicação |
| `saude_cuidados` | 1641 | Saúde e cuidados pessoais |
| `despesas_pessoais` | 1642 | Despesas pessoais |
| `educacao` | 1643 | Educação |

### Variáveis derivadas (calculadas pelo `AnalisadorDados`)

| Coluna | Fórmula | Unidade |
|---|---|---|
| `teto_meta`, `piso_meta` | meta ± intervalo de tolerância do ano | % ao ano |
| `desvio_meta` | `ipca_12m − meta_inflacao` | pontos percentuais |
| `situacao_meta` | "Abaixo do piso", "Dentro do intervalo" ou "Acima do teto" | categoria |
| `juro_real` | `((1 + selic/100) / (1 + ipca_12m/100) − 1) × 100` | % ao ano |
| `dolar_var_12m` | variação percentual do dólar em 12 meses | % |
| `ibc_br_var_12m` | variação percentual do IBC-Br em 12 meses | % |

O intervalo de tolerância da meta mudou ao longo do tempo. O projeto usa a tabela abaixo
(`config.TOLERANCIAS_META`), transcrita do histórico de metas publicado pelo Banco Central:

| Vigência | Intervalo de tolerância |
|---|---|
| 1999 a 2002 | ± 2,0 p.p. |
| 2003 a 2005 | ± 2,5 p.p. |
| 2006 a 2016 | ± 2,0 p.p. |
| 2017 em diante | ± 1,5 p.p. |

## Exploração inicial (Etapa 2)

A análise exploratória está no notebook
[`notebooks/01_exploracao_dos_dados.ipynb`](https://github.com/augustolamounier/painel-macroeconomico-bcb/blob/main/notebooks/01_exploracao_dos_dados.ipynb),
já executado. Os principais achados:

- **4.662 registros brutos** em 16 séries; todas as colunas chegam como texto.
- **Nenhum valor não numérico, nenhuma duplicidade e nenhuma data futura** nas séries
  utilizadas na data da coleta.
- **Valores ausentes estruturais:** a taxa de desocupação só existe a partir de 03/2012 (148
  meses sem valor na base) e o IBC-Br a partir de 01/2003 (36 meses), além dos meses mais
  recentes ainda não divulgados.
- **Coerência entre séries:** recalcular o IPCA em 12 meses compondo as variações mensais dá
  uma diferença máxima de 0,009 ponto percentual em relação à série publicada — apenas
  arredondamento.
- **Conferência dos códigos dos grupos:** o grupo Educação sobe em média 4,71% em fevereiro e
  menos de 0,5% nos demais meses, exatamente o padrão esperado dos reajustes de mensalidades
  escolares.

## Procedimentos de tratamento (Etapa 4)

O tratamento é feito pela classe `TratadorDados`, em seis passos. Cada passo é um método
privado, e tudo o que foi corrigido é contado em um `RelatorioQualidade`, exibido no próprio
dashboard (aba *Tabela de dados*).

| # | Método | O que faz | Recurso do Pandas |
|---|---|---|---|
| 1 | `_padronizar_tipos` | Converte datas (`dd/mm/aaaa`) e valores de texto para `datetime64` e `float64`; descarta o que não puder ser convertido | `to_datetime`, `to_numeric(errors="coerce")` |
| 2 | `_remover_duplicidades` | Mantém um registro por série e data | `drop_duplicates(subset=...)` |
| 3 | `_remover_datas_futuras` | Descarta registros posteriores à data de referência | filtragem booleana |
| 4 | `_para_formato_largo` | Passa do formato longo para uma tabela mensal, uma coluna por série, com calendário completo | `pivot_table`, `reindex`, `date_range` |
| 5 | `_propagar_series_anuais` | Repete a meta anual em todos os meses do ano | `groupby(...).transform("first")` |
| 6 | `_interpolar_lacunas_internas` | Interpola linearmente apenas lacunas curtas *no meio* da série | `interpolate(limit_area="inside")` |

!!! warning "Decisão sobre valores ausentes"
    Valores ausentes no **início** (a série ainda não existia) ou no **fim** (o dado ainda não
    foi divulgado) **não são preenchidos**. Preenchê-los com média ou com o último valor seria
    inventar informação. Os indicadores usam sempre o último valor realmente disponível de cada
    variável e informam a que mês ele se refere.

### Operações de análise com Pandas

A classe `AnalisadorDados` concentra as operações de manipulação pedidas no enunciado:

| Requisito | Método | Recurso do Pandas |
|---|---|---|
| Seleção e filtragem | `filtrar_periodo`, `tabela`, `ultimo_valor` | `loc`, máscaras booleanas, `dropna` |
| Tratamento de ausentes | `TratadorDados` + `dropna` nas análises | `isna`, `dropna`, `interpolate` |
| Remoção de duplicidades | `TratadorDados._remover_duplicidades` | `drop_duplicates` |
| Agrupamentos | `inflacao_por_ano`, `media_por_mes_do_ano`, `distribuicao_situacao_meta` | `groupby().agg()`, `value_counts` |
| Ordenação | `inflacao_por_grupo`, `maiores_valores`, `tabela` | `sort_values` |
| Estatísticas descritivas | `estatisticas_descritivas`, `correlacoes`, `tendencia_linear` | `describe`, `corr`, `std` |
| Reestruturação | `variacoes_por_grupo`, `sazonalidade` | `stack`, `pivot` |
| Janelas e defasagens | `_enriquecer` | `pct_change(12)` |

Exemplo — inflação de cada ano comparada à meta:

```python
por_ano = dados.groupby(dados.index.year).agg(
    ipca_ano=("ipca", acumular_percentuais),   # Π(1 + v/100) − 1
    meta=("meta_inflacao", "first"),
    piso=("piso_meta", "first"),
    teto=("teto_meta", "first"),
    meses=("ipca", "count"),
)
```
