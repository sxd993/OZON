import time as tm
import logging
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver


def _get_stars_reviews(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Функция для получения рейтинга и отзывов продавца."""
    try:
        product_statistic = soup.find("div", attrs={"data-widget": "webSingleProductScore"})
        if product_statistic:
            product_statistic = product_statistic.text.strip()
            if product_statistic and " • " in product_statistic:
                product_stars = product_statistic.split(" • ")[0].strip()
                product_reviews = product_statistic.split(" • ")[1].strip()
                logging.info(f"Найден рейтинг: {product_stars}, отзывы: {product_reviews}")
                return product_stars, product_reviews
        logging.warning("Не найден блок рейтинга и отзывов")
        return None, None
    except Exception as e:
        logging.error(f"Ошибка при получении рейтинга и отзывов: {e}")
        return None, None


def _get_sale_price(soup: BeautifulSoup) -> str | None:
    """Функция для получения цены с Ozon Картой."""
    try:
        price_element = soup.find("span", string=lambda text: text and "Ozon Карт" in text)
        if not price_element or not price_element.parent:
            logging.warning("Не найден элемент цены с Ozon Картой")
            return None
        price_container = price_element.parent.find("div")
        if not price_container:
            logging.warning("Не найден контейнер цены с Ozon Картой")
            return None
        price_span = price_container.find("span")
        if not price_span or not price_span.text:
            logging.warning("Не найдена цена с Ozon Картой")
            return None
        price = price_span.text.strip().replace("\u2009", "").replace("₽", "").strip()
        logging.info(f"Найдена цена с Ozon Картой: {price}")
        return price
    except Exception as e:
        logging.error(f"Ошибка при получении цены с Ozon Картой: {e}")
        return None


def _get_full_prices(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Функция для получения цены до скидок и без Ozon Карты."""
    try:
        price_element = soup.find("span", string=lambda text: text and "без Ozon Карт" in text)
        if not price_element or not price_element.parent or not price_element.parent.parent:
            logging.warning("Не найден элемент цены без Ozon Карты")
            return None, None
        price_containers = price_element.parent.parent.find("div")
        if not price_containers:
            logging.warning("Не найден контейнер цен без Ozon Карты")
            return None, None
        price_spans = price_containers.find_all("span")
        def _clean_price(price: str) -> str:
            return price.replace("\u2009", "").replace("₽", "").strip() if price else ""
        product_discount_price = None
        product_base_price = None
        if price_spans and len(price_spans) > 0:
            product_discount_price = _clean_price(price_spans[0].text.strip())
            logging.info(f"Найдена цена со скидкой: {product_discount_price}")
        if price_spans and len(price_spans) > 1:
            product_base_price = _clean_price(price_spans[1].text.strip())
            logging.info(f"Найдена базовая цена: {product_base_price}")
        if not product_discount_price and not product_base_price:
            logging.warning("Не найдены цены без Ozon Карты")
        return product_discount_price, product_base_price
    except Exception as e:
        logging.error(f"Ошибка при получении цен без Ozon Карты: {e}")
        return None, None


def _get_product_name(soup: BeautifulSoup) -> str:
    """Функция для получения имени продукта."""
    try:
        heading_div = soup.find("div", attrs={"data-widget": "webProductHeading"})
        if not isinstance(heading_div, Tag):
            logging.warning("Не найден блок названия товара")
            return ""
        title_element = heading_div.find("h1")
        if not isinstance(title_element, Tag):
            logging.warning("Не найдено название товара")
            return ""
        name = title_element.text.strip().replace("\t", "").replace("\n", " ")
        logging.info(f"Найдено название товара: {name}")
        return name
    except Exception as e:
        logging.error(f"Ошибка при получении названия товара: {e}")
        return ""


from bs4 import BeautifulSoup, Tag
import logging

def _get_salesman_name(soup: BeautifulSoup) -> str | None:
    """Функция для получения имени продавца."""
    try:
        # Попытка 1: Ищем ссылки с /seller/ в href
        salesman_elements = soup.select("a[href*='/seller/']")
        for element in salesman_elements:
            href = element.get('href', '').lower()
            text = element.text.strip()
            # Пропускаем ссылки с 'reviews', 'info' или пустым/коротким текстом
            if 'reviews' in href or 'info' in href or len(text) < 2:
                continue
            # Проверяем, что текст не пустой и выглядит как имя продавца
            if text:
                logging.info(f"Найден продавец по селектору 'a[href*='/seller/']': {text}")
                return text
        logging.warning("Не найден подходящий продавец по селектору 'a[href*='/seller/']'")

        # Попытка 2: Ищем по атрибуту title, если он содержит имя
        title_elements = soup.select("a[title]")
        for element in title_elements:
            text = element.text.strip()
            href = element.get('href', '').lower()
            # Проверяем, что текст совпадает с title и не пустой
            if text and text == element.get('title', '').strip() and 'seller' in href:
                logging.info(f"Найден продавец по селектору 'a[title]' и href: {text}")
                return text
        logging.warning("Не найден продавец по селектору 'a[title]'")

        logging.warning("Не удалось найти имя продавца ни одним методом")
        return None
    except Exception as e:
        logging.error(f"Ошибка при получении имени продавца: {e}")
        return None


def _get_product_id(driver: WebDriver) -> str:
    """Функция для получения артикула товара."""
    try:
        element = driver.find_element(By.XPATH, '//div[contains(text(), "Артикул: ")]')
        product_id = element.text.split("Артикул: ")[1].strip()
        logging.info(f"Найден артикул: {product_id}")
        return product_id
    except Exception as e:
        logging.error(f"Ошибка при получении артикула: {e}")
        return None


def _get_product_brand(soup: BeautifulSoup) -> str | None:
    """Функция для получения бренда товара из хлебных крошек."""
    try:
        breadcrumbs = soup.find("div", {"data-widget": "breadCrumbs"})
        if not breadcrumbs:
            logging.warning("Блок хлебных крошек не найден.")
            return None

        breadcrumb_items = breadcrumbs.find_all("li")
        if not breadcrumb_items:
            logging.warning("Элементы хлебных крошек не найдены.")
            return None

        last_item = breadcrumb_items[-1]
        brand_tag = last_item.find("span")
        if brand_tag:
            brand = brand_tag.get_text(strip=True)
            logging.info(f"Найден бренд в последнем элементе хлебных крошек: {brand}")
            return brand
        else:
            logging.warning("Тег <span> в последнем элементе хлебных крошек не найден.")

    except Exception as e:
        logging.warning(f"Ошибка при поиске бренда в хлебных крошках: {e}")

    # Резервный способ — поиск по лейблу "Бренд"
    try:
        for tag in soup.find_all(['span', 'div', 'p', 'dt']):
            if 'бренд' in tag.get_text(strip=True).lower():
                next_el = tag.find_next(['span', 'div', 'dd', 'p'])
                if next_el and next_el.text.strip():
                    brand = next_el.text.strip()
                    logging.info(f"Найден бренд рядом с меткой 'Бренд': {brand}")
                    return brand
    except Exception as e:
        logging.warning(f"Ошибка при поиске бренда рядом с меткой 'Бренд': {e}")

    logging.warning("Не удалось найти бренд товара ни одним из способов.")
    return None


import logging
import time
from typing import Optional
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

def get_ozon_seller_info(driver: WebDriver, url: str) -> Optional[str]:
    """
    Извлекает информацию о продавце с сайта Ozon в виде строки.

    :param driver: WebDriver для управления браузером.
    :param url: URL страницы товара.
    :return: Строка с данными продавца или None в случае ошибки.
    """
    logging.basicConfig(level=logging.DEBUG)
    original_window = driver.current_window_handle
    new_window = None
    try:
        logging.debug(f"Начало обработки URL: {url}")
        driver.switch_to.new_window("tab")
        new_window = driver.current_window_handle
        logging.debug(f"Открыта новая вкладка: {new_window}")
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # Ищем ссылку на страницу продавца
        try:
            seller_link = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "a[href*='/seller/'][title]"
            )))
            seller_href = seller_link.get_attribute("href")
            seller_name = seller_link.get_attribute("title")
            logging.debug(f"Найдена ссылка на продавца: {seller_href}, название: {seller_name}")
        except TimeoutException:
            logging.warning(f"Ссылка на продавца не найдена на странице {url}")
            return None

        # Переходим на страницу продавца
        try:
            driver.get(seller_href)
            logging.debug(f"Перешли на страницу продавца: {seller_href}")
            wait = WebDriverWait(driver, 15)
        except WebDriverException as e:
            logging.error(f"Ошибка при переходе на страницу продавца {seller_href}: {e}")
            return None

        # Ищем кнопку по SVG
        try:
            clickable_button = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//*[name()='svg' and @class='ag01-b2']/*[name()='path' and @d='M12 21c5.584 0 9-3.416 9-9s-3.416-9-9-9-9 3.416-9 9 3.416 9 9 9m1-13a1 1 0 1 1-2 0 1 1 0 0 1 2 0m-2 4a1 1 0 1 1 2 0v4a1 1 0 1 1-2 0z']/ancestor::button"
            )))
            clickable_button.click()
            logging.debug("Кнопка с SVG найдена и нажата")
            time.sleep(2)  # Даём время для загрузки всплывающего блока
        except TimeoutException:
            logging.warning("Кнопка с указанным SVG не найдена")
            # Пробуем альтернативный селектор
            try:
                clickable_button = wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "button.ag01-a0"
                )))
                clickable_button.click()
                logging.debug("Найдена и нажата альтернативная кнопка с классом ag01-a0")
                time.sleep(2)
            except TimeoutException:
                logging.warning("Альтернативная кнопка ag01-a0 также не найдена")
                return None

        # Ищем блок с данными продавца
        try:
            seller_block = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "div.e8l_11[data-widget='textBlock']"
            )))
            logging.debug("Найден блок с данными продавца")
        except TimeoutException:
            logging.warning("Блок с информацией о продавце не найден по селектору div.e8l_11[data-widget='textBlock']")
            # Пробуем альтернативный селектор
            try:
                seller_block = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div[class*='seller-info'], div[class*='modal'], div[class*='popup']"
                )))
                logging.debug("Найден альтернативный блок с данными продавца")
            except TimeoutException:
                logging.warning("Альтернативный блок с данными продавца также не найден")
                logging.debug(f"HTML страницы: {driver.page_source[:1000]}...")
                return None

        # Парсим страницу
        soup = BeautifulSoup(driver.page_source, 'lxml')
        block = soup.select_one("div.e8l_11[data-widget='textBlock'], div[class*='seller-info'], div[class*='modal'], div[class*='popup']")
        if not block:
            logging.warning("Блок с данными продавца не найден в DOM")
            logging.debug(f"HTML страницы: {driver.page_source[:1000]}...")
            return None

        # Извлекаем данные продавца
        seller_info = []
        spans = block.select("span.tsBody400Small, span[class*='text'], p, div")
        logging.debug(f"Найдено {len(spans)} элементов для извлечения текста")
        for span in spans:
            text = span.get_text(strip=True)
            if text:
                lines = text.split('\n')
                seller_info.extend(line.strip() for line in lines if line.strip())
                logging.debug(f"Извлечён текст: {text}")

        # Объединяем данные в строку
        result = "; ".join(seller_info) if seller_info else None
        if result:
            logging.info(f"Извлечена информация о продавце: {result}")
        else:
            logging.warning("Данные продавца пусты")
        return result

    except Exception as e:
        logging.error(f"Общая ошибка при извлечении информации о продавце для URL {url}: {e}")
        return None

    finally:
        try:
            if new_window:
                driver.switch_to.window(new_window)
                driver.close()
                logging.debug(f"Закрыта вкладка: {new_window}")
            driver.switch_to.window(original_window)
            logging.debug(f"Вернулись к исходной вкладке: {original_window}")
        except Exception as e:
            logging.error(f"Ошибка при закрытии вкладки или возврате к исходной: {e}")


def collect_product_info(driver: WebDriver, url: str) -> dict[str, str | None]:
    """
    Функция для сбора информации о товаре.
    """
    try:
        driver.switch_to.new_window("tab")
        tm.sleep(2)  # Увеличиваем время ожидания для загрузки страницы
        driver.get(url=url)
        tm.sleep(2)
        page_source = str(driver.page_source)
        soup = BeautifulSoup(page_source, "lxml")

        product_id = _get_product_id(driver)
        product_name = _get_product_name(soup)
        product_stars, product_reviews = _get_stars_reviews(soup)
        product_ozon_card_price = _get_sale_price(soup)
        product_discount_price, product_base_price = _get_full_prices(soup)
        salesman = _get_salesman_name(soup)
        product_brand = _get_product_brand(soup)
        seller_info = get_ozon_seller_info(driver, url)

        product_data = {
            "Артикул": product_id,
            "Название товара": product_name,
            "Бренд": product_brand,
            "Цена с картой озона": product_ozon_card_price,
            "Цена со скидкой": product_discount_price,
            "Цена": product_base_price,
            "Рейтинг": product_stars,
            "Отзывы": product_reviews,
            "Продавец": salesman,
            "Данные": seller_info,
            "Ссылка": url,
        }

        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return product_data
    except Exception as e:
        logging.error(f"Ошибка в collect_product_info для URL {url}: {e}")
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return {"Артикул": None, "Название товара": None, "Бренд": None, "Цена с картой озона": None,
                "Цена со скидкой": None, "Цена": None, "Рейтинг": None, "Отзывы": None,
                "Продавец": None, "Данные": None, "Ссылка": url}
    

    '''Вова'''