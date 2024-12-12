from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.models import Base
from app.database import engine
from app.crud import get_parsed_data, update_product, delete_product, delete_all_products
from app.parser import parse_and_save_data
from pydantic import BaseModel

app = FastAPI()

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
    Обновляет продукт по его ID.
    """
    updated_product = await update_product(db, product_id, product.name, product.price)
    if updated_product:
        return updated_product
    raise HTTPException(status_code=404, detail="Product not found")


@app.delete("/products/{product_id}")
async def delete_product_endpoint(product_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаляет продукт по его ID.
    """
    success = await delete_product(db, product_id)
    if success:
        return {"message": f"Product with ID {product_id} deleted successfully"}
    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/products/")
async def delete_all(db: AsyncSession = Depends(get_db)):
    try:
        await delete_all_products(db)
        return {"message": "All products deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while deleting products")

