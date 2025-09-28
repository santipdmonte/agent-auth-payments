from fastapi import FastAPI
import os

from starlette.middleware.sessions import SessionMiddleware
from routes.users_routes import users_router
from routes.auth_routes import auth_router
from utils.email_utlis import email_router
from database import create_db_and_tables
import uvicorn

create_db_and_tables()

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(email_router)


@app.get("/")
def home():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)