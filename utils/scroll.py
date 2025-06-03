import logging
import time

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By


def page_down(
    driver: WebDriver,
    class_name: str,
    pause_time: int = 2,
    max_attempts: int = 3,
) -> list[str]:
    """Функция, которая скроллит страницу до конца."""
    logging.warning("[INFO] Начинаем прокрутку и сбор ссылок...")

    collected_links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    attempts = 0

    while attempts < max_attempts:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)

        try:
            # Используем By.CLASS_NAME с классом q4b10-a
            find_links = driver.find_elements(By.CLASS_NAME, class_name)
            new_links = {
                link.get_attribute("href")
                for link in find_links
                if link.get_attribute("href")
            }
            collected_links.update(new_links)
            if len(collected_links) >= 3:
                collected_links = set(list(collected_links)[:3])
                break
        except Exception as e:
            msg_error = "[!] Ошибка при сборе ссылок:"
            logging.error(msg_error, e)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            attempts += 1
        else:
            attempts = 0

        last_height = new_height

    logging.warning(f"[INFO] Сбор завершен, найдено {len(collected_links)} ссылок.")
    return list(collected_links)