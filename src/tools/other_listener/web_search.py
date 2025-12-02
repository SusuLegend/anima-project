"""
Web Search Tool

This tool provides web search functionality using DuckDuckGo search API.
It allows the AI assistant to search the internet for information.

Requirements:
- pip install duckduckgo-search
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional

# Try to import duckduckgo_search
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("Warning: duckduckgo-search not installed. Install with: pip install duckduckgo-search")


class WebSearcher:
    """
    Performs web searches using DuckDuckGo.
    """
    
    def __init__(self):
        """Initialize web searcher."""
        self.ddgs = DDGS() if DDGS_AVAILABLE else None
    
    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt"
    ) -> List[Dict[str, str]]:
        """
        Search the web for a query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            region: Search region (default: worldwide)
        
        Returns:
            List of dicts with keys: 'title', 'link', 'snippet'
        """
        if not DDGS_AVAILABLE or not self.ddgs:
            return [{
                'title': 'Search Unavailable',
                'link': '',
                'snippet': 'Web search requires duckduckgo-search package. Install with: pip install duckduckgo-search'
            }]
        
        try:
            results = []
            search_results = self.ddgs.text(query, region=region, max_results=max_results)
            
            for result in search_results:
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('href', result.get('link', '')),
                    'snippet': result.get('body', result.get('snippet', ''))
                })
            
            return results
        
        except Exception as e:
            print(f"Search error: {e}")
            return [{
                'title': 'Search Error',
                'link': '',
                'snippet': f'An error occurred during search: {str(e)}'
            }]
    
    def search_formatted(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt"
    ) -> str:
        """
        Search and return formatted results as a string.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
        
        Returns:
            Formatted string with search results
        """
        results = self.search(query, max_results=max_results, region=region)
        
        if not results:
            return f"No results found for: {query}"
        
        output_parts = [f"Search results for '{query}':\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No Title')
            link = result.get('link', '')
            snippet = result.get('snippet', 'No description available')
            
            output_parts.append(
                f"\n{i}. {title}\n"
                f"   Link: {link}\n"
                f"   {snippet}"
            )
        
        return "\n".join(output_parts)
    
    def quick_search(self, query: str) -> str:
        """
        Perform a quick search and return a concise summary.
        
        Args:
            query: Search query
        
        Returns:
            Brief summary of top results
        """
        results = self.search(query, max_results=3)
        
        if not results:
            return f"No information found for: {query}"
        
        summaries = []
        for result in results:
            snippet = result.get('snippet', '')[:150]
            if snippet:
                summaries.append(snippet)
        
        if summaries:
            return " ".join(summaries)
        else:
            return f"Found results for '{query}' but couldn't extract summaries."


def web_search(query: str, max_results: int = 5, region: str = "wt-wt") -> str:
    """
    Simple function to search the web and return formatted results.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
    
    Returns:
        Formatted string with search results
    """
    searcher = WebSearcher()
    return searcher.search_formatted(query, max_results=max_results, region=region)


def quick_search(query: str) -> str:
    """
    Quick search function for brief information.
    
    Args:
        query: Search query
    
    Returns:
        Brief summary of search results
    """
    searcher = WebSearcher()
    return searcher.quick_search(query)


# Example usage for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Web Search Tool - Test")
    print("=" * 60)
    
    if not DDGS_AVAILABLE:
        print("\n❌ DuckDuckGo Search not available")
        print("Install with: pip install duckduckgo-search")
        sys.exit(1)
    
    searcher = WebSearcher()
    
    # Test search
    test_query = "name of disney famous mouse"
    print(f"\nSearching for: {test_query}")
    print("\n" + searcher.search_formatted(test_query, max_results=3))
    
    # Test quick search
    print("\n" + "=" * 60)
    test_query2 = "weather today"
    print(f"\nQuick search for: {test_query2}")
    print(searcher.quick_search(test_query2))
