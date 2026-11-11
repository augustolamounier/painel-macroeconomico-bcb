# 1. Tema e problema

## Tema

**Conjuntura macroeconômica brasileira: inflação, juros e câmbio de 2000 em diante**, com
dados abertos do Banco Central do Brasil (fonte da área de *Economia* indicada no enunciado do
projeto).

## Justificativa da escolha do tema

- **Relevância prática.** A inflação afeta diretamente o orçamento das famílias e das empresas:
  corrige aluguéis, salários, contratos e preços. A taxa Selic define o custo do crédito e o
  rendimento das aplicações. O câmbio influencia o preço de combustíveis, alimentos e
  eletrônicos. São três variáveis que entram em decisões do dia a dia — de reajustar um
  contrato a escolher um investimento.
- **Apoio à tomada de decisão.** O enunciado pede uma solução computacional que apoie
  decisões. Um painel que mostra se a inflação está dentro da meta, quanto rende o juro
  descontada a inflação e quais itens de consumo mais encarecem responde a perguntas reais de
  quem faz planejamento financeiro ou contábil.
- **Qualidade da fonte.** O Banco Central oferece uma API pública, gratuita, sem cadastro e
  com séries históricas longas — o que permite automatizar a coleta e manter o painel sempre
  atualizado.
- **Adequação à disciplina.** O problema tem estruturas naturalmente modeláveis com
  orientação a objetos: várias *fontes* de dados com o mesmo contrato, vários *indicadores*
  com regras de cálculo diferentes e vários *tipos de gráfico* — três hierarquias em que
  herança e polimorfismo aparecem de forma legítima, e não forçada.

## Problema investigado

> **A inflação brasileira tem ficado dentro da meta definida pelo governo? O que explica os
> períodos em que ela escapou, como os juros reagiram e quanto isso custou em poder de compra?**

Desde 1999 o Brasil adota o regime de metas para a inflação: o Conselho Monetário Nacional
(CMN) fixa uma meta para o IPCA, com um intervalo de tolerância, e o Banco Central usa a taxa
Selic para tentar mantê-la nesse intervalo. O projeto investiga, com dados, como esse sistema
se comportou na prática.

## Objetivos da análise

**Objetivo geral.** Construir um sistema, orientado a objetos, que colete, trate, analise e
apresente de forma interativa os principais indicadores de inflação, juros e câmbio do Brasil.

**Objetivos específicos.**

1. Medir com que frequência a inflação ficou dentro, acima ou abaixo do intervalo da meta.
2. Identificar os grupos de consumo que mais pressionaram os preços.
3. Comparar a trajetória dos juros com a da inflação e calcular o juro real.
4. Avaliar a relação entre a variação do câmbio e a inflação.
5. Quantificar a perda de poder de compra da moeda no período.
6. Verificar se a inflação tem padrão sazonal ao longo do ano.

## Perguntas que a análise responde

| # | Pergunta | Onde é respondida |
|---|---|---|
| 1 | A inflação tem ficado dentro da meta? Em que períodos ela estourou o teto? | Gráficos de linhas, barras e setores (aba *Inflação e meta*) |
| 2 | Quais grupos de consumo mais encareceram e quais são os mais instáveis? | Barras e boxplot (aba *Grupos de consumo*) |
| 3 | Como a Selic reagiu à inflação? O juro real foi positivo? | Linhas (aba *Juros e câmbio*) |
| 4 | A alta do dólar anda junto com a inflação? | Dispersão (aba *Juros e câmbio*) |
| 5 | Quanto poder de compra o real perdeu desde 2000? | Indicadores principais |
| 6 | Existe um padrão sazonal na inflação? | Mapa de calor (aba *Inflação e meta*) |

As respostas, com os números, estão em [Conclusões e limitações](conclusoes.md).

## Planejamento

O desenvolvimento seguiu as oito etapas do enunciado; cada etapa corresponde a um ou mais
*commits* no repositório.

| Etapa | Entrega | Onde está |
|---|---|---|
| 1. Definição do problema | Tema, problema, objetivos e perguntas | Esta página |
| 2. Obtenção e exploração | Coleta pela API e análise exploratória | `scripts/atualizar_dados.py`, `notebooks/01_exploracao_dos_dados.ipynb` |
| 3. Modelagem orientada a objetos | Classes e hierarquias | Pacote `painel_macro/` |
| 4. Tratamento e análise com Pandas | Limpeza, agrupamentos, indicadores | `tratamento.py`, `analisador.py`, `indicadores.py` |
| 5. Visualizações | Gráficos Plotly | `visualizadores.py`, `galeria.py` |
| 6. Dashboard | Aplicação Streamlit | `dashboard.py`, `app.py` |
| 7. Integração e testes | Testes automatizados | Pasta `tests/` |
| 8. Documentação | Este site (branch `gh-pages`) | Pasta `docs/` |
