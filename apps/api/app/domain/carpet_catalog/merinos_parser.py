"""Parser module for official Merinos public catalog pages."""
import hashlib
import json
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup


NON_PRODUCT_URL_PATTERNS = [
    r"/blog\b",
    r"/blog/",
    r"/blog/month/",
    r"/blog/category/",
    r"/blog/tag/",
    r"/haber\b",
    r"/haberler\b",
    r"/duyuru\b",
    r"/kurumsal\b",
    r"/iletisim\b",
    r"/sepet\b",
    r"/hesabim\b",
    r"/kategori\b",
    r"\.(jpg|jpeg|png|webp|gif|css|js|pdf)\b",
]


def is_non_product_url(url: str) -> bool:
    """Return True if the URL points to a non-product page (blog, news, nav, asset)."""
    if not url:
        return True
    url_lower = url.lower()
    for pattern in NON_PRODUCT_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False


def is_valid_product_sku(sku: str) -> bool:
    """Validate if a SKU string represents a legitimate product SKU (not a date or nav string)."""
    if not sku:
        return False
    # Reject date patterns like YYYY MM or YYYY-MM e.g. 2022 10, 2024 11
    if re.match(r"^(19|20)\d{2}[\s-](0[1-9]|1[0-2])$", sku):
        return False
    return True


def normalize_sku(raw_sku: str) -> str:
    """Normalize raw SKU string. Preserves official SKU characters after stripping extra whitespace."""
    if not raw_sku:
        return ""
    cleaned = re.sub(r"\s+", " ", raw_sku.strip())
    return cleaned


def parse_collection_page(html: str, collection_url: str) -> Dict[str, Any]:
    """Parse a Merinos collection HTML page to extract collection name and product links."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract collection title
    h1 = soup.find("h1")
    collection_name = h1.get_text(strip=True) if h1 else ""
    if not collection_name and soup.title and soup.title.string:
        title_str = soup.title.string
        if "Merinos" in title_str:
            collection_name = title_str.replace("Merinos.", "").replace("Merinos", "").strip()

    product_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if is_non_product_url(href):
            continue

        # Product path patterns on Merinos site e.g. /90823-070 or /73941-060
        if re.search(r"/\d{4,6}[-\s]\d{2,4}", href) or (
            re.search(r"/\d{5,7}", href)
            and not any(x in href.lower() for x in ["thumb", "image", "content", "ajax", "css", "js", "png", "jpg"])
        ):
            if not href.startswith("http"):
                if href.startswith("/"):
                    full_url = "https://www.merinos.com.tr" + href
                else:
                    full_url = "https://www.merinos.com.tr/" + href
            else:
                full_url = href
            
            if not is_non_product_url(full_url):
                product_links.add(full_url)

    return {
        "collection_name": collection_name,
        "collection_url": collection_url,
        "product_links": sorted(list(product_links)),
    }


def parse_product_page(html: str, product_url: str, fallback_collection: Optional[str] = None) -> Dict[str, Any]:
    """Parse a Merinos product HTML page to extract factual product metadata."""
    if is_non_product_url(product_url):
        raise ValueError(f"Invalid non-product URL provided to parse_product_page: {product_url}")

    soup = BeautifulSoup(html, "html.parser")

    # 1. Collection Name
    h1 = soup.find("h1")
    collection_name = h1.get_text(strip=True) if h1 else (fallback_collection or "")

    # 2. SKU
    raw_sku = ""
    sku_node = soup.find(string=re.compile(r"Ürün Kodu", re.I))
    if sku_node:
        parent = sku_node.parent
        raw_sku = parent.get_text(strip=True).replace("Ürün Kodu:", "").replace("Ürün Kodu", "").strip()

    if not raw_sku:
        # Fallback to URL path regex match (e.g. 90823-070 from /90823-070)
        match = re.search(r"/(\d{4,6}[-\s]\d{2,4})", product_url)
        if match:
            cand = match.group(1).replace("-", " ")
            if is_valid_product_sku(cand):
                raw_sku = cand

    sku = normalize_sku(raw_sku)
    if not is_valid_product_sku(sku):
        raise ValueError(f"Product page at {product_url} did not yield a valid product SKU (got '{sku}').")

    # 3. Product Name
    name = f"{collection_name} {sku}".strip() if collection_name and sku else (sku or collection_name or "Merinos Halı")

    # 4. Available Sizes
    sizes: List[str] = []
    for option in soup.find_all(["option", "li", "button", "span", "td", "p"]):
        t = option.get_text(strip=True)
        if re.search(r"\b\d{2,3}\s*[xX*]\s*\d{2,3}\b", t):
            m = re.search(r"\b\d{2,3}\s*[xX*]\s*\d{2,3}\b", t).group(0)
            clean_size = m.lower().replace(" ", "")
            if clean_size not in sizes:
                sizes.append(clean_size)

    # 5. Primary Image URL (Metadata only for A2, NOT downloaded in A1)
    primary_image_url: Optional[str] = None
    sku_slug = sku.replace(" ", "-") if sku else ""
    sku_compact = sku.replace(" ", "") if sku else ""

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        if src and isinstance(src, str):
            src_lower = src.lower()
            if any(k in src_lower for k in ["thumbs", "product", "upload"]) or (sku_slug and sku_slug in src_lower) or (sku_compact and sku_compact in src_lower):
                if not src.startswith("http"):
                    if src.startswith("/"):
                        src = "https://www.merinos.com.tr" + src
                    else:
                        src = "https://www.merinos.com.tr/" + src
                if "default-image" not in src:
                    primary_image_url = src
                    break

    factual_dict: Dict[str, Any] = {
        "sku": sku,
        "name": name,
        "collection": collection_name,
        "manufacturer": "Merinos",
        "source_url": product_url,
        "available_sizes": sizes,
        "primary_image_url": primary_image_url,
    }
    hash_str = json.dumps(factual_dict, sort_keys=True)
    factual_dict["source_hash"] = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()

    return factual_dict
