import json
import ssl
from pathlib import Path
from utils.collect_product_data import collect_data
from utils.load_in_excel import write_data_to_excel
from utils.prepare_work import preparation_before_work
from utils.scroll import page_down
from utils.write_products_urls_in_file import write_products_urls

ssl._create_default_https_context = ssl._create_unverified_context

def main() -> None:
    """Функция запуска программы."""
    driver = None
    try:
        driver = preparation_before_work(item_name=input('Введите название товара: '))
        products_urls_list = page_down(driver=driver, css_selector="a[href*='/product/']")
        write_products_urls(products_urls=products_urls_list)

        path_urls_products = Path("products_urls_dict_small.json")
        with path_urls_products.open("r", encoding="utf-8") as file:
            products_urls = json.load(file)

        collect_data(products_urls=products_urls, driver=driver)

        path_data_products = Path("PRODUCTS_DATA.json")
        with path_data_products.open("r", encoding="utf-8") as file:
            products_data = json.load(file)

        write_data_to_excel(products_data=products_data)
    finally:
        if driver is not None:
            driver.close()
            driver.quit()

if __name__ == "__main__":
    main()