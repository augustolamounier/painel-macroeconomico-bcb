# 7. Integração e testes

O sistema tem **77 testes automatizados** (pytest), que cobrem **95% das linhas** do pacote
`painel_macro`. Os testes não acessam a internet: usam fontes de dados falsas e a cópia local
dos dados.

```bash
pip install -r requirements-dev.txt
pytest                                   # executa todos os testes
pytest --cov=painel_macro                # com relatório de cobertura
```

## O que é testado

| Arquivo | Testes | O que verifica |
|---|---|---|
| `tests/test_fontes.py` | 13 | Montagem da requisição à API, divisão em janelas de dez anos, leitura e gravação de CSV, uso da cópia local quando a API falha, novas tentativas após erro passageiro |
| `tests/test_tratamento.py` | 8 | Conversão de tipos, descarte de valores inválidos, remoção de duplicidades e datas futuras, propagação da meta anual, interpolação apenas de lacunas internas |
| `tests/test_analisador.py` | 18 | Variáveis derivadas, filtros, agrupamentos, ordenação, estatísticas, classificação frente à meta, encapsulamento |
| `tests/test_indicadores.py` | 12 | Fórmula de cada indicador, formatação brasileira, comportamento sem dados, extensão do painel |
| `tests/test_visualizadores.py` | 17 | Tipo de gráfico gerado por cada classe, cores, estado vazio, tipos exigidos no enunciado |
| `tests/test_interpretacao.py` | 4 | Texto coerente com os números e sensível aos filtros |
| `tests/test_app.py` | 5 | **Integração**: executa o dashboard inteiro e simula o uso dos filtros |

## Testes unitários

Cada classe é testada isoladamente, com uma base sintética de valores simples, em que o
resultado correto pode ser calculado à mão. Exemplo — o IPCA sobe 0,3% ao mês em 2019, logo a
inflação do ano deve ser `1,003¹² − 1`:

```python
def test_inflacao_por_ano_compara_com_a_meta(analisador):
    por_ano = analisador.inflacao_por_ano().set_index("ano")

    assert por_ano.loc[2019, "ipca_ano"] == pytest.approx((1.003 ** 12 - 1) * 100)
    assert por_ano.loc[2019, "situacao"] == SITUACAO_DENTRO
```

A injeção de dependência torna os testes simples: em vez de acessar a rede, `FonteDadosSGS`
recebe um cliente HTTP falso que registra as requisições.

```python
def test_sgs_divide_series_diarias_em_janelas_de_dez_anos():
    diaria = SerieConfig(1, "dolar_diario", "Dólar", "R$", "diaria", "macro", "")
    cliente = ClienteFalso()
    FonteDadosSGS(cliente).carregar(diaria, date(2000, 1, 1), date(2025, 12, 31))

    janelas = [(p["dataInicial"], p["dataFinal"]) for _, p in cliente.requisicoes]
    assert janelas == [
        ("01/01/2000", "31/12/2009"),
        ("01/01/2010", "31/12/2019"),
        ("01/01/2020", "31/12/2025"),
    ]
```

## Testes dos princípios de POO

Alguns testes existem especificamente para comprovar as propriedades de projeto:

| Teste | Propriedade comprovada |
|---|---|
| `test_fonte_dados_e_abstrata`, `test_indicador_e_abstrato`, `test_visualizador_e_abstrato` | Classes abstratas não podem ser instanciadas |
| `test_encapsulamento_dados_devolve_copia` | O estado interno do analisador não é alterável por fora |
| `test_fontes_sao_intercambiaveis` | Polimorfismo e substituição de Liskov nas fontes |
| `test_painel_trata_todos_os_indicadores_da_mesma_forma` | Polimorfismo nos indicadores |
| `test_painel_aceita_novos_indicadores_sem_modificacao` | Princípio aberto/fechado |
| `test_todo_visualizador_lida_com_dados_vazios` | Todas as subclasses de `Visualizador` respeitam o contrato da base |

## Testes de integração

`tests/test_app.py` usa o `AppTest`, ferramenta de testes do próprio Streamlit, para executar
o `app.py` completo — fonte de dados, tratamento, análise, indicadores, gráficos e página — e
simular o usuário mexendo nos filtros:

```python
def test_filtro_de_periodo_recalcula_os_indicadores(app):
    antes = [metrica.value for metrica in app.metric]
    app.sidebar.slider[0].set_value((2010, 2015)).run()

    assert not app.exception
    depois = [metrica.value for metrica in app.metric]
    assert antes != depois
```

Esses testes verificam que todos os componentes obrigatórios estão presentes (cabeçalho, dez
KPIs, filtros, abas, tabela e análise interpretativa), que os filtros recalculam os
indicadores e que situações-limite — como desmarcar todos os grupos — geram um aviso em vez de
um erro.

## Verificação da consistência dos dados

Além dos testes de código, os próprios dados foram conferidos (ver o
[notebook de exploração](https://github.com/augustolamounier/painel-macroeconomico-bcb/blob/main/notebooks/01_exploracao_dos_dados.ipynb)):

- o IPCA em 12 meses publicado bate com a composição das variações mensais (diferença máxima
  de 0,009 p.p.);
- os anos em que o painel aponta inflação acima do teto ou abaixo do piso — 2001, 2002, 2003,
  2015, 2017, 2021, 2022 e 2024 — podem ser conferidos com o histórico de metas publicado
  pelo Banco Central.

## Um erro encontrado pelos testes

Durante a integração, os testes revelaram que o `TratadorDados` devolvia colunas do tipo
`Float64` (tipo anulável do Pandas) em vez de `float64`, o que fazia três testes de
integração do dashboard falharem. A correção foi uma conversão explícita de tipo em
`_padronizar_tipos`, e o teste `test_converte_tipos_e_monta_base_mensal` passou a garantir
que o problema não volte.

## Integração contínua

O arquivo `.github/workflows/testes.yml` configura o GitHub Actions para executar o
verificador de estilo (`ruff`) e todos os testes a cada envio ao repositório.
