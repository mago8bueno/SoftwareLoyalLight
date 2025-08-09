# app/api/admin.py
from fastapi import APIRouter, Header, HTTPException, status
from app.core.settings import settings
from app.db.supabase import supabase
from passlib.context import CryptContext

router = APIRouter()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS_TO_SEED = [
    # Cambia los correos/contraseñas que necesites
    {"email": "cliente1@example.com", "name": "Cliente 1", "password": "Cliente1!23", "role": "user"},
    {"email": "cliente2@example.com", "name": "Cliente 2", "password": "Cliente2!23", "role": "user"},
    {"email": "cliente3@example.com", "name": "Cliente 3", "password": "Cliente3!23", "role": "user"},
    {"email": "cliente4@example.com", "name": "Cliente 4", "password": "Cliente4!23", "role": "user"},
    {"email": "cliente5@example.com", "name": "Cliente 5", "password": "Cliente5!23", "role": "user"},
    {"email": "cliente6@example.com", "name": "Cliente 6", "password": "Cliente6!23", "role": "user"},
    {"email": "cliente7@example.com", "name": "Cliente 7", "password": "Cliente7!23", "role": "user"},
    {"email": "cliente8@example.com", "name": "Cliente 8", "password": "Cliente8!23", "role": "user"},
    {"email": "cliente9@example.com", "name": "Cliente 9", "password": "Cliente9!23", "role": "user"},
    {"email": "cliente10@example.com", "name": "Cliente 10", "password": "Cliente10!23", "role": "user"},
    # Si quieres, también un segundo admin
    # {"email": "manager@example.com", "name": "Manager", "password": "Manager!23", "role": "admin"},
]

@router.post("/seed-users", tags=["admin"])
def seed_users(x_seed_token: str = Header(default="")):
    if not settings.SEED_TOKEN or x_seed_token != settings.SEED_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    created, skipped = [], []

    for u in USERS_TO_SEED:
        # idempotente: si existe por email, saltamos
        exists = supabase.table("users").select("id").eq("email", u["email"]).execute()
        if exists.data:
            skipped.append(u["email"])
            continue

        hashed = pwd.hash(u["password"])
        ins = supabase.table("users").insert({
            "email": u["email"],
            "name": u["name"],
            "password_hash": hashed,
            "role": u["role"],
        }).execute()

        if ins.error:
            raise HTTPException(status_code=400, detail=str(ins.error.message))
        created.append(u["email"])

    return {"created": created, "skipped": skipped}
