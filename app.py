import dash
from dash import dcc, html, Input, Output
import dash_table
import pandas as pd
import time
from flask_caching import Cache
import plotly.express as px
from datetime import datetime

# Replace with your actual scalar value columns
scalar_columns = ["value1", "value2", "value3"]

app = dash.Dash(__name__)
server = app.server

# Cache setup
cache = Cache(app.server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 60 * 60 * 24  # 24 hours
})

# Simulate heavy dataset loading
@cache.memoize()
def load_large_dataset():
    print("Loading dataset...")
    time.sleep(3)
    df = pd.read_csv("your_large_dataset.csv", parse_dates=True, index_col=0)
    df.index = pd.to_datetime(df.index)
    return df

# Heatmap-style background coloring
def generate_heatmap_styles(df, columns):
    styles = []
    for col in columns:
        col_min = df[col].min()
        col_max = df[col].max()
        for i, val in enumerate(df[col]):
            norm = (val - col_min) / (col_max - col_min + 1e-6) if col_max != col_min else 0.5
            color = f"rgba({int(255 * norm)}, {int(255 * norm)}, 255, 0.85)"  # gradient blue
            styles.append({
                "if": {"row_index": i, "column_id": col},
                "backgroundColor": color,
                "color": "black"
            })
    return styles

# Layout
app.layout = html.Div([
    html.H2("ISO Heatmap Viewer"),

    # Dropdowns side by side
    html.Div([
        html.Div([
            dcc.Dropdown(id="iso-dropdown", placeholder="Select ISO")
        ], style={"flex": "1", "padding": "5px"}),

        html.Div([
            dcc.Dropdown(id="client-dropdown", placeholder="Select Client")
        ], style={"flex": "1", "padding": "5px"}),

        html.Div([
            dcc.Dropdown(id="duration-dropdown", placeholder="Select Duration")
        ], style={"flex": "1", "padding": "5px"}),
    ], style={"display": "flex", "flexDirection": "row"}),

    # Slider with margin and thicker height
    html.Div([
        dcc.RangeSlider(
            id="time-slider",
            step=86400,  # 1 day step
            tooltip={"placement": "bottom", "always_visible": True},
            style={"height": "30px"}
        )
    ], style={"marginTop": "20px"}),

    html.Br(),

    html.H4("Average Table by Asset"),
    html.Div(id="time-range-display", style={"fontWeight": "bold", "marginTop": "1em"}),

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

# Initialize dropdown options and slider
@app.callback(
    Output("iso-dropdown", "options"),
    Output("client-dropdown", "options"),
    Output("duration-dropdown", "options"),
    Output("time-slider", "min"),
    Output("time-slider", "max"),
    Output("time-slider", "value"),
    Output("time-slider", "marks"),
    Input("iso-dropdown", "id")  # dummy trigger
)
def init_controls(_):
    try:
        df = load_large_dataset()

        iso_options = [{"label": iso, "value": iso} for iso in df["ISO"].unique()]
        client_options = [{"label": client, "value": client} for client in df["Client"].unique()]
        duration_options = [{"label": f"{duration:.2f}", "value": float(duration)}
                            for duration in sorted(df["Duration"].dropna().unique())]

        df_sorted = df.sort_index()
        time_list = df_sorted.index.unique()

        if len(time_list) < 2:
            return iso_options, client_options, duration_options, 0, 1, [0, 1], {0: "0", 1: "1"}

        timestamps = [int(t.timestamp()) for t in time_list]
        marks = {
            int(t.timestamp()): t.strftime("%m-%d")
            for t in time_list[::max(1, len(time_list) // 6)]
        }

        return (
            iso_options,
            client_options,
            duration_options,
            min(timestamps),
            max(timestamps),
            [min(timestamps), max(timestamps)],
            marks
        )

    except Exception as e:
        print("Slider init error:", e)
        return [], [], [], 0, 1, [0, 1], {0: "0", 1: "1"}

@app.callback(
    Output("time-slider", "value"),
    Input("date-dropdown", "value"),
    Input("time-slider", "value"),
    prevent_initial_call=True
)
def sync_date_dropdown(selected_date, current_slider_range):
    if selected_date is None:
        return current_slider_range
    return [selected_date, selected_date]


# Update table, figure, and time range label
@app.callback(
    Output("heatmap-table", "data"),
    Output("heatmap-table", "columns"),
    Output("heatmap-table", "style_data_conditional"),
    Output("heatmap-graph", "figure"),
    Output("time-range-display", "children"),
    Input("iso-dropdown", "value"),
    Input("client-dropdown", "value"),
    Input("duration-dropdown", "value"),
    Input("time-slider", "value")
)
def update_outputs(selected_iso, selected_client, selected_duration, time_range):
    if time_range is None:
        return [], [], [], {}, ""

    df = load_large_dataset()

    # Apply filters if selected
    if selected_iso:
        df = df[df["ISO"] == selected_iso]
    if selected_client:
        df = df[df["Client"] == selected_client]
    if selected_duration is not None:
        df = df[df["Duration"] == selected_duration]

    df_sorted = df.sort_index()

    # Convert slider timestamps to datetime
    start_ts = datetime.fromtimestamp(time_range[0])
    end_ts = datetime.fromtimestamp(time_range[1])

    df_selected = df_sorted[(df_sorted.index >= start_ts) & (df_sorted.index <= end_ts)]

    if df_selected.empty or "Asset" not in df_selected.columns:
        return [], [], [], {}, ""

    # Group and format table
    grouped_avg = df_selected.groupby("Asset")[scalar_columns].mean().reset_index()
    table_data = grouped_avg.copy()
    table_data[scalar_columns] = table_data[scalar_columns].round(2)
    table_data = table_data.to_dict("records")
    table_columns = [{"name": col, "id": col} for col in grouped_avg.columns]
    table_styles = generate_heatmap_styles(grouped_avg, scalar_columns)

    # Plotly heatmap
    grouped_avg_fig = grouped_avg.set_index("Asset")
    fig = px.imshow(
        grouped_avg_fig,
        labels=dict(x="Variables", y="Asset", color="Avg Value"),
        aspect="auto",
        color_continuous_scale="Viridis"
    )
    fig.update_layout(
        title=f"Averaged Heatmap<br>{start_ts.strftime('%Y-%m-%d %H:%M')} → {end_ts.strftime('%Y-%m-%d %H:%M')}",
        xaxis_tickangle=-45
    )

    # Time window label
    time_label = f"Showing data from {start_ts.strftime('%Y-%m-%d %H:%M')} to {end_ts.strftime('%Y-%m-%d %H:%M')}"

    return table_data, table_columns, table_styles, fig, time_label

# Run app
if __name__ == '__main__':
    app.run_server(debug=True)
