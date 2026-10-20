> **Despliegue Railway + Netlify:** consulte [`DEPLOY_RAILWAY_NETLIFY.md`](DEPLOY_RAILWAY_NETLIFY.md).

**Última versión: v0.3.0. GPS, tarifas y despacho en vivo.** Consulte [actualización v0.3.0](ACTUALIZACION_v0.3.0.md).

# DEGARITAO Express — Plataforma MVP v0.2.0

**Un centro de despacho y dos servicios:** Delivery (mensajería/paquetería) y Asistencia Vial (grúas, remolque y auxilio).

Este repositorio es un **MVP funcional para pruebas controladas**, no una plataforma autorizada para atender servicios pagados en producción. No modificar el repositorio histórico `backend_gruas_go` sin evaluar y migrar datos existentes.

## Tecnologías

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PyJWT.
- **Base de datos:** PostgreSQL 17 (Docker) o SQLite temporal para desarrollo/pruebas.
- **Frontend:** React 19, TypeScript, Vite; usa la identidad gráfica DEGARITAO Express aprobada.
- **Despliegue local:** Docker Compose con API, PostgreSQL y panel web Nginx.

## Cómo ejecutar (Windows 11, macOS o Linux con Docker Desktop)

1. Descomprimir este proyecto y abrir una terminal en `DEGARITAO_Express_Plataforma_MVP`.
2. Copiar `.env.example` a `.env`.
3. Generar una clave JWT **única** y sustituir `JWT_SECRET`:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

4. Ajustar también `POSTGRES_PASSWORD`, el mismo valor dentro de `DATABASE_URL` y las variables `ADMIN_EMAIL` y `ADMIN_PASSWORD` en `.env`. No subir `.env` a Git.
5. Ejecutar:

   ```bash
   docker compose up -d --build db
   docker compose run --rm api alembic upgrade head
   docker compose run --rm api python -m scripts.create_admin
   docker compose up -d --build
   ```

6. Abrir el panel **http://localhost:8081**. API documentada en **http://localhost:8000/docs**. Acceder con los datos de administrador configurados en `.env`.

**Nota de seguridad:** Los contenedores están configurados para entorno local. No exponer los puertos del panel ni de API a Internet sin HTTPS, gestión de secretos, autenticación reforzada, limitación de peticiones, monitoreo y controles adicionales.

## Ejecución local de backend sin Docker

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
# exportar DATABASE_URL=sqlite:///./degaritao-dev.db y JWT_SECRET de al menos 32 caracteres
alembic upgrade head
# exportar ADMIN_EMAIL y ADMIN_PASSWORD
python -m scripts.create_admin
uvicorn app.main:app --reload
```

## Ejecución frontend de desarrollo (requiere acceso a npm)

```bash
cd frontend
npm install
npm run dev
```

El frontend utiliza proxy de Vite a la API local `localhost:8000`, panel en `localhost:5173`.

## Flujo completo

1. Administrador crea usuarios y operadores (Delivery o Vial).
2. Un operador nuevo queda **pendiente**: la homologación exige licencia, matrícula, póliza, fechas vigentes y aprobación de un administrador; cambios revocan la aprobación.
3. Despacho o comercio registra una solicitud y sus datos de contacto y dirección.
4. Despacho establece la cotización y el pago propuesto al operador.
5. Despacho asigna únicamente operadores activos, verificados y de la misma modalidad.
6. La solicitud pasa por **Asignado → En ruta → En sitio → Completado**; Delivery también puede completar desde *En ruta*.
7. El cierre exige una nota de comprobante o resultado. Los cambios quedan auditados en el historial.

**Limitación:** La captura de cotización no prueba aceptación del cliente ni realiza cobro. Antes del primer servicio pagado, implementar la aceptación verificable de tarifa, flujo fiscal, pasarela de pago si se va a usar y protocolo de incidencias. Los estados son operativos, no constancias legales.

## Seguridad y aislamiento

- Autenticación con JWT firmado; contraseña hasheada PBKDF2-SHA256 con sal aleatoria.
- Roles: `admin`, `dispatcher`, `merchant`, `driver`.
- Filtrado de `company_id` y visibilidad por función; comerciantes ven sus solicitudes y conductores solo las asignadas.
- Separación de modalidades (Delivery ≠ Roadside) y bloqueo de operadores no verificados.
- Sin clave secreta en el código ni registros de contraseñas recibidas.

**Importante:** PBKDF2 es adecuado como base MVP, pero aún faltan protección anti fuerza bruta, auditoría centralizada, cookies HttpOnly si se decide migrar desde tokens en sessionStorage, backups, retención de datos y pruebas de penetración para producción.

## API principal

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/v1/auth/login` | Login y JWT |
| GET | `/api/v1/auth/me` | Usuario actual |
| GET / POST | `/api/v1/users` | Usuarios (admin) |
| GET / POST | `/api/v1/operators` | Operadores por unidad |
| PATCH | `/api/v1/operators/{id}/verification` | Verificación documentada |
| GET / POST | `/api/v1/services` | Solicitudes |
| GET | `/api/v1/services/{id}` | Detalles e historial |
| POST | `/api/v1/services/{id}/quote` | Cotización controlada por despacho |
| POST | `/api/v1/services/{id}/assign` | Asignación verificada |
| POST | `/api/v1/services/{id}/status` | Transiciones de estado |
| GET | `/api/v1/dashboard` | Contadores por unidad |
| GET | `/health` | Estado básico de API |

Ejemplo de solicitud para `POST /api/v1/services`:

```json
{
  "kind": "delivery",
  "service_type": "parcel",
  "customer_name": "Cliente Demo",
  "customer_phone": "8095550000",
  "pickup_address": "Santo Domingo, República Dominicana",
  "destination_address": "Santo Domingo Este, República Dominicana",
  "notes": "Paquete pequeño"
}
```

Servicios Viales: `tow`, `jumpstart`, `tire_change`, `fuel`, `mechanical`. Delivery: `parcel`, `scheduled_route`.

## Pruebas

```bash
cd backend
PYTHONPATH=. pytest -q
```

En Windows PowerShell: `$env:PYTHONPATH='.'; pytest -q`.

El resultado de referencia en el entorno de desarrollo fue **11 pruebas aprobadas**. Se ejecutaron pruebas de lógica y migración usando SQLite, **no PostgreSQL en Docker**, porque el entorno que generó este paquete no dispone de Docker ni de dependencias npm descargables.

## Documentación adicional

- `docs/ARQUITECTURA_Y_RIESGOS.md`
- `docs/MIGRACION_DESDE_GRUASGO.md`
- `docs/PLAN_SIGUIENTES_SPRINTS.md`
- `docs/QA_RESULTADOS.md`

## Identidad visual

`frontend/public/degaritao-express.svg` y `frontend/public/favicon.ico` provienen del kit técnico de Express aprobado. Los SVG son reconstrucciones técnicas previas del diseño aprobado y pueden requerir ajuste de contornos antes de impresión industrial.


## Actualización desde v0.1.x

Consulta [ACTUALIZACION_v0.2.0.md](ACTUALIZACION_v0.2.0.md): instrucciones seguras para Windows, respaldo automático y migración de PostgreSQL sin borrar solicitudes.


## Actualización v0.2.1

Incluye interfaz homogénea de homologación (estados en español, checklist, historial visible) y confirmación documental obligatoria en el servidor para decisiones de aprobación. No incorpora migraciones nuevas: se mantiene el esquema v0.2.0.

**Si estás usando v0.2.0 con datos existentes**, instala el parche `DEGARITAO_Express_PARCHE_v0.2.1.zip` en lugar de reemplazar manualmente el proyecto. El instalador respalda PostgreSQL, no altera `.env` y actualiza los contenedores.
