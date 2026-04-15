from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.categories import router as categories_router
from backend.routes.items import router as items_router
from backend.routes.top import router as top_router
from backend.routes.sync import router as sync_router

app = FastAPI(title="Effict API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories_router)
app.include_router(items_router)
app.include_router(top_router)
app.include_router(sync_router)


@app.get("/health")
def health():
    return {"status": "ok"}
