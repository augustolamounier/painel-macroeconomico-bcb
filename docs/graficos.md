# 5. Gráficos e interpretação

Todos os gráficos são interativos (Plotly): passe o cursor para ver os valores, arraste para
ampliar e dê dois cliques para voltar. Os gráficos desta página foram gerados com o período
completo da base (01/2000 a 09/2026); no dashboard eles acompanham os filtros.

| Requisito do enunciado | Gráfico do painel | Classe |
|---|---|---|
| Gráfico de barras | Inflação anual frente à meta; inflação por grupo | `GraficoBarras` |
| Gráfico de linhas | Inflação e meta; juros e inflação; câmbio | `GraficoLinhas` |
| Gráfico de setores ou treemap | Meses dentro e fora da meta | `GraficoSetores` |
| Gráfico adicional | Dispersão, boxplot e mapa de calor | `GraficoDispersao`, `GraficoBoxplot`, `GraficoMapaCalor` |

---

## 1. Inflação em 12 meses e a meta — *linhas*

<iframe class="grafico" src="../graficos/inflacao_e_meta.html" loading="lazy" title="Inflação em 12 meses e a meta"></iframe>

**O que mostra.** A linha verde (jade) é o IPCA acumulado em 12 meses; a faixa cinza é o intervalo de
tolerância da meta e a linha tracejada, o seu centro.

**Interpretação.** A inflação passou boa parte do período fora da faixa: ficou acima do teto em
**123 dos 321 meses (38,3%)** e abaixo do piso em 17 (5,3%). Há três grandes episódios de
descontrole: 2002–2003 (pico de **17,24% em maio de 2003**), 2015–2016 e 2021–2022. Em
setembro de 2026 o índice estava em **4,58%**, 1,58 ponto percentual acima do centro da meta
(3,00%) e ligeiramente acima do teto (4,50%).

---

## 2. Inflação anual frente à meta — *barras*

<iframe class="grafico" src="../graficos/inflacao_anual.html" loading="lazy" title="Inflação anual frente à meta"></iframe>

**O que mostra.** Cada barra é o IPCA acumulado no ano; a cor indica a situação frente ao
intervalo (cinza = dentro, vinho = acima do teto, azul = abaixo do piso) e a linha preta é
o centro da meta. O asterisco marca o ano com dados parciais.

**Interpretação.** Dos 26 anos completos, **7 terminaram acima do teto** (2001, 2002, 2003,
2015, 2021, 2022 e 2024) e **1 abaixo do piso** (2017). A maior inflação anual foi a de 2002
(12,53%) e a menor, a de 2017 (2,95%). Em quase todos os anos a barra fica acima da linha
preta: mesmo quando a meta foi formalmente cumprida, a inflação ficou na metade superior do
intervalo.

---

## 3. Meses dentro e fora da meta — *setores*

<iframe class="grafico" src="../graficos/situacao_meta.html" loading="lazy" title="Meses dentro e fora da meta"></iframe>

**O que mostra.** A divisão dos 321 meses conforme a posição do IPCA em 12 meses em relação
ao intervalo de tolerância.

**Interpretação.** Em **56,4%** dos meses a inflação esteve dentro do intervalo; em **38,3%**,
acima do teto; em apenas **5,3%**, abaixo do piso. Os desvios são fortemente assimétricos:
quando a inflação sai do intervalo, quase sempre é para cima.

---

## 4. Inflação acumulada por grupo de consumo — *barras horizontais*

<iframe class="grafico" src="../graficos/inflacao_por_grupo.html" loading="lazy" title="Inflação acumulada por grupo"></iframe>

**O que mostra.** A variação acumulada dos preços de cada um dos nove grupos do IPCA, em ordem
decrescente. A linha tracejada marca o IPCA geral (384,5%).

**Interpretação.** **Alimentação e bebidas** foi o grupo que mais encareceu (539,8%), seguido
de Educação (476,8%) e Despesas pessoais (469,0%). Habitação e Saúde também ficaram acima do
índice geral. No outro extremo, **Comunicação (150,8%)** e **Artigos de residência (152,0%)**
subiram menos da metade do IPCA. Como a alimentação costuma pesar mais no orçamento das
famílias de menor renda, a inflação do período tende a ter sido sentida de forma desigual.

---

## 5. Distribuição das variações mensais por grupo — *boxplot*

<iframe class="grafico" src="../graficos/distribuicao_por_grupo.html" loading="lazy" title="Distribuição das variações mensais por grupo"></iframe>

**O que mostra.** Para cada grupo, a caixa reúne a metade central das variações mensais, a
linha interna é a mediana e os pontos são meses atípicos.

**Interpretação.** O gráfico separa dois tipos de comportamento. **Educação** tem uma das caixas mais
estreitas, mas muitos pontos distantes à direita: os preços quase não mudam ao longo do ano e
saltam em fevereiro, com os reajustes de mensalidades — por isso é o grupo de maior
desvio-padrão (1,36 p.p.). **Alimentação** e **Transportes** têm caixas largas: oscilam o
tempo todo, para cima e para baixo. **Despesas pessoais** e **Saúde** sobem de forma regular,
quase sem quedas.

---

## 6. Sazonalidade da inflação — *mapa de calor*

<iframe class="grafico grafico--alto" src="../graficos/sazonalidade.html" loading="lazy" title="Sazonalidade da inflação"></iframe>

**O que mostra.** O IPCA de cada mês (colunas) em cada ano (linhas). Vinho indica alta de
preços e azul, queda. A escala de cores ignora os 2% de valores mais extremos para que meses
excepcionais não apaguem os demais.

**Interpretação.** Em média, **dezembro (0,68%)**, fevereiro (0,66%) e janeiro (0,62%) são os
meses de inflação mais alta, e **agosto (0,28%)** e junho (0,29%), os de inflação mais baixa.
As colunas do meio do ano são visivelmente mais claras. As linhas de 2002–2003, 2015 e
2021–2022 aparecem escuras de ponta a ponta, mostrando que nos episódios de descontrole a
inflação sobe em todos os meses, e não só nos sazonalmente altos. Meses de deflação são raros
(16 em 321).

---

## 7. Juros, inflação e juro real — *linhas*

<iframe class="grafico" src="../graficos/juros_e_inflacao.html" loading="lazy" title="Juros, inflação e juro real"></iframe>

**O que mostra.** A taxa Selic, o IPCA em 12 meses e o juro real (Selic descontada a
inflação), todos em % ao ano e no mesmo eixo.

**Interpretação.** A Selic acompanha a inflação com defasagem: sobe depois que os preços
aceleram e só cai depois que eles cedem (correlação de 0,57 entre as duas séries). O juro
real foi positivo na maior parte do tempo — **média de 5,81% ao ano** — e ficou negativo em
apenas 22 dos 321 meses, concentrados em 2020–2021, quando a Selic chegou ao mínimo de 1,90%
(setembro de 2020) enquanto a inflação acelerava; o piso do juro real foi de −4,44% em julho de
2021. Em setembro de 2026 o juro real estava em **8,80%**, bem acima da média histórica.

---

## 8. Taxa de câmbio — *linhas*

<iframe class="grafico" src="../graficos/cambio.html" loading="lazy" title="Taxa de câmbio"></iframe>

**O que mostra.** A cotação média mensal do dólar, em reais.

**Interpretação.** O dólar passou de **R$ 1,80 (01/2000) para R$ 5,13 (10/2026)**, alta de
184,4%, com máxima de R$ 6,10 em dezembro de 2024. A trajetória não é contínua: há saltos em
2002, 2015 e 2020, cada um seguido por um novo patamar. Note que a alta do dólar (184%) foi
bem menor que a inflação acumulada (384%).

---

## 9. Variação do dólar × inflação — *dispersão*

<iframe class="grafico" src="../graficos/dispersao.html" loading="lazy" title="Variação do dólar e inflação"></iframe>

**O que mostra.** Cada ponto é um mês: no eixo horizontal, a variação do dólar em 12 meses; no
vertical, o IPCA em 12 meses. A reta é a tendência linear.

**Interpretação.** A relação é **positiva, mas fraca** (r = 0,21 em 309 meses): meses com o
dólar em forte alta tendem a ter inflação um pouco maior, mas a nuvem de pontos é bastante
dispersa. O câmbio sozinho explica pouco da inflação. Correlação também não significa
causalidade — choques de oferta e a própria política de juros atuam ao mesmo tempo. No
dashboard é possível trocar a variável do eixo horizontal (Selic, desocupação ou atividade
econômica).

## Decisões de projeto visual

- **Paleta testada para daltonismo.** As cores das séries (jade, latão e ameixa) e das
  situações (azul-ardósia, cinza e vinho) foram conferidas por simulação de protanopia,
  deuteranopia e tritanopia, e todas têm contraste mínimo de 3:1 com o fundo.
- **Um eixo por gráfico.** Não há gráficos com dois eixos verticais, que induzem a
  correlações visuais arbitrárias. Selic, inflação e juro real compartilham o eixo porque têm
  a mesma unidade; o dólar tem gráfico próprio.
- **Cor com significado.** A cor representa a situação frente à meta (cinza, vinho, azul)
  ou identifica a série; quando há uma única série, todas as barras têm a mesma cor.
- **Ordenação.** Barras de categorias sem ordem natural são ordenadas pelo valor.
- **Rótulo no último ponto.** Os gráficos de linha destacam o valor mais recente.
- **Estado vazio.** Se o filtro não deixar dados, o gráfico mostra uma mensagem em vez de um
  erro.
