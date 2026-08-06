"""Channel-neutral billable product unit."""
from .converter import html_to_result
from .generator import build_llms_full_txt, build_llms_txt


def build_site_bundle(payload: dict, max_pages: int = 20, max_html_chars: int = 1_000_000) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    name = payload.get("site_name")
    summary = payload.get("site_summary")
    pages = payload.get("pages")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("site_name must be a non-empty string")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("site_summary must be a non-empty string")
    if not isinstance(pages, list) or not pages:
        raise ValueError("pages must be a non-empty array")
    if len(pages) > max_pages:
        raise ValueError(f"at most {max_pages} pages per paid unit")
    total_chars = 0
    normalized = []
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            raise ValueError(f"pages[{index}] must be an object")
        html = page.get("html")
        url = page.get("url")
        if not isinstance(html, str) or not html.strip():
            raise ValueError(f"pages[{index}].html must be a non-empty string")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError(f"pages[{index}].url must be an http(s) URL")
        total_chars += len(html)
        if total_chars > max_html_chars:
            raise ValueError(f"combined HTML exceeds {max_html_chars} characters")
        result = html_to_result(html, url)
        normalized.append({
            "title": result["title"] or url,
            "url": url,
            "description": result["meta_description"] or result["markdown"].split("\n", 1)[0][:160],
            "content": result["markdown"],
            "word_count": result["word_count"],
        })
    fixture = {"site": {"name": name.strip(), "summary": summary.strip()}, "sections": [{"title": "Pages", "pages": normalized}]}
    return {
        "unit": {"pages": len(normalized), "input_html_chars": total_chars, "output_words": sum(p["word_count"] for p in normalized)},
        "llms_txt": build_llms_txt(fixture),
        "llms_full_txt": build_llms_full_txt(fixture),
        "pages": normalized,
    }

