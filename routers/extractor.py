from settings import get_CognitoSettings
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException

settings = get_CognitoSettings()

REGION = settings.REGION
USERPOOL_ID = settings.USERPOOL_ID
APP_CLIENT_ID = settings.APP_CLIENT_ID
JWKS_URL = (
    f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"
)

# PyJWKClient を使用して クライアント作成
jwks_client = PyJWKClient(JWKS_URL)


def get_token_from_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    parts = auth_header.split()
    if parts[0].lower() != "bearer" or len(parts) == 1:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1]


def verify_cognito_jwt(token: str) -> dict:
    try:
        # 公開鍵の取得
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=APP_CLIENT_ID,
            issuer=f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}",
            options={"require": ["exp", "iat", "iss", "sub"], "verify_aud": True},
        )
        return data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Token validation failed: {str(e)}"
        )


def extract_user_id_from_token(request: Request) -> str:
    token = get_token_from_header(request)
    user_data = verify_cognito_jwt(token)
    user_id = user_data.get("sub")
    return user_id
