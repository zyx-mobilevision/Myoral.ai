from fastapi import FastAPI
from routers import update, print,register, login, photoUpload, retrieve, readPhoto, analyze, reminder
from fastapi.middleware.cors  import CORSMiddleware  # Middleware import
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.add_middleware( 
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
 
# Register routers
app.include_router(register.router, prefix="/v1")
app.include_router(login.router, prefix="/v1")
app.include_router(update.router, prefix="/v1")
app.include_router(photoUpload.router, prefix="/v1")
app.include_router(retrieve.router, prefix="/v1")
app.include_router(readPhoto.router, prefix="/v1")
app.include_router(analyze.router, prefix="/v1")
app.include_router(reminder.router, prefix="/v1")
app.include_router(print.router,prefix="/v1")

