from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from api.main import app as api


class ReactFrontend(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or Path(path).suffix:
                raise
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(_app):
    async with api.router.lifespan_context(api):
        yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.mount("/api", api)
app.mount("/", ReactFrontend(directory=Path(__file__).with_name("web"), html=True))
