from dash import Dash, html, dcc, callback, Input, Output
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc



df = pd.read_csv("../data/MENSQ_33_previous-1950-2024.csv", sep=";")

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(__name__ ,external_stylesheets=external_stylesheets)

app.layout= dbc.Container([
    dbc.Row([
        html.Div("Dashboard", className="Title fs-3")
    ]),
    dbc.Row([
        dbc.RadioItems(options=['LAT', 'LON'], value='LAT', id='controls-and-radio-items', inline=True),
    ]),
    dbc.Row([
        dbc.Col([
            dag.AgGrid(
                rowData=df.to_dict('records'),
                columnDefs=[{"field": i} for i in df.columns]
            )
        ], width=6),
        dbc.Col([
            dcc.Graph(figure={}, id='control-and-graph')
        ], width=50),
    ])
], fluid=True)

@callback(
    Output(component_id="control-and-graph", component_property="figure"),
    Input(component_id="controls-and-radio-items", component_property="value")
)
def update_graph(value):
    fig = px.histogram(df, x="LAT", y=value , histfunc='avg')
    return fig

if __name__ == '__main__':
    app.run(debug=True)