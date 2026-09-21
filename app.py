from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import STATIC_DIR
from web.routes import router


app = FastAPI(title="MoonTrace")
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)
app.include_router(router)
