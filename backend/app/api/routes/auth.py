"""注册和登录接口。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.app.services.auth_service import register, login

router = APIRouter(prefix="/auth", tags=["认证"])
class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=4, max_length=128)
class LoginCredentials(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)

@router.post("/register")
def register_user(data: Credentials):
    try: return register(data.username, data.password)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/login")
def login_user(data: LoginCredentials):
    try: return login(data.username, data.password)
    except ValueError as exc: raise HTTPException(status_code=401, detail=str(exc)) from exc
