from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.models import Base
from app.database import engine
from app.crud import get_parsed_data, update_product, delete_product, delete_all_products
from app.parser import parse_and_save_data, stop_parsing_job
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client left the chat")

class ProductResponse(BaseModel):
    id: int
    name: str
    price: str

    class Config:
        orm_mode = True

# Создаем таблицы
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Запускаем планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(parse_and_save_data, "interval", minutes=60)  # Парсинг каждые 60 минут
    scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    stop_parsing_job()


@app.get("/products/", response_model=List[ProductResponse])
async def get_products(db: AsyncSession = Depends(get_db)):
    products = await get_parsed_data(db)
    return products

@app.post("/parse/")
async def parse_data(db: AsyncSession = Depends(get_db)):
    """
    Эндпоинт для запуска парсинга данных.
    """
    try:
        await parse_and_save_data()
        return {"message": "Parsing started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during parsing: {str(e)}")


class ProductUpdate(BaseModel):
    name: str
    price: str

@app.put("/products/{product_id}")
async def update_product_endpoint(product_id: int, product: ProductUpdate, db: AsyncSession = Depends(get_db)):
    """
    Обновляет продукт по его ID и отправляет уведомление через WebSocket.
    """
    updated_product = await update_product(db, product_id, product.name, product.price)
    if updated_product:
        await manager.broadcast(f"Product updated: {product_id}")
        return updated_product
    raise HTTPException(status_code=404, detail="Product not found")



@app.delete("/products/{product_id}")
async def delete_product_endpoint(product_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаляет продукт по его ID и отправляет уведомление через WebSocket.
    """
    success = await delete_product(db, product_id)
    if success:
        await manager.broadcast(f"Product deleted: {product_id}")
        return {"message": f"Product with ID {product_id} deleted successfully"}
    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/products/")
async def delete_all(db: AsyncSession = Depends(get_db)):
    try:
        await delete_all_products(db)
        await manager.broadcast("All products deleted")
        return {"message": "All products deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while deleting products")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)