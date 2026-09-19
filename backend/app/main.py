from fastapi import FastAPI
from app.core.database import engine,Base
from app.models import user
from app.routes import auth

Base.metadata.create_all(bind=engine)

app=FastAPI()

app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message":"Hello, Backend is working!!"}

@app.get("/test-db")
def test_db():
    try:
        connection=engine.connect()
        connection.close()
        return{"status":"Database connected successfully!!"}
    except Exception as e:
        return{"status":"Database connection failed","error":str(e)}