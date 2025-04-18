import dash
from dash import dcc, html, Input, Output
import dash_table
import pandas as pd
import time
from flask_caching import Cache
import plotly.express as px

# Replace with your scalar columns
scalar_columns = ["value1", "value2", "value3"]

app = dash.Dash(__name__)
server = app.server

# Cache setup
cache = Cache(app.server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24
})

@cache.memoize()
def load_large_dataset():
    print("Loading dataset...")
    time.sleep(3)
    df = pd.read_csv("your_large_dataset.csv", parse_dates=True, index_col=0)
    df.index = pd.to_datetime(df.index)
    return df

# Heatmap-style coloring for DataTable
def generate_heatmap_styles(df, columns):
    styles = []
    for col in columns:
        col_min = df[col].min()
        col_max = df[col].max()
        for i, val in enumerate(df[col]):
            norm = (val - col_min) / (col_max - col_min + 1e-6)
            # Gradient from light to dark blue
            color = f"rgba({int(255 * norm)}, {int(255 * norm)}, 255, 0.85)"
            styles.append({
                "if": {"row_index": i, "column_id": col},
                "backgroundColor": color,
                "color": "black"
            })
    return styles

# Layout
app.layout = html.Div([
    html.H2("ISO Heatmap Viewer"),
    dcc.Dropdown(id="iso-dropdown", placeholder="Select ISO"),
    dcc.RangeSlider(
        id="time-slider",
        step=1,
        tooltip={"placement": "bottom", "always_visible": True}
    ),
    html.Br(),
    html.H4("Average Table by Asset"),
    dash_table.DataTable(
        id="heatmap-table",
        style_cell={"textAlign": "center"},
        style_header={"fontWeight": "bold"},
        style_data_conditional=[],
        data=[], columns=[]
    ),
    html.Br(),
    html.H4("Heatmap Visualization"),
    dcc.Graph(id="heatmap-graph")
])

# Init ISO dropdown & slider
@app.callback(
    Output("iso-dropdown", "options"),
    Output("time-slider", "min"),
    Output("time-slider", "max"),
    Output("time-slider", "value"),
    Output("time-slider", "marks"),
    Input("iso-dropdown", "id")
)
def init_controls(_):
    try:
        df = load_large_dataset()
        iso_options = [{"label": iso, "value": iso} for iso in df["ISO"].unique()]
        df_sorted = df.sort_index()
        time_list = df_sorted.index.unique()

        if len(time_list) < 2:
            return iso_options, 0, 1, [0, 1], {0: "0", 1: "1"}

        min_idx = 0
        max_idx = len(time_list) - 1
        marks = {
            i: time_list[i].strftime("%m-%d %H:%M")
            for i in range(0, len(time_list), max(1, len(time_list) // 6))
        }

        return iso_options, min_idx, max_idx, [min_idx, max_idx], marks

    except Exception as e:
        print("Slider init error:", e)
        return [], 0, 1, [0, 1], {0: "0", 1: "1"}

# Shared callback for both table + figure
@app.callback(
    Output("heatmap-table", "data"),
    Output("heatmap-table", "columns"),
    Output("heatmap-table", "style_data_conditional"),
    Output("heatmap-graph", "figure"),
    Input("iso-dropdown", "value"),
    Input("time-slider", "value")
)
def update_outputs(selected_iso, time_range):
    if selected_iso is None or time_range is None:
        return [], [], [], {}

    df = load_large_dataset()
    df = df[df["ISO"] == selected_iso]
    df_sorted = df.sort_index()
    time_list = df_sorted.index.unique()

    if len(time_list) == 0:
        return [], [], [], {}

    end_idx = min(time_range[1], len(time_list) - 1)
    selected_times = time_list[time_range[0]:end_idx + 1]
    df_selected = df_sorted[df_sorted.index.isin(selected_times)]

    if df_selected.empty or "Asset" not in df_selected.columns:
        return [], [], [], {}

    grouped_avg = df_selected.groupby("Asset")[scalar_columns].mean().reset_index()

    table_data = grouped_avg.copy()
    table_data[scalar_columns] = table_data[scalar_columns].round(2)
    table_data = table_data.to_dict("records")

    # Table setup
    # table_data = grouped_avg.to_dict("records")
    table_columns = [{"name": col, "id": col} for col in grouped_avg.columns]
    table_styles = generate_heatmap_styles(grouped_avg, scalar_columns)

    # Heatmap figure setup
    grouped_avg_fig = grouped_avg.set_index("Asset")
    fig = px.imshow(
        grouped_avg_fig,
        labels=dict(x="Variables", y="Asset", color="Avg Value"),
        aspect="auto",
        color_continuous_scale="Viridis"
    )
    fig.update_layout(
        title=f"Averaged Heatmap for ISO: {selected_iso}<br>"
              f"{selected_times[0].strftime('%m-%d %H:%M')} → {selected_times[-1].strftime('%m-%d %H:%M')}",
        xaxis_tickangle=-45
    )

    return table_data, table_columns, table_styles, fig

# Run
if __name__ == "__main__":
    app.run_server(debug=True)
