import json
import ssl
from pathlib import Path
from utils.collect_product_data import collect_data
from utils.load_in_excel import write_data_to_excel
from utils.prepare_work import preparation_before_work
from utils.scroll import page_down
from utils.write_products_urls_in_file import write_products_urls

ssl._create_default_https_context = ssl._create_unverified_context


async def main(query: str, max_products: int, output_file: str, progress_handler) -> None:
    """Функция запуска программы."""
    driver = None
    try:
        driver = preparation_before_work(item_name=query)
        products_urls_list = page_down(
            driver=driver, css_selector="a[href*='/product/']", colvo=max_products)
        write_products_urls(products_urls=products_urls_list)

        path_urls_products = Path("products_urls_dict_small.json")
        with path_urls_products.open("r", encoding="utf-8") as file:
            products_urls = json.load(file)

        collect_data(products_urls=products_urls, driver=driver,
                     progress_handler=progress_handler, output_file=output_file)

        path_data_products = Path("PRODUCTS_DATA.json")
        with path_data_products.open("r", encoding="utf-8") as file:
            products_data = json.load(file)

        write_data_to_excel(products_data=products_data, filename=output_file)
    finally:
        if driver is not None:
            driver.close()
            driver.quit()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main(query="смартфон", max_products=1000,
                output_file="ozon_products.xlsx", progress_handler=None))
