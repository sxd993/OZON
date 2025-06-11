import warnings
import ssl
import gc
import os
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
    logger.info(f"Запуск парсера с запросом: {query}")
    driver = None
    original_window = None
    worker_tab = None
    try:
        logger.info("Инициализация браузера")
        driver = preparation_before_work(item_name=query)
        original_window = driver.current_window_handle
        logger.info("Браузер успешно открыт")
        products_urls_list = page_down(
            driver=driver,
            css_selector="a[href*='/product/']",
            colvo=max_products,
            # Уникальный файл для каждого запроса
            temp_file=f"temp_links_{query.replace(' ', '_')}.txt"
        )
        logger.info(f"Найдено товаров: {len(products_urls_list)}")
        products_urls = {
            str(i): url for i, url in enumerate(products_urls_list)
        }

        driver.execute_script("window.open('');")
        worker_tab = driver.window_handles[-1]
        driver.switch_to.window(worker_tab)
        logger.info("Рабочая вкладка открыта")

        collect_data(
            products_urls=products_urls,
            driver=driver,
            progress_handler=progress_handler,
            output_file=output_file,
        )
        logger.info(f"Excel-файл сохранён: {output_file}")
    except Exception as e:
        logger.error(f"Ошибка в main: {e}")
        raise
    finally:
        if driver is not None:
            try:
                if worker_tab and worker_tab in driver.window_handles:
                    driver.switch_to.window(worker_tab)
                    driver.close()
                if original_window and original_window in driver.window_handles:
                    driver.switch_to.window(original_window)
                logger.info("Закрытие браузера")
                driver.quit()
            except Exception:
                pass
            with open(os.devnull, "w") as devnull:
                with redirect_stderr(devnull):
                    del driver
                    gc.collect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        main(
            query="кран шаровой",
            max_products=50,
            output_file="ozon_products.xlsx",
            progress_handler=None,
        )
    )
