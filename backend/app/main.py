from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api.routes import router
from app.core.config import settings

app=FastAPI(title=settings.app_name,version="1.0.0",description="API quản lý Daily Report và báo cáo tuần")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000","http://localhost:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
@app.get("/health",tags=["System"])
def health(): return {"status":"ok"}
@app.exception_handler(RequestValidationError)
async def validation_error(_:Request,exc:RequestValidationError):
    return JSONResponse(status_code=422,content={"detail":"Dữ liệu không hợp lệ","errors":[{"field":".".join(str(x) for x in e["loc"]),"message":e["msg"]} for e in exc.errors()]})

