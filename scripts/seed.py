# scripts/seed.py
# Propósito: Sembrar datos de ejemplo en Supabase para clientes, items y compras.

import os
from app.db.supabase import supabase

def main():
    # Cargar secretos desde .env (SUPABASE_URL y SUPABASE_KEY) vía app.core.settings
    # Idempotencia: usamos upsert para evitar duplicados
    clients = [
        {"id": "11111111-1111-1111-1111-111111111111", "name": "Alice", "email": "alice@example.com", "phone": "600111222"},
        {"id": "22222222-2222-2222-2222-222222222222", "name": "Bob",   "email": "bob@example.com",   "phone": "600333444"},
    ]
    items = [
        {"id": "aaaaaaa1-aaaa-aaaa-aaaa-aaaaaaaaaaa1", "name": "T-Shirt", "description": "Camiseta algodón", "price": 19.99, "stock": 50},
        {"id": "bbbbbbb2-bbbb-bbbb-bbbb-bbbbbbbbbbb2", "name": "Jeans",   "description": "Vaqueros slim",    "price": 49.99, "stock": 30},
    ]
    purchases = [
        {"id": "purch000-0000-0000-0000-000000000001", "client_id": clients[0]["id"], "item_id": items[0]["id"], "quantity": 2, "total_price": 39.98},
        {"id": "purch000-0000-0000-0000-000000000002", "client_id": clients[1]["id"], "item_id": items[1]["id"], "quantity": 1, "total_price": 49.99},
    ]

    try:
        # Upsert clients
        for c in clients:
            supabase.table("clients").upsert(c, on_conflict="id").execute()
        # Upsert items
        for i in items:
            supabase.table("items").upsert(i, on_conflict="id").execute()
        # Upsert purchases
        for p in purchases:
            # Asegurar que el cliente y el item existen antes
            supabase.table("purchases").upsert(p, on_conflict="id").execute()

        print("✅ Seed completado con éxito.")
    except Exception as e:
        print(f"❌ Error en seed: {e}")
        exit(1)

if __name__ == "__main__":
    main()

# Buenas prácticas:
# - Gestión de secretos: .env sin subir a VCS, cargado por app.core.settings.
# - Idempotencia: uso de upsert para no duplicar entradas.
# - Manejo de errores: captura genérica para abortar con código != 0.
