"""HTML to clean Markdown conversion, inherited from the validated probe."""
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def html_to_result(html: str, source_url: str | None = None) -> dict:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta_description = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_description = meta_tag["content"].strip()
    links = sorted({a["href"] for a in soup.find_all("a", href=True) if a["href"].strip()})
    headings = [
        {"level": int(h.name[1]), "text": h.get_text(strip=True)}
        for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if h.get_text(strip=True)
    ]
    body = soup.body if soup.body else soup
    markdown = md(str(body), heading_style="ATX").strip()
    return {
        "source_url": source_url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "links": links,
        "word_count": len(markdown.split()),
        "markdown": markdown,
    }

