from fastapi import FastAPI
from app.api.routes import auth, user, service
from app.database.init_db import init_db

app = FastAPI(title="GruaGo API")

# Inicializar la base de datos
@app.on_event("startup")
def startup_event():
    init_db()

# Incluir rutas
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(service.router, prefix="/services", tags=["Services"])

