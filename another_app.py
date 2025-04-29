from dash import Dash, dcc, html, Input, Output
import pages.fleet_overview as fleet_overview

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Register callbacks
fleet_overview.register_callbacks(app)

# Main layout
app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div(id="page-content")
])

# Routing
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/" or pathname == "/fleet-overview":
        return fleet_overview.layout
    else:
        return html.H1("404: Page Not Found")

if __name__ == "__main__":
    app.run_server(debug=True)
