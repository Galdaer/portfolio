"""Medical search utilities for data source-specific URL generation and formatting."""

from typing import Any, Dict, List


def generate_source_url(source: Dict[str, Any]) -> str:
    """
    Generate appropriate URLs for different medical data sources.

    Uses the database schema fields to create proper links:
    - PubMed: DOI links when available, fallback to PubMed
    - Clinical Trials: ClinicalTrials.gov study links
    - FDA Drugs: DailyMed or FDA database links
    """
    source_type = source.get("source_type", "").lower()

    if source_type in ["condition_information", "symptom_literature"] and source.get("source", "").startswith("PubMed"):
        # PubMed articles - prefer DOI links to actual journals
        doi = source.get("doi", "").strip()
        pmid = source.get("pmid", "").strip()

        if doi and doi.lower() != "no doi":
            # DOI link goes to actual journal
            return f"https://doi.org/{doi}"
        elif pmid:
            # Fallback to PubMed abstract page
            return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        else:
            return source.get("url", "#")

    elif source_type == "clinical_guideline" or "trial" in source_type:
        # Clinical trials
        nct_id = source.get("nct_id", "").strip()
        if nct_id:
            return f"https://clinicaltrials.gov/study/{nct_id}"
        else:
            return source.get("url", "#")

    elif source_type == "drug_info":
        # FDA drug information
        ndc = source.get("ndc", "").strip()
        generic_name = source.get("drug_name", source.get("generic_name", "")).strip()

        if ndc:
            # DailyMed for drug labels (more user-friendly than raw FDA database)
            return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={ndc}"
        elif generic_name:
            # DailyMed search by name
            return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={generic_name.replace(' ', '+')}"
        else:
            return source.get("url", "https://dailymed.nlm.nih.gov/dailymed/")

    else:
        # Fallback to source URL or database indicator
        return source.get("url", "#database_record")


def format_source_for_display(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a source for user-friendly display with proper URLs and metadata.
    """
    formatted = source.copy()

    # Generate proper URL
    formatted["url"] = generate_source_url(source)

    # Add source type-specific formatting
    source_type = source.get("source_type", "")

    if source_type in ["condition_information", "symptom_literature"]:
        # PubMed articles
        authors = source.get("authors", [])
        if authors and isinstance(authors, list):
            formatted["authors_display"] = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        else:
            formatted["authors_display"] = "Authors not listed"

        # Journal with date
        journal = source.get("journal", "")
        pub_date = source.get("publication_date", source.get("pubDate", ""))
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
        nct_id = source.get("nct_id", "")
        status = source.get("status", "")
        phase = source.get("phase", "")

        if nct_id:
            formatted["identifier"] = f"NCT ID: {nct_id}"
        if status:
            formatted["status_display"] = f"Status: {status.title()}"
        if phase and phase.lower() != "n/a":
            formatted["phase_display"] = f"Phase: {phase}"

    elif source_type == "drug_info":
        # FDA drugs
        manufacturer = source.get("manufacturer", "")
        approval_date = source.get("fda_approval", source.get("approval_date", ""))

        if manufacturer:
            formatted["manufacturer_display"] = f"Manufacturer: {manufacturer}"
        if approval_date:
            formatted["approval_display"] = f"FDA Approved: {approval_date}"

    return formatted


def generate_conversational_summary(sources: List[Dict[str, Any]], query: str) -> str:
    """
    Generate a conversational summary of search results.
    """
    if not sources:
        return f"I couldn't find any medical literature specifically about '{query}'. You might want to try rephrasing your search or using different medical terms."

    summary_parts = []
    summary_parts.append(f"I found {len(sources)} relevant medical sources about '{query}':\n")

    # Group by source type
    pubmed_sources = [s for s in sources if s.get("source_type") in ["condition_information", "symptom_literature"]]
    trial_sources = [s for s in sources if "trial" in s.get("source_type", "")]
    drug_sources = [s for s in sources if s.get("source_type") == "drug_info"]

    # PubMed literature
    if pubmed_sources:
        summary_parts.append(f"\n**📚 Medical Literature ({len(pubmed_sources)} articles):**")
        for i, source in enumerate(pubmed_sources[:5]):  # Top 5
            formatted = format_source_for_display(source)
            title = source.get("title", "Untitled article")
            url = formatted["url"]
            citation = formatted.get("citation", "")

            if url.startswith("https://doi.org/"):
                link_text = "📄 Read full article"
            else:
                link_text = "📄 View abstract"

            summary_parts.append(f"{i+1}. **{title}**")
            if citation:
                summary_parts.append(f"   *{citation}*")
            summary_parts.append(f"   [{link_text}]({url})")

            # Brief abstract if available
            abstract = source.get("abstract", source.get("content", ""))
            if abstract and len(abstract) > 100:
                summary_parts.append(f"   {abstract[:200]}...")
            summary_parts.append("")

    # Clinical trials
    if trial_sources:
        summary_parts.append(f"\n**🔬 Clinical Trials ({len(trial_sources)} studies):**")
        for i, source in enumerate(trial_sources[:3]):  # Top 3
            formatted = format_source_for_display(source)
            title = source.get("title", "Unnamed study")
            url = formatted["url"]

            summary_parts.append(f"{i+1}. **{title}**")
            if formatted.get("status_display"):
                summary_parts.append(f"   {formatted['status_display']}")
            if formatted.get("phase_display"):
                summary_parts.append(f"   {formatted['phase_display']}")
            summary_parts.append(f"   [🔬 View study details]({url})")
            summary_parts.append("")

    # FDA drug information
    if drug_sources:
        summary_parts.append(f"\n**💊 FDA Drug Information ({len(drug_sources)} drugs):**")
        for i, source in enumerate(drug_sources[:3]):  # Top 3
            formatted = format_source_for_display(source)
            drug_name = source.get("drug_name", source.get("name", "Unknown drug"))
            url = formatted["url"]

            summary_parts.append(f"{i+1}. **{drug_name}**")
            if formatted.get("manufacturer_display"):
                summary_parts.append(f"   {formatted['manufacturer_display']}")
            if formatted.get("approval_display"):
                summary_parts.append(f"   {formatted['approval_display']}")
            summary_parts.append(f"   [💊 View drug information]({url})")
            summary_parts.append("")

    # Medical disclaimer
    summary_parts.append("\n---")
    summary_parts.append("**⚠️ Medical Disclaimer:** This information is for educational purposes only and is not medical advice. Always consult with a qualified healthcare professional for medical concerns.")

    return "\n".join(summary_parts)
