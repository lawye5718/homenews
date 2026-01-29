"""
Custom web scraping tool with enhanced error handling and validation.

This tool wraps ScrapeWebsiteTool to add:
1. Content-type validation (reject PDFs, images, binary files)
2. Detection of blocking pages (Cloudflare, etc.)
3. Size limits to prevent huge downloads
4. Garbled content detection
5. Better error handling with meaningful error messages
"""

import re
import requests
from typing import Any, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScrapeWebsiteToolSchema(BaseModel):
    """Input schema for ScrapeWebsiteTool."""
    website_url: str = Field(..., description="Mandatory website URL to read the file")


class SafeScrapeWebsiteTool(BaseTool):
    """
    Enhanced web scraping tool with validation and error handling.
    
    This tool validates content before scraping to avoid:
    - PDF files and binary content
    - Cloudflare and other blocking pages
    - Garbled or corrupted content
    - Excessively large pages
    """
    
    name: str = "read_website_content"
    description: str = (
        "A tool that can be used to read a website's content safely. "
        "Automatically validates content and skips invalid pages (PDFs, blocked pages, etc.)."
    )
    args_schema: Type[BaseModel] = ScrapeWebsiteToolSchema
    
    # Configuration
    max_content_size: int = 5 * 1024 * 1024  # 5MB limit
    timeout: int = 15  # Request timeout in seconds
    
    def _run(self, **kwargs: Any) -> Any:
        """
        Safely scrape website content with validation.
        
        Args:
            website_url: URL to scrape
            
        Returns:
            Scraped text content or error message
        """
        from bs4 import BeautifulSoup
        
        website_url: str | None = kwargs.get("website_url")
        if not website_url:
            return "Error: Website URL must be provided."
        
        try:
            # Step 1: HEAD request to check content type and size
            try:
                head_response = requests.head(
                    website_url,
                    timeout=10,
                    allow_redirects=True,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                
                # Check content type
                content_type = head_response.headers.get('content-type', '').lower()
                
                # Reject non-HTML content
                if any(x in content_type for x in ['pdf', 'image/', 'video/', 'audio/', 'application/zip', 'application/octet-stream']):
                    return f"Error: Cannot scrape non-HTML content (Content-Type: {content_type}). This appears to be a {content_type.split('/')[0]} file, not a web page."
                
                # Check content length
                content_length = head_response.headers.get('content-length')
                if content_length and int(content_length) > self.max_content_size:
                    return f"Error: Content too large ({int(content_length) / 1024 / 1024:.2f}MB). Maximum allowed size is {self.max_content_size / 1024 / 1024}MB."
                    
            except requests.exceptions.RequestException:
                # If HEAD fails, continue with GET (some servers don't support HEAD)
                pass
            
            # Step 2: GET request to fetch content
            response = requests.get(
                website_url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                stream=True  # Stream to check size incrementally
            )
            
            # Check response status
            if response.status_code != 200:
                return f"Error: Failed to fetch page (HTTP {response.status_code})"
            
            # Read content with size limit
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.max_content_size:
                    return f"Error: Content exceeds size limit ({self.max_content_size / 1024 / 1024}MB)"
            
            # Detect encoding
            response.encoding = response.apparent_encoding
            text_content = content.decode(response.encoding or 'utf-8', errors='ignore')
            
            # Step 3: Validate content is not blocked or corrupted
            
            # Check for binary/PDF content in response body
            if text_content.startswith('%PDF'):
                return "Error: This URL returns a PDF file, not a web page. Cannot extract meaningful text content."
            
            # Check for Cloudflare blocking
            if 'cloudflare' in text_content.lower() and any(x in text_content.lower() for x in ['blocked', 'attention required', 'enable cookies', 'ray id']):
                return "Error: Access blocked by Cloudflare. This website is protecting itself from automated access. Please try a different source."
            
            # Check for other common blocking patterns
            if any(pattern in text_content.lower() for pattern in [
                'access denied',
                'forbidden',
                '403 forbidden',
                'you are being rate limited',
                'captcha',
                'please verify you are human'
            ]):
                return "Error: Access denied or blocked by the website. Please try a different source."
            
            # Check for empty or minimal content
            if len(text_content.strip()) < 100:
                return "Error: Page content is too short or empty. This may not be a valid news article."
            
            # Step 4: Parse HTML and extract text
            parsed = BeautifulSoup(text_content, "html.parser")
            
            # Remove script and style elements
            for script in parsed(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = "The following text is scraped website content:\n\n"
            text += parsed.get_text(" ", strip=True)
            
            # Clean up whitespace
            text = re.sub("[ \t]+", " ", text)
            text = re.sub("\\s+\n\\s+", "\n", text)
            text = re.sub("\n{3,}", "\n\n", text)  # Limit consecutive newlines
            
            # Final validation - check if we got meaningful content
            if len(text.strip()) < 200:
                return "Error: Extracted content is too short. This page may not contain useful information."
            
            # Check for garbled content (too many non-ASCII characters relative to length)
            ascii_chars = sum(1 for c in text if ord(c) < 128)
            if len(text) > 500 and ascii_chars / len(text) < 0.3:
                # This might be OK for Chinese content, but check if it's actually readable
                # For Chinese, we expect certain Unicode ranges
                chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                if chinese_chars / len(text) < 0.1:  # Not much Chinese either
                    return "Error: Content appears to be garbled or in an unsupported encoding."
            
            return text
            
        except requests.exceptions.Timeout:
            return f"Error: Request timed out after {self.timeout} seconds. The website may be slow or unresponsive."
        
        except requests.exceptions.ConnectionError:
            return "Error: Failed to connect to the website. The server may be down or the URL may be invalid."
        
        except requests.exceptions.TooManyRedirects:
            return "Error: Too many redirects. The URL may be broken or redirecting in a loop."
        
        except Exception as e:
            return f"Error: Failed to scrape website: {type(e).__name__}: {str(e)}"
