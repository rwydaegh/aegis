"""
Nature Career Column Scraper
Scrapes all career column articles from Nature.com
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path

# Base URLs
LIST_URL_TEMPLATE = "https://www.nature.com/nature/articles?searchType=journalSearch&sort=PubDate&type=career-column&page={}"
BASE_URL = "https://www.nature.com"

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def get_article_urls_from_page(page_num):
    """Get all article URLs from a single listing page."""
    url = LIST_URL_TEMPLATE.format(page_num)
    print(f"Fetching page {page_num}: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error fetching page {page_num}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all article links - they're in h3 tags within article listings
    article_links = []
    
    # Look for article links in various formats
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/articles/d41586-' in href:
            full_url = BASE_URL + href if href.startswith('/') else href
            if full_url not in article_links:
                article_links.append(full_url)
    
    print(f"  Found {len(article_links)} articles on page {page_num}")
    return article_links


def get_article_content(url):
    """Get the title and full text of a single article."""
    print(f"  Fetching article: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"    Error: {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Get title
    title = None
    title_tag = soup.find('h1', class_='c-article-magazine-title')
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        title_tag = soup.find('h1')
        if title_tag:
            title = title_tag.get_text(strip=True)
    
    # Get author(s)
    authors = []
    author_tags = soup.find_all('a', {'data-test': 'author-name'})
    for author in author_tags:
        authors.append(author.get_text(strip=True))
    
    # If no authors found via data-test, try other methods
    if not authors:
        author_list = soup.find('ul', class_='c-article-author-list')
        if author_list:
            for li in author_list.find_all('li'):
                author_name = li.get_text(strip=True)
                if author_name:
                    authors.append(author_name)
    
    # Get article body text
    body_text = ""
    
    # Try to find the main article body
    article_body = soup.find('div', class_='c-article-body')
    if article_body:
        # Get all paragraphs
        paragraphs = article_body.find_all('p')
        body_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    
    # If not found, try alternative selectors
    if not body_text:
        article_body = soup.find('article')
        if article_body:
            paragraphs = article_body.find_all('p')
            body_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    
    # Get publication date
    pub_date = None
    time_tag = soup.find('time')
    if time_tag:
        pub_date = time_tag.get('datetime') or time_tag.get_text(strip=True)
    
    if not title:
        print(f"    Warning: No title found")
        return None
    
    return {
        'url': url,
        'title': title,
        'authors': authors,
        'publication_date': pub_date,
        'full_text': body_text
    }


def main():
    print("=" * 60)
    print("Nature Career Column Scraper")
    print("=" * 60)
    
    # Step 1: Collect all article URLs from all pages
    print("\n[Phase 1] Collecting article URLs from all pages...")
    all_urls = []
    
    # There are 29 pages
    for page_num in range(1, 30):
        urls = get_article_urls_from_page(page_num)
        all_urls.extend(urls)
        time.sleep(1)  # Be polite to the server
    
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in all_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    print(f"\n[Phase 1 Complete] Found {len(unique_urls)} unique articles")
    
    # Save URLs to a file for reference
    urls_file = Path("article_urls.json")
    with open(urls_file, 'w', encoding='utf-8') as f:
        json.dump(unique_urls, f, indent=2)
    print(f"Saved URLs to {urls_file}")
    
    # Step 2: Fetch each article's content
    print("\n[Phase 2] Fetching article content...")
    articles = []
    
    for i, url in enumerate(unique_urls, 1):
        print(f"\n[{i}/{len(unique_urls)}]")
        article = get_article_content(url)
        if article:
            articles.append(article)
            print(f"    ✓ {article['title'][:60]}...")
        else:
            print(f"    ✗ Failed to fetch article")
        
        # Save progress every 10 articles
        if i % 10 == 0:
            temp_file = Path("articles_partial.json")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            print(f"    [Progress saved: {len(articles)} articles]")
        
        time.sleep(1.5)  # Be polite to the server
    
    # Step 3: Save final results
    print("\n[Phase 3] Saving results...")
    output_file = Path("nature_career_columns.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"COMPLETE!")
    print(f"{'=' * 60}")
    print(f"Total articles scraped: {len(articles)}")
    print(f"Output file: {output_file.absolute()}")
    
    # Also create a simpler text version
    txt_file = Path("nature_career_columns.txt")
    with open(txt_file, 'w', encoding='utf-8') as f:
        for article in articles:
            f.write("=" * 80 + "\n")
            f.write(f"TITLE: {article['title']}\n")
            f.write(f"URL: {article['url']}\n")
            if article.get('authors'):
                f.write(f"AUTHORS: {', '.join(article['authors'])}\n")
            if article.get('publication_date'):
                f.write(f"DATE: {article['publication_date']}\n")
            f.write("-" * 80 + "\n")
            f.write(article['full_text'] + "\n\n")
    
    print(f"Text version: {txt_file.absolute()}")


if __name__ == "__main__":
    main()
