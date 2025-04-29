# Remove these lines:
# cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})

cache = None  # <-- initialize an empty global first

def register_callbacks(app):

    global cache
    cache = Cache(app.server, config={'CACHE_TYPE': 'SimpleCache'})
    cache.init_app(app.server)  # optional

    # now define your callbacks here
    ...
