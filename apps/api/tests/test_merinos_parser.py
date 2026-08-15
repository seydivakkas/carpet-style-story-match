"""Unit tests for Merinos catalog HTML parser using synthetic HTML fixtures."""
import pytest
from app.domain.carpet_catalog.merinos_parser import (
    normalize_sku,
    parse_collection_page,
    parse_product_page,
)


def test_normalize_sku():
    assert normalize_sku(" 90823 070 ") == "90823 070"
    assert normalize_sku("90823\t  070\n") == "90823 070"
    assert normalize_sku("") == ""


def test_parse_collection_page_synthetic():
    html_fixture = """
    <!DOCTYPE html>
    <html>
    <head><title>Merinos. Elegance</title></head>
    <body>
        <h1>Elegance</h1>
        <div class="product-grid">
            <a href="/90823-070">Elegance 90823-070</a>
            <a href="/73941-060">Elegance 73941-060</a>
            <a href="https://www.merinos.com.tr/74423-096">Elegance 74423-096</a>
            <a href="/contact">İletişim</a>
        </div>
    </body>
    </html>
    """
    res = parse_collection_page(html_fixture, "https://www.merinos.com.tr/Elegance")
    assert res["collection_name"] == "Elegance"
    assert res["collection_url"] == "https://www.merinos.com.tr/Elegance"
    assert "https://www.merinos.com.tr/90823-070" in res["product_links"]
    assert "https://www.merinos.com.tr/73941-060" in res["product_links"]
    assert "https://www.merinos.com.tr/74423-096" in res["product_links"]
    assert not any("contact" in link for link in res["product_links"])


def test_parse_product_page_synthetic():
    html_fixture = """
    <!DOCTYPE html>
    <html>
    <head><title>Merinos. 90823 070</title></head>
    <body>
        <h1>Elegance</h1>
        <div>
            <span>Ürün Kodu:</span>
            <span>90823 070</span>
        </div>
        <select name="size">
            <option>80x150</option>
            <option>100x200</option>
            <option>160x230</option>
            <option>200x290</option>
        </select>
        <img src="https://wwwmerinoscomtr.sm.mncdn.com/content/images/thumbs/183/90823-070.jpeg" alt="Elegance" />
    </body>
    </html>
    """
    res = parse_product_page(html_fixture, "https://www.merinos.com.tr/90823-070")

    assert res["sku"] == "90823 070"
    assert res["collection"] == "Elegance"
    assert res["manufacturer"] == "Merinos"
    assert res["name"] == "Elegance 90823 070"
    assert res["source_url"] == "https://www.merinos.com.tr/90823-070"
    assert res["available_sizes"] == ["80x150", "100x200", "160x230", "200x290"]
    assert res["primary_image_url"] == "https://wwwmerinoscomtr.sm.mncdn.com/content/images/thumbs/183/90823-070.jpeg"
    assert "source_hash" in res
    assert len(res["source_hash"]) == 64


def test_parse_product_page_missing_sku_fallback():
    html_fixture = """
    <html>
    <body>
        <h1>Arden</h1>
        <div>No SKU tag here</div>
        <span>80x150</span>
    </body>
    </html>
    """
    res = parse_product_page(html_fixture, "https://www.merinos.com.tr/74430-060", fallback_collection="Arden")
    assert res["sku"] == "74430 060"
    assert res["collection"] == "Arden"


def test_multiple_sizes_do_not_create_multiple_products():
    """Verify that multiple size options in product HTML extract into a single product record with an available_sizes array."""
    html_fixture = """
    <html>
    <body>
        <h1>Vega</h1>
        <span>Ürün Kodu: 12345 678</span>
        <ul>
            <li>80x150</li>
            <li>120x180</li>
            <li>160x230</li>
        </ul>
    </body>
    </html>
    """
    res = parse_product_page(html_fixture, "https://www.merinos.com.tr/12345-678")
    assert res["sku"] == "12345 678"
    assert isinstance(res["available_sizes"], list)
    assert len(res["available_sizes"]) == 3
    # Exactly ONE single product dict is returned
    assert res["name"] == "Vega 12345 678"
