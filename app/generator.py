"""Generate llms.txt variants from a normalized website fixture."""
import re


def _clean(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"


def build_llms_txt(site: dict) -> str:
    lines = [f"# {site['site']['name']}", "", f"> {site['site']['summary']}", ""]
    for section in site.get("sections", []):
        lines += [f"## {section['title']}", ""]
        for page in section.get("pages", []):
            lines.append(f"- [{page['title']}]({page['url']}): {page['description']}")
        lines.append("")
    return _clean("\n".join(lines))


def build_llms_full_txt(site: dict) -> str:
    lines = [f"# {site['site']['name']}", "", f"> {site['site']['summary']}", ""]
    for section in site.get("sections", []):
        lines += [f"## {section['title']}", ""]
        for page in section.get("pages", []):
            lines += [f"### {page['title']}", "", f"Source: {page['url']}", "", page.get("content", "").strip(), ""]
    return _clean("\n".join(lines))

