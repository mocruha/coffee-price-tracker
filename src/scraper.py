import json
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


# ---------- Config ----------

BASE_URL = "https://www.santaluzia.com.br/matinais/cafe/cafe-em-graos"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CoffeeMonitor/1.0; +https://github.com/seu-usuario)"
}
PAGE_DELAY_SECONDS = 2


# ---------- Ponto de entrada ----------


def scrape_all() -> dict:
    """Coleta todas as páginas e devolve um envelope com metadados + produtos."""
    collected_at = datetime.now(timezone.utc).isoformat()
    products = []
    seen_skus = set()
    page = 1

    while True:
        print(f"Coletando página {page}...")
        page_products = scrape_page(page)
        if not page_products:
            break
        for product in page_products:
            if product["sku"] not in seen_skus:
                product["collected_at"] = collected_at
                products.append(product)
                seen_skus.add(product["sku"])
        page += 1
        time.sleep(PAGE_DELAY_SECONDS)

    return {
        "collected_at": collected_at,
        "source": BASE_URL,
        "total_products": len(products),
        "products": products,
    }


# ---------- Coleta de uma página ----------

def scrape_page(page: int) -> list[dict]:
    """Baixa o HTML de uma página e extrai os produtos do JSON-LD."""
    url = f"{BASE_URL}?page={page}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    item_list = find_item_list(soup)
    if not item_list:
        return []

    return extract_products(item_list)


# ---------- Extração do JSON-LD ----------

def find_item_list(soup: BeautifulSoup) -> dict | None:
    """Procura o <script type='application/ld+json'> que contém o ItemList."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("@type") == "ItemList":
            return data
    return None


def extract_products(item_list: dict) -> list[dict]:
    """Transforma o ItemList em uma lista enxuta de produtos (campos brutos)."""
    products = []
    for entry in item_list.get("itemListElement", []):
        item = entry.get("item", {})
        offers = item.get("offers", {})

        products.append({
            "sku": item.get("sku"),
            "name": item.get("name", ""),
            "brand": item.get("brand", {}).get("name"),
            "price": offers.get("lowPrice"),
            "description": item.get("description", ""),
            "url": item.get("@id"),
        })
    return products


# ---------- Execução direta ----------

if __name__ == "__main__":
    result = scrape_all()
    print(f"\n{len(result)} produtos coletados.")
    print(json.dumps(result[:2], ensure_ascii=False, indent=2))