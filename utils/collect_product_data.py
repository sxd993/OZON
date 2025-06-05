import json
import time
from pathlib import Path
from selenium.webdriver.chrome.webdriver import WebDriver
from utils.product_data import collect_product_info

def writing_product_data_in_file(
    products_data: dict[str, dict[str, str | None]]) -> None:
    """Функция для записи данных в файл."""
    path = Path("PRODUCTS_DATA.json")
    with path.open("w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=4, ensure_ascii=False)

def collect_data(products_urls: dict[str, str], driver: WebDriver, progress_handler=None) -> None:
    """Функция сбора данных."""
    products_data = {}
    if progress_handler:
        progress_handler.set_total(len(products_urls))
    for url in products_urls.values():
        data = collect_product_info(driver=driver, url=url)
        product_id = data.get("Артикул")
        if product_id is None:
            continue
        time.sleep(1)
        if product_id not in products_data:
            products_data[product_id] = data
        if progress_handler:
            progress_handler.update()
    writing_product_data_in_file(products_data=products_data)