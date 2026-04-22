from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


frontend_router = APIRouter(tags=["Frontend"])
templates = Jinja2Templates(directory="app/html_templates")


@frontend_router.get("/admin")
def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@frontend_router.get("/admin/read")
def read_variables_page(request: Request):
    return templates.TemplateResponse("read.html", {"request": request})

@frontend_router.get("/admin/create")
def create_variables_page(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@frontend_router.get("/admin/delete")
def delete_variables_page(request: Request):
    return templates.TemplateResponse("delete.html", {"request": request})