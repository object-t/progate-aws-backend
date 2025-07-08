from pydantic import BaseModel

class UserName(BaseModel):
    username: str

class User(UserName):
    UserId: str