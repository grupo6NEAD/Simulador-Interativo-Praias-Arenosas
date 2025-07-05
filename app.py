from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os

app = Dash(__name__)
server = app.server

# Tabela de pontuação combinada para tamanho do grão e inclinação
grain_table = {
    ">710": {"1/5": 5, "1/10": 4, "1/20": 3, "1/25": 2, "1/50": 1},
    "500-710": {"1/5": 4, "1/10": 4, "1/20": 3, "1/25": 2, "1/50": 1},
    "350-500": {"1/5": 3, "1/10": 3, "1/20": 3, "1/25": 2, "1/50": 1},
    "250-350": {"1/5": 2, "1/10": 2, "1/20": 2, "1/25": 2, "1/50": 1},
    "180-250": {"1/5": 1, "1/10": 1, "1/20": 1, "1/25": 1, "1/50": 1},
    "<180": {"1/5": 1, "1/10": 1, "1/20": 1, "1/25": 1, "1/50": 1},
}
slope_map = {"1/5": "1/5", "1/10": "1/10", "1/20": "1/20", "1/25": "1/25", "1/50": "1/50"}

def classificar_praia(escore):
    if escore <= 5:
        return "Muito Protegida"
    elif escore <= 10:
        return "Protegida"
    elif escore <= 15:
        return "Exposta"
    else:
        return "Muito Exposta"

# Layout corrigido com sliders ajustados
app.layout = html.Div([
    html.H1("Simulador Interativo: Classificação de Praias Arenosas"),

    html.Label("1. Ação de Ondas"),
    dcc.Slider(0, 4, step=1, value=0, marks={i: str(i) for i in range(5)}, id='wave'),

    html.Label("2. Zona de Arrebentação"),
    dcc.Slider(0, 2, step=1, value=0, marks={i: str(i) for i in range(3)}, id='breaker'),

    html.Label("3. % de Areia Fina"),
    dcc.Slider(0, 2, step=1, value=0, marks={i: str(i) for i in range(3)}, id='fine'),

    html.Label("4. Tamanho do Grão (mm)"),
    dcc.Dropdown(list(grain_table.keys()), "250-350", id='grain'),

    html.Label("4b. Inclinação da Praia"),
    dcc.Dropdown(list(slope_map.keys()), "1/20", id='slope'),

    html.Label("5. Profundidade da Camada Redox"),
    dcc.Slider(0, 4, step=1, value=0, marks={i: str(i) for i in range(5)}, id='redox'),

    html.Label("6. Organismos Tubícolas"),
    dcc.RadioItems(
        id='tubicola',
        options=[
            {'label': 'Presentes', 'value': 'Presentes'},
            {'label': 'Ausentes', 'value': 'Ausentes'}
        ],
        value='Presentes',
        labelStyle={'display': 'block'}
    ),

    html.Div(id='output-div'),
    dcc.Graph(id='morpho-graph')
])

@app.callback(
    Output('output-div', 'children'),
    Output('morpho-graph', 'figure'),
    Input('wave', 'value'),
    Input('breaker', 'value'),
    Input('fine', 'value'),
    Input('grain', 'value'),
    Input('slope', 'value'),
    Input('redox', 'value'),
    Input('tubicola', 'value')
)
def update_output(wave, breaker, fine, grain, slope, redox, tubicola):
    if None in (grain, slope, tubicola):
        return 'Carregando...', go.Figure()

    try:
        score4 = grain_table[grain][slope_map[slope]]
    except:
        score4 = 0

    tubicola_score = 1 if tubicola == 'Ausentes' else 0
    total = wave + breaker + fine + score4 + redox + tubicola_score
    tipo = classificar_praia(total)
    total = min(total, 20)

    d_range = np.linspace(0.2, 1.0, 300)
    def curva_protegida(d): return 3.1 * d**-1.1
    def curva_moderada(d): return 2.1 * d**-1.8
    def curva_exposta(d): return 3.9 * d**-1.85

    x1 = curva_protegida(d_range)
    x2 = curva_moderada(d_range)
    x3 = curva_exposta(d_range)

    mask1 = x1 <= 100
    mask2 = x2 <= 100
    mask3 = x3 <= 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x1[mask1], y=d_range[mask1], mode='lines',
        name='Protegida (x = 3,1·d⁻¹·¹)', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=x2[mask2], y=d_range[mask2], mode='lines',
        name='Moderada (x = 2,1·d⁻¹·⁸)', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=x3[mask3], y=d_range[mask3], mode='lines',
        name='Exposta (x = 3,9·d⁻¹·⁸⁵)', line=dict(color='red')))

    try:
        slope_val = eval(slope)
        grain_val = {
            ">710": 0.71, "500-710": 0.6, "350-500": 0.43,
            "250-350": 0.3, "180-250": 0.215, "<180": 0.15
        }[grain]
        if 0 < grain_val <= 1.0 and 0 < 1/slope_val <= 100:
            fig.add_trace(go.Scatter(
                x=[1/slope_val], y=[grain_val], mode='markers',
                name='Sua Seleção', marker=dict(color='black', size=10)
            ))
    except:
        pass

    fig.update_layout(
        xaxis_title="Inclinação da Praia (1:x)",
        yaxis_title="Diâmetro Médio do Grão (mm)",
        title="Classificação da Exposição de Praias Arenosas",
        xaxis=dict(range=[0, 100]),
        yaxis=dict(range=[0, 1.0]),
        legend=dict(font=dict(size=12))
    )

    return f"Escore Total: {total} → Tipo de Praia: {tipo}", fig

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
