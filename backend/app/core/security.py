from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.base import get_db
from app.models.entities import Role, User

password_hasher=PasswordHash.recommended()
bearer=HTTPBearer(auto_error=False)
def hash_password(password:str)->str: return password_hasher.hash(password)
def verify_password(password:str, hashed:str)->bool: return password_hasher.verify(password,hashed)
def create_token(user:User)->str:
    now=datetime.now(timezone.utc)
    return jwt.encode({"sub":str(user.id),"role":user.role.value,"iat":now,"exp":now+timedelta(minutes=settings.access_token_expire_minutes)},settings.jwt_secret_key,algorithm="HS256")
def get_current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),db:Session=Depends(get_db))->User:
    unauthorized=HTTPException(status.HTTP_401_UNAUTHORIZED,"Phiên đăng nhập không hợp lệ hoặc đã hết hạn",headers={"WWW-Authenticate":"Bearer"})
    if not credentials: raise unauthorized
    try: user_id=int(jwt.decode(credentials.credentials,settings.jwt_secret_key,algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError,KeyError,ValueError): raise unauthorized
    user=db.get(User,user_id)
    if not user or not user.is_active: raise unauthorized
    return user
def require_admin(user:User=Depends(get_current_user))->User:
    if user.role != Role.ADMIN: raise HTTPException(status.HTTP_403_FORBIDDEN,"Bạn không có quyền thực hiện thao tác này")
    return user

