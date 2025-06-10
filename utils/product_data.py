from typing import Optional, Tuple
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchWindowException,
)
import time
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
        return None


def _get_product_id(driver: WebDriver) -> Optional[str]:
    """Извлекает артикул товара."""
    try:
        element = driver.find_element(By.XPATH, '//div[contains(text(), "Артикул: ")]')
        product_id = element.text.split("Артикул: ")[1].strip()
        return product_id
    except Exception:
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
        return None


def get_ozon_seller_info(driver: WebDriver) -> Optional[str]:
    """Извлекает информацию о продавце из модального окна на странице товара."""
    try:
        seller_block = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-widget='webCurrentSeller']")
            )
        )
        svg = seller_block.find_element(
            By.CSS_SELECTOR,
            "svg path[d='M8 0c4.964 0 8 3.036 8 8s-3.036 8-8 8-8-3.036-8-8 3.036-8 8-8m-.889 11.556a.889.889 0 0 0 1.778 0V8A.889.889 0 0 0 7.11 8zM8.89 4.444a.889.889 0 1 0-1.778 0 .889.889 0 0 0 1.778 0']",
        )
        button = svg.find_element(By.XPATH, "./ancestor::button")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(button))
        try:
            button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", button)
        time.sleep(1)

        modal = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div[data-popper-placement='top']")
            )
        )
        soup = BeautifulSoup(driver.page_source, "lxml")
        modal_div = soup.select_one("div[data-popper-placement='top']")
        if not modal_div:
            return None

        paragraphs = modal_div.find_all("p")
        if not paragraphs:
            return None
        seller_info = [p.get_text(strip=True) for p in paragraphs[:-1]]
        result = "; ".join(seller_info) if seller_info else None
        return result

    except Exception:
        return None


def collect_product_info(driver: WebDriver, url: str) -> dict[str, Optional[str]]:
    """Собирает информацию о товаре с сайта Ozon."""
    original_window = driver.current_window_handle
    new_window = None
    try:
        driver.switch_to.new_window("tab")
        new_window = driver.current_window_handle
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-widget='webProductHeading']")
            )
        )
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
            pass

        product_id = _get_product_id(driver)
        product_name = _get_product_name(soup)
        product_stars, product_reviews = _get_stars_reviews(soup)
        product_ozon_card_price = _get_sale_price(soup)
        product_discount_price, product_base_price = _get_full_prices(soup)
        salesman = _get_salesman_name(soup)
        product_brand = _get_product_brand(soup)
        seller_info = get_ozon_seller_info(driver).rsplit(";", 1)

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
            "Данные": seller_info[0],
            "ИНН": seller_info[1],
            "Ссылка на товар": url,
        }

    except (TimeoutException, WebDriverException, NoSuchWindowException):
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
            "ИНН": None,
            "Ссылка на товар": url,
        }
    finally:
        try:
            if new_window and new_window in driver.window_handles:
                driver.switch_to.window(new_window)
                driver.close()
            driver.switch_to.window(original_window)
        except Exception:
            pass
