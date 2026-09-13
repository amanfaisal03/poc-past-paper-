import re
from dataclasses import dataclass

from app.database import settings


@dataclass(frozen=True)
class ExtractedMaterial:
    content: str
    unit_names: list[str]
    lesson_names: list[str]
    lessons_by_unit: dict[str, list[str]]
    unit_contents: dict[str, str]


@dataclass(frozen=True)
class TocEntries:
    unit_names: list[str]
    lesson_names: list[str]
    lessons_by_unit: dict[str, list[str]]


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

    toc_entries = extract_toc_entries(content)
    if not toc_entries.unit_names:
        raise RuntimeError("No units beginning with 'الوحدة' were found")

    return ExtractedMaterial(
        content=content,
        unit_names=toc_entries.unit_names,
        lesson_names=toc_entries.lesson_names,
        lessons_by_unit=toc_entries.lessons_by_unit,
        unit_contents=extract_unit_contents(content, toc_entries.unit_names),
    )


def extract_toc_entries(text: str) -> TocEntries:
    """Return unique unit and lesson titles from table-of-contents headings."""
    units: list[str] = []
    lessons: list[str] = []
    lessons_by_unit: dict[str, list[str]] = {}
    current_unit: str | None = None
    for line in text.splitlines():
        line = re.sub(r"^#+\s*", "", line.strip())
        line = re.sub(r"^[*•\-]+\s*|\d+\s*[.)\-:]\s*", "", line).strip()
        line = line.strip("*`_ ")
        if not line or line.startswith("الفصل الدراسي"):
            continue
        has_page_number = bool(re.search(r"\s+\d{1,4}\s*$", line))
        title_match = re.match(
            r"^(الوحدة|unit|chapter|الدرس|الدّرس|درس|lesson)\b",
            line,
            re.IGNORECASE,
        )
        if title_match is None and not (current_unit and has_page_number):
            continue

        title = re.sub(r"\s+\d{1,4}\s*$", "", line).strip(" .:-")
        if not title:
            continue
        if re.match(r"^(?:icon|logo|photo|image|مراجعة الوحدة)\b", title, re.IGNORECASE):
            continue
        if title_match and title_match.group(1).casefold() in {
            "الدرس", "الدّرس", "درس", "lesson"
        } or title_match is None:
            if title not in lessons:
                lessons.append(title)
            if current_unit is not None:
                lessons_by_unit.setdefault(current_unit, [])
                if title not in lessons_by_unit[current_unit]:
                    lessons_by_unit[current_unit].append(title)
        elif title not in units:
            units.append(title)
            current_unit = title
    return TocEntries(
        unit_names=units,
        lesson_names=lessons,
        lessons_by_unit=lessons_by_unit,
    )


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
