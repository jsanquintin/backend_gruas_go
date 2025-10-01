from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: str
    name: str

class UserCreate(UserBase):
    password: str
    role_id: int  # ⬅️ en lugar de 'role: str'

class UserOut(UserBase):
    id: int
    role_id: int  # ⬅️ también corregido aquí

    class Config:
        orm_mode = True

# Esquema para actualizar perfil
class UpdateUserSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

    class Config:
        orm_mode = True

class UpdatePasswordSchema(BaseModel):
    old_password: str
    new_password: str
