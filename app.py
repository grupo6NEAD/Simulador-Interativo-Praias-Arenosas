from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import numpy as np
import os

# --- DADOS E FUNÇÕES DE CLASSIFICAÇÃO ---

# Tabela de pontuação para o tamanho do grão e inclinação
grain_table = {
    ">710": {"1/5": 7, "1/10": 6, "1/20": 5, "1/25": 4, "1/50": 3},
    "500-710": {"1/5": 6, "1/10": 5, "1/20": 4, "1/25": 3, "1/50": 2},
    "350-500": {"1/5": 5, "1/10": 4, "1/20": 3, "1/25": 2, "1/50": 1},
    "250-350": {"1/5": 4, "1/10": 3, "1/20": 2, "1/25": 1, "1/50": 0},
    "180-250": {"1/5": 3, "1/10": 2, "1/20": 1, "1/25": 0, "1/50": 0},
    "<180": {"1/5": 2, "1/10": 1, "1/20": 0, "1/25": 0, "1/50": 0},
}

# Mapeamento para valores numéricos do diâmetro do grão para o gráfico
grain_numerical_map = {
    ">710": 0.71, "500-710": 0.6, "350-500": 0.43,
    "250-350": 0.3, "180-250": 0.215, "<180": 0.15
}

# Opções para os componentes de entrada
wave_action_options = {0: "Praticamente ausente", 1: "Fraca", 2: "Moderada", 3: "Forte", 4: "Extremamente forte (>1,5m)"}
breaker_zone_options = {0: "Muito larga, quebra em bancos", 1: "Média", 2: "Quebra na face da praia"}
fine_sand_options = {0: "5%", 1: "2–3%", 2: "<1%"}
redox_options = {0: "0–10 cm", 1: "10–25 cm", 2: "25–50 cm", 3: "50–80 cm", 4: ">80 cm"}

def classificar_praia(escore):
    """Classifica o tipo de praia com base na pontuação total."""
    if escore <= 5:
        return "Refletiva (Muito Protegida)"
    elif escore <= 10:
        return "Intermediária (Protegida)"
    elif escore <= 15:
        return "Dissipativa (Exposta)"
    else:
        return "Muito Dissipativa (Muito Exposta)"

# --- INICIALIZAÇÃO DO APP DASH ---
app = Dash(__name__)
server = app.server

# --- ESTILOS DO TEMA ESCURO ---
colors = {
    'background': '#1E1E1E',
    'text': '#EAEAEA',
    'container': '#2D2D2D',
    'accent': '#4491D3',
    'border': '#444444'
}

# Estilo para o container principal
main_style = {
    "backgroundColor": colors['background'],
    "color": colors['text'],
    "fontFamily": "Arial, sans-serif",
    "maxWidth": "1400px",
    "margin": "40px auto",
    "padding": "30px",
}

# Função auxiliar para criar seções de input com espaçamento
def create_input_section(label, component):
    children = [html.Label(label, style={"fontWeight": "bold"})]
    children.append(component)
    return html.Div(children, style={"marginBottom": "25px"})

# --- LAYOUT DO APLICATIVO ---
app.layout = html.Div([
    html.H1("Simulador Interativo: Classificação de Praias Arenosas", style={"textAlign": "center", "color": colors['accent']}),
    html.P(
        "Esta ferramenta classifica o estado morfodinâmico de praias arenosas com base em parâmetros físicos e biológicos. "
        "Ajuste os valores abaixo para ver como eles influenciam a pontuação e o tipo de praia.",
        style={"textAlign": "center", "marginBottom": "40px"}
    ),

    # Container para o layout de duas colunas
    html.Div([
        # Coluna da Esquerda: Controles
        html.Div([
            html.H3("Parâmetros de Entrada", style={"borderBottom": f"1px solid {colors['border']}", "paddingBottom": "10px"}),
            create_input_section("1. Ação de Ondas",
                dcc.Slider(0, 4, step=1, value=0, marks=wave_action_options, id='wave')),
            create_input_section("2. Zona de Arrebentação",
                dcc.Slider(0, 2, step=1, value=0, marks=breaker_zone_options, id='breaker')),
            create_input_section("3. Percentual de Areia Fina",
                dcc.Slider(0, 2, step=1, value=0, marks=fine_sand_options, id='fine')),
            html.Div([
                html.H4("4. Morfologia e Sedimento", style={"marginTop": "20px"}),
                create_input_section("4a. Tamanho do Grão (mm)",
                    dcc.Dropdown(list(grain_table.keys()), "250-350", id='grain', clearable=False)),
                create_input_section("4b. Inclinação da Praia",
                    dcc.Dropdown(list(grain_table[">710"].keys()), "1/20", id='slope', clearable=False)),
            ], style={"background": "#3c3c3c", "padding": "15px", "borderRadius": "5px"}),
            create_input_section("5. Profundidade da Camada Redox (RPD)",
                dcc.Slider(0, 4, step=1, value=0, marks=redox_options, id='redox')),
            create_input_section("6. Organismos Tubícolas",
                dcc.RadioItems(id='tubicola', options=[{'label': 'Presentes', 'value': 'Presentes'}, {'label': 'Ausentes', 'value': 'Ausentes'}], value='Presentes',
                               labelStyle={'display': 'inline-block', 'marginRight': '20px'})),
        ], style={
            'flex': '1', 'minWidth': '450px', 'padding': '25px',
            'backgroundColor': colors['container'], 'borderRadius': '10px', 'border': f"1px solid {colors['border']}"
        }),

        # Coluna da Direita: Resultados e Gráfico
        html.Div([
            html.Div(id='output-div', style={
                "padding": "20px", "background": colors['accent'], "color": "#FFFFFF", "borderRadius": "10px",
                "textAlign": "center", "fontSize": "1.3em", "marginBottom": "20px", "fontWeight": "bold"
            }),
            dcc.Graph(id='morpho-graph', style={'height': '80vh'})
        ], style={'flex': '1.5', 'paddingLeft': '30px'})

    ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '30px'})

], style=main_style)

# --- CALLBACKS ---
@app.callback(
    Output('output-div', 'children'),
    Output('morpho-graph', 'figure'),
    [Input(i, 'value') for i in ['wave', 'breaker', 'fine', 'grain', 'slope', 'redox', 'tubicola']]
)
def update_output(wave, breaker, fine, grain, slope, redox, tubicola):
    # --- Cálculo da Pontuação ---
    score4 = grain_table.get(grain, {}).get(slope, 0)
    tubicola_score = 1 if tubicola == 'Ausentes' else 0
    total_score = wave + breaker + fine + score4 + redox + tubicola_score
    tipo_praia = classificar_praia(total_score)
    
    # --- Geração do Gráfico ---
    fig = go.Figure()
    d_range = np.linspace(0.1, 1.0, 300)

    curves = {
        "Refletiva": {"func": lambda d: 3.1 * d**-1.1, "color": "#33C3F0", "formula": "x = 3,1·d⁻¹·¹"},
        "Intermediária": {"func": lambda d: 2.1 * d**-1.8, "color": "#39E991", "formula": "x = 2,1·d⁻¹·⁸"},
        "Dissipativa": {"func": lambda d: 3.9 * d**-1.85, "color": "#E95D39", "formula": "x = 3,9·d⁻¹·⁸⁵"}
    }

    for name, props in curves.items():
        x = props["func"](d_range)
        mask = (x >= 5) & (x <= 100)
        fig.add_trace(go.Scatter(x=x[mask], y=d_range[mask], mode='lines', name=f'{name} ({props["formula"]})', line=dict(color=props["color"])))

    try:
        slope_val_inv = 1 / eval(slope)
        grain_val = grain_numerical_map.get(grain, 0)
        if 5 <= slope_val_inv <= 100 and 0.1 <= grain_val <= 1.0:
            fig.add_trace(go.Scatter(x=[slope_val_inv], y=[grain_val], mode='markers', name='Sua Seleção', marker=dict(color=colors['text'], size=14, symbol='star')))
    except (SyntaxError, ZeroDivisionError, TypeError):
        pass

    fig.update_layout(
        title="Classificação Morfodinâmica da Praia",
        xaxis_title="Inclinação da Praia (1:x)",
        yaxis_title="Diâmetro Médio do Grão (mm)",
        xaxis=dict(range=[5, 100]),
        yaxis=dict(range=[0.1, 1.0]),
        legend=dict(font=dict(size=10), yanchor="top", y=0.99, xanchor="right", x=0.99),
        margin=dict(l=40, r=40, t=40, b=40),
        template='plotly_dark'
    )
    
    output_text = [
        html.Span(f"Escore Total: {total_score}"),
        html.Span(" → ", style={"margin": "0 10px"}),
        html.Span(f"Tipo de Praia: {tipo_praia}")
    ]

    return output_text, fig

# --- EXECUÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
