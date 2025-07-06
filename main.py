from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from routers import user

app = FastAPI()

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"message": "Hello"}


prefix = "/api"
app.include_router(user.user_router, prefix=prefix)
# app.include_router(room.room_router, prefix=prefix)
# app.include_router(game.game_router, prefix=prefix)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
