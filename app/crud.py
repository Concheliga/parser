from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Product
from typing import List, Dict

async def save_products(db: AsyncSession, products: List[Dict]):
    for product in products:
        db.add(Product(name=product["name"], price=product["price"]))
    await db.commit()


async def delete_product(db: AsyncSession, product_id: int):
    """
    Удаляет продукт из базы данных по ID.
    """
    product = await db.get(Product, product_id)
    if product:
        await db.delete(product)
        await db.commit()
        return True
    return False


async def update_product(db: AsyncSession, product_id: int, name: str, price: str):
    """
    Обновляет данные продукта в базе данных по ID.
    """
    # Получаем продукт по ID
    product = await db.get(Product, product_id)

    if product:
        # Обновляем поля
        product.name = name
        product.price = price

        # Сохраняем изменения
        await db.commit()
        await db.refresh(product)

        return product
    return None

async def delete_all_products(db: AsyncSession):
    # Удаляем все записи из таблицы Product
    result = await db.execute(select(Product))
    products = result.scalars().all()
    for product in products:
        await db.delete(product)
    await db.commit()

    # Сбрасываем счетчик последовательности для Product
    await db.execute(text("ALTER SEQUENCE products_id_seq RESTART WITH 1"))
    await db.commit()

async def get_parsed_data(db: AsyncSession):
    # Добавление сортировки по 'id'
    result = await db.execute(select(Product).order_by(Product.id))  # сортировка по 'id'
    return result.scalars().all()
