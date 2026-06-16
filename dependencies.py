from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.auth import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_student(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=401, 
            detail="Invalid token"
            )
    return user