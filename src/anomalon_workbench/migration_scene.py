"""Escaped presentation only: no access to hidden ownership or selection logic."""

from html import escape
from pathlib import Path


def stylesheet() -> str:
    """The shared Anomalon stylesheet (an exact copy of anomalon.com/ds/v1) followed by Owed's Streamlit layer."""
    assets = Path(__file__).parent / "assets"
    return "\n".join((assets / name).read_text(encoding="utf-8") for name in ("anomalon.css", "owed.css"))


def scene_html(
    sources: list[dict[str, str]],
    destinations: list[dict[str, str]],
    links: list[dict[str, str]],
    *,
    title: str,
    caption: str,
) -> str:
    source_cards = "".join(
        '<article class="an-card"><span class="an-card__name">'
        + escape(s["name"])
        + '</span><span class="an-card__amount">'
        + escape(s["balance"])
        + '</span><span class="an-card__meta">'
        + escape(s["id"])
        + " · Fictional customer</span></article>"
        for s in sources
    )
    destination_cards = ""
    for d in destinations:
        known = d["owner"] != "Owner not established"
        previous = d.get("previous", "")
        destination_cards += (
            '<article class="an-card an-card--dest'
            + (" an-card--known" if known else "")
            + '">'
            + '<span class="an-card__name">'
            + escape(d["id"])
            + "</span>"
            + '<span class="an-card__owner">'
            + escape(d["owner"])
            + "</span>"
            + '<span class="an-card__amount">'
            + (
                '<small class="an-balance-label">'
                + escape(d.get("balance_label", ""))
                + "</small> "
                if d.get("balance_label")
                else ""
            )
            + escape(d["balance"])
            + "</span>"
            + (
                '<span class="an-card__previous">Was ' + escape(previous) + "</span>"
                if previous
                else ""
            )
            + "</article>"
        )
    paths, text_links, descriptions = [], [], []
    source_index = {s["id"]: i for i, s in enumerate(sources)}
    destination_index = {d["id"]: i for i, d in enumerate(destinations)}
    source_names = {s["id"]: s["name"] for s in sources}
    for link in links:
        if link["source"] not in source_index or link["destination"] not in destination_index:
            continue
        start, end = (
            source_index[link["source"]] * 96 + 44,
            destination_index[link["destination"]] * 96 + 44,
        )
        verified = link["kind"] == "verified"
        descriptions.append(
            ("Verified: " if verified else "Proposed: ")
            + source_names[link["source"]]
            + " to "
            + link["destination"]
        )
        paths.append(
            '<path class="an-conn__line'
            + (" an-conn__line--verified" if verified else "")
            + f'" d="M0 {start} C70 {start} 90 {end} 160 {end}"/>'
        )
        text_links.append(
            "<li>"
            + ("Verified: " if verified else "Proposed: ")
            + escape(source_names[link["source"]])
            + " → "
            + escape(link["destination"])
            + "</li>"
        )
    return (
        '<section aria-label="'
        + escape(title, quote=True)
        + '">'
        + '<div class="an-scene"><div><div class="an-scene__head">Current system · customers</div>'
        + source_cards
        + "</div>"
        + f'<svg class="an-conn" style="height:{len(sources) * 96}px" '
        + f'viewBox="0 0 160 {len(sources) * 96}" preserveAspectRatio="none" '
        + 'role="img" aria-label="'
        + escape(title + " connections: " + "; ".join(descriptions), quote=True)
        + '">'
        + "".join(paths)
        + '</svg><div><div class="an-scene__head">New system · accounts</div>'
        + destination_cards
        + '</div></div><ul class="an-rel" aria-label="Connections in text">'
        + "".join(text_links)
        + '</ul><p class="an-note">'
        + escape(caption)
        + "</p></section>"
    )


def alternatives_html(first: list[dict[str, str]], second: list[dict[str, str]]) -> str:
    other = {r["source"]: r["destination"] for r in second}
    different = {r["source"] for r in first if other.get(r["source"]) != r["destination"]}
    panels = []
    for title, rows in (("Possible assignment A", first), ("Possible assignment B", second)):
        content = "".join(
            '<div class="an-possible__row'
            + (" an-possible__row--different" if r["source"] in different else "")
            + '"><span>'
            + escape(r["name"])
            + " · "
            + escape(r["balance"])
            + '</span><span class="an-possible__id">'
            + escape(r["destination"])
            + "</span></div>"
            for r in rows
        )
        panels.append(
            '<section class="an-possible__panel"><div class="an-possible__title">'
            + title
            + "</div>"
            + content
            + "</section>"
        )
    return '<div class="an-possible">' + "".join(panels) + "</div>"
