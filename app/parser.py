from sched import scheduler
from httpx import AsyncClient
from bs4 import BeautifulSoup
from app.crud import save_products
from app.database import async_session

BASE_URL = "https://e-katalog.kz/list/298/"

async def fetch_page(client: AsyncClient, url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.text

async def parse_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    items = soup.select(".model-short-div")

    for item in items:
        name_element = item.select_one("a.no-u span.u")
        name = name_element.text.strip() if name_element else "Название не указано"
        price_element = item.select_one(".model-price-range")
        price = price_element.text.replace("\xa0", " ").strip() if price_element else "Цена не указана"
        products.append({"name": name, "price": price})

    return products

async def find_next_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    next_button = soup.select_one("a.pager-next")

    if next_button and "href" in next_button.attrs:
        return "https://e-katalog.kz" + next_button["href"]

    return None

async def scrape_category():
    async with AsyncClient() as client:
        current_url = BASE_URL
        all_products = []

        while current_url:
            html = await fetch_page(client, current_url)
            products = await parse_page(html)
            all_products.extend(products)

            next_page = await find_next_page(html)
            if next_page:
                current_url = next_page
            else:
                break

        return all_products

async def parse_and_save_data():
    products = await scrape_category()
    async with async_session() as session:
        await save_products(session, products)


def stop_parsing_job():
    scheduler.shutdown()


