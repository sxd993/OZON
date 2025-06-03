import json
import time
from pathlib import Path


def write_products_urls(products_urls: list[str]) -> None:
    """Функция для записи urls в файл."""
    products_urls_dict = {}
    for k, v in enumerate(products_urls):
        products_urls_dict.update({k: v})
    path_products_url = Path("products_urls_dict_small.json")
    with path_products_url.open("w", encoding="utf-8") as file:
        json.dump(products_urls_dict, file, indent=4, ensure_ascii=False)
    time.sleep(2)
