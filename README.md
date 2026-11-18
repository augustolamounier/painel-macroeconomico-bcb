# Inflação, juros e câmbio no Brasil

Sistema de análise de dados e dashboard interativo com dados abertos do Banco Central do
Brasil, desenvolvido em Python com Programação Orientada a Objetos, Pandas, Plotly e Streamlit.

Projeto final da disciplina de Programação Orientada a Objetos — Ciência de Dados e
Inteligência Artificial.

![Tela do dashboard](docs/img/dashboard.png)

**Documentação completa:** <https://augustolamounier.github.io/painel-macroeconomico-bcb/>

## O problema

> A inflação brasileira tem ficado dentro da meta? O que explica os períodos em que ela
> escapou, como os juros reagiram e quanto isso custou em poder de compra?

O painel consulta a API pública de séries temporais do Banco Central (SGS), trata os dados e
responde a seis perguntas:

1. A inflação tem ficado dentro da meta? Em que períodos estourou o teto?
2. Quais grupos de consumo mais encareceram?
3. Como a Selic reagiu à inflação? O juro real foi positivo?
4. A alta do dólar anda junto com a inflação?
5. Quanto poder de compra o real perdeu desde 2000?
6. Existe padrão sazonal na inflação?

## Como abrir o painel

> **Importante:** `localhost` significa "este computador". O endereço
> `http://localhost:8501` só funciona **depois** que você roda o painel na sua máquina com os
> comandos abaixo, e só enquanto a janela do terminal continuar aberta. Clicar nele direto
> aqui no GitHub não abre nada.

Requer **Python 3.11 ou mais recente**. Para conferir a versão: `python --version` (no Mac:
`python3 --version`).

Os comandos abaixo não exigem "ativar" o ambiente virtual, o que evita o erro de permissão do
PowerShell no Windows.

### Windows (Prompt de Comando ou PowerShell)

```bat
git clone https://github.com/augustolamounier/painel-macroeconomico-bcb.git
cd painel-macroeconomico-bcb
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```

### macOS e Linux

```bash
git clone https://github.com/augustolamounier/painel-macroeconomico-bcb.git
cd painel-macroeconomico-bcb
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Na primeira vez, a instalação leva alguns minutos. Quando o terminal mostrar
`Local URL: http://localhost:8501`, o navegador abre sozinho; se não abrir, copie esse endereço
para o navegador. Para fechar o painel, volte ao terminal e aperte `Ctrl + C`.

Nas próximas vezes, basta entrar na pasta do projeto e rodar só a última linha.

### Se não abrir

| Sintoma | Causa | Solução |
|---|---|---|
| "Não é possível acessar esse site" ao clicar no link | O painel não está rodando | Rode os comandos acima e deixe o terminal aberto |
| `No matching distribution found for pandas` | Python mais antigo que 3.11 | Instale o Python 3.12 ou mais recente em [python.org](https://www.python.org/downloads/) |
| `'python' não é reconhecido` (Windows) | Python fora do PATH | Troque `python` por `py` no terceiro comando, ou reinstale marcando *Add python.exe to PATH* |
| `'streamlit' não é reconhecido` | Ambiente virtual não ativado | Use os comandos com `python -m streamlit`, como acima |
| `Port 8501 is already in use` | Outro painel aberto | Feche o outro terminal ou rode `... -m streamlit run app.py --server.port 8502` e abra `http://localhost:8502` |
| O terminal para em `Email:` | Versão antiga deste repositório | Atualize com `git pull` (ou apenas aperte Enter) |

O painel consulta a API do Banco Central a cada seis horas; se a API não responder, usa a
cópia local dos dados em `data/raw/`.

### Outros comandos

| Comando (com o ambiente do projeto) | O que faz |
|---|---|
| `python -m streamlit run app.py` | Abre o dashboard |
| `python scripts/atualizar_dados.py` | Baixa as séries e atualiza a pasta `data/` |
| `python -m pytest` | Executa os testes (requer `pip install -r requirements-dev.txt`) |
| `python -m mkdocs serve` | Abre a documentação localmente |

Para abrir o painel sem internet, usando só a cópia local, defina a variável `PAINEL_FONTE=csv`
antes de rodar (Windows/PowerShell: `$env:PAINEL_FONTE="csv"`; macOS/Linux:
`export PAINEL_FONTE=csv`).

## O que o dashboard tem

- **Cabeçalho** com a fonte, o período coberto e o horário da atualização.
- **Dez indicadores (KPIs):** IPCA em 12 meses, desvio da meta, Selic, juro real, inflação
  acumulada, poder de compra, meses acima do teto, variação do dólar, desocupação e o grupo
  que mais encareceu.
- **Filtros interativos:** período, grupos do IPCA e variável comparada à inflação.
- **Nove gráficos Plotly:** linhas, barras, setores, dispersão, boxplot e mapa de calor.
- **Tabela de dados** com escolha de colunas, ordenação e download em CSV.
- **Análise interpretativa** gerada a partir dos números do período selecionado.

## Arquitetura

O código fica no pacote `painel_macro`, em que cada classe tem uma única responsabilidade:

```text
FonteDados ──► PipelineDados ──► TratadorDados ──► AnalisadorDados ──┬─► PainelIndicadores ─┐
(API ou CSV)                                                         ├─► GaleriaGraficos ───┼─► Dashboard
                                                                     └─► GeradorInterpretacao┘
```

| Classe | Responsabilidade |
|---|---|
| `FonteDados` *(abstrata)* → `FonteDadosSGS`, `FonteDadosCSV`, `FonteDadosComCache` | Gerenciar a origem dos dados |
| `TratadorDados` | Converter tipos, remover duplicidades e tratar valores ausentes |
| `AnalisadorDados` | Filtrar, agrupar, ordenar e calcular estatísticas |
| `Indicador` *(abstrata)* → sete subclasses | Representar os indicadores calculados |
| `Visualizador` *(abstrata)* → seis subclasses | Gerar os gráficos |
| `Dashboard` | Organizar os componentes do painel |

Conceitos de POO aplicados: classes abstratas, herança (três hierarquias), polimorfismo,
encapsulamento com `@property` e os cinco princípios SOLID. O detalhamento, com diagrama de
classes, está na [documentação](https://augustolamounier.github.io/painel-macroeconomico-bcb/arquitetura/).

## Estrutura do repositório

```text
├── app.py                 # ponto de entrada do dashboard
├── painel_macro/          # classes do sistema
├── scripts/               # atualização dos dados, notebook e gráficos da documentação
├── notebooks/             # análise exploratória dos dados
├── data/raw/              # cópia dos dados brutos (um CSV por série)
├── data/processed/        # base mensal tratada
├── tests/                 # 77 testes automatizados
├── docs/                  # fonte da documentação (publicada no branch gh-pages)
├── requirements.txt       # dependências do painel
└── requirements-dev.txt   # dependências de testes e documentação
```

## Fonte dos dados

[Banco Central do Brasil — Sistema Gerenciador de Séries Temporais (SGS)](https://dadosabertos.bcb.gov.br/),
pela API `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados`. Séries utilizadas:
433, 13522, 4189, 3698, 24369, 24363, 13521 e 1635 a 1643. O IPCA e a taxa de desocupação são
produzidos pelo IBGE e redistribuídos pelo Banco Central.

## Testes

```bash
pip install -r requirements-dev.txt
pytest --cov=painel_macro
```

São 77 testes (unitários e de integração), com 95% de cobertura. Eles não acessam a internet.

## Autor

Augusto Lamounier
