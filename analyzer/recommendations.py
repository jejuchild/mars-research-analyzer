"""Research recommendation engine.

Synthesizes all analysis results into:
1. Trend summary — what's hot, what's growing
2. Open problems — what's still unsolved
3. Research topic recommendations — what YOU should work on
"""

import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Mars-relevance check for gap contexts
_MARS_TERMS = {"mars", "martian", "crater", "rover", "hirise", "crism", "sharad",
               "mola", "perseverance", "curiosity", "jezero", "olympus", "valles",
               "gale", "atmosphere", "regolith", "dust storm", "subsurface ice"}


def _is_mars_relevant(text: str) -> bool:
    text_lower = text.lower()
    return any(t in text_lower for t in _MARS_TERMS)


def synthesize(analysis_results: dict) -> dict:
    """Generate actionable research recommendations from all analyses."""
    trends = analysis_results.get("trends", {})
    emerging = analysis_results.get("emerging_topics", [])
    keywords = analysis_results.get("keywords", {})
    crossfield = analysis_results.get("crossfield", {})
    gaps = analysis_results.get("gaps", {})
    venues = analysis_results.get("venues", {})
    summary = analysis_results.get("summary", {})

    return {
        "trend_summary": _summarize_trends(trends, emerging, summary),
        "open_problems": _extract_open_problems(gaps, crossfield),
        "recommendations": _generate_recommendations(
            emerging, crossfield, gaps, keywords, venues
        ),
    }


def _summarize_trends(trends: dict, emerging: list, summary: dict) -> list[dict]:
    """Summarize key research trends."""
    insights = []

    yearly = trends.get("yearly_papers", {})
    years = sorted(yearly.keys())
    if len(years) >= 2:
        growth = trends.get("growth_rates", {})
        total = sum(yearly.values())
        insights.append({
            "category": "Publication Volume",
            "insight": f"Total {total} Mars-relevant papers across {len(years)} years. "
                       f"Peak year: {max(yearly, key=yearly.get)} ({max(yearly.values())} papers).",
            "trend": "stable",
        })

    avg_cit = trends.get("yearly_avg_citations", {})
    if avg_cit:
        highest_cit_year = max(avg_cit, key=avg_cit.get)
        insights.append({
            "category": "Citation Impact",
            "insight": f"Highest avg citations: {highest_cit_year} ({avg_cit[highest_cit_year]}). "
                       f"Recent papers show where the field is heading; older papers show what the field validated.",
            "trend": "expected_decay",
        })

    if emerging:
        # Filter to Mars-relevant emerging topics
        mars_emerging = [e for e in emerging if _is_mars_relevant(e["term"])]
        if mars_emerging:
            top5 = [e["term"] for e in mars_emerging[:5]]
            insights.append({
                "category": "Emerging Mars Topics",
                "insight": f"Growing terms (2025-2026): {', '.join(top5)}. "
                           f"These represent accelerating research directions in Mars science.",
                "trend": "rising",
            })

    cf = trends.get("yearly_field_distribution", {})
    if cf:
        cs_trend = []
        for y in sorted(cf.keys()):
            cs_count = cf[y].get("computer_science", 0)
            total_y = sum(cf[y].values())
            if total_y > 0:
                cs_trend.append((y, round(cs_count / total_y * 100, 1)))

        if len(cs_trend) >= 2:
            first_pct = cs_trend[0][1]
            last_pct = cs_trend[-1][1]
            direction = "increasing" if last_pct > first_pct else "stable"
            insights.append({
                "category": "CS + Mars Integration",
                "insight": f"CS methods in Mars research: "
                           f"{first_pct}% ({cs_trend[0][0]}) → {last_pct}% ({cs_trend[-1][0]}). "
                           f"ML/DL adoption is {direction}, but still a small fraction — "
                           f"large room for CS contributions.",
                "trend": direction,
            })

    return insights


def _extract_open_problems(gaps: dict, crossfield: dict) -> list[dict]:
    """Extract and rank open research problems — Mars-relevant only."""
    problems = []

    # Skip generic / non-Mars themes
    skip_themes = {"limited time", "without need", "low earth", "earth orbit",
                   "high resolution", "large scale", "long term", "real time",
                   "present study", "recent years", "proposed method"}

    themes = gaps.get("gap_themes", [])
    for theme in themes[:20]:
        if theme["theme"] in skip_themes:
            continue
        # Check Mars relevance from example papers
        example_papers = theme.get("example_papers", [])
        examples_text = " ".join(example_papers)
        if not _is_mars_relevant(theme["theme"]) and not _is_mars_relevant(examples_text):
            continue

        problems.append({
            "problem": theme["theme"],
            "evidence": f"Mentioned across {theme['mention_count']} papers",
            "gap_types": theme.get("gap_types", []),
            "avg_citations": theme.get("avg_citations", 0),
            "source": "gap_analysis",
        })

    # From direct paper quotes — Mars-relevant only
    seen_titles = set()
    for gap_type in ["challenge", "knowledge_gap", "open_question"]:
        instances = gaps.get("gap_instances", {}).get(gap_type, [])
        for inst in instances[:12]:
            title = inst.get("paper_title", "")
            context = inst.get("context", "")
            if title in seen_titles:
                continue
            if not _is_mars_relevant(f"{title} {context}"):
                continue
            seen_titles.add(title)
            problems.append({
                "problem": context[:200],
                "evidence": f"{title} ({inst.get('year', '?')})",
                "gap_types": [gap_type],
                "avg_citations": inst.get("citations", 0),
                "source": "paper_quote",
            })

    problems.sort(key=lambda x: x["avg_citations"], reverse=True)
    return problems[:15]


def _generate_recommendations(
    emerging: list,
    crossfield: dict,
    gaps: dict,
    keywords: dict,
    venues: dict,
) -> list[dict]:
    """Generate specific, actionable research topic recommendations."""
    recommendations = []

    # Specific recommendations based on data patterns
    top_bigrams = {kw for kw, _ in keywords.get("bigrams", [])[:40]}

    # 1. CRISM + deep learning
    recommendations.append({
        "title": "Transformer-based CRISM hyperspectral mineral classification",
        "rationale": "CRISM mineral mapping is a core Mars remote sensing task, "
                     "but most work uses traditional methods or basic CNNs. "
                     "Vision Transformers and self-supervised pretraining on unlabeled "
                     "CRISM data could dramatically improve mineral identification accuracy, "
                     "especially for rare mineral phases.",
        "type": "CS + Planetary Science",
        "priority": "high",
        "target_venues": [
            "Journal of Geophysical Research Planets",
            "IEEE Transactions on Geoscience and Remote Sensing",
            "Remote Sensing of Environment",
        ],
    })

    # 2. SHARAD + ML
    recommendations.append({
        "title": "Automated subsurface ice mapping from SHARAD radar using deep learning",
        "rationale": "SHARAD radargram interpretation for subsurface ice detection "
                     "is currently manual and time-consuming. Deep learning (U-Net, "
                     "attention-based models) applied to radargram image analysis could "
                     "automate large-scale mapping of Mars subsurface water ice — "
                     "critical for habitability assessment and future human missions.",
        "type": "CS + Satellite + Planetary",
        "priority": "high",
        "target_venues": [
            "Journal of Geophysical Research Planets",
            "Icarus",
            "Geophysical Research Letters",
        ],
    })

    # 3. Dust storm prediction
    if "dust storm" in top_bigrams or "dust storms" in top_bigrams:
        recommendations.append({
            "title": "Data-driven prediction of Martian dust storms using time-series ML",
            "rationale": "Dust storms remain one of the least predictable phenomena on Mars. "
                         "Applying modern time-series models (Temporal Fusion Transformer, "
                         "Mamba) to MAVEN/MCS atmospheric data could enable forecasting. "
                         "This is both scientifically impactful and practically important "
                         "for future Mars missions.",
            "type": "CS + Planetary Science",
            "priority": "high",
            "target_venues": [
                "Journal of Geophysical Research Planets",
                "Geophysical Research Letters",
                "Nature Geoscience",
            ],
        })

    # 4. Crater detection with foundation models
    if any("crater" in kw for kw in top_bigrams):
        recommendations.append({
            "title": "Few-shot Mars crater segmentation with vision foundation models",
            "rationale": "Crater detection has been studied extensively with CNNs, "
                         "but vision foundation models (SAM 2, DINOv2) enable "
                         "few-shot segmentation with minimal labeled data. "
                         "Applying these to HiRISE imagery bridges cutting-edge CS "
                         "with planetary geomorphology. Low labeled data requirement "
                         "makes it highly practical.",
            "type": "CS + Satellite",
            "priority": "high",
            "target_venues": [
                "Icarus",
                "IEEE Transactions on Geoscience and Remote Sensing",
                "CVPR Workshop",
            ],
        })

    # 5. Rover autonomy
    recommendations.append({
        "title": "Sim-to-real transfer learning for Mars rover terrain navigation",
        "rationale": "Rover autonomous navigation requires real-time hazard assessment, "
                     "but labeled Mars terrain data is scarce. Training in simulation "
                     "(using HiRISE-derived 3D terrain) and transferring to rover cameras "
                     "via domain adaptation addresses the data gap. Combines robotics, "
                     "computer vision, and planetary surface science.",
        "type": "CS + Satellite + Planetary",
        "priority": "medium",
        "target_venues": [
            "Science Robotics",
            "Acta Astronautica",
            "IEEE Robotics and Automation Letters",
        ],
    })

    # 6. Cross-field gap opportunity
    triple_count = crossfield.get("triple_intersection_count", 0)
    total_cf = crossfield.get("multi_field_papers_count", 0)
    if triple_count > 0 and total_cf > 0:
        triple_pct = round(triple_count / total_cf * 100, 1)
        recommendations.append({
            "title": "Multimodal Mars data fusion (orbital + in-situ + ML)",
            "rationale": f"Only {triple_pct}% of cross-field papers span all three domains "
                         f"(planetary science + satellite + CS). Fusing multi-instrument data "
                         f"(CRISM spectra + HiRISE imagery + SHARAD radar) with multimodal "
                         f"deep learning is largely unexplored and could reveal subsurface-surface "
                         f"correlations invisible to single-instrument analysis.",
            "type": "Triple Intersection",
            "priority": "high",
            "target_venues": [
                "Journal of Geophysical Research Planets",
                "IEEE Transactions on Geoscience and Remote Sensing",
                "Nature Geoscience",
            ],
        })

    # 7. Martian atmosphere spectroscopy
    if "martian atmosphere" in top_bigrams:
        recommendations.append({
            "title": "ML-enhanced retrieval of trace gases from Mars atmospheric spectra",
            "rationale": "Retrieving trace gas abundances (methane, water vapor) from "
                         "orbital spectrometer data involves complex radiative transfer. "
                         "Neural network emulators can speed up retrievals by 1000x while "
                         "maintaining accuracy, enabling global-scale atmospheric mapping.",
            "type": "CS + Planetary Science",
            "priority": "medium",
            "target_venues": [
                "Journal of Geophysical Research Planets",
                "Icarus",
                "The Planetary Science Journal",
            ],
        })

    return recommendations
