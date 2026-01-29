#!/usr/bin/env python3
"""
Unit tests for SafeScrapeWebsiteTool

This test suite verifies the custom scraping tool's error handling
without requiring actual internet access.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from custom_scrape_tool import SafeScrapeWebsiteTool


class TestSafeScrapeWebsiteTool(unittest.TestCase):
    """Test cases for SafeScrapeWebsiteTool"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tool = SafeScrapeWebsiteTool()
    
    def test_tool_initialization(self):
        """Test that tool initializes correctly"""
        self.assertEqual(self.tool.name, "read_website_content")
        self.assertIn("safely", self.tool.description.lower())
    
    @patch('custom_scrape_tool.requests.head')
    @patch('custom_scrape_tool.requests.get')
    def test_pdf_rejection(self, mock_get, mock_head):
        """Test that PDF files are rejected"""
        # Mock HEAD response indicating PDF
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {'content-type': 'application/pdf'}
        mock_head.return_value = mock_head_response
        
        result = self.tool.run(website_url="https://example.com/file.pdf")
        
        self.assertIn("Error:", result)
        self.assertIn("non-HTML content", result)
        mock_get.assert_not_called()  # Should not proceed to GET
    
    @patch('custom_scrape_tool.requests.head')
    @patch('custom_scrape_tool.requests.get')
    def test_cloudflare_detection(self, mock_get, mock_head):
        """Test that Cloudflare blocking is detected"""
        # Mock HEAD succeeds
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {'content-type': 'text/html'}
        mock_head.return_value = mock_head_response
        
        # Mock GET returns Cloudflare block page
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.encoding = 'utf-8'
        mock_get_response.apparent_encoding = 'utf-8'
        mock_get_response.iter_content = lambda chunk_size: [
            b'<html><body>Attention Required! | Cloudflare\nYou are unable to access example.com\nSorry, you have been blocked</body></html>'
        ]
        mock_get.return_value = mock_get_response
        
        result = self.tool.run(website_url="https://example.com")
        
        self.assertIn("Error:", result)
        self.assertIn("Cloudflare", result)
    
    @patch('custom_scrape_tool.requests.head')
    @patch('custom_scrape_tool.requests.get')
    def test_successful_scrape(self, mock_get, mock_head):
        """Test successful scraping of valid HTML"""
        # Mock HEAD succeeds
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {'content-type': 'text/html'}
        mock_head.return_value = mock_head_response
        
        # Mock GET returns valid HTML
        html_content = '''
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Heading</h1>
                <p>This is a test paragraph with enough content to pass validation checks. 
                We need at least 200 characters to pass the content validation, so let's add 
                some more text here to make sure we meet that threshold. This is important 
                for testing the successful scraping functionality.</p>
            </body>
        </html>
        '''
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.encoding = 'utf-8'
        mock_get_response.apparent_encoding = 'utf-8'
        mock_get_response.iter_content = lambda chunk_size: [html_content.encode('utf-8')]
        mock_get.return_value = mock_get_response
        
        result = self.tool.run(website_url="https://example.com")
        
        self.assertNotIn("Error:", result)
        self.assertIn("scraped website content", result)
        self.assertIn("Main Heading", result)
        self.assertIn("test paragraph", result)
    
    @patch('custom_scrape_tool.requests.head')
    @patch('custom_scrape_tool.requests.get')
    def test_size_limit(self, mock_get, mock_head):
        """Test that oversized content is rejected"""
        # Mock HEAD with large content-length
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {
            'content-type': 'text/html',
            'content-length': str(10 * 1024 * 1024)  # 10MB
        }
        mock_head.return_value = mock_head_response
        
        result = self.tool.run(website_url="https://example.com")
        
        self.assertIn("Error:", result)
        self.assertIn("too large", result.lower())
        mock_get.assert_not_called()
    
    @patch('custom_scrape_tool.requests.head')
    @patch('custom_scrape_tool.requests.get')
    def test_timeout_handling(self, mock_get, mock_head):
        """Test that timeouts are handled gracefully"""
        import requests
        
        mock_head.side_effect = requests.exceptions.Timeout()
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = self.tool.run(website_url="https://example.com")
        
        self.assertIn("Error:", result)
        self.assertIn("timed out", result.lower())
    
    @patch('custom_scrape_tool.requests.head')
    @patch('custom_scrape_tool.requests.get')
    def test_connection_error(self, mock_get, mock_head):
        """Test that connection errors are handled"""
        import requests
        
        mock_head.side_effect = requests.exceptions.ConnectionError()
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        result = self.tool.run(website_url="https://example.com")
        
        self.assertIn("Error:", result)
        self.assertIn("connect", result.lower())
    
    def test_missing_url(self):
        """Test that missing URL is handled"""
        result = self.tool.run()
        
        self.assertIn("Error:", result)
        self.assertIn("must be provided", result)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
