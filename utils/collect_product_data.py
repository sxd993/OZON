import json
import logging
import time
from pathlib import Path


from selenium.webdriver.chrome.webdriver import WebDriver

from utils.product_data import collect_product_info


def writing_product_data_in_file(
    products_data: dict[str, dict[str, str | None]],
) -> None:
    """Функция для запиши данных в файл."""
    path = Path("PRODUCTS_DATA.json")
    with path.open("w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=4, ensure_ascii=False)


def collect_data(
    products_urls: dict[str, str],
    driver: WebDriver,
) -> None:
    """Функция сбора данных."""
    products_data = {}

    for url in products_urls.values():
        data = collect_product_info(driver=driver, url=url)
        logging.warning(f'[+] Собрал данные товара с id: {data.get("Артикул")}')
        time.sleep(1)
        if data.get("Артикул") not in products_data:
            products_data[data.get("Артикул")] = data

    writing_product_data_in_file(products_data=products_data)  # type:ignore[arg-type]