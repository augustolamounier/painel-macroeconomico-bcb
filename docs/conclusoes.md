# 8. Conclusões e limitações

## Respostas às perguntas da análise

Os números referem-se ao período completo da base (01/2000 a 09/2026; coleta em 10/11/2026).

### 1. A inflação tem ficado dentro da meta?

**Na maior parte do tempo sim, mas por pouco — e os desvios são quase sempre para cima.** O
IPCA em 12 meses ficou dentro do intervalo de tolerância em 56,4% dos meses, acima do teto em
38,3% e abaixo do piso em apenas 5,3%. Dos 26 anos completos, 7 terminaram acima do teto
(2001, 2002, 2003, 2015, 2021, 2022 e 2024) e 1 abaixo do piso (2017). Em setembro de 2026 a
inflação estava em 4,58%, ligeiramente acima do teto de 4,50%.

### 2. Quais grupos de consumo mais encareceram?

**Alimentação e bebidas (539,8%), Educação (476,8%) e Despesas pessoais (469,0%)**, todos
acima do IPCA geral (384,5%). Comunicação (150,8%) e Artigos de residência (152,0%) subiram
menos da metade do índice. Os grupos mais instáveis são Educação (reajustes concentrados em
fevereiro), Comunicação, Transportes e Alimentação.

### 3. Como a Selic reagiu à inflação?

**A Selic acompanha a inflação com defasagem** (correlação de 0,57). O juro real foi positivo
em 299 dos 321 meses, com média de 5,81% ao ano; só ficou negativo em 2020–2021, quando a
Selic chegou a 1,90% e a inflação acelerou. Em setembro de 2026 o juro real era de 8,80%,
acima da média histórica.

### 4. A alta do dólar anda junto com a inflação?

**Sim, mas a relação é fraca** (r = 0,21). Períodos de forte desvalorização do real tendem a
ter inflação mais alta, porém o câmbio sozinho explica pouco: a nuvem de pontos é bastante
dispersa. O dólar subiu 184,4% no período, menos que a inflação acumulada.

### 5. Quanto poder de compra o real perdeu?

**Cerca de 79%.** Os preços subiram 384,5% entre janeiro de 2000 e setembro de 2026 (6,08% ao
ano, em média). R$ 100,00 guardados sem correção desde 2000 compram hoje o equivalente a
R$ 20,64; para comprar o mesmo que R$ 100,00 compravam, são necessários R$ 484,46.

### 6. Existe padrão sazonal na inflação?

**Sim.** A inflação média é mais alta na virada do ano — dezembro (0,68%), fevereiro (0,66%) e
janeiro (0,62%) — e mais baixa no meio do ano — agosto (0,28%) e junho (0,29%).

## Principais conclusões

1. **O regime de metas funciona com folga pequena.** A inflação costuma ficar na metade
   superior do intervalo, e escapa pelo teto com frequência muito maior do que pelo piso.
2. **A inflação é desigual entre itens de consumo.** Alimentação subiu três vezes e meia mais
   que Comunicação. O índice geral esconde realidades muito diferentes.
3. **O Brasil convive com juros reais altos.** Uma média de 5,81% ao ano acima da inflação
   tem impacto direto no custo do crédito e no retorno de aplicações de renda fixa.
4. **Dinheiro parado perde valor rapidamente.** Com 6% de inflação média ao ano, o poder de
   compra cai pela metade em cerca de doze anos — informação essencial para planejamento
   financeiro e para a correção de contratos.

Sobre o projeto em si: a orientação a objetos permitiu separar a coleta, o tratamento, a
análise e a apresentação de modo que cada parte pode ser testada e trocada isoladamente. O
mesmo código alimenta o dashboard, os gráficos desta documentação e os testes.

## Limitações da análise

**Sobre os dados**

- **Séries com início tardio.** A taxa de desocupação só existe a partir de 03/2012 e o IBC-Br
  a partir de 01/2003; análises com essas variáveis cobrem menos tempo.
- **Defasagem de divulgação.** Cada série é divulgada com atraso diferente; por isso os
  indicadores podem se referir a meses distintos (o painel sempre informa o mês de referência).
- **Revisões.** Séries como o IBC-Br e a taxa de desocupação são revisadas depois de
  divulgadas; os valores podem mudar entre uma coleta e outra.
- **Códigos das séries.** A API consultada não devolve o nome das séries, apenas os valores.
  A correspondência entre códigos e descrições foi conferida por coerência dos dados (ver
  [Dados e tratamento](dados.md)), mas deve ser confirmada no portal do SGS em caso de dúvida.

**Sobre o método**

- **Análise descritiva.** O painel mostra associações, não relações de causa e efeito. A
  correlação entre câmbio e inflação, por exemplo, não isola o efeito de outras variáveis.
- **Juro real ex-post.** O cálculo usa a inflação passada. O juro real relevante para decisões
  de investimento é o *ex-ante*, baseado na inflação esperada, que não está nas séries usadas.
- **Avaliação da meta.** Até 2024, o cumprimento oficial da meta era avaliado pelo IPCA do
  ano-calendário; a comparação mês a mês do IPCA em 12 meses com o intervalo é uma
  aproximação. O intervalo de tolerância foi transcrito do histórico de metas do Banco Central
  e está registrado em `config.TOLERANCIAS_META`. Em alguns anos (como 2003 e 2004) as metas
  foram revistas depois de fixadas; o painel usa os valores da série 13521 do SGS.
- **Grupos sem pesos.** Os grupos do IPCA têm pesos diferentes no índice. A inflação
  acumulada de um grupo mostra quanto *aquele grupo* encareceu, não quanto ele contribuiu para
  o índice geral.
- **Média nacional.** O IPCA é uma média de regiões metropolitanas e de famílias com
  diferentes faixas de renda; a inflação percebida por uma família específica pode ser bem
  diferente.

**Sobre o sistema**

- O painel depende da disponibilidade da API do Banco Central; a cópia local reduz o risco,
  mas pode ficar desatualizada.
- A análise interpretativa é gerada por regras fixas: descreve os números, mas não substitui
  a leitura de um analista.

## Trabalhos futuros

- Incluir as expectativas de inflação do Boletim Focus para calcular o juro real *ex-ante*.
- Incorporar os pesos dos grupos do IPCA (IBGE/SIDRA) e medir a contribuição de cada grupo.
- Acrescentar outras fontes do enunciado (por exemplo, dados do IBGE por região).
- Estimar modelos com defasagens para estudar o repasse do câmbio aos preços.
