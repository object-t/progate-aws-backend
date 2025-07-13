import jwt
from fastapi import Request, HTTPException

def extract_user_id_without_verification(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = auth_header.split()[1]

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid JWT format")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="sub claim missing")
    return user_id