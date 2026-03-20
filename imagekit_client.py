"""
HEM Product Catalogue - ImageKit.io Client Module
ImageKit configuration, image operations, and file management.
"""
import os
import io
import base64
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image

from config import (
    IMAGEKIT_URL_ENDPOINT, IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY,
    PRODUCTS_DB_FILE, SAVED_TEMPLATES_FILE,
)

logger = logging.getLogger(__name__)

# Reusable HTTP session for connection pooling (avoids TCP/TLS handshake per image)
_http_session = requests.Session()
_http_session.headers.update({"User-Agent": "Mozilla/5.0"})
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
_http_session.mount("https://", adapter)
_http_session.mount("http://", adapter)


# --- Initialize ImageKit ---
def init_imagekit():
    """Validate ImageKit.io configuration. Call once at startup."""
    if not IMAGEKIT_PRIVATE_KEY:
        logger.warning("IMAGEKIT_PRIVATE_KEY not set - image features will be limited")
    if not IMAGEKIT_URL_ENDPOINT:
        logger.warning("IMAGEKIT_URL_ENDPOINT not set - image URLs cannot be constructed")
    else:
        logger.info(f"ImageKit.io configured: {IMAGEKIT_URL_ENDPOINT}")


# --- Image Processing ---
def get_image_as_base64_str(url_or_path, resize=None, max_size=None, retries=1):
    """Download/open an image and return it as a base64-encoded JPEG string.
    Supports both HTTP URLs and local file paths.
    Includes retry logic for network fetches."""
    if not url_or_path:
        return ""
    for attempt in range(retries + 1):
        try:
            img = None
            if str(url_or_path).startswith("http"):
                response = _http_session.get(url_or_path, timeout=5)
                if response.status_code != 200:
                    return ""
                img = Image.open(io.BytesIO(response.content))
            else:
                if not os.path.exists(url_or_path):
                    return ""
                img = Image.open(url_or_path)

            if max_size:
                img.thumbnail(max_size)
            elif resize:
                img = img.resize(resize)

            buffered = io.BytesIO()
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buffered, format="JPEG", quality=75)
            return base64.b64encode(buffered.getvalue()).decode()

        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(0.3 * (attempt + 1))
                continue
            logger.warning(f"Image fetch timed out: {url_or_path}")
            return ""
        except Exception as e:
            logger.warning(f"Error processing image {url_or_path}: {e}")
            return ""
    return ""


def batch_download_images(url_list, max_workers=16):
    """Download multiple images in parallel and return a dict of {url: base64_str}.
    Uses ThreadPoolExecutor for concurrent HTTP requests."""
    results = {}
    if not url_list:
        return results

    def _fetch_one(url):
        return url, get_image_as_base64_str(url, max_size=None)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, url): url for url in url_list}
        for future in as_completed(futures):
            try:
                url, b64 = future.result()
                results[url] = b64
            except Exception:
                results[futures[future]] = ""
    return results


# --- ImageKit.io File Listing (replaces Cloudinary resource indexing) ---
def fetch_all_imagekit_resources():
    """Fetch all uploaded files from ImageKit.io media library.
    Returns a list of dicts with 'filePath' and 'url' keys
    (mapped to match the old 'public_id' / 'secure_url' interface)."""
    resources = []
    if not IMAGEKIT_PRIVATE_KEY:
        logger.warning("Cannot fetch ImageKit resources: IMAGEKIT_PRIVATE_KEY not set")
        return resources

    try:
        skip = 0
        limit = 1000
        while True:
            resp = requests.get(
                "https://api.imagekit.io/v1/files",
                params={"skip": skip, "limit": limit},
                auth=(IMAGEKIT_PRIVATE_KEY, ""),
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning(f"ImageKit API error {resp.status_code}: {resp.text}")
                break

            batch = resp.json()
            if not batch:
                break

            for item in batch:
                file_path = item.get("filePath", "")
                url = item.get("url", "")
                # Strip leading slash for consistency with old cloudinary public_id
                public_id = file_path.lstrip("/")
                # Remove file extension from public_id to match old behaviour
                name_no_ext = public_id
                for ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']:
                    if name_no_ext.lower().endswith(ext):
                        name_no_ext = name_no_ext[:-len(ext)]
                        break
                resources.append({
                    "public_id": name_no_ext,
                    "secure_url": url,
                })

            if len(batch) < limit:
                break
            skip += limit

        logger.info(f"Fetched {len(resources)} resources from ImageKit.io")
    except Exception as e:
        logger.warning(f"ImageKit resource fetch failed: {e}")
    return resources


# --- Custom Image Upload ---
def upload_custom_image(image_file):
    """Upload a custom product image to ImageKit.io.
    Returns the URL or empty string."""
    if not IMAGEKIT_PRIVATE_KEY:
        logger.error("Cannot upload: IMAGEKIT_PRIVATE_KEY not set")
        return ""
    try:
        # Read file content and encode to base64
        file_content = image_file.read()
        file_b64 = base64.b64encode(file_content).decode()
        file_name = getattr(image_file, 'name', 'custom_image.jpg')

        resp = requests.post(
            "https://upload.imagekit.io/api/v1/files/upload",
            data={
                "file": file_b64,
                "fileName": file_name,
                "folder": "/custom_uploads",
            },
            auth=(IMAGEKIT_PRIVATE_KEY, ""),
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("url", "")
        else:
            logger.error(f"ImageKit upload failed ({resp.status_code}): {resp.text}")
            return ""
    except Exception as e:
        logger.error(f"Custom image upload failed: {e}")
        return ""


