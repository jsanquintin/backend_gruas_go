from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.dependencies import get_db
from app.crud.user import get_users, get_user_by_id, get_user_by_email, update_user_profile, update_user_password
from app.schemas.user import UserOut, UpdateUserSchema, UpdatePasswordSchema  
from app.core.security import get_current_user, verify_password, get_password_hash

router = APIRouter()


# Obtener lista de usuarios (Solo Administradores)
@router.get("/", response_model=List[UserOut], summary="Listar Usuarios", description="Devuelve una lista de todos los usuarios registrados. Solo accesible para administradores.")
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Devuelve una lista de todos los usuarios registrados.  
    ⚠️ **Solo accesible para administradores.**
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta ruta."
        )
    
    users = get_users(db)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron usuarios."
        )
    return users


# Obtener un usuario por ID (Autenticado)
@router.get("/{user_id}", response_model=UserOut, summary="Obtener Usuario por ID", description="Devuelve los detalles de un usuario específico mediante su ID.")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Devuelve los detalles de un usuario específico mediante su ID.  
    ⚠️ **Accesible para usuarios autenticados.**
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
    return user

# Actualizar Perfil del Usuario Autenticado
@router.put("/me", summary="Actualizar Perfil de Usuario", description="Permite actualizar el nombre y correo electrónico del usuario autenticado.")
async def update_profile(
    data: UpdateUserSchema,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualiza el nombre y/o correo electrónico del usuario autenticado.  
    ⚠️ **Accesible para usuarios autenticados.**
    """
    updated_user = update_user_profile(db, current_user["email"], data.name, data.email)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {
        "message": "Perfil actualizado correctamente",
        "user": {
            "id": updated_user.id,
            "name": updated_user.name,
            "email": updated_user.email,
            "role": updated_user.role
        }
    }

@router.put("/me/password", summary="Actualizar Contraseña", description="Permite actualizar la contraseña del usuario autenticado.")
async def update_password(
    data: UpdatePasswordSchema,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualiza la contraseña de un usuario autenticado.
    ⚠️ **Requiere autenticación.**
    """
    user = get_user_by_email(db, current_user["email"])
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta."
        )

    new_hashed_password = get_password_hash(data.new_password)
    update_user_password(db, user.id, new_hashed_password)

    return {"message": "Contraseña actualizada correctamente"}

@router.delete("/me", summary="Eliminar Cuenta de Usuario", description="Permite eliminar la cuenta del usuario autenticado.")
async def delete_account(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina la cuenta del usuario autenticado.
    ⚠️ **Requiere autenticación.**
    """
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    db.delete(user)
    db.commit()

    return {"message": "Cuenta eliminada correctamente"}



