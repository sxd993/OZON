import time
import os
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from utils.logger import setup_logger

logger = setup_logger()


def page_down(
    driver: WebDriver,
    css_selector: str = "a[href*='/product/']",
    pause_time: float = 3.0,
    max_attempts: int = 3,
    colvo: int = 1000,
    scroll_step: int = 500,
    scroll_interval: float = 0.5,
    temp_file: str = "temp_links.txt"
) -> list[str]:
    """Функция, которая плавно скроллит страницу и собирает ссылки на продукты."""
    collected_links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    attempts = 0
    current_position = 0

    # Загружаем существующие ссылки из файла, если он есть
    if os.path.exists(temp_file):
        try:
            with open(temp_file, "r", encoding="utf-8") as f:
                collected_links.update(line.strip()
                                       for line in f if line.strip())
            logger.info(
                f"Загружено {len(collected_links)} ссылок из {temp_file}")
        except Exception as e:
            logger.warning(f"Ошибка при чтении {temp_file}: {str(e)}")

    while True:
        # Плавная прокрутка на шаг scroll_step
        target_position = current_position + scroll_step
        driver.execute_script(f"window.scrollTo(0, {target_position});")
        time.sleep(scroll_interval)
        current_position = target_position

        # Проверка наличия элементов
        try:
            WebDriverWait(driver, pause_time).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, css_selector))
            )
            # Собираем ссылки сразу после нахождения элементов
            new_links = set()
            find_links = driver.find_elements(By.CSS_SELECTOR, css_selector)
            logger.info(
                f"Найдено элементов на текущей итерации: {len(find_links)}")
            for link in find_links:
                try:
                    href = link.get_attribute("href")
                    if href and "/product/" in href:
                        new_links.add(href)
                except StaleElementReferenceException:
                    logger.debug(
                        "Пропущен устаревший элемент при получении href")
                    continue
                except Exception as e:
                    logger.warning(f"Ошибка при получении href: {str(e)}")
                    continue
            collected_links.update(new_links)
            logger.info(
                f"Собрано новых ссылок: {len(new_links)}, всего: {len(collected_links)}")

            # Сохраняем ссылки в файл
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    for link in collected_links:
                        f.write(f"{link}\n")
                logger.debug(f"Ссылки сохранены в {temp_file}")
            except Exception as e:
                logger.warning(
                    f"Ошибка при сохранении в {temp_file}: {str(e)}")
        except Exception as e:
            logger.warning(f"Ошибка при поиске элементов: {str(e)}")
            # Продолжаем прокрутку, даже если элементы не найдены

        # Если colvo > 0 и собрано достаточно ссылок, обрезаем список
        if colvo > 0 and len(collected_links) >= colvo:
            collected_links = set(list(collected_links)[:colvo])
            logger.info(f"Достигнуто целевое количество ссылок: {colvo}")
            break

        # Проверка высоты страницы
        new_height = driver.execute_script("return document.body.scrollHeight")
        logger.debug(
            f"Позиция: {current_position}, Новая высота: {new_height}, Старая высота: {last_height}")
        # Если достигли конца страницы
        if current_position >= new_height:
            if new_height == last_height:
                attempts += 1
                if attempts >= max_attempts:
                    logger.info(
                        "Достигнут конец страницы, новых элементов нет")
                    break
            else:
                attempts = 0
            last_height = new_height
            current_position = new_height

    # Удаляем временный файл после завершения
    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.debug(f"Временный файл {temp_file} удалён")
    except Exception as e:
        logger.warning(f"Ошибка при удалении {temp_file}: {str(e)}")

    logger.info(
        f"Итоговое количество собранных ссылок: {len(collected_links)}")
    return list(collected_links)
