"""
HEM Product Catalogue v3 - Configuration
All paths, constants, environment variables, and catalogue definitions.
"""
import os

# ── Base directory (folder this file lives in) ──────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── ImageKit.io credentials (set these in Streamlit Cloud → Secrets) ────────
# Locally you can put them in a .env file or system environment variables.
IMAGEKIT_URL_ENDPOINT = os.environ.get("IMAGEKIT_URL_ENDPOINT", "https://ik.imagekit.io/tov7hy7nb/")       # e.g. https://ik.imagekit.io/your_id
IMAGEKIT_PUBLIC_KEY   = os.environ.get("IMAGEKIT_PUBLIC_KEY",   "public_1JQ1CHYT064IsWvlfWoInjo2LWk=")       # your public key
IMAGEKIT_PRIVATE_KEY  = os.environ.get("IMAGEKIT_PRIVATE_KEY",  "private_ZmZna8+ENuwze8tG9goU4Iny7NQ=")       # your private key

# ── Local asset paths ────────────────────────────────────────────────────────
LOGO_PATH          = os.path.join(BASE_DIR, "assets", "logo.png")
STORY_IMG_1_PATH   = os.path.join(BASE_DIR, "image-journey.png")
COVER_IMG_PATH     = os.path.join(BASE_DIR, "assets", "cover page.png")
WATERMARK_IMG_PATH = os.path.join(BASE_DIR, "assets", "watermark.png")

# ── JSON database & template paths ──────────────────────────────────────────
TEMPLATES_DIR       = os.path.join(BASE_DIR, "templates")
SAVED_TEMPLATES_FILE= os.path.join(BASE_DIR, "saved_templates.json")
CUSTOM_ITEMS_FILE   = os.path.join(BASE_DIR, "custom_products.json")   # legacy
PRODUCTS_DB_FILE    = os.path.join(BASE_DIR, "data", "products_db.json")

# ── Remote image / data URLs ─────────────────────────────────────────────────
GITHUB_RAW_BASE  = "https://raw.githubusercontent.com/jitu0426/Hem-Export-Catalogue/main/"

# ── Case Size Excel — loaded from New-App repo (always latest) ───────────────
CASE_SIZE_PATH   = "PK"
# ── Update these with your ImageKit.io URLs after uploading ─────────────────
COVER_IMAGE_URL  = "https://ik.imagekit.io/tov7hy7nb/cover-page.jpg"   # e.g. https://ik.imagekit.io/your_id/Cover_page_3_1.jpg
JOURNEY_IMAGE_URL= "https://ik.imagekit.io/tov7hy7nb/JOURNEY2.jpeg"   # e.g. https://ik.imagekit.io/your_id/JOURNEY2.jpg

# ── Catalogue-specific cover images ──────────────────────────────────────────
# When ALL products in the cart belong to a single catalogue, use that cover.
# Otherwise (HEM-only or mixed catalogues) → use the default COVER_IMAGE_URL.
# Upload your cover images to ImageKit.io and update these URLs.
CATALOGUE_COVER_URLS = {
    "Sacred Elements Catalogue": "https://ik.imagekit.io/tov7hy7nb/Sacred%20Elements%20cover%20page%201.jpg%20(1).png",   # ← paste Sacred Elements cover URL here
    "Pooja Oil Catalogue":       "https://ik.imagekit.io/tov7hy7nb/Pooja%20catalogue%20Front%20page.jpg?updatedAt=1774527941706",   # ← paste Pooja Oil cover URL here
    "Candle Catalogue":          "https://ik.imagekit.io/tov7hy7nb/Candles%20catalogue%20CTC%20(1).jpg?updatedAt=1774527941959",   # ← paste Candle cover URL here
}

# ── Excel catalogue file paths ───────────────────────────────────────────────
# Keys are the catalogue display names; values are local Excel file paths.
CATALOGUE_PATHS = {
    "HEM Product Catalogue":   os.path.join(BASE_DIR, "Hem catalogue.xlsx"),
    "Sacred Elements Catalogue": os.path.join(BASE_DIR, "SacredElement.xlsx"),
    "Pooja Oil Catalogue":     os.path.join(BASE_DIR, "Pooja Oil Catalogue.xlsx"),
    "Candle Catalogue":        os.path.join(BASE_DIR, "Candle Catalogue.xlsx"),
}

# ── Column name mapping (Excel column → internal name) ──────────────────────
GLOBAL_COLUMN_MAPPING = {
    "Category":                  "Category",
    "Sub-Category":              "Subcategory",
    "Item Name":                 "ItemName",
    "ItemName":                  "ItemName",
    "Description":               "Fragrance",
    "SKU Code":                  "SKU Code",
    "New Product ( Indication )":"IsNew",
}

# ── Required columns in the output DataFrame ─────────────────────────────────
REQUIRED_OUTPUT_COLS = [
    'Category', 'Subcategory', 'ItemName', 'Fragrance', 'SKU Code',
    'Catalogue', 'Packaging', 'ImageB64', 'ProductID', 'IsNew',
]

# ── Columns stored in the cart list-of-dicts ────────────────────────────────
CART_COLUMNS = [
    'SKU Code', 'ItemName', 'Category', 'Subcategory', 'Fragrance',
    'Packaging', 'SerialNo', 'ImageB64', 'Catalogue', 'ProductID', 'IsNew',
]

# ── UI text constants ─────────────────────────────────────────────────────────
NO_SELECTION_PLACEHOLDER = "Select..."
APP_TITLE = "HEM PRODUCT CATALOGUE"
APP_ICON  = "🛍️"
