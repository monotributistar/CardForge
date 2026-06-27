"""vCard builder — generates vCard text from owner config."""


def build_vcard(owner: dict) -> str:
    """Build a vCard 3.0 string from an owner dict.

    Args:
        owner: Dict with name, title, phone, email, website, github, linkedin.

    Returns:
        vCard formatted string.
    """
    lines = ["BEGIN:VCARD", "VERSION:3.0"]

    if owner.get("name"):
        lines.append(f"FN:{owner['name']}")
    if owner.get("title"):
        lines.append(f"TITLE:{owner['title']}")
    if owner.get("phone"):
        lines.append(f"TEL:{owner['phone']}")
    if owner.get("email"):
        lines.append(f"EMAIL:{owner['email']}")
    if owner.get("website"):
        lines.append(f"URL:{owner['website']}")
    if owner.get("github"):
        lines.append(f"NOTE:GitHub: {owner['github']}")
    if owner.get("linkedin"):
        lines.append(f"NOTE:LinkedIn: {owner['linkedin']}")

    lines.append("END:VCARD")
    return "\n".join(lines)
