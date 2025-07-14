from fastapi import FastAPI
from routers import update, print,register, login, photoUpload, retrieve, readPhoto, analyze, reminder
from fastapi.middleware.cors  import CORSMiddleware  # 导入中间件
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.add_middleware( 
    CORSMiddleware,
    allow_origins=["*"],  # 前端地址 
    allow_methods=["*"],                      # 允许所有 HTTP 方法 
    allow_headers=["*"],                      # 允许所有请求头
)
 
# Include routers
app.include_router(register.router, prefix="/v1")
app.include_router(login.router, prefix="/v1")
app.include_router(update.router, prefix="/v1")
app.include_router(photoUpload.router, prefix="/v1")
app.include_router(retrieve.router, prefix="/v1")
app.include_router(readPhoto.router, prefix="/v1")
app.include_router(analyze.router, prefix="/v1")
app.include_router(reminder.router, prefix="/v1")
app.include_router(print.router,prefix="/v1")

