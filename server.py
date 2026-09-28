import marimo

# ASGI Application serving marimo notebooks with Uvicorn
server = (
    marimo.create_asgi_app()
    .with_app(path="", root="app.py")
    .build()
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:server", host="0.0.0.0", port=8000, reload=True)
