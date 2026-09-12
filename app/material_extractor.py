import re
from dataclasses import dataclass

from app.database import settings


@dataclass(frozen=True)
class ExtractedMaterial:
    content: str
    unit_names: list[str]
    unit_contents: dict[str, str]


def extract_material(pdf_bytes: bytes) -> ExtractedMaterial:
    if not settings.llama_cloud_api_key:
        raise RuntimeError("LLAMA_CLOUD_API_KEY is not configured")

    from llama_cloud import LlamaCloud

    client = LlamaCloud(api_key=settings.llama_cloud_api_key)
    try:
        result = client.parsing.parse(
            tier=settings.llama_parse_tier,
            version="latest",
            upload_file=("material.pdf", pdf_bytes, "application/pdf"),
            page_ranges={"max_pages": settings.material_toc_max_pages},
            expand=["markdown_full"],
        )
    finally:
        client.close()

    content = result.markdown_full or result.text_full or ""
    if not content:
        raise RuntimeError("Llama Cloud returned no text for the material")

    unit_names = extract_toc_entries(content)
    if not unit_names:
        raise RuntimeError("No units beginning with 'الوحدة' were found")

    return ExtractedMaterial(
        content=content,
        unit_names=unit_names,
        unit_contents=extract_unit_contents(content, unit_names),
    )


def extract_toc_entries(text: str) -> list[str]:
    """Return unique Arabic unit titles from TOC headings."""
    units: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"^#+\s*", "", line.strip())
        if not line.startswith("الوحدة"):
            continue

        title = re.sub(r"\s+\d{1,4}\s*$", "", line).strip(" .:-")
        if title and title not in units:
            units.append(title)
    return units


def extract_unit_contents(text: str, unit_names: list[str]) -> dict[str, str]:
    """Split parsed text into sections beginning at each unit title."""
    positions = [
        (text.find(name), name)
        for name in unit_names
        if text.find(name) >= 0
    ]
    positions.sort()

    contents: dict[str, str] = {}
    for index, (start, name) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(text)
        contents[name] = text[start:end].strip()
    return contents
