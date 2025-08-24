"""Medical search utilities for data source-specific URL generation and formatting."""

import re
from collections.abc import Mapping

# Load configurable parameters (e.g., list limits) without creating cycles
try:
    from config.medical_search_config_loader import MedicalSearchConfigLoader  # type: ignore

    _cfg_loader = MedicalSearchConfigLoader()
    _search_cfg = _cfg_loader.load_config()
except Exception:  # pragma: no cover - fallback if config loader unavailable
    _cfg_loader = None
    _search_cfg = None


def _as_str(val: object | None) -> str:
    """Coerce possibly non-string values to string safely."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return str(val)


def generate_source_url(source: Mapping[str, object]) -> str:
    """Generate URL for a source using DOI only"""

    # PRIORITY 1: DOI - links to actual full article
    doi = _as_str(source.get("doi", "")).strip()
    if doi and doi.lower() not in ["", "no doi", "none"]:
        if doi.startswith("http"):
            return doi
        return f"https://doi.org/{doi}"

    # PRIORITY 2: Direct URL if provided
    url = _as_str(source.get("url", "")).strip()
    if url and url not in ["", "#", "#database_record"]:
        return url

    # PRIORITY 4: Source-type specific handling
    source_type = _as_str(source.get("source_type")).lower()

    if source_type == "clinical_guideline" or "trial" in source_type:
        # Clinical trials
        nct_id = _as_str(source.get("nct_id")).strip()
        if nct_id:
            return f"https://clinicaltrials.gov/study/{nct_id}"

    elif source_type == "drug_info":
        # FDA drug information
        ndc = _as_str(source.get("ndc")).strip()
        generic_name = _as_str(source.get("drug_name", source.get("generic_name", ""))).strip()

        if ndc:
            return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={ndc}"
        if generic_name:
            return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={generic_name.replace(' ', '+')}"
        return "https://dailymed.nlm.nih.gov/dailymed/"

    # Fallback
    return "#"


def format_source_for_display(source: Mapping[str, object]) -> dict[str, object]:
    """
    Format a source for user-friendly display with proper URLs and metadata.
    """
    formatted: dict[str, object] = dict(source)

    # Generate proper URL
    formatted["url"] = generate_source_url(source)

    # Add source type-specific formatting
    source_type = _as_str(source.get("source_type"))

    if source_type in ["condition_information", "symptom_literature"]:
        # PubMed articles
        authors_val = source.get("authors", [])
        authors_list = [str(a) for a in authors_val] if isinstance(authors_val, list) else []
        if authors_list:
            formatted["authors_display"] = ", ".join(authors_list[:3]) + (
                " et al." if len(authors_list) > 3 else ""
            )
        else:
            formatted["authors_display"] = "Authors not listed"

        # Journal with date
        journal = _as_str(source.get("journal"))
        pub_date = _as_str(source.get("publication_date", source.get("pubDate", "")))
        if journal and pub_date:
            formatted["citation"] = f"{journal} ({pub_date})"
        elif journal:
            formatted["citation"] = journal
        elif pub_date:
            formatted["citation"] = f"Published {pub_date}"
        else:
            formatted["citation"] = "Citation not available"

    elif source_type == "clinical_guideline" or "trial" in source_type:
        # Clinical trials
        nct_id = _as_str(source.get("nct_id"))
        status = _as_str(source.get("status"))
        phase = _as_str(source.get("phase"))

        if nct_id:
            formatted["identifier"] = f"NCT ID: {nct_id}"
        if status:
            formatted["status_display"] = f"Status: {status.title()}"
        if phase and phase.lower() != "n/a":
            formatted["phase_display"] = f"Phase: {phase}"

    elif source_type == "drug_info":
        # FDA drugs
        manufacturer = _as_str(source.get("manufacturer"))
        approval_date = _as_str(source.get("fda_approval", source.get("approval_date", "")))

        if manufacturer:
            formatted["manufacturer_display"] = f"Manufacturer: {manufacturer}"
        if approval_date:
            formatted["approval_display"] = f"FDA Approved: {approval_date}"

    return formatted


def generate_conversational_summary(sources: list[dict[str, object]], query: str) -> str:
    """
    Generate a concise, minimal list of sources without extra preface or headers.
    Includes clean DOI/PubMed links and short abstract snippets when available.
    """
    # Import logger here to avoid circular imports
    try:
        from core.infrastructure.healthcare_logger import get_healthcare_logger

        logger = get_healthcare_logger("conversational_summary")
        logger.info(
            f"DIAGNOSTIC: generate_conversational_summary called with {len(sources) if sources else 0} sources for query: '{query}'",
        )
    except Exception:
        logger = None

    if not sources:
        if logger:
            logger.info("DIAGNOSTIC: No sources provided, returning 'No literature found.'")
        return "No literature found."

    # Deduplicate by doi/pmid/url/title to avoid double-counting
    seen: set[str] = set()
    unique: list[dict[str, object]] = []
    for s in sources:
        key = (
            _as_str(s.get("doi") or s.get("pmid") or s.get("url") or s.get("title")).strip().lower()
        )
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(s)

    if logger:
        logger.info(f"DIAGNOSTIC: After deduplication, {len(unique)} unique sources")

    lines: list[str] = []

    # Determine display limit from config; fallback to 10
    display_limit = 10
    try:
        # Prefer a dedicated summary/display limit if present
        sp = getattr(_search_cfg, "search_parameters", None)
        # Some configs might include a general 'display_limit'
        maybe_display_limit = None
        if isinstance(sp, object):
            # If the dataclass has a dict for max_results, we can piggyback on a sensible default
            mr = getattr(sp, "max_results", {})
            if isinstance(mr, dict):
                # Use condition_info as a reasonable global default if no explicit key
                maybe_display_limit = (
                    mr.get("summary_display_limit")
                    or mr.get("display_limit")
                    or mr.get("condition_info")
                )
        if isinstance(maybe_display_limit, int) and maybe_display_limit > 0:
            display_limit = maybe_display_limit
    except Exception:
        display_limit = 10

    if logger:
        logger.info(f"DIAGNOSTIC: Using display_limit: {display_limit}")

    # Show top N items in order provided (already ranked upstream)
    for i, source in enumerate(unique[:display_limit], 1):
        formatted = format_source_for_display(source)
        title = _as_str(source.get("title") or "Untitled article").strip()
        url = _as_str(formatted.get("url"))
        citation = _as_str(formatted.get("citation", ""))
        pub_date = _as_str(source.get("publication_date", "")).strip()

        # Make title clickable if URL exists
        title_with_link = f"[{title}]({url})" if url else title

        header = f"{i}. {title_with_link}"
        if pub_date:
            header += f" ({pub_date})"
        if citation:
            header += f" — {citation}"
        lines.append(header)

        # Brief abstract if available
        abstract = _as_str(source.get("abstract", source.get("content", ""))).strip()
        if abstract:
            snippet = abstract if len(abstract) <= 500 else abstract[:500].rstrip() + "..."
            lines.append(f"   {snippet}")
        lines.append("")

    result = "\n".join(lines).rstrip()
    if logger:
        logger.info(
            f"DIAGNOSTIC: Generated summary length: {len(result)}, preview: {result[:200] if result else 'EMPTY'}",
        )

    return result


def _normalize_doi_url(doi_raw: str) -> str:
    """Return a clean https://doi.org/<id> URL from various DOI formats.

    Accepts values like:
    - "10.1000/xyz"
    - "doi: 10.1000/xyz"
    - "https://doi.org/10.1000/xyz"
    - mixed elocation strings containing a DOI
    """
    if not doi_raw:
        return ""
    s = doi_raw.strip()
    # If it's already a DOI URL, normalize and return
    if s.lower().startswith("https://doi.org/"):
        # Extract the DOI part after the domain to de-duplicate
        part = s[len("https://doi.org/") :].lstrip("/")
        return f"https://doi.org/{part}"

    # Extract a DOI pattern if present anywhere in the string
    m = re.search(r"(10\.\d{4,9}/\S+)", s, flags=re.IGNORECASE)
    if m:
        return f"https://doi.org/{m.group(1)}"

    # Remove common prefixes like 'doi:' and spaces
    s = re.sub(r"^\s*(doi\s*:?)\s*", "", s, flags=re.IGNORECASE)
    if s:
        return f"https://doi.org/{s}"
    return ""
