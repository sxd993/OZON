import time
from typing import Optional
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
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
                return product_stars, product_reviews
        return None, None
    except Exception:
        return None, None


def _get_sale_price(soup: BeautifulSoup) -> str | None:
    """Функция для получения цены с Ozon Картой."""
    try:
        price_element = soup.find("span", string=lambda text: text and "Ozon Карт" in text)
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


def _get_full_prices(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Функция для получения цены до скидок и без Ozon Карты."""
    try:
        price_element = soup.find("span", string=lambda text: text and "без Ozon Карты" in text)
        if not price_element or not price_element.parent or not price_element.parent.parent:
            return None, None
        price_containers = price_element.parent.parent.find("div")
        if not price_containers:
            return None, None
        price_spans = price_containers.find_all("span")
        def _clean_price(price: str) -> str:
            return price.replace("\u2009", "").replace("₽", "").strip() if price else ""
        product_discount_price = None
        product_base_price = None
        if price_spans and len(price_spans) > 0:
            product_discount_price = _clean_price(price_spans[0].text.strip())
        if price_spans and len(price_spans) > 1:
            product_base_price = _clean_price(price_spans[1].text.strip())
        return product_discount_price, product_base_price
    except Exception:
        return None, None


def _get_product_name(soup: BeautifulSoup) -> str:
    """Функция для получения имени продукта."""
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


def _get_salesman_name(soup: BeautifulSoup) -> str | None:
    """Функция для получения имени продавца."""
    try:
        salesman_elements = soup.select("a[href*='/seller/']")
        for element in salesman_elements:
            href = element.get('href', '').lower()
            text = element.text.strip()
            if 'reviews' in href or 'info' in href or len(text) < 2:
                continue
            if text:
                return text
        return None
    except Exception:
        return None


def _get_product_id(driver: WebDriver) -> str:
    """Функция для получения артикула товара."""
    try:
        element = driver.find_element(By.XPATH, '//div[contains(text(), "Артикул: ")]')
        product_id = element.text.split("Артикул: ")[1].strip()
        return product_id
    except Exception:
        return None


def _get_product_brand(soup: BeautifulSoup) -> str | None:
    """Функция для получения бренда товара из хлебных крошек."""
    try:
        breadcrumbs = soup.find("div", {"data-widget": "breadCrumbs"})
        if not breadcrumbs:
            return None
        breadcrumb_items = breadcrumbs.find_all("li")
        if not breadcrumb_items:
            return None
        last_item = breadcrumb_items[-1]
        brand_tag = last_item.find("span")
        if brand_tag:
            brand = brand_tag.get_text(strip=True)
            return brand
        return None
    except Exception:
        return None


def get_ozon_seller_info(driver: WebDriver, url: str) -> Optional[str]:
    """
    Извлекает информацию о продавце с сайта Ozon в виде строки, беря только третий блок с data-widget="textBlock".
    :param driver: WebDriver для управления браузером.
    :param url: URL страницы товара.
    :return: Строка с данными третьего блока продавца или None в случае ошибки.
    """
    original_window = driver.current_window_handle
    new_window = None
    try:
        driver.switch_to.new_window("tab")
        new_window = driver.current_window_handle
        driver.get(url)
        wait = WebDriverWait(driver, 25)
        # Ищем ссылку на страницу продавца
        try:
            seller_link = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "a[href*='/seller/'][title]"
            )))
            seller_href = seller_link.get_attribute("href")
        except TimeoutException:
            return None
        # Переходим на страницу продавца
        try:
            driver.get(seller_href)
            wait = WebDriverWait(driver, 25)
        except WebDriverException as e:
            return None
        # Ищем кнопку по SVG с повторными попытками
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                clickable_button = wait.until(EC.element_to_be_clickable((
                    By.XPATH,
                    "//*[name()='svg' and @class='ag01-b2']/*[name()='path' and @d='M12 21c5.584 0 9-3.416 9-9s-3.416-9-9-9-9 3.416-9 9 3.416 9 9 9m1-13a1 1 0 1 1-2 0 1 1 0 0 1 2 0m-2 4a1 1 0 1 1 2 0v4a1 1 0 1 1-2 0z']/ancestor::button"
                )))
                clickable_button.click()
                time.sleep(7)  # Задержка 7 секунд для загрузки блоков
                break
            except TimeoutException:
                if attempt == max_attempts - 1:
                    return None
                time.sleep(3)  # Пауза 3 секунды перед повторной попыткой

        # Ищем все блоки с данными продавца
        try:
            seller_blocks = wait.until(EC.presence_of_all_elements_located((
                By.CSS_SELECTOR,
                "div[data-widget='textBlock']"
            )))
        except TimeoutException:
            return None
        # Парсим страницу для последнего блока
        soup = BeautifulSoup(driver.page_source, 'lxml')
        blocks = soup.select("div[data-widget='textBlock']")
        # Берем последний блок
        last_block = blocks[-1]

        # Извлекаем данные из третьего блока
        seller_info = []
        divs = last_block.select("div.bq000-a")
        for div in divs:
            spans = div.select("span.tsBody400Small")
            for span in spans:
                text = span.get_text(strip=True)
                if text and text != "О магазине" and len(text) > 2:
                    import re
                    # Проверяем, содержит ли строка ИНН (10 или 12 цифр) в конце
                    inn_match = re.search(r'^(.+?)(\d{12,15})$', text)
                    if inn_match:
                        # Если найдены ФИО и ИНН, разделяем их
                        name_part, inn_part = inn_match.groups()
                        name_part = name_part.strip()
                        if name_part and name_part != "О магазине":
                            seller_info.append(name_part)
                        seller_info.append(inn_part)
                    else:
                        # Если ИНН не найден, добавляем строку как есть
                        if text != "О магазине":
                            seller_info.append(text)
        # Объединяем данные в строку
        result = "; ".join(seller_info) if seller_info else None
        if result:
            result = result.replace("Работает согласно графику Ozon", "").strip("; ").strip("")
        return result, seller_href

    except Exception as e:
        return None
    finally:
        try:
            if new_window:
                driver.switch_to.window(new_window)
                driver.close()
            driver.switch_to.window(original_window)
        except Exception as e:
            return None


def collect_product_info(driver: WebDriver, url: str) -> dict[str, str | None]:
    """
    Функция для сбора информации о товаре.
    """
    try:
        driver.switch_to.new_window("tab")
        time.sleep(2)
        driver.get(url=url)
        time.sleep(2)
        page_source = str(driver.page_source)
        soup = BeautifulSoup(page_source, "lxml")
        product_id = _get_product_id(driver)
        if product_id is None:
            return {"Артикул": None, "Название товара": None, "Бренд": None, "Цена с картой озона": None,
                    "Цена со скидкой": None, "Цена": None, "Рейтинг": None, "Отзывы": None,
                    "Продавец": None, "Ссылка на продавца": None, "Данные": None, "Ссылка на товар": url}
        product_name = _get_product_name(soup)
        product_stars, product_reviews = _get_stars_reviews(soup)
        product_ozon_card_price = _get_sale_price(soup)
        product_discount_price, product_base_price = _get_full_prices(soup)
        salesman = _get_salesman_name(soup)
        product_brand = _get_product_brand(soup)
        seller_info, seller_href = get_ozon_seller_info(driver, url) if get_ozon_seller_info(driver, url) else (None, None)
        product_data = {
            "Продавец": salesman,
            "Данные": seller_info,
            "Ссылка на продавца": seller_href,
            "Бренд": product_brand,
            "Название товара": product_name,
            "Цена с картой озона": product_ozon_card_price,
            "Цена со скидкой": product_discount_price,
            "Цена": product_base_price,
            "Рейтинг": product_stars,
            "Отзывы": product_reviews,
            "Ссылка на товар": url,
            "Артикул": product_id,
        }
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return product_data
    except Exception:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return {"Артикул": None, "Название товара": None, "Бренд": None, "Цена с картой озона": None,
                "Цена со скидкой": None, "Цена": None, "Рейтинг": None, "Отзывы": None,
                "Продавец": None, "Ссылка на продавца": None, "Данные": None, "Ссылка на товар": url}
