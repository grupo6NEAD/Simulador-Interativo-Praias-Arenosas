from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go
import numpy as np
import os

# --- DADOS E FUNÇÕES DE CLASSIFICAÇÃO ---

grain_table = {
    ">710": {"1/5": 7, "1/10": 6, "1/20": 5, "1/25": 4, "1/50": 3},
    "500-710": {"1/5": 6, "1/10": 5, "1/20": 4, "1/25": 3, "1/50": 2},
    "350-500": {"1/5": 5, "1/10": 4, "1/20": 3, "1/25": 2, "1/50": 1},
    "250-350": {"1/5": 4, "1/10": 3, "1/20": 2, "1/25": 1, "1/50": 0},
    "180-250": {"1/5": 3, "1/10": 2, "1/20": 1, "1/25": 0, "1/50": 0},
    "<180": {"1/5": 2, "1/10": 1, "1/20": 0, "1/25": 0, "1/50": 0},
}

grain_numerical_map = {
    ">710": 0.71, "500-710": 0.6, "350-500": 0.43,
    "250-350": 0.3, "180-250": 0.215, "<180": 0.15
}

wave_action_options = {0: "Praticamente ausente", 1: "Fraca", 2: "Moderada", 3: "Forte", 4: "Extremamente forte (>1,5m)"}
breaker_zone_options = {0: "Muito larga, quebra em bancos", 1: "Média", 2: "Quebra na face da praia"}
fine_sand_options = {0: "5%", 1: "2–3%", 2: "<1%"}
redox_options = {0: "0–10 cm", 1: "10–25 cm", 2: "25–50 cm", 3: "50–80 cm", 4: ">80 cm"}

def classificar_praia(escore):
    if escore <= 5:
        return "Muito Protegida"
    elif escore <= 10:
        return "Protegida"
    elif escore <= 15:
        return "Exposta"
    else:
        return "Muito Exposta"

# Definição única das três curvas de referência (usada tanto na classificação
# quanto na plotagem), para manter os dois pontos do código sempre consistentes.
# Existem apenas três classificações possíveis na aba do gráfico — uma para
# cada curva. O ponto pertence à classe da curva que estiver geometricamente
# mais próxima dele (não há categorias "Muito Protegida" / "Muito Exposta"
# nesta aba).
CURVAS_REFERENCIA = [
    {"nome": "Protegida",               "coef": 3.1, "expo": -1.1},
    {"nome": "Moderadamente Protegida", "coef": 2.1, "expo": -1.8},
    {"nome": "Exposta",                 "coef": 3.9, "expo": -1.85},
]

# Domínio visível do gráfico (usado para normalizar a distância entre eixos
# com escalas muito diferentes: x ~ [5,150] vs d ~ [0.06,1.5]).
GRAPH_X_MIN, GRAPH_X_MAX = 5, 150
GRAPH_D_MIN, GRAPH_D_MAX = 0.06, 1.5


def _curve_x(d, coef, expo):
    return coef * np.asarray(d, dtype=float) ** expo


def classificar_por_posicao(slope_x, grain_mm):
    """Classifica um ponto (slope_x, grain_mm) pela curva de referência
    geometricamente mais próxima dele.

    Calcula a distância mínima do ponto a cada uma das três curvas,
    percorrendo-as em toda a extensão do domínio visível do gráfico (as
    distâncias em x e em d são normalizadas pelos respectivos intervalos
    dos eixos, já que têm escalas muito diferentes) e retorna o nome da
    curva mais próxima. Só existem três classificações possíveis:
    "Protegida", "Moderadamente Protegida" e "Exposta".
    """
    d_amostras = np.linspace(GRAPH_D_MIN, GRAPH_D_MAX, 2000)
    x_range = GRAPH_X_MAX - GRAPH_X_MIN
    d_range = GRAPH_D_MAX - GRAPH_D_MIN

    curva_mais_proxima = None
    menor_distancia = None

    for curva in CURVAS_REFERENCIA:
        x_curva = _curve_x(d_amostras, curva["coef"], curva["expo"])
        dx = (slope_x - x_curva) / x_range
        dd = (grain_mm - d_amostras) / d_range
        distancia_min = np.sqrt(dx**2 + dd**2).min()

        if menor_distancia is None or distancia_min < menor_distancia:
            menor_distancia = distancia_min
            curva_mais_proxima = curva

    return curva_mais_proxima["nome"]

# --- APP ---
app = Dash(__name__)
server = app.server

colors = {
    'background': '#1E1E1E',
    'text': '#EAEAEA',
    'container': '#2D2D2D',
    'accent': '#4491D3',
    'border': '#444444',
    'slider_mark': '#CCCCCC',
}

main_style = {
    "backgroundColor": colors['background'],
    "color": colors['text'],
    "fontFamily": "Arial, sans-serif",
    "maxWidth": "1400px",
    "margin": "40px auto",
    "padding": "30px",
    "minHeight": "100vh",
}

tab_style = {
    "backgroundColor": colors['container'],
    "color": colors['text'],
    "border": f"1px solid {colors['border']}",
    "padding": "10px 20px",
    "borderRadius": "5px 5px 0 0",
}

tab_selected_style = {
    "backgroundColor": colors['accent'],
    "color": "#FFFFFF",
    "border": f"1px solid {colors['accent']}",
    "padding": "10px 20px",
    "borderRadius": "5px 5px 0 0",
    "fontWeight": "bold",
}

def create_input_section(label, component):
    return html.Div([
        html.Label(label, style={"fontWeight": "bold"}),
        component
    ], style={"marginBottom": "25px"})

# --- LAYOUT ---
app.layout = html.Div([
    html.H1(
        "Simulador Interativo: Classificação de Praias Arenosas",
        style={"textAlign": "center", "color": colors['accent'], "marginBottom": "8px"}
    ),
    html.P(
        "Esta ferramenta classifica o estado morfodinâmico de praias arenosas com base em parâmetros físicos e biológicos.",
        style={"textAlign": "center", "marginBottom": "30px", "color": "#BBBBBB"}
    ),

    dcc.Tabs(
        id="tabs",
        value="tab-escore",
        children=[
            # ── ABA 1: ESCORE ────────────────────────────────────────────
            dcc.Tab(
                label="📋 Parâmetros & Escore",
                value="tab-escore",
                style=tab_style,
                selected_style=tab_selected_style,
                children=[
                    html.Div([
                        # Coluna esquerda — inputs
                        html.Div([
                            html.H3("Parâmetros de Entrada", style={
                                "borderBottom": f"1px solid {colors['border']}",
                                "paddingBottom": "10px"
                            }),

                            create_input_section("1. Ação de Ondas",
                                html.Div(dcc.Slider(0, 4, step=1, value=0,
                                    marks={k: {'label': v, 'style': {'color': colors['slider_mark']}}
                                           for k, v in wave_action_options.items()},
                                    id='wave'), style={'padding': '5px 20px 0'})),

                            create_input_section("2. Zona de Arrebentação",
                                html.Div(dcc.Slider(0, 2, step=1, value=0,
                                    marks={k: {'label': v, 'style': {'color': colors['slider_mark']}}
                                           for k, v in breaker_zone_options.items()},
                                    id='breaker'), style={'padding': '5px 20px 0'})),

                            create_input_section("3. Percentual de Areia Fina",
                                html.Div(dcc.Slider(0, 2, step=1, value=0,
                                    marks={k: {'label': v, 'style': {'color': colors['slider_mark']}}
                                           for k, v in fine_sand_options.items()},
                                    id='fine'), style={'padding': '5px 20px 0'})),

                            html.Div([
                                html.H4("4. Morfologia e Sedimento", style={"marginTop": "20px"}),
                                create_input_section("4a. Tamanho do Grão (mm)",
                                    dcc.Dropdown(list(grain_table.keys()), "250-350", id='grain',
                                                 clearable=False, style={'color': 'black'})),
                                create_input_section("4b. Inclinação da Praia",
                                    dcc.Dropdown(list(grain_table[">710"].keys()), "1/20", id='slope',
                                                 clearable=False, style={'color': 'black'})),
                            ], style={"background": "#3c3c3c", "padding": "15px", "borderRadius": "5px"}),

                            create_input_section("5. Profundidade da Camada Redox (RPD)",
                                html.Div(dcc.Slider(0, 4, step=1, value=0,
                                    marks={k: {'label': v, 'style': {'color': colors['slider_mark']}}
                                           for k, v in redox_options.items()},
                                    id='redox'), style={'padding': '5px 20px 0'})),

                            create_input_section("6. Organismos Tubícolas",
                                dcc.RadioItems(
                                    id='tubicola',
                                    options=[
                                        {'label': 'Presentes', 'value': 'Presentes'},
                                        {'label': 'Ausentes',  'value': 'Ausentes'}
                                    ],
                                    value='Presentes',
                                    labelStyle={'display': 'inline-block', 'marginRight': '20px'}
                                )),
                        ], style={
                            'flex': '1', 'minWidth': '450px', 'padding': '25px',
                            'backgroundColor': colors['container'],
                            'borderRadius': '0 10px 10px 10px',
                            'border': f"1px solid {colors['border']}"
                        }),

                        # Coluna direita — resultado
                        html.Div([
                            html.Div(id='output-div', style={
                                "padding": "25px",
                                "background": colors['accent'],
                                "color": "#FFFFFF",
                                "borderRadius": "10px",
                                "textAlign": "center",
                                "fontSize": "1.3em",
                                "fontWeight": "bold",
                                "marginBottom": "20px",
                            }),

                            # Tabela de referência de pontuações
                            html.Div([
                                html.H4("Tabela de Classificação", style={"marginBottom": "12px"}),
                                html.Table([
                                    html.Thead(html.Tr([
                                        html.Th("Escore", style={"padding": "8px 16px"}),
                                        html.Th("Tipo de Praia", style={"padding": "8px 16px"}),
                                    ], style={"backgroundColor": "#3a3a3a"})),
                                    html.Tbody([
                                        html.Tr([html.Td("0 – 5",  style={"padding": "6px 16px", "textAlign": "center"}),
                                                 html.Td("Muito Protegida")]),
                                        html.Tr([html.Td("6 – 10", style={"padding": "6px 16px", "textAlign": "center"}),
                                                 html.Td("Protegida")],
                                                style={"backgroundColor": "#2a2a2a"}),
                                        html.Tr([html.Td("11 – 15", style={"padding": "6px 16px", "textAlign": "center"}),
                                                 html.Td("Exposta")]),
                                        html.Tr([html.Td("> 15",   style={"padding": "6px 16px", "textAlign": "center"}),
                                                 html.Td("Muito Exposta")],
                                                style={"backgroundColor": "#2a2a2a"}),
                                    ])
                                ], style={
                                    "width": "100%", "borderCollapse": "collapse",
                                    "border": f"1px solid {colors['border']}", "borderRadius": "8px",
                                    "overflow": "hidden"
                                })
                            ], style={
                                "padding": "20px", "backgroundColor": colors['container'],
                                "borderRadius": "10px", "border": f"1px solid {colors['border']}"
                            }),
                        ], style={'flex': '1', 'paddingLeft': '30px'}),

                    ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '30px', 'marginTop': '20px'}),
                ]
            ),

            # ── ABA 2: GRÁFICO ───────────────────────────────────────────
            dcc.Tab(
                label="📈 Gráfico",
                value="tab-grafico",
                style=tab_style,
                selected_style=tab_selected_style,
                children=[
                    html.Div([
                        # Painel de inputs livres
                        html.Div([
                            html.H3("Insira os Valores", style={
                                "borderBottom": f"1px solid {colors['border']}",
                                "paddingBottom": "10px"
                            }),

                            html.P(
                                "Digite valores contínuos para posicionar o marcador no gráfico e identificar "
                                "em qual região morfodinâmica a praia se encontra.",
                                style={"color": "#BBBBBB", "marginBottom": "25px", "lineHeight": "1.6"}
                            ),

                            html.Div([
                                html.Label("Inclinação da Praia — valor de x em 1:x",
                                           style={"fontWeight": "bold", "display": "block", "marginBottom": "6px"}),
                                html.Span("Ex: digite 20 para representar inclinação 1:20",
                                          style={"fontSize": "0.85em", "color": "#999", "display": "block", "marginBottom": "8px"}),
                                dcc.Input(
                                    id='slope-input',
                                    type='number',
                                    placeholder='Ex: 20',
                                    min=5, max=200, step=0.1,
                                    style={
                                        "width": "100%", "padding": "10px", "fontSize": "1.1em",
                                        "backgroundColor": "#3c3c3c", "color": colors['text'],
                                        "border": f"1px solid {colors['border']}", "borderRadius": "6px",
                                        "boxSizing": "border-box"
                                    }
                                ),
                            ], style={"marginBottom": "25px"}),

                            html.Div([
                                html.Label("Diâmetro Médio do Grão (mm)",
                                           style={"fontWeight": "bold", "display": "block", "marginBottom": "6px"}),
                                html.Span("Ex: 0.35 para areia média",
                                          style={"fontSize": "0.85em", "color": "#999", "display": "block", "marginBottom": "8px"}),
                                dcc.Input(
                                    id='grain-input',
                                    type='number',
                                    placeholder='Ex: 0.35',
                                    min=0.06, max=2.0, step=0.01,
                                    style={
                                        "width": "100%", "padding": "10px", "fontSize": "1.1em",
                                        "backgroundColor": "#3c3c3c", "color": colors['text'],
                                        "border": f"1px solid {colors['border']}", "borderRadius": "6px",
                                        "boxSizing": "border-box"
                                    }
                                ),
                            ], style={"marginBottom": "30px"}),

                            # Card de resultado da classificação pelo gráfico
                            html.Div(id='graph-classification', style={
                                "padding": "18px",
                                "background": "#3c3c3c",
                                "borderRadius": "8px",
                                "border": f"1px solid {colors['border']}",
                                "textAlign": "center",
                                "fontSize": "1.05em",
                                "minHeight": "60px",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                            }),

                            # Referência de tamanho de grão
                            html.Div([
                                html.H4("Referência: Escala de Wentworth", style={"marginBottom": "10px"}),
                                html.Table([
                                    html.Thead(html.Tr([
                                        html.Th("Diâmetro (mm)", style={"padding": "6px 12px"}),
                                        html.Th("Classificação",  style={"padding": "6px 12px"}),
                                    ], style={"backgroundColor": "#3a3a3a"})),
                                    html.Tbody([
                                        html.Tr([html.Td("> 0,710", style={"padding": "5px 12px", "textAlign": "center"}), html.Td("Areia muito grossa")]),
                                        html.Tr([html.Td("0,500 – 0,710", style={"padding": "5px 12px", "textAlign": "center"}), html.Td("Areia grossa")], style={"backgroundColor": "#2a2a2a"}),
                                        html.Tr([html.Td("0,350 – 0,500", style={"padding": "5px 12px", "textAlign": "center"}), html.Td("Areia média")]),
                                        html.Tr([html.Td("0,250 – 0,350", style={"padding": "5px 12px", "textAlign": "center"}), html.Td("Areia média")], style={"backgroundColor": "#2a2a2a"}),
                                        html.Tr([html.Td("0,180 – 0,250", style={"padding": "5px 12px", "textAlign": "center"}), html.Td("Areia fina")]),
                                        html.Tr([html.Td("< 0,180", style={"padding": "5px 12px", "textAlign": "center"}), html.Td("Areia muito fina")], style={"backgroundColor": "#2a2a2a"}),
                                    ])
                                ], style={
                                    "width": "100%", "borderCollapse": "collapse",
                                    "border": f"1px solid {colors['border']}", "fontSize": "0.88em"
                                })
                            ], style={
                                "marginTop": "30px", "padding": "15px",
                                "backgroundColor": colors['container'],
                                "borderRadius": "8px", "border": f"1px solid {colors['border']}"
                            }),

                        ], style={
                            'flex': '1', 'minWidth': '320px', 'maxWidth': '400px',
                            'padding': '25px', 'backgroundColor': colors['container'],
                            'borderRadius': '0 10px 10px 10px',
                            'border': f"1px solid {colors['border']}"
                        }),

                        # Gráfico
                        html.Div([
                            dcc.Graph(id='morpho-graph', style={'height': '80vh'})
                        ], style={'flex': '2', 'paddingLeft': '30px'}),

                    ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '30px', 'marginTop': '20px'}),
                ]
            ),
        ],
        style={"marginBottom": "0"},
        colors={"border": colors['border'], "primary": colors['accent'], "background": colors['background']},
    ),

], style=main_style)


# --- CALLBACK: ABA ESCORE ---
@app.callback(
    Output('output-div', 'children'),
    [Input(i, 'value') for i in ['wave', 'breaker', 'fine', 'grain', 'slope', 'redox', 'tubicola']]
)
def update_escore(wave, breaker, fine, grain, slope, redox, tubicola):
    score4 = grain_table.get(grain, {}).get(slope, 0)
    tubicola_score = 1 if tubicola == 'Ausentes' else 0
    total_score = wave + breaker + fine + score4 + redox + tubicola_score
    tipo_praia = classificar_praia(total_score)

    return [
        html.Div(f"Escore Total: {total_score}", style={"fontSize": "1.4em", "marginBottom": "8px"}),
        html.Div(f"Tipo de Praia: {tipo_praia}", style={"fontSize": "1.1em", "opacity": "0.9"}),
    ]


# --- CALLBACK: ABA GRÁFICO ---
@app.callback(
    Output('morpho-graph', 'figure'),
    Output('graph-classification', 'children'),
    Input('slope-input', 'value'),
    Input('grain-input', 'value'),
)
def update_graph(slope_x, grain_mm):
    fig = go.Figure()
    d_range = np.linspace(0.06, 1.5, 500)

    curves = {
        "Protegida": {
            "func": lambda d: 3.1 * d**-1.1,
            "color": "#33C3F0",
            "formula": "x = 3,1·d⁻¹·¹"
        },
        "Moderadamente Protegida": {
            "func": lambda d: 2.1 * d**-1.8,
            "color": "#39E991",
            "formula": "x = 2,1·d⁻¹·⁸"
        },
        "Exposta": {
            "func": lambda d: 3.9 * d**-1.85,
            "color": "#E95D39",
            "formula": "x = 3,9·d⁻¹·⁸⁵"
        },
    }

    for name, props in curves.items():
        x_vals = props["func"](d_range)
        mask = (x_vals >= 5) & (x_vals <= 200)
        fig.add_trace(go.Scatter(
            x=x_vals[mask], y=d_range[mask],
            mode='lines',
            name=f'{name} ({props["formula"]})',
            line=dict(color=props["color"], width=2)
        ))

    # Marcador do aluno
    classification_text = html.Span("Insira os valores para ver a classificação.",
                                    style={"color": "#999"})

    # Limites do domínio visível do gráfico
    X_MIN, X_MAX = 5, 150
    D_MIN, D_MAX = 0.06, 1.5

    # Cores por classificação — mesmas cores usadas para cada curva no gráfico
    class_colors = {
        "Protegida": "#33C3F0",
        "Moderadamente Protegida": "#39E991",
        "Exposta": "#E95D39",
    }

    if slope_x is not None and grain_mm is not None:
        try:
            sx = float(slope_x)
            gm = float(grain_mm)
            if sx > 0 and gm > 0:
                # Verifica se está dentro do domínio do gráfico
                fora_dominio = sx < X_MIN or sx > X_MAX or gm < D_MIN or gm > D_MAX

                fig.add_trace(go.Scatter(
                    x=[sx], y=[gm],
                    mode='markers',
                    name='Sua Seleção',
                    marker=dict(color='#FFD700', size=16, symbol='star',
                                line=dict(color='white', width=1))
                ))

                if fora_dominio:
                    classification_text = [
                        html.Div("⚠️ Ponto fora do domínio do gráfico",
                                 style={"fontWeight": "bold", "color": "#E9A039", "marginBottom": "6px"}),
                        html.Div(
                            f"Os valores inseridos (1:{sx}, {gm} mm) estão fora da janela representada "
                            f"(inclinação 1:{X_MIN}–1:{X_MAX}, grão {D_MIN}–{D_MAX} mm). "
                            "Tente valores dentro desses limites.",
                            style={"fontSize": "0.88em", "color": "#BBBBBB", "lineHeight": "1.5"}
                        ),
                    ]
                else:
                    tipo = classificar_por_posicao(sx, gm)
                    card_color = class_colors.get(tipo, colors['accent'])
                    classification_text = [
                        html.Div("Classificação pelo Gráfico",
                                 style={"fontWeight": "bold", "marginBottom": "6px"}),
                        html.Div(tipo, style={"fontSize": "1.2em", "color": card_color}),
                        html.Div(f"Inclinação 1:{sx}  |  Grão {gm} mm",
                                 style={"fontSize": "0.85em", "color": "#999", "marginTop": "6px"}),
                    ]
        except (ValueError, TypeError):
            pass

    fig.update_layout(
        title="Classificação Morfodinâmica da Praia",
        xaxis_title="Inclinação da Praia (1:x)",
        yaxis_title="Diâmetro Médio do Grão (mm)",
        xaxis=dict(range=[5, 150], title_font=dict(size=13)),
        yaxis=dict(range=[0.06, 1.5], title_font=dict(size=13)),
        legend=dict(font=dict(size=10), yanchor="top", y=0.99, xanchor="right", x=0.99),
        margin=dict(l=50, r=40, t=50, b=50),
        template='plotly_dark',
        plot_bgcolor='#1a1a2e',
        paper_bgcolor='#1E1E1E',
    )

    return fig, classification_text


# --- EXECUÇÃO ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
