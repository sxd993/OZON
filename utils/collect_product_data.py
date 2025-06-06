import json
from pathlib import Path
from selenium.webdriver.chrome.webdriver import WebDriver
from utils.product_data import collect_product_info
from utils.load_in_excel import write_data_to_excel


def writing_product_data_in_file(
    products_data: dict[str, dict[str, str | None]], filename: str
) -> None:
    """Функция для записи данных в файл."""
    path = Path("PRODUCTS_DATA.json")
    with path.open("w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=4, ensure_ascii=False)


def collect_data(products_urls: dict[str, str], driver: WebDriver, progress_handler=None, output_file: str = "ozon_products.xlsx") -> None:
    """Функция сбора данных."""
    products_data = {}
    if progress_handler:
        progress_handler.set_total(len(products_urls))
    processed_count = 0

    for url in products_urls.values():
        data = collect_product_info(driver=driver, url=url)
        product_id = data.get("Артикул")
        if product_id is None:
            continue
        if product_id not in products_data:
            products_data[product_id] = data
        processed_count += 1
        if progress_handler:
            progress_handler.update()

        # Сохраняем данные в Excel каждые 2 продукта
        if processed_count % 2 == 0:
            write_data_to_excel(products_data=products_data,
                                filename=output_file)

    # Сохраняем оставшиеся данные в Excel и JSON
    if products_data:
        write_data_to_excel(products_data=products_data, filename=output_file)
    writing_product_data_in_file(
        products_data=products_data, filename=output_file)
