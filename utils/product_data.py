from typing import Optional, Tuple
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import re
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
        return None, None
    except Exception:
        logger.warning("Не удалось извлечь рейтинг и отзывы")
        return None, None


def _get_sale_price(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает цену с Ozon Картой."""
    try:
        price_element = soup.find(
            "span", string=lambda text: text and "Ozon Карт" in text
        )
        if not price_element or not price_element.parent:
            return None
        price_container = price_element.parent.find("div")
        if not price_container:
            return None
        price_span = price_container.find("span")
        if not price_span or not price_span.text:
            return None
        price = price_span.text.strip().replace("\u2009", "").replace("₽", "").strip()
        return price
    except Exception:
        logger.warning("Не удалось извлечь цену с Ozon Картой")
        return None


def _get_full_prices(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """Извлекает цену до скидок и без Ozon Карты."""
    try:
        price_element = soup.find(
            "span", string=lambda text: text and "без Ozon Карты" in text
        )
        if (
            not price_element
            or not price_element.parent
            or not price_element.parent.parent
        ):
            return None, None
        price_containers = price_element.parent.parent.find("div")
        if not price_containers:
            return None, None
        price_spans = price_containers.find_all("span")

        def _clean_price(price: str) -> str:
            return price.replace("\u2009", "").replace("₽", "").strip() if price else ""

        discount_price = (
            _clean_price(price_spans[0].text.strip()) if price_spans else None
        )
        base_price = (
            _clean_price(price_spans[1].text.strip())
            if price_spans and len(price_spans) > 1
            else None
        )
        return discount_price, base_price
    except Exception:
        logger.warning("Не удалось извлечь цены")
        return None, None


def _get_product_name(soup: BeautifulSoup) -> str:
    """Извлекает название товара."""
    try:
        heading_div = soup.find("div", attrs={"data-widget": "webProductHeading"})
        if not isinstance(heading_div, Tag):
            return ""
        title_element = heading_div.find("h1")
        if not isinstance(title_element, Tag):
            return ""
        name = title_element.text.strip().replace("\t", "").replace("\n", " ")
        return name
    except Exception:
        logger.warning("Не удалось извлечь название товара")
        return ""


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
                return text
        return None
    except Exception:
        logger.warning("Не удалось извлечь имя продавца")
        return None


def _get_product_id(driver: WebDriver) -> Optional[str]:
    """Извлекает артикул товара."""
    try:
        element = driver.find_element(By.XPATH, '//div[contains(text(), "Артикул: ")]')
        product_id = element.text.split("Артикул: ")[1].strip()
        return product_id
    except Exception:
        logger.warning("Не удалось извлечь артикул")
        return None


def _get_product_brand(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает бренд товара из хлебных крошек."""
    try:
        breadcrumbs = soup.find("div", {"data-widget": "breadCrumbs"})
        if not breadcrumbs:
            return None
        breadcrumb_items = breadcrumbs.find_all("li")
        if not breadcrumb_items:
            return None
        last_item = breadcrumb_items[-1]
        brand_tag = last_item.find("span")
        brand = brand_tag.get_text(strip=True) if brand_tag else None
        return brand
    except Exception:
        logger.warning("Не удалось извлечь бренд")
        return None


def get_ozon_seller_info(
    driver: WebDriver, seller_href: str
) -> Optional[Tuple[str, str]]:
    """
    Извлекает информацию о продавце с сайта Ozon из последнего блока с data-widget="textBlock".
    :param driver: WebDriver для управления браузером.
    :param seller_href: URL страницы продавца.
    :return: Кортеж (данные продавца, ссылка на профиль) или None в случае ошибки.
    """
    logger.info(f"Получение данных продавца по ссылке: {seller_href}")
    original_window = driver.current_window_handle
    new_window = None
    try:
        driver.get(seller_href)
        wait = WebDriverWait(driver, 25)

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                xpath = (
                    "//*[name()='svg']"
                    "/*[name()='path' and @d=\"M12 21c5.584 0 9-3.416 9-9s-3.416-9-9-9-9 3.416-9 9 "
                    '3.416 9 9 9m1-13a1 1 0 1 1-2 0 1 1 0 0 1 2 0m-2 4a1 1 0 1 1 2 0v4a1 1 0 1 1-2 0z"]'
                    "/ancestor::button"
                )

                clickable_button = WebDriverWait(driver, timeout=10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                clickable_button.click()
                time.sleep(0.5)
                logger.info("Нажата кнопка информации о продавце")
                break
            except TimeoutException:
                if attempt == max_attempts - 1:
                    logger.warning(
                        "Не удалось нажать кнопку информации о продавце после всех попыток"
                    )
                    return None
                time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "lxml")
        blocks = soup.select("div[data-widget='textBlock']")
        if not blocks:
            logger.warning(
                f"Блоки textBlock не найдены на странице продавца: {seller_href}"
            )
            return None

        last_block = blocks[-1]
        seller_info = []
        divs = last_block.select("div.bq000-a")
        for div in divs:
            spans = div.select("span.tsBody400Small")
            for span in spans:
                text = span.get_text(strip=True)
                if text and text != "О магазине" and len(text) > 2:
                    inn_match = re.search(r"^(.+?)(\d{10}|\d{12}|\d{15})$", text)
                    if inn_match:
                        name_part, inn_part = inn_match.groups()
                        name_part = name_part.strip()
                        if name_part and name_part != "О магазине":
                            seller_info.append(name_part)
                        seller_info.append(inn_part)
                    else:
                        if text != "О магазине":
                            seller_info.append(text)

        result = "; ".join(seller_info) if seller_info else None
        if result:
            result = (
                result.replace("Работает согласно графику Ozon", "").strip("; ").strip()
            )
        logger.info(f"Извлечены данные продавца: {result}")
        return (result, seller_href) if result else None

    except (TimeoutException, WebDriverException, IndexError) as e:
        logger.warning(
            f"Ошибка при получении данных продавца по ссылке {seller_href}: {str(e)}"
        )
        return None

    finally:
        if new_window:
            driver.switch_to.window(new_window)
            driver.close()
        driver.switch_to.window(original_window)


def collect_product_info(driver: WebDriver, url: str) -> dict[str, Optional[str]]:
    """
    Собирает информацию о товаре с сайта Ozon.
    :param driver: WebDriver для управления браузером.
    :param url: URL страницы товара.
    :return: Словарь с данными о товаре.
    """
    logger.info(f"Обработка URL товара: {url}")
    original_window = driver.current_window_handle
    new_window = None
    try:
        driver.switch_to.new_window("tab")
        new_window = driver.current_window_handle
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
        if seller_href:
            seller_info_tuple = get_ozon_seller_info(driver, seller_href)
            seller_info = seller_info_tuple[0] if seller_info_tuple else None

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
            "Данные": seller_info,
            "Ссылка на товар": url,
        }

    except (TimeoutException, WebDriverException) as e:
        logger.warning(f"Ошибка при обработке URL товара {url}: {str(e)}")
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
            "Данные": None,
            "Ссылка на товар": url,
        }

    finally:
        if new_window:
            driver.switch_to.window(new_window)
            driver.close()
        driver.switch_to.window(original_window)
