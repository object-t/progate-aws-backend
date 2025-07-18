from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from routers import play
from routers import share
from routers import costs

app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://dmwfbfheezrkk.cloudfront.net"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"message": "Hello!"}


@app.get("/production/health")
def health_health_check():
    return {"message": "Hello!"}


app.include_router(play.play_router)
app.include_router(share.share_router)
app.include_router(costs.costs_router)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
