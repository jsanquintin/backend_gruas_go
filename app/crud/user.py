from sqlalchemy.orm import Session
from app.database.models import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash
from typing import Optional 

# Obtener un usuario por ID
def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Devuelve un usuario por su ID.
    """
    return db.query(User).filter(User.id == user_id).first()


# Obtener un usuario por email
def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Devuelve un usuario por su email.
    """
    return db.query(User).filter(User.email == email).first()


# Crear un nuevo usuario
def create_user(db: Session, user: UserCreate) -> User:
    """
    Crea un nuevo usuario en la base de datos.
    """
    hashed_password = get_password_hash(user.password)  # Hashing seguro
    db_user = User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password,
        role_id=user.role_id,        
        created_by="systems"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Actualizar contraseña de un usuario
def update_user_password(db: Session, user_id: int, new_hashed_password: str) -> bool:
    """
    Actualiza la contraseña de un usuario.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.hashed_password = new_hashed_password
        db.commit()
        db.refresh(user)
        return True
    return False


# Actualizar perfil de un usuario
def update_user_profile(db: Session, email: str, name: Optional[str], new_email: Optional[str]):
    """
    Actualiza el nombre y/o correo electrónico de un usuario autenticado.
    """
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.name = name if name else user.name
        user.email = new_email if new_email else user.email
        db.commit()
        db.refresh(user)
        return user
    return None


# Obtener todos los usuarios
def get_users(db: Session) -> list[User]:
    """
    Devuelve una lista de todos los usuarios.
    """
    return db.query(User).all()

def update_user_password(db: Session, user_id: int, new_hashed_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.hashed_password = new_hashed_password
        db.commit()
        db.refresh(user)
        return user
    return None


