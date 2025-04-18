import dash
from dash import dcc, html, Input, Output
import pandas as pd
import time
from flask_caching import Cache
import plotly.express as px

# Replace with your actual scalar column names
scalar_columns = ["value1", "value2", "value3"]

# Initialize app
app = dash.Dash(__name__)
server = app.server

# Cache config (24 hours)
cache = Cache(app.server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24  # 24 hours
})

# Simulated large dataset loader
@cache.memoize()
def load_large_dataset():
    print("Loading dataset...")
    time.sleep(3)  # simulate long load
    df = pd.read_csv("your_large_dataset.csv", parse_dates=True, index_col=0)
    return df

# App layout
app.layout = html.Div([
    html.H2("ISO Heatmap Viewer"),
    dcc.Dropdown(id="iso-dropdown", placeholder="Select ISO"),
    dcc.RangeSlider(id="time-slider", tooltip={"placement": "bottom", "always_visible": True}),
    dcc.Graph(id="heatmap-graph")
])

# Populate ISO dropdown and time slider
@app.callback(
    Output("iso-dropdown", "options"),
    Output("time-slider", "min"),
    Output("time-slider", "max"),
    Output("time-slider", "value"),
    Output("time-slider", "marks"),
    Input("iso-dropdown", "id")  # dummy input to trigger at load
)
def init_controls(_):
    df = load_large_dataset()
    df.index = pd.to_datetime(df.index)
    iso_options = [{"label": iso, "value": iso} for iso in df["ISO"].unique()]
    df_sorted = df.sort_index()
    time_list = df_sorted.index.unique()
    min_idx = 0
    max_idx = len(time_list) - 1
    marks = {i: time_list[i].strftime("%m-%d %H:%M") for i in range(0, len(time_list), len(time_list) // 6 or 1)}
    return iso_options, min_idx, max_idx, [min_idx, max_idx], marks

# Generate heatmap
@app.callback(
    Output("heatmap-graph", "figure"),
    Input("iso-dropdown", "value"),
    Input("time-slider", "value")
)
def update_heatmap(selected_iso, time_range):
    if selected_iso is None or time_range is None:
        return {}
    df = load_large_dataset()
    df.index = pd.to_datetime(df.index)
    df = df[df["ISO"] == selected_iso]
    df_sorted = df.sort_index()
    time_list = df_sorted.index.unique()
    selected_times = time_list[time_range[0]:time_range[1]+1]
    df_selected = df_sorted[df_sorted.index.isin(selected_times)]

    if df_selected.empty:
        return {}

    # Create heatmap-style DataFrame
    df_plot = df_selected[scalar_columns].copy()
    df_plot["Time"] = df_selected.index.strftime("%m-%d %H:%M")
    df_plot = df_plot.set_index("Time").T

    fig = px.imshow(df_plot,
                    labels=dict(x="Time", y="Variables", color="Value"),
                    aspect="auto",
                    color_continuous_scale="Viridis")
    fig.update_layout(title=f"Heatmap for ISO: {selected_iso}", xaxis_tickangle=-45)
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
