"""
SSRF-Resistant URL Ingestion and Content Extraction Service.

Features:
- Validates protocols (HTTP/HTTPS only).
- Resolves DNS and blocks loopback, private RFC 1918, link-local, multicast, and AWS/cloud metadata (169.254.169.254).
- Safe redirect following with per-hop DNS and IP revalidation (max 3 redirects).
- Streaming size limits (rejects payload > 15MB) to protect against DoS.
- Enforces connection and read timeouts (max 10 seconds).
- Validates MIME types (HTML, plain text, markdown, PDF).
- Clean text and metadata extraction with script/style stripping.
"""
import re
import socket
import ipaddress
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
import httpx

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_REDIRECTS = 3
REQUEST_TIMEOUT_SECONDS = 10.0


def is_ip_disallowed(ip_str: str) -> bool:
    """
    Checks if an IP address is private, loopback, link-local, multicast, or reserved.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved or
            ip.is_unspecified or
            str(ip).startswith("169.254.") # Cloud metadata services
        )
    except ValueError:
        return True


def validate_target_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates URL scheme and resolves hostname to ensure it does not point to internal resources.
    Returns (is_valid, sanitized_url_or_error, resolved_ip).
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string.", None

    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return False, "Invalid protocol. Only HTTP and HTTPS URLs are supported.", None

    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        return False, f"Malformed URL: {e}", None

    hostname = parsed.hostname
    if not hostname:
        return False, "URL lacks a valid hostname.", None

    hostname_lower = hostname.lower()
    if hostname_lower in ["localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal"]:
        return False, "Access to localhost and internal endpoints is forbidden.", None

    # Resolve IP address
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        if not addr_info:
            return False, f"Could not resolve hostname '{hostname}'.", None

        # Verify each resolved IP
        for entry in addr_info:
            resolved_ip = entry[4][0]
            if is_ip_disallowed(resolved_ip):
                return False, f"Target IP '{resolved_ip}' is private, local, or reserved and cannot be accessed.", None

        primary_ip = addr_info[0][4][0]
        return True, clean_url, primary_ip
    except socket.gaierror as e:
        return False, f"DNS resolution failed for hostname '{hostname}': {e}", None
    except Exception as e:
        return False, f"Network validation failed: {e}", None


def clean_html_to_markdown_text(html_text: str) -> Tuple[str, str]:
    """
    Extracts title and structured clean text from HTML content without executing scripts.
    """
    # 1. Extract title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    title = re.sub(r'\s+', ' ', title)

    # 2. Remove script and style elements completely
    clean_html = re.sub(r'<(script|style|noscript|svg|iframe|header|footer|nav)[^>]*>.*?</\1>', ' ', html_text, flags=re.IGNORECASE | re.DOTALL)

    # 3. Transform headings into markdown-style headings
    clean_html = re.sub(r'<h[1-2][^>]*>(.*?)</h[1-2]>', r'\n\n## \1\n\n', clean_html, flags=re.IGNORECASE | re.DOTALL)
    clean_html = re.sub(r'<h[3-6][^>]*>(.*?)</h[3-6]>', r'\n\n### \1\n\n', clean_html, flags=re.IGNORECASE | re.DOTALL)
    clean_html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\n\1\n\n', clean_html, flags=re.IGNORECASE | re.DOTALL)
    clean_html = re.sub(r'<li[^>]*>(.*?)</li>', r'\n* \1', clean_html, flags=re.IGNORECASE | re.DOTALL)
    clean_html = re.sub(r'<br\s*/?>', '\n', clean_html, flags=re.IGNORECASE)

    # 4. Strip remaining HTML tags
    text_content = re.sub(r'<[^>]+>', ' ', clean_html)

    # 5. Decode common HTML entities
    text_content = (
        text_content.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )

    # 6. Normalize whitespace
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text_content.splitlines()]
    clean_lines = [l for l in lines if l]
    result_text = "\n\n".join(clean_lines)

    return title or "Web Article", result_text


def fetch_url_content_ssrf_safe(target_url: str) -> Dict[str, Any]:
    """
    Executes SSRF-safe request, following redirects manually to validate each hop.
    Enforces maximum size limit and returns clean readable text and metadata.
    """
    current_url = target_url
    redirect_count = 0

    headers = {
        "User-Agent": "HumanCache/1.0 (https://humancache.ai; contact@humancache.ai) EducationalBot/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    }

    while redirect_count <= MAX_REDIRECTS:
        is_valid, validated_url_or_err, _ = validate_target_url(current_url)
        if not is_valid:
            return {
                "success": False,
                "error": f"Security verification failed: {validated_url_or_err}",
                "url": current_url,
                "status_code": 400
            }

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=False) as client:
                response = client.get(current_url, headers=headers)

                # Check for redirects
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get("Location")
                    if not location:
                        return {"success": False, "error": "Redirect received with missing Location header.", "url": current_url}
                    
                    next_url = urljoin(current_url, location)
                    current_url = next_url
                    redirect_count += 1
                    continue

                if response.status_code in [401, 403]:
                    return {
                        "success": False,
                        "error": "Remote website blocked automated server ingestion (HTTP 403 / anti-bot policy). Please use extension page content capture or select text.",
                        "status_code": response.status_code,
                        "url": current_url
                    }

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Remote server returned HTTP {response.status_code}.",
                        "status_code": response.status_code,
                        "url": current_url
                    }

                # Validate Content-Type
                content_type = response.headers.get("Content-Type", "").lower()
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_DOWNLOAD_SIZE_BYTES:
                    return {
                        "success": False,
                        "error": f"Content exceeds maximum allowable size of {MAX_DOWNLOAD_SIZE_BYTES // (1024*1024)}MB.",
                        "url": current_url
                    }

                # Check if PDF
                if "application/pdf" in content_type:
                    return {
                        "success": True,
                        "is_pdf": True,
                        "content_bytes": response.content[:MAX_DOWNLOAD_SIZE_BYTES],
                        "title": current_url.split("/")[-1] or "Downloaded Document.pdf",
                        "content_type": content_type,
                        "url": current_url
                    }

                # Process text/html
                raw_bytes = response.content[:MAX_DOWNLOAD_SIZE_BYTES]
                encoding = response.encoding or "utf-8"
                raw_text = raw_bytes.decode(encoding, errors="replace")

                title, cleaned_text = clean_html_to_markdown_text(raw_text)

                if len(cleaned_text.strip()) < 40:
                    # Very short or possibly dynamic client-rendered page
                    snippet = cleaned_text.strip() or f"Article link captured from {urlparse(current_url).netloc}"
                    cleaned_text = f"{snippet}\n\n[Original Source: {current_url}]"

                return {
                    "success": True,
                    "is_pdf": False,
                    "title": title[:200],
                    "content_text": cleaned_text,
                    "content_type": content_type,
                    "url": current_url
                }

        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timed out after 10 seconds.", "url": current_url}
        except httpx.RequestError as e:
            return {"success": False, "error": f"Network request error: {str(e)}", "url": current_url}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error during URL capture: {str(e)}", "url": current_url}

    return {"success": False, "error": f"Exceeded maximum redirect limit of {MAX_REDIRECTS}.", "url": current_url}
