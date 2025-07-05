
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import numpy as np

# Opções dos parâmetros
wave_action_options = {
    0: "Praticamente ausente",
    1: "Leve a moderada (<1m)",
    2: "Contínua moderada (<1m)",
    3: "Contínua forte (>1m)",
    4: "Extremamente forte (>1.5m)"
}
breaker_zone_options = {
    0: "Muito larga",
    1: "Moderada (50-150m)",
    2: "Estreita (face da praia)"
}
fine_sand_options = {
    0: "5%",
    1: "1 a 5%",
    2: "<1%"
}
redox_layer_options = {
    0: "0-10 cm",
    1: "10-25 cm",
    2: "25-50 cm",
    3: "50-80 cm",
    4: ">80 cm"
}
tubeworms_options = {
    0: "Presentes",
    1: "Ausentes"
}

# Classificação do tipo de praia pelo escore total
def classificar_praia(escore):
    if escore <= 5:
        return "Muito Protegida"
    elif escore <= 10:
        return "Protegida"
    elif escore <= 15:
        return "Exposta"
    else:
        return "Muito Exposta"

app = Dash(__name__)

app.layout = html.Div([
    html.H2("Simulador Interativo: Classificação de Praias Arenosas", style={'textAlign': 'center'}),

    html.Div([
        html.Label("1. Ação de Ondas"),
        dcc.Slider(0, 4, 1, value=2, marks={i: wave_action_options[i] for i in range(5)}, id='wave-action'),

        html.Label("2. Zona de Arrebentação"),
        dcc.Slider(0, 2, 1, value=1, marks={i: breaker_zone_options[i] for i in range(3)}, id='breaker-zone'),

        html.Label("3. % de Areia Fina"),
        dcc.Slider(0, 2, 1, value=1, marks={i: fine_sand_options[i] for i in range(3)}, id='fine-sand'),

        html.Label("4. Tamanho do Grão (mm)"),
        dcc.Dropdown(
            options=[
                {"label": ">710 µm", "value": ">710"},
                {"label": "500-710 µm", "value": "500-710"},
                {"label": "350-500 µm", "value": "350-500"},
                {"label": "250-350 µm", "value": "250-350"},
                {"label": "180-250 µm", "value": "180-250"},
                {"label": "<180 µm", "value": "<180"}
            ],
            value="250-350",
            id='grain-size'
        ),

        html.Label("4b. Inclinação da Praia"),
        dcc.Dropdown(
            options=[
                {"label": "1/5", "value": "1/5"},
                {"label": "1/10", "value": "1/10"},
                {"label": "1/20", "value": "1/20"},
                {"label": "1/30", "value": "1/30"},
                {"label": "1/50", "value": "1/50"},
                {"label": "1/100", "value": "1/100"}
            ],
            value="1/25",
            id='slope'
        ),

        html.Label("5. Profundidade da Camada Redox"),
        dcc.Slider(0, 4, 1, value=2, marks={i: redox_layer_options[i] for i in range(5)}, id='redox'),

        html.Label("6. Organismos Tubícolas"),
        dcc.RadioItems(
            options=[
                {"label": "Presentes", "value": 0},
                {"label": "Ausentes", "value": 1}
            ],
            value=1,
            id='tubeworms'
        )
    ], style={'columnCount': 2, 'margin': '40px'}),

    html.Div(id='output-div', style={'textAlign': 'center', 'fontSize': '20px', 'margin': '20px'}),
    dcc.Graph(id='morpho-graph')
])

grain_table = {
    ">710": [5, 6, 7, 7, 7, 7],
    "500-710": [4, 5, 6, 6, 7, 7],
    "350-500": [3, 4, 5, 5, 6, 6],
    "250-350": [2, 3, 4, 4, 5, 5],
    "180-250": [1, 2, 3, 3, 4, 4],
    "<180": [0, 0, 1, 1, 2, 2]
}
slope_map = {"1/5": 0, "1/10": 1, "1/20": 2, "1/30": 3, "1/50": 4, "1/100": 5}

@app.callback(
    Output('output-div', 'children'),
    Output('morpho-graph', 'figure'),
    Input('wave-action', 'value'),
    Input('breaker-zone', 'value'),
    Input('fine-sand', 'value'),
    Input('grain-size', 'value'),
    Input('slope', 'value'),
    Input('redox', 'value'),
    Input('tubeworms', 'value')
)

def update_output(wave, breaker, fine, grain, slope, redox, worms):
    if None in (grain, slope):
        return 'Carregando...', go.Figure()

    try:
        slope_val = eval(slope) if isinstance(slope, str) else float(slope)
        slope_decimal = 1 / slope_val

        slope_headers = list(grain_table[grain].keys()) if isinstance(grain_table[grain], dict) else list(slope_map.keys())
        slope_values = [eval(k) if isinstance(k, str) else k for k in slope_headers]
        closest_index = min(range(len(slope_values)), key=lambda i: abs(slope_values[i] - slope_decimal))
        closest_slope_key = slope_headers[closest_index]

        score4 = grain_table[grain][slope_map[slope]]
    except Exception:
        score4 = 0

    total = wave + breaker + fine + score4 + redox + worms
    tipo = classificar_praia(total)

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

    fig.add_trace(go.Scatter(x=x1[mask1], y=d_range[mask1],
                             mode='lines', name='Praias Protegidas (x = 3,1·d⁻¹·¹)',
                             line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=x2[mask2], y=d_range[mask2],
                             mode='lines', name='Moderadamente Protegidas (x = 2,1·d⁻¹·⁸)',
                             line=dict(color='green')))
    fig.add_trace(go.Scatter(x=x3[mask3], y=d_range[mask3],
                             mode='lines', name='Praias Expostas (x = 3,9·d⁻¹·⁸⁵)',
                             line=dict(color='red')))

    try:
        slope_val = eval(slope) if isinstance(slope, str) else float(slope)
        grain_val = {
            ">710": 0.71, "500-710": 0.6, "350-500": 0.43,
            "250-350": 0.3, "180-250": 0.215, "<180": 0.15
        }[grain]

        if 0 < grain_val <= 1.0 and 0 < 1/slope_val <= 100:
            fig.add_trace(go.Scatter(
                x=[1/slope_val],
                y=[grain_val],
                mode='markers',
                name='Sua Seleção',
                marker=dict(color='black', size=10)
            ))
    except Exception:
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


if __name__ == "__main__":
    app.run(debug=True)
