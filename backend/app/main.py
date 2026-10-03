from app.routes import link_shares
from fastapi import FastAPI
from app.core.database import engine,Base
from app.models import user, folder, file,share, link_share
from app.routes import auth,files,folders,shares
from app.core.supabase_client import supabase, SUPABASE_BUCKET_NAME

Base.metadata.create_all(bind=engine)

app=FastAPI()

app.include_router(auth.router)
app.include_router(files.router)
app.include_router(folders.router)
app.include_router(shares.router)
app.include_router(link_shares.router)

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
    
@app.get("/test-supabase")
def test_supabase():
    try:
        buckets=supabase.storage.list_buckets()
        bucket_names=[b.name for b in buckets]
        return{"status":"Supabase connected","buckets":bucket_names}
    except Exception as e:
        return{"status":"Supabase connection failed","error":str(e)}