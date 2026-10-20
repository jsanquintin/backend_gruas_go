# DEGARITAO Express v0.3 — Railway + Netlify

**Un repositorio, dos servicios independientes.** El backend y la SPA deben desplegarse con HTTPS; no exponer el panel sin controles adicionales si contiene datos reales.

## Railway (API)
1. Conectar el repositorio y seleccionar la rama `degaritao-express-deploy`. Crear el servicio **desde GitHub**.
2. Configurar **Root Directory**: `backend`. El Dockerfile del directorio será usado para la construcción.
3. Añadir PostgreSQL administrado en Railway al mismo proyecto.
4. Variables del servicio API: `DATABASE_URL` = referencia al `DATABASE_URL` proporcionado por PostgreSQL Railway (`${{Postgres.DATABASE_URL}}`, ajustar al nombre real del servicio); `JWT_SECRET` = secreto aleatorio NUEVO de al menos 32 caracteres; `ENVIRONMENT=production`; `ALLOWED_ORIGINS=https://TU-NOMBRE.netlify.app`.
5. Solo durante el primer despliegue: `ADMIN_EMAIL` y `ADMIN_PASSWORD` (contraseña privada de 12+ caracteres); el arranque crea el admin si no existe y **no modifica** un administrador existente. Tras el alta, retirar la contraseña del panel de Railway y redeplegar.
6. Generar dominio HTTPS público en Railway. Comprobar `https://URL/health` y `/docs`.
7. **Inicio:** `start.sh` ejecuta `alembic upgrade head` y luego `uvicorn` en `$PORT` (no es necesario configurar Start Command).
8. Esta versión usa una instancia/worker de API; streaming SSE y cuotas de GPS necesitan pruebas de carga y robustecimiento antes de producción.

### Variables API
| Variable | Valor |
|--|--|
| `DATABASE_URL` | URL privada de Railway Postgres, referenciada sin exponerla |
| `JWT_SECRET` | Un secreto aleatorio nuevo (32+ caracteres) |
| `ALLOWED_ORIGINS` | URL completa HTTPS de Netlify, sin barra final; varias separadas por coma |
| `ENVIRONMENT` | `production` |
| `ADMIN_EMAIL` | Cuenta administradora inicial (retirable después) |
| `ADMIN_PASSWORD` | Solo para primera creación; borrar luego |

## Netlify (React)
1. Importar **el mismo repositorio y rama**, pero para el sitio Netlify.
2. El archivo `netlify.toml` en la raíz configura automáticamente base=`frontend`, comando=`npm run build`, publish=`dist`.
3. Configurar variable del sitio en **Environment variables**:
   `VITE_API_BASE_URL=https://URL_PUBLICA_DE_RAILWAY` (sin `/api/v1`). No es un secreto; se incrusta en el JS público.
4. Lanzar/repetir deploy tras configurar la variable. Comprobar la ruta pública del frontend.
5. Volver a Railway y establecer `ALLOWED_ORIGINS` con el dominio real del sitio Netlify, luego redeplegar la API.
6. Probar inicio de sesión, listado, creación de solicitudes, GPS, tarifas y SSE con HTTPS en la pestaña Network del navegador.

**Nota:** Netlify no ejecuta PostgreSQL ni FastAPI. Si `VITE_API_BASE_URL` no está definida en Netlify, el frontend seguirá buscando `/api/v1` en el dominio Netlify y **no funcionará** en producción.

## Local sin cambios disruptivos
Docker Compose mantiene su proxy Nginx (solicitudes same-origin a `/api`), el `.env` local, el puerto `8081`, la base local y el panel actual. Usar `docker compose up -d --build` tras aplicar las actualizaciones localmente.

## Seguridad y limitaciones
- No publicar archivos `.env`, contraseñas, JWT, ni datos de clientes.
- Las URLs Netlify Preview necesitan CORS explícito si se usan.
- Las distancias GPS aún son en línea recta. No representan rutas de carretera.
- No hay cobro real ni autenticación multifactor; se requiere endurecimiento antes de operar con clientes reales.
- Los datos de Railway no se migran automáticamente desde tu PostgreSQL local. La DB Railway empezará vacía con el administrador inicial.
