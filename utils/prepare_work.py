import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from utils.logger import setup_logger
import undetected_chromedriver as uc

logger = setup_logger()


def preparation_before_work(item_name: str) -> WebDriver:
    """Функция, которая подготавливает программу для парсинга данных."""
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = uc.Chrome(options=options)
    driver.implicitly_wait(5)

    logger.info("Переход на сайт Ozon")
    driver.get(url="https://ozon.ru")
    time.sleep(4)
    logger.info(f"Ввод поискового запроса: {item_name}")
    find_input = driver.find_element(By.NAME, "text")
    find_input.clear()
    time.sleep(2)
    find_input.send_keys(item_name)
    time.sleep(2)
    find_input.send_keys(Keys.ENTER)
    time.sleep(2)
    logger.info("Поисковый запрос отправлен")

    return driver
