import time
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.logger import setup_logger

logger = setup_logger()


def page_down(
    driver: WebDriver,
    css_selector: str = "a[href*='/product/']",
    pause_time: float = 1.0,
    max_attempts: int = 3,
    colvo: int = 1000,
) -> list[str]:
    """Функция, которая скроллит страницу до конца и собирает ссылки на продукты."""
    collected_links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    attempts = 0

    while attempts < max_attempts:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        WebDriverWait(driver, pause_time).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
        )
        find_links = driver.find_elements(By.CSS_SELECTOR, css_selector)
        new_links = {
            link.get_attribute("href")
            for link in find_links
            if link.get_attribute("href") and "/product/" in link.get_attribute("href")
        }
        collected_links.update(new_links)

        if len(collected_links) >= colvo:
            collected_links = set(list(collected_links)[:colvo])
            break

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            attempts += 1
        else:
            attempts = 0
        last_height = new_height

    logger.info(f"Собрано ссылок: {len(collected_links)}")
    return list(collected_links)
