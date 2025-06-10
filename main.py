import warnings
import ssl
import time
import gc
import os
import sys
from contextlib import redirect_stderr
from utils.logger import setup_logger
from utils.collect_product_data import collect_data
from utils.prepare_work import preparation_before_work
from utils.scroll import page_down

warnings.filterwarnings("ignore", message="Exception ignored in.*__del__")

ssl._create_default_https_context = ssl._create_unverified_context

logger = setup_logger()


async def main(
    query: str, max_products: int, output_file: str, progress_handler=None
) -> None:
    """Функция запуска программы."""
    logger.info(f"Запуск парсера с запросом: {query}, максимум товаров: {max_products}")
    driver = None
    try:
        logger.info("Открытие браузера")
        driver = preparation_before_work(item_name=query)
        logger.info("Браузер успешно открыт")
        products_urls_list = page_down(
            driver=driver, css_selector="a[href*='/product/']", colvo=max_products
        )
        logger.info(f"Найдено товаров: {len(products_urls_list)}")
        if len(products_urls_list) >= max_products:
            logger.info(f"Достигнут лимит max_products: {max_products}")
        products_urls = {str(i): url for i, url in enumerate(products_urls_list)}

        collect_data(
            products_urls=products_urls,
            driver=driver,
            progress_handler=progress_handler,
            output_file=output_file,
        )
        logger.info("Сбор данных завершён")
        logger.info(f"Excel-файл сохранён: {output_file}")
    except Exception as e:
        logger.error(f"Ошибка в main: {str(e)}")
    finally:
        if driver is not None:
            try:
                logger.info("Закрытие браузера")
                driver.close()
                time.sleep(0.1)
                driver.quit()
                logger.info("Браузер закрыт")
            except OSError as e:
                logger.warning(f"Ошибка при закрытии драйвера: {str(e)}")
            with open(os.devnull, "w") as devnull:
                with redirect_stderr(devnull):
                    del driver
                    gc.collect()
                    logger.info("Сборка мусора завершена")


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        main(
            query="смартфон",
            max_products=10,
            output_file="ozon_products.xlsx",
            progress_handler=None,
        )
    )
