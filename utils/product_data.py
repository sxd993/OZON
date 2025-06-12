from typing import Optional, Tuple
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import re
import gc
from utils.logger import setup_logger

logger = setup_logger()


def _get_stars_reviews(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """Извлекает рейтинг и количество отзывов продавца."""
    try:
        product_statistic = soup.find(
            "div", attrs={"data-widget": "webSingleProductScore"}
        )
        if product_statistic:
            text = product_statistic.text.strip()
            if text and " • " in text:
                stars, reviews = text.split(" • ")
                return stars.strip(), reviews.strip()
        logger.debug("Не найдены данные рейтинга и отзывов")
        return None, None
    except Exception as e:
        logger.warning(f"Ошибка при извлечении рейтинга и отзывов: {str(e)}")
        return None, None
    finally:
        product_statistic = None  # Очистка переменной


def _get_sale_price(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает цену с Ozon Картой или скидочную цену, если надписи нет."""
    try:
        price_element = soup.find(
            "span", string=lambda text: text and "Ozon Карт" in text
        )
        if price_element and price_element.parent:
            price_container = price_element.parent.find("div")
            if price_container:
                price_span = price_container.find("span")
                if price_span and price_span.text:
                    price = (
                        price_span.text.strip()
                        .replace("\u2009", "")
                        .replace("₽", "")
                        .strip()
                    )
                    logger.debug(f"Извлечена цена с Ozon Картой: {price}")
                    return price

        price_spans = soup.find_all("span", class_=True)
        if price_spans:
            for span in price_spans:
                if span.text and "₽" in span.text:
                    price = (
                        span.text.strip().replace("\u2009", "").replace("₽", "").strip()
                    )
                    logger.debug(f"Извлечена скидочная цена (без надписей): {price}")
                    return price

        logger.debug("Не найден элемент с ценой")
        return None
    except Exception as e:
        logger.warning(f"Ошибка при извлечении цены с Ozon Картой: {str(e)}")
        return None
    finally:
        price_element = price_container = price_span = price_spans = (
            None  # Очистка переменных
        )


def _get_full_prices(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """Извлекает цену до скидок и без Ozon Карты."""
    try:
        price_element = soup.find(
            "span", string=lambda text: text and "без Ozon Карты" in text
        )
        if price_element and price_element.parent and price_element.parent.parent:
            price_containers = price_element.parent.parent.find("div")
            if price_containers:
                price_spans = price_containers.find_all("span")
                if price_spans:
                    discount_price = (
                        _clean_price(price_spans[0].text.strip())
                        if price_spans
                        else None
                    )
                    base_price = (
                        _clean_price(price_spans[1].text.strip())
                        if price_spans and len(price_spans) > 1
                        else None
                    )
                    logger.debug(
                        f"Извлечены цены: скидочная={discount_price}, базовая={base_price}"
                    )
                    return discount_price, base_price

        price_spans = soup.find_all("span", class_=True)
        if price_spans and len(price_spans) >= 2:
            prices = [
                span.text.strip().replace("\u2009", "").replace("₽", "").strip()
                for span in price_spans
                if span.text and "₽" in span.text
            ]
            if len(prices) >= 2:
                discount_price = prices[0]
                base_price = prices[1]
                logger.debug(
                    f"Извлечены цены (без надписей): скидочная={discount_price}, базовая={base_price}"
                )
                return discount_price, base_price

        logger.debug("Не найдены элементы с ценами")
        return None, None
    except Exception as e:
        logger.warning(f"Ошибка при извлечении цен: {str(e)}")
        return None, None
    finally:
        price_element = price_containers = price_spans = prices = (
            None  # Очистка переменных
        )


def _clean_price(price: str) -> str:
    """Очищает цену от лишних символов."""
    return price.replace("\u2009", "").replace("₽", "").strip() if price else ""


def _get_product_name(soup: BeautifulSoup) -> str:
    """Извлекает название товара."""
    try:
        heading_div = soup.find("div", attrs={"data-widget": "webProductHeading"})
        if not heading_div:
            logger.debug("Не найден div с data-widget='webProductHeading'")
            return ""
        if not isinstance(heading_div, Tag):
            logger.debug("Найденный div не является Tag")
            return ""
        title_element = heading_div.find("h1")
        if not title_element:
            logger.debug("Элемент h1 не найден в webProductHeading")
            return ""
        if not isinstance(title_element, Tag):
            logger.debug("Найденный h1 не является Tag")
            return ""
        name = title_element.text.strip().replace("\t", "").replace("\n", " ")
        logger.debug(f"Извлечено название товара: {name}")
        return name
    except Exception as e:
        logger.warning(f"Ошибка при извлечении названия товара: {str(e)}")
        return ""
    finally:
        heading_div = title_element = None  # Очистка переменных


def _get_salesman_name(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает имя продавца."""
    try:
        salesman_elements = soup.select("a[href*='/seller/']")
        for element in salesman_elements:
            href = element.get("href", "").lower()
            text = element.text.strip()
            if "reviews" in href or "info" in href or len(text) < 2:
                continue
            if text:
                logger.debug(f"Извлечено имя продавца: {text}")
                return text
        logger.debug("Имя продавца не найдено")
        return None
    except Exception as e:
        logger.warning(f"Ошибка при извлечении имени продавца: {str(e)}")
        return None
    finally:
        salesman_elements = None  # Очистка переменной


def _get_product_id(driver: WebDriver) -> Optional[str]:
    """Извлекает артикул товара."""
    try:
        element = driver.find_element(By.XPATH, '//div[contains(text(), "Артикул: ")]')
        product_id = element.text.split("Артикул: ")[1].strip()
        logger.debug(f"Извлечён артикул: {product_id}")
        return product_id
    except Exception as e:
        logger.warning(f"Ошибка при извлечении артикула: {str(e)}")
        return None
    finally:
        element = None  # Очистка переменной


def _get_product_brand(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает бренд товара из хлебных крошек."""
    try:
        breadcrumbs = soup.find("div", {"data-widget": "breadCrumbs"})
        if not breadcrumbs:
            logger.debug("Хлебные крошки не найдены")
            return None
        breadcrumb_items = breadcrumbs.find_all("li")
        if not breadcrumb_items:
            logger.debug("Элементы хлебных крошек отсутствуют")
            return None
        last_item = breadcrumb_items[-1]
        brand_tag = last_item.find("span")
        brand = brand_tag.get_text(strip=True) if brand_tag else None
        logger.debug(f"Извлечён бренд: {brand}")
        return brand
    except Exception as e:
        logger.warning(f"Ошибка при извлечении бренда: {str(e)}")
        return None
    finally:
        breadcrumbs = breadcrumb_items = last_item = brand_tag = (
            None  # Очистка переменных
        )


def get_ozon_seller_info(
    driver: WebDriver, seller_href: str
) -> Optional[Tuple[str, str, str]]:
    """
    Извлекает информацию о продавце с сайта Ozon из модального окна (data-widget='modalLayout').
    """
    logger.info(f"Получение данных продавца по ссылке: {seller_href}")
    original_window = driver.current_window_handle
    try:
        driver.get(seller_href)
        wait = WebDriverWait(driver, 25)

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                xpath = "//*[name()='svg']/*[name()='path' and @d=\"M12 21c5.584 0 9-3.416 9-9s-3.416-9-9-9-9 3.416-9 9 3.416 9 9 9m1-13a1 1 0 1 1-2 0 1 1 0 0 1 2 0m-2 4a1 1 0 1 1 2 0v4a1 1 0 1 1-2 0z\"]/ancestor::button"
                clickable_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                clickable_button.click()
                time.sleep(1.5)
                logger.info("Нажата кнопка информации о продавце")
                break
            except TimeoutException:
                if attempt == max_attempts - 1:
                    logger.warning(
                        "Не удалось нажать кнопку информации о продавце после всех попыток"
                    )
                    return None
                time.sleep(1.5)

        soup = BeautifulSoup(driver.page_source, "lxml")
        modal = soup.find("div", attrs={"data-widget": "modalLayout"})
        if not modal:
            logger.warning("Модальное окно не найдено")
            return None

        text_blocks = modal.find_all("div", attrs={"data-widget": "textBlock"})
        if not text_blocks:
            logger.warning("Блоки textBlock не найдены в модальном окне")
            return None

        last_block = text_blocks[-1]
        spans = last_block.select("div.bq011-a span")
        if not spans:
            logger.warning("Не найдены span элементы в последнем textBlock")
            return None

        spans = spans[:-1]
        if not spans:
            logger.warning("Нет данных продавца после исключения последнего span")
            return None

        text = spans[0].get_text(strip=True)
        inn_match = re.search(r"^(.+?)(\d{10}|\d{12}|\d{15})$", text)
        if inn_match:
            seller_name, inn = inn_match.groups()
            seller_name = seller_name.strip()
            logger.info(f"Извлечены данные продавца: {seller_name}, ИНН: {inn}")
            return (seller_name, inn, seller_href)
        else:
            logger.warning("Не удалось разделить имя и ИНН продавца")
            return (text, None, seller_href)

    except (TimeoutException, WebDriverException, IndexError) as e:
        logger.warning(
            f"Ошибка при получении данных продавца по ссылке {seller_href}: {str(e)}"
        )
        return None
    finally:
        if "soup" in locals():
            soup.decompose()  # Очистка объекта BeautifulSoup
        modal = text_blocks = last_block = spans = clickable_button = (
            None  # Очистка переменных
        )
        driver.switch_to.window(original_window)
        gc.collect()  # Принудительная сборка мусора


def collect_product_info(driver: WebDriver, url: str) -> dict[str, Optional[str]]:
    """
    Собирает информацию о товаре с сайта Ozon с повторными попытками при неудаче.
    """
    logger.info(f"Обработка URL товара: {url}")
    max_retries = 3
    attempt = 1

    while attempt <= max_retries:
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 25)
            soup = BeautifulSoup(driver.page_source, "lxml")

            seller_href = None
            try:
                seller_link = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[href*='/seller/'][title]")
                    )
                )
                seller_href = seller_link.get_attribute("href")
                logger.debug(f"Извлечена ссылка на продавца: {seller_href}")
            except TimeoutException:
                logger.warning("Не удалось извлечь ссылку на продавца")

            product_id = _get_product_id(driver)
            product_name = _get_product_name(soup)
            product_stars, product_reviews = _get_stars_reviews(soup)
            product_ozon_card_price = _get_sale_price(soup)
            product_discount_price, product_base_price = _get_full_prices(soup)
            salesman = _get_salesman_name(soup)
            product_brand = _get_product_brand(soup)

            seller_info = None
            seller_inn = None
            if seller_href:
                seller_info_tuple = get_ozon_seller_info(driver, seller_href)
                if seller_info_tuple:
                    seller_info, seller_inn, _ = seller_info_tuple

            # Проверяем, есть ли None в критически важных полях
            critical_fields = [
                product_id,
                product_name,
                product_ozon_card_price,
                product_discount_price,
                product_base_price,
                product_stars,
                product_reviews,
                salesman,
                product_brand,
                seller_info,
                seller_inn,
            ]

            if all(
                field is None or (isinstance(field, str) and not field)
                for field in critical_fields
            ):
                logger.warning(
                    f"Попытка {attempt} не удалась: все поля пустые для URL {url}"
                )
                if attempt == max_retries:
                    logger.error(
                        f"Достигнуто максимальное количество попыток для URL {url}"
                    )
                    return {
                        "Артикул": None,
                        "Название товара": None,
                        "Бренд": None,
                        "Цена с картой озона": None,
                        "Цена со скидкой": None,
                        "Цена": None,
                        "Рейтинг": None,
                        "Отзывы": None,
                        "Продавец": None,
                        "Ссылка на продавца": None,
                        "Данные продавца": None,
                        "ИНН продавца": None,
                        "Ссылка на товар": url,
                    }
                attempt += 1
                time.sleep(2)  # Пауза перед повторной попыткой
                continue

            if not product_name:
                logger.warning(f"Название товара не извлечено для URL: {url}")

            logger.info(f"Данные о товаре собраны: {product_name}")
            return {
                "Артикул": product_id,
                "Название товара": product_name,
                "Бренд": product_brand,
                "Цена с картой озона": product_ozon_card_price,
                "Цена со скидкой": product_discount_price,
                "Цена": product_base_price,
                "Рейтинг": product_stars,
                "Отзывы": product_reviews,
                "Продавец": salesman,
                "Ссылка на продавца": seller_href,
                "Данные продавца": seller_info,
                "ИНН продавца": seller_inn,
                "Ссылка на товар": url,
            }

        except (TimeoutException, WebDriverException) as e:
            logger.warning(
                f"Ошибка при обработке URL товара {url} на попытке {attempt}: {str(e)}"
            )
            if attempt == max_retries:
                logger.error(
                    f"Достигнуто максимальное количество попыток для URL {url}"
                )
                return {
                    "Артикул": None,
                    "Название товара": None,
                    "Бренд": None,
                    "Цена с картой озона": None,
                    "Цена со скидкой": None,
                    "Цена": None,
                    "Рейтинг": None,
                    "Отзывы": None,
                    "Продавец": None,
                    "Ссылка на продавца": None,
                    "Данные продавца": None,
                    "ИНН продавца": None,
                    "Ссылка на товар": url,
                }
            attempt += 1
            time.sleep(2)  # Пауза перед повторной попыткой
        finally:
            if "soup" in locals():
                soup.decompose()  # Очистка объекта BeautifulSoup
            seller_link = None  # Очистка переменной
            gc.collect()  # Принудительная сборка мусора
