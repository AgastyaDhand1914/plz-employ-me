def print_scraper_header(source: str, title: str) -> None:
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"[{source}] {title}")
    print(separator)


def print_scraper_section(source: str, section_title: str) -> None:
    print(f"\n--- [{source}] {section_title} ---")


def print_scraper_footer(source: str, summary: str) -> None:
    print(f"[{source}] {summary}")
    print("=" * 70)
    print()
