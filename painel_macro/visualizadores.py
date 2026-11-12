"""Gráficos interativos (Plotly).

``Visualizador`` é a classe base: ela define o método público ``gerar``
(padrão *Template Method*), que valida os dados, delega o desenho ao método
abstrato ``_construir`` e aplica o tema visual. Cada tipo de gráfico é uma
subclasse que implementa apenas ``_construir``.

Os visualizadores recebem tabelas já preparadas pelo ``AnalisadorDados``:
eles só desenham, não calculam.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Paleta "Porcelana". As três cores de série foram escolhidas por simulação de
# daltonismo (protanopia, deuteranopia e tritanopia): o pior par mantém
# diferença perceptível (ΔE OKLab ≥ 8) e todas têm contraste ≥ 3:1 com o fundo.
JADE = "#1F6B57"
LATAO = "#B8862B"
AMEIXA = "#6B4C9A"
ARDOSIA = "#2E4A7A"
VINHO = "#9B2C3A"
CINZA = "#A8A398"
CINZA_CLARO = "#E4E0D8"
NEUTRO = "#F0EEE9"


@dataclass(frozen=True)
class TemaGrafico:
    """Aparência comum a todos os gráficos do painel."""

    fundo: str = "#FBFAF7"
    texto: str = "#16181B"
    texto_secundario: str = "#5F656D"
    grade: str = "#ECE9E3"
    fonte: str = (
        "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', 'Segoe UI', "
        "system-ui, sans-serif"
    )
    altura: int = 420
    cores_series: tuple[str, ...] = field(
        default=(JADE, LATAO, AMEIXA)
    )

    def aplicar(self, figura: go.Figure, titulo: str, subtitulo: str = "") -> go.Figure:
        """Aplica título, cores, fontes e eixos padronizados à figura."""
        tem_legenda = figura.layout.showlegend is not False
        margem_extra = figura.layout.margin.t or 0
        margem_superior = 56 + (22 if subtitulo else 0) + (30 if tem_legenda else 0)
        figura.update_layout(
            title={
                "text": titulo,
                "subtitle": {"text": subtitulo, "font": {"color": self.texto_secundario,
                                                         "size": 13}},
                "x": 0, "xref": "container", "xanchor": "left",
                "y": 1, "yref": "container", "yanchor": "top",
                "pad": {"l": 10, "t": 12},
                "font": {"size": 17, "color": self.texto},
            },
            font={"family": self.fonte, "color": self.texto, "size": 13},
            paper_bgcolor=self.fundo,
            plot_bgcolor=self.fundo,
            height=figura.layout.height or self.altura,
            margin={"l": 10, "r": 20, "t": margem_superior + margem_extra, "b": 10},
            separators=",.",
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.01,
                    "xanchor": "left", "x": 0},
            hoverlabel={"font": {"family": self.fonte, "size": 13}},
            barcornerradius=4,
        )
        figura.update_xaxes(showgrid=False, linecolor=self.grade, automargin=True,
                            zerolinecolor=CINZA_CLARO,
                            tickfont={"color": self.texto_secundario},
                            title_font={"color": self.texto_secundario})
        figura.update_yaxes(gridcolor=self.grade, zerolinecolor=CINZA_CLARO, automargin=True,
                            tickfont={"color": self.texto_secundario},
                            title_font={"color": self.texto_secundario})
        return figura


class Visualizador(ABC):
    """Classe base dos gráficos do painel."""

    def __init__(self, titulo: str, subtitulo: str = "", tema: TemaGrafico | None = None) -> None:
        self._titulo = titulo
        self._subtitulo = subtitulo
        self._tema = tema or TemaGrafico()

    @property
    def titulo(self) -> str:
        return self._titulo

    @property
    def tipo(self) -> str:
        """Nome do tipo de gráfico (o nome da subclasse)."""
        return type(self).__name__

    def gerar(self, dados: pd.DataFrame) -> go.Figure:
        """Gera a figura; devolve um aviso visual se não houver dados."""
        if dados is None or dados.empty:
            return self._figura_sem_dados()
        figura = self._construir(dados)
        return self._tema.aplicar(figura, self._titulo, self._subtitulo)

    @abstractmethod
    def _construir(self, dados: pd.DataFrame) -> go.Figure:
        """Desenha o gráfico propriamente dito (implementado pelas subclasses)."""

    def _figura_sem_dados(self) -> go.Figure:
        figura = go.Figure()
        figura.add_annotation(
            text="Não há dados para o filtro selecionado.", showarrow=False,
            xref="paper", yref="paper", x=0.5, y=0.5,
            font={"size": 15, "color": self._tema.texto_secundario},
        )
        figura.update_xaxes(visible=False)
        figura.update_yaxes(visible=False)
        return self._tema.aplicar(figura, self._titulo, self._subtitulo)


class GraficoLinhas(Visualizador):
    """Séries temporais em linhas, com faixa de referência opcional."""

    def __init__(
        self,
        titulo: str,
        series: dict[str, str],
        subtitulo: str = "",
        titulo_eixo_y: str = "",
        sufixo: str = "%",
        faixa: tuple[str, str, str] | None = None,
        linha_referencia: tuple[str, str] | None = None,
        rotular_ultimo: bool = True,
        tema: TemaGrafico | None = None,
    ) -> None:
        """
        ``series`` mapeia coluna → nome exibido. ``faixa`` é a tupla
        (coluna inferior, coluna superior, nome) e ``linha_referencia`` é
        (coluna, nome) de uma série desenhada como linha tracejada neutra.
        """
        super().__init__(titulo, subtitulo, tema)
        if not series:
            raise ValueError("Informe ao menos uma série para o gráfico de linhas.")
        if len(series) > len(self._tema.cores_series):
            raise ValueError(
                f"O gráfico de linhas aceita no máximo {len(self._tema.cores_series)} séries."
            )
        self._series = dict(series)
        self._titulo_eixo_y = titulo_eixo_y
        self._sufixo = sufixo
        self._faixa = faixa
        self._linha_referencia = linha_referencia
        self._rotular_ultimo = rotular_ultimo

    def _construir(self, dados: pd.DataFrame) -> go.Figure:
        figura = go.Figure()
        modelo = f"%{{y:,.2f}}{self._sufixo}"
        if self._faixa:
            self._desenhar_faixa(figura, dados, modelo)
        if self._linha_referencia:
            coluna, nome = self._linha_referencia
            figura.add_trace(go.Scatter(
                x=dados.index, y=dados[coluna], name=nome, mode="lines",
                line={"color": CINZA, "width": 1.5, "dash": "dash", "shape": "hv"},
                hovertemplate=modelo,
            ))
        for (coluna, nome), cor in zip(self._series.items(), self._tema.cores_series):
            serie = dados[coluna]
            figura.add_trace(go.Scatter(
                x=serie.index, y=serie, name=nome, mode="lines",
                line={"color": cor, "width": 2}, hovertemplate=modelo,
            ))
            if self._rotular_ultimo:
                self._rotular_ponto_final(figura, serie, cor)
        figura.update_layout(hovermode="x unified", showlegend=self._tem_legenda())
        figura.update_xaxes(hoverformat="%m/%Y", tickformat=self._formato_datas(dados.index))
        figura.update_yaxes(title_text=self._titulo_eixo_y,
                            ticksuffix=self._sufixo if self._sufixo == "%" else "")
        return figura

    def _desenhar_faixa(self, figura: go.Figure, dados: pd.DataFrame, modelo: str) -> None:
        inferior, superior, nome = self._faixa
        figura.add_trace(go.Scatter(
            x=dados.index, y=dados[inferior], mode="lines", line={"width": 0, "shape": "hv"},
            showlegend=False, hoverinfo="skip",
        ))
        figura.add_trace(go.Scatter(
            x=dados.index, y=dados[superior], mode="lines", line={"width": 0, "shape": "hv"},
            fill="tonexty", fillcolor="rgba(168, 163, 152, 0.22)", name=nome,
            customdata=dados[inferior],
            hovertemplate="%{customdata:,.2f}% a %{y:,.2f}%",
        ))

    def _rotular_ponto_final(self, figura: go.Figure, serie: pd.Series, cor: str) -> None:
        validos = serie.dropna()
        if validos.empty:
            return
        valor = validos.iloc[-1]
        texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        figura.add_trace(go.Scatter(
            x=[validos.index[-1]], y=[valor], mode="markers+text",
            marker={"color": cor, "size": 8, "line": {"color": self._tema.fundo, "width": 2}},
            text=[f"{texto}{self._sufixo}"], textposition="middle right",
            textfont={"color": self._tema.texto, "size": 12},
            cliponaxis=False, showlegend=False, hoverinfo="skip",
        ))

    def _tem_legenda(self) -> bool:
        return len(self._series) > 1 or bool(self._faixa) or bool(self._linha_referencia)

    @staticmethod
    def _formato_datas(indice: pd.DatetimeIndex) -> str:
        anos = (indice.max() - indice.min()).days / 365.25
        return "%m/%Y" if anos <= 4 else "%Y"


class GraficoBarras(Visualizador):
    """Barras verticais ou horizontais, com cores por categoria opcionais."""

    def __init__(
        self,
        titulo: str,
        categoria: str,
        valor: str,
        subtitulo: str = "",
        horizontal: bool = False,
        sufixo: str = "%",
        casas: int = 1,
        nome_serie: str = "",
        coluna_cor: str | None = None,
        mapa_cores: dict[str, str] | None = None,
        marcador: tuple[str, str] | None = None,
        referencia: tuple[float, str] | None = None,
        mostrar_valores: bool = True,
        tema: TemaGrafico | None = None,
    ) -> None:
        """
        ``coluna_cor`` + ``mapa_cores`` pintam cada barra conforme uma
        categoria; ``marcador`` é (coluna, nome) de um valor de comparação
        desenhado sobre cada barra; ``referencia`` é (valor, texto) de uma
        linha que atravessa o gráfico.
        """
        super().__init__(titulo, subtitulo, tema)
        self._categoria = categoria
        self._valor = valor
        self._horizontal = horizontal
        self._sufixo = sufixo
        self._casas = casas
        self._nome_serie = nome_serie
        self._coluna_cor = coluna_cor
        self._mapa_cores = mapa_cores or {}
        self._marcador = marcador
        self._referencia = referencia
        self._mostrar_valores = mostrar_valores

    def _construir(self, dados: pd.DataFrame) -> go.Figure:
        figura = go.Figure()
        if self._coluna_cor:
            for categoria, cor in self._mapa_cores.items():
                parte = dados[dados[self._coluna_cor] == categoria]
                if not parte.empty:
                    figura.add_trace(self._barras(parte, cor, categoria))
        else:
            figura.add_trace(self._barras(dados, self._tema.cores_series[0], self._nome_serie))
        if self._marcador:
            self._desenhar_marcador(figura, dados)
        if self._referencia:
            self._desenhar_referencia(figura)

        eixo_valor = figura.update_xaxes if self._horizontal else figura.update_yaxes
        eixo_categoria = figura.update_yaxes if self._horizontal else figura.update_xaxes
        eixo_valor(ticksuffix=self._sufixo, showgrid=True, gridcolor=self._tema.grade)
        eixo_categoria(type="category", showgrid=False,
                       categoryorder="array", categoryarray=list(dados[self._categoria]))
        if self._horizontal:
            figura.update_yaxes(autorange="reversed")
        figura.update_layout(
            bargap=0.3, showlegend=bool(self._coluna_cor or self._marcador), barmode="overlay",
        )
        return figura

    def _barras(self, dados: pd.DataFrame, cor: str, nome: str) -> go.Bar:
        categorias, valores = dados[self._categoria], dados[self._valor]
        formato = f",.{self._casas}f"
        eixo = "x" if self._horizontal else "y"
        return go.Bar(
            x=valores if self._horizontal else categorias,
            y=categorias if self._horizontal else valores,
            orientation="h" if self._horizontal else "v",
            name=nome, marker={"color": cor},
            texttemplate=f"%{{{eixo}:{formato}}}{self._sufixo}" if self._mostrar_valores else None,
            textposition="outside", cliponaxis=False,
            textfont={"size": 11, "color": self._tema.texto_secundario},
            hovertemplate=f"%{{{'y' if self._horizontal else 'x'}}}: "
                          f"%{{{eixo}:,.2f}}{self._sufixo}<extra>{nome}</extra>",
        )

    def _desenhar_marcador(self, figura: go.Figure, dados: pd.DataFrame) -> None:
        """Desenha o valor de comparação como uma linha em degraus sobre as barras."""
        coluna, nome = self._marcador
        categorias, valores = dados[self._categoria], dados[coluna]
        figura.add_trace(go.Scatter(
            x=valores if self._horizontal else categorias,
            y=categorias if self._horizontal else valores,
            name=nome, mode="lines",
            line={"color": self._tema.texto, "width": 1.5,
                  "shape": "vhv" if self._horizontal else "hvh"},
            hovertemplate=f"{nome}: %{{{'x' if self._horizontal else 'y'}:,.2f}}"
                          f"{self._sufixo}<extra></extra>",
        ))

    def _desenhar_referencia(self, figura: go.Figure) -> None:
        valor, texto = self._referencia
        estilo = {"line_color": self._tema.texto, "line_width": 1.5, "line_dash": "dash",
                  "annotation_text": f" {texto}",
                  "annotation_font": {"size": 12, "color": self._tema.texto}}
        if self._horizontal:
            figura.add_vline(x=valor, annotation_position="bottom right", **estilo)
        else:
            figura.add_hline(y=valor, annotation_position="top left", **estilo)


class GraficoSetores(Visualizador):
    """Gráfico de setores (rosca) para mostrar a composição de um total."""

    def __init__(
        self,
        titulo: str,
        rotulos: str,
        valores: str,
        subtitulo: str = "",
        mapa_cores: dict[str, str] | None = None,
        unidade_valor: str = "meses",
        tema: TemaGrafico | None = None,
    ) -> None:
        super().__init__(titulo, subtitulo, tema)
        self._rotulos = rotulos
        self._valores = valores
        self._mapa_cores = mapa_cores or {}
        self._unidade_valor = unidade_valor

    def _construir(self, dados: pd.DataFrame) -> go.Figure:
        dados = dados[dados[self._valores] > 0]
        cores = [self._mapa_cores.get(rotulo, CINZA) for rotulo in dados[self._rotulos]]
        figura = go.Figure(go.Pie(
            labels=dados[self._rotulos], values=dados[self._valores], hole=0.55, sort=False,
            direction="clockwise",
            marker={"colors": cores, "line": {"color": self._tema.fundo, "width": 2}},
            texttemplate="%{percent:.1%}", textposition="auto",
            insidetextfont={"color": "#ffffff", "size": 13},
            outsidetextfont={"color": self._tema.texto, "size": 13},
            hovertemplate=f"%{{label}}: %{{value}} {self._unidade_valor} "
                          "(%{percent:.1%})<extra></extra>",
        ))
        total = int(dados[self._valores].sum())
        figura.add_annotation(
            text=f"<b>{total}</b><br>{self._unidade_valor}", showarrow=False,
            font={"size": 16, "color": self._tema.texto},
        )
        figura.update_layout(showlegend=True, margin={"t": 16})
        return figura


class GraficoDispersao(Visualizador):
    """Dispersão entre duas variáveis, com reta de tendência opcional."""

    def __init__(
        self,
        titulo: str,
        x: str,
        y: str,
        rotulo_x: str,
        rotulo_y: str,
        subtitulo: str = "",
        sufixo_x: str = "%",
        sufixo_y: str = "%",
        tendencia: bool = True,
        tema: TemaGrafico | None = None,
    ) -> None:
        super().__init__(titulo, subtitulo, tema)
        self._x, self._y = x, y
        self._rotulo_x, self._rotulo_y = rotulo_x, rotulo_y
        self._sufixo_x, self._sufixo_y = sufixo_x, sufixo_y
        self._tendencia = tendencia

    def gerar(self, dados: pd.DataFrame) -> go.Figure:
        pares = dados[[self._x, self._y]].dropna() if dados is not None else dados
        return super().gerar(pares)

    def _construir(self, dados: pd.DataFrame) -> go.Figure:
        figura = go.Figure(go.Scatter(
            x=dados[self._x], y=dados[self._y], mode="markers", name="Meses",
            marker={"color": JADE, "size": 8, "opacity": 0.6,
                    "line": {"color": self._tema.fundo, "width": 1}},
            customdata=dados.index.strftime("%m/%Y"),
            hovertemplate=(
                "%{customdata}<br>"
                f"{self._rotulo_x}: %{{x:,.2f}}{self._sufixo_x}<br>"
                f"{self._rotulo_y}: %{{y:,.2f}}{self._sufixo_y}<extra></extra>"
            ),
        ))
        if self._tendencia and len(dados) >= 3 and dados[self._x].nunique() > 1:
            inclinacao, intercepto = np.polyfit(dados[self._x], dados[self._y], deg=1)
            extremos = np.array([dados[self._x].min(), dados[self._x].max()])
            correlacao = dados[self._x].corr(dados[self._y])
            figura.add_trace(go.Scatter(
                x=extremos, y=inclinacao * extremos + intercepto, mode="lines",
                name=f"Tendência linear (r = {correlacao:.2f})".replace(".", ","),
                line={"color": LATAO, "width": 2.5}, hoverinfo="skip",
            ))
        figura.update_xaxes(title_text=self._rotulo_x, ticksuffix=self._sufixo_x,
                            showgrid=True, gridcolor=self._tema.grade)
        figura.update_yaxes(title_text=self._rotulo_y, ticksuffix=self._sufixo_y)
        figura.update_layout(showlegend=self._tendencia)
        return figura


class GraficoBoxplot(Visualizador):
    """Boxplots horizontais para comparar distribuições entre categorias."""

    def __init__(
        self,
        titulo: str,
        categoria: str,
        valor: str,
        subtitulo: str = "",
        sufixo: str = "%",
        tema: TemaGrafico | None = None,
    ) -> None:
        super().__init__(titulo, subtitulo, tema)
        self._categoria = categoria
        self._valor = valor
        self._sufixo = sufixo

    def _construir(self, dados: pd.DataFrame) -> go.Figure:
        ordem = (
            dados.groupby(self._categoria)[self._valor].median()
            .sort_values(ascending=False).index.tolist()
        )
        figura = go.Figure(go.Box(
            x=dados[self._valor], y=dados[self._categoria], orientation="h",
            marker={"color": JADE, "size": 4, "opacity": 0.55},
            line={"color": JADE, "width": 1.5}, fillcolor="rgba(31, 107, 87, 0.14)",
            boxpoints="outliers", name="", hoverinfo="x",
        ))
        figura.update_yaxes(categoryorder="array", categoryarray=ordem, autorange="reversed",
                            showgrid=False)
        figura.update_xaxes(ticksuffix=self._sufixo, showgrid=True, gridcolor=self._tema.grade,
                            zeroline=True)
        figura.update_layout(showlegend=False)
        return figura


class GraficoMapaCalor(Visualizador):
    """Mapa de calor de uma tabela (linhas × colunas) com escala divergente."""

    def __init__(
        self,
        titulo: str,
        subtitulo: str = "",
        sufixo: str = "%",
        rotulo_valor: str = "Valor",
        tema: TemaGrafico | None = None,
    ) -> None:
        super().__init__(titulo, subtitulo, tema)
        self._sufixo = sufixo
        self._rotulo_valor = rotulo_valor

    def _construir(self, dados: pd.DataFrame) -> go.Figure:
        # O limite da escala ignora os 2% de valores mais extremos, para que
        # meses excepcionais não "apaguem" as cores dos demais.
        limite = float(np.nanquantile(np.abs(dados.to_numpy(dtype=float)), 0.98))
        figura = go.Figure(go.Heatmap(
            z=dados.to_numpy(dtype=float), x=list(dados.columns),
            y=[str(indice) for indice in dados.index],
            colorscale=[[0.0, ARDOSIA], [0.5, NEUTRO], [1.0, VINHO]],
            zmid=0, zmin=-limite, zmax=limite, xgap=2, ygap=2,
            colorbar={"ticksuffix": self._sufixo, "thickness": 12, "outlinewidth": 0},
            hovertemplate=f"%{{x}}/%{{y}}<br>{self._rotulo_valor}: "
                          f"%{{z:,.2f}}{self._sufixo}<extra></extra>",
            hoverongaps=False,
        ))
        figura.update_yaxes(autorange="reversed", type="category", showgrid=False)
        figura.update_xaxes(side="top", showgrid=False)
        figura.update_layout(height=max(self._tema.altura, 22 * len(dados) + 150),
                             margin={"t": 26}, showlegend=False)
        return figura
