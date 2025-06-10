from selenium.webdriver.chrome.webdriver import WebDriver
from utils.product_data import collect_product_info
from utils.load_in_excel import write_data_to_excel
from utils.logger import setup_logger

logger = setup_logger()


def collect_data(
    products_urls: dict[str, str],
    driver: WebDriver,
    progress_handler=None,
    output_file: str = "ozon_products.xlsx",
) -> None:
    """Функция сбора данных."""
    products_data = {}
    if progress_handler:
        progress_handler.set_total(len(products_urls))
    processed_count = 0

    for url in products_urls.values():
        processed_count += 1
        logger.info(f"Обработка товара {processed_count}")
        data = collect_product_info(driver=driver, url=url)
        product_id = data.get("Артикул")
        if product_id is None:
            continue
        if product_id not in products_data:
            products_data[product_id] = data
        if progress_handler:
            progress_handler.update()

        if processed_count % 2 == 0:
            write_data_to_excel(products_data=products_data, filename=output_file)

    if products_data:
        write_data_to_excel(products_data=products_data, filename=output_file)
