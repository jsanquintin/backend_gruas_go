from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import get_settings
from app.routers import auth, users, operators, services, metrics, tariffs, dispatch

app = FastAPI(title='DEGARITAO Express API', version='0.3.0', description='MVP despacho de Delivery y Asistencia Vial')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in get_settings().allowed_origins.split(',') if x.strip()], allow_methods=['GET','POST','PATCH','PUT'], allow_headers=['Authorization','Content-Type'])
app.include_router(auth.router, prefix='/api/v1')
app.include_router(users.router, prefix='/api/v1')
app.include_router(operators.router, prefix='/api/v1')
app.include_router(services.router, prefix='/api/v1')
app.include_router(metrics.router, prefix='/api/v1')
app.include_router(tariffs.router, prefix='/api/v1')
app.include_router(dispatch.router, prefix='/api/v1')

@app.get('/health', tags=['Sistema'])
def health():
    return {'status': 'ok', 'product': 'DEGARITAO Express', 'version': '0.3.0'}
