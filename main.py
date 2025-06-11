from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import routers explicitly
from routers.update import router as update_router
from routers.register import router as register_router
from routers.login import router as login_router
from routers.photoUpload import router as photo_upload_router
from routers.retrieve import router as retrieve_router
from routers.readPhoto import router as read_photo_router
from routers.analyze import router as analyze_router

app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware( 
    CORSMiddleware,
    allow_origins=["*"],  # 前端地址 
    allow_methods=["*"],                      # 允许所有 HTTP 方法 
    allow_headers=["*"],                      # 允许所有请求头
)
 
# Include routers with tags for better organization
# User-related endpoints with consistent /v1/users prefix
app.include_router(register_router, prefix="/v1/users", tags=["users"])
app.include_router(update_router, prefix="/v1/users", tags=["users"])
app.include_router(login_router, prefix="/v1/users", tags=["users"])
app.include_router(retrieve_router, prefix="/v1/users", tags=["users"])

# Photo-related endpoints
app.include_router(photo_upload_router, prefix="/v1", tags=["photos"])
app.include_router(read_photo_router, prefix="/v1", tags=["photos"])

# Analysis endpoints
app.include_router(analyze_router, prefix="/v1", tags=["photos"])