import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routes import auth, user, service
from app.database.init_db import init_db
from app.core.config import settings  # Importa las variables desde .env

app = FastAPI(title="GruaGo API")

# Evento de inicio de la aplicación
@app.on_event("startup")
def startup_event():
    # Inicializar la base de datos
    init_db()

    # Crear carpetas estáticas y logs si no existen
    for folder in [
        "static/profile_pics",
        "static/ride_receipts",
        "static/misc",
        "logs"
    ]:
        os.makedirs(folder, exist_ok=True)

# Montar carpeta estática (para imágenes, recibos, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir rutas
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(service.router, prefix="/services", tags=["Services"])

# Punto de entrada principal
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT)
