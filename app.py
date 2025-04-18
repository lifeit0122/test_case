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

    # Guard against index overflow
    if time_range[1] >= len(time_list):
        time_range[1] = len(time_list) - 1

    selected_times = time_list[time_range[0]:time_range[1] + 1]
    df_selected = df_sorted[df_sorted.index.isin(selected_times)]

    if df_selected.empty or "Asset" not in df_selected.columns:
        return {}

    # Group by Asset and calculate mean of scalar columns
    grouped_avg = df_selected.groupby("Asset")[scalar_columns].mean()

    # Assets as rows, scalar columns as columns (no transpose needed)
    fig = px.imshow(
        grouped_avg,
        labels=dict(x="Variables", y="Asset", color="Avg Value"),
        aspect="auto",
        color_continuous_scale="Viridis"
    )

    fig.update_layout(
        title=f"Averaged Heatmap (Assets as rows) for ISO: {selected_iso}<br>{selected_times[0].strftime('%m-%d %H:%M')} → {selected_times[-1].strftime('%m-%d %H:%M')}",
        xaxis_tickangle=-45
    )

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
