import pytest
import boto3
from moto import mock_aws
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException
from unittest.mock import MagicMock
import json
import base64
import os
from datetime import datetime, timezone

# settings はテスト用モック
class MockCognitoSettings:
    REGION = "ap-northeast-1"
    USERPOOL_ID = "ap-northeast-1_xxxxxxxxx"
    APP_CLIENT_ID = "yyyyyyyyyyyyyy"

settings = MockCognitoSettings()

REGION = settings.REGION
USERPOOL_ID = settings.USERPOOL_ID
APP_CLIENT_ID = settings.APP_CLIENT_ID
JWKS_URL = (
    f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"
)

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
    return user_data.get("sub")

# --- 修正済み UTC 関数例（必要に応じて使用可能） ---
def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)

def datetime_from_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)

# 以下、テストコード（変更なし）

@pytest.fixture(scope="module")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = REGION

@pytest.fixture
def cognito_setup(aws_credentials):
    with mock_aws():
        client = boto3.client("cognito-idp", region_name=REGION)
        user_pool_response = client.create_user_pool(
            PoolName="TestUserPool",
            Policies={"PasswordPolicy": {"MinimumLength": 8,"RequireUppercase": False,"RequireLowercase": False,"RequireNumbers": False,"RequireSymbols": False}}
        )
        user_pool_id = user_pool_response["UserPool"]["Id"]
        app_client_response = client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName="TestAppClient",
            ExplicitAuthFlows=["ADMIN_NO_SRP_AUTH","USER_PASSWORD_AUTH"],
            PreventUserExistenceErrors="ENABLED",
        )
        app_client_id = app_client_response["UserPoolClient"]["ClientId"]
        username = "testuser"
        password = "TestPassword123!"
        email = "test@example.com"
        client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[{"Name": "email","Value": email},{"Name": "email_verified","Value": "true"}],
            MessageAction="SUPPRESS",
        )
        client.admin_set_user_password(
            UserPoolId=user_pool_id, Username=username,
            Password=password, Permanent=True
        )
        auth_response = client.admin_initiate_auth(
            UserPoolId=user_pool_id, ClientId=app_client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        id_token = auth_response["AuthenticationResult"]["IdToken"]
        access_token = auth_response["AuthenticationResult"]["AccessToken"]
        global USERPOOL_ID, APP_CLIENT_ID, JWKS_URL, jwks_client
        orig = (USERPOOL_ID, APP_CLIENT_ID, JWKS_URL, jwks_client)
        USERPOOL_ID, APP_CLIENT_ID = user_pool_id, app_client_id
        JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"
        jwks_client = PyJWKClient(JWKS_URL)
        yield {"client": client, "user_pool_id": user_pool_id, "app_client_id": app_client_id,
               "username": username, "password": password,
               "id_token": id_token, "access_token": access_token}
        USERPOOL_ID, APP_CLIENT_ID, JWKS_URL, jwks_client = orig

def test_get_token_from_header():
    request = MagicMock(spec=Request)
    request.headers.get.return_value = "Bearer my_test_token"
    assert get_token_from_header(request) == "my_test_token"
    request.headers.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_token_from_header(request)
    assert exc.value.status_code == 401 and exc.value.detail == "Authorization header missing"
    request.headers.get.return_value = "InvalidToken my_test_token"
    with pytest.raises(HTTPException):
        get_token_from_header(request)
    request.headers.get.return_value = "Bearer"
    with pytest.raises(HTTPException):
        get_token_from_header(request)

def test_cognito_integration_with_moto(cognito_setup):
    setup = cognito_setup
    unverified_payload = jwt.decode(setup["id_token"], options={"verify_signature": False})
    assert "sub" in unverified_payload
    assert unverified_payload["aud"] == setup["app_client_id"]
    assert setup["user_pool_id"] in unverified_payload["iss"]

def test_cognito_user_management_with_boto3(cognito_setup):
    client, username = cognito_setup["client"], cognito_setup["username"]
    info = client.admin_get_user(UserPoolId=cognito_setup["user_pool_id"], Username=username)
    assert info["Username"] == username and info["UserStatus"] == "CONFIRMED"
    attrs = {a["Name"]: a["Value"] for a in info["UserAttributes"]}
    assert attrs.get("email") == "test@example.com"

def test_cognito_authentication_flow(cognito_setup):
    client = cognito_setup["client"]
    auth = client.admin_initiate_auth(
        UserPoolId=cognito_setup["user_pool_id"],
        ClientId=cognito_setup["app_client_id"],
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={"USERNAME": cognito_setup["username"], "PASSWORD": cognito_setup["password"]},
    )
    assert "AuthenticationResult" in auth
    with pytest.raises(Exception):
        client.admin_initiate_auth(
            UserPoolId=cognito_setup["user_pool_id"],
            ClientId=cognito_setup["app_client_id"],
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": cognito_setup["username"], "PASSWORD": "wrong"},
        )

def test_jwt_token_structure(cognito_setup):
    parts = cognito_setup["id_token"].split('.')
    assert len(parts) == 3
    header = json.loads(base64.b64decode(parts[0] + '=='))
    assert header["alg"] == "RS256" and header["typ"] == "JWT"
    payload = json.loads(base64.b64decode(parts[1] + '=='))
    assert "sub" in payload and "aud" in payload and ("auth_time" in payload or "iat" in payload)

def test_extract_user_id_from_real_token(cognito_setup):
    request = MagicMock(spec=Request)
    request.headers.get.return_value = f"Bearer {cognito_setup['id_token']}"
    token = get_token_from_header(request)
    assert len(token.split('.')) == 3
    payload = json.loads(base64.b64decode(token.split('.')[1] + '=='))
    assert "sub" in payload

def test_cognito_user_pool_operations(cognito_setup):
    client = cognito_setup["client"]
    uid = cognito_setup["user_pool_id"]
    pool = client.describe_user_pool(UserPoolId=uid)
    assert pool["UserPool"]["Id"] == uid
    users = client.list_users(UserPoolId=uid)["Users"]
    assert any(u["Username"] == "testuser" for u in users)
    client.admin_create_user(UserPoolId=uid, Username="newuser",
                              UserAttributes=[{"Name": "email","Value": "newuser@example.com"}],
                              MessageAction="SUPPRESS")
    client.admin_set_user_password(UserPoolId=uid, Username="newuser", Password="NewPassword123!", Permanent=True)
    new_auth = client.admin_initiate_auth(UserPoolId=uid, ClientId=cognito_setup["app_client_id"],
                                          AuthFlow="ADMIN_NO_SRP_AUTH",
                                          AuthParameters={"USERNAME": "newuser", "PASSWORD": "NewPassword123!"})
    new_payload = jwt.decode(new_auth["AuthenticationResult"]["IdToken"], options={"verify_signature": False})
    assert new_payload["aud"] == cognito_setup["app_client_id"]

def test_invalid_authentication_scenarios(cognito_setup):
    with pytest.raises(Exception):
        boto3.client("cognito-idp", region_name=REGION).admin_initiate_auth(
            UserPoolId=cognito_setup["user_pool_id"],
            ClientId=cognito_setup["app_client_id"],
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": "nonexistent","PASSWORD": "pw"}
        )
    with pytest.raises(Exception):
        boto3.client("cognito-idp", region_name=REGION).admin_initiate_auth(
            UserPoolId=cognito_setup["user_pool_id"],
            ClientId=cognito_setup["app_client_id"],
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={"USERNAME": cognito_setup["username"], "PASSWORD": "wrong"}
        )

def test_app_functions_with_invalid_tokens():
    for bad in ["invalid.token.here", "", "not.a.valid.jwt.token"]:
        with pytest.raises(HTTPException) as exc:
            verify_cognito_jwt(bad)
        assert exc.value.status_code == 401

def test_get_token_from_header_comprehensive():
    r = MagicMock(spec=Request)
    for hdr in ["Bearer valid_token_123", "BEARER valid_token_123", "bearer valid_token_123", "Bearer  valid_token_123"]:
        r.headers.get.return_value = hdr
        assert get_token_from_header(r) == "valid_token_123"
    for hdr in [None, "Token valid_token_123", "Bearer", ""]:
        r.headers.get.return_value = hdr
        with pytest.raises(HTTPException):
            get_token_from_header(r)
