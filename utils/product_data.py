import time as tm
import logging
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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


def _get_salesman_name(soup: BeautifulSoup) -> str | None:
    """Функция для получения имени продавца."""
    try:
        salesman_elements = soup.find_all("div", class_="t1k_28")
        if salesman_elements:
            salesman = salesman_elements[0].text.strip()
            logging.info(f"Найден продавец: {salesman}")
            return salesman
        logging.warning("Не найден продавец с классом l5k_28")
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
    """Функция для получения бренда товара."""
    try:
        # Ищем блок характеристик, где может быть бренд
        characteristics = soup.find_all("dl", class_="q4b10-a zd6_12")
        for char in characteristics:
            if not isinstance(char, Tag):
                continue
            title_element = char.find("dt")
            value_element = char.find("dd")
            title = title_element.get_text(strip=True) if isinstance(title_element, Tag) else None
            value = value_element.get_text(strip=True) if isinstance(value_element, Tag) else None
            if title and "Бренд" in title:
                logging.info(f"Найден бренд: {value}")
                return value
        logging.warning("Не найден бренд товара")
        return None
    except Exception as e:
        logging.error(f"Ошибка при получении бренда: {e}")
        return None


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
                "Продавец": None, "Ссылка": url}