"""Generate an image (e.g., cache/summary.png) containing:
Total number of countries
Top 5 countries by estimated GDP
Timestamp of last refresh
Save the generated image on disk at cache/summary.png
"""

from sqlmodel import Session, select
from .schema import Country
import os
from datetime import datetime


def generate_image(db: Session):
    """Generate a summary image from database refresh results."""
    countries = db.exec(select(Country)).all()
    sorted_countries = sorted(
        countries,
        key=lambda c: (getattr(c, "estimated_gdp", 0) or 0),
        reverse=True,
    )
    top5 = sorted_countries[:5]
    total = len(countries)

    # fallback if Pillow not installed
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return {
            "total": total,
            "top5": [getattr(c, "name", None) for c in top5],
        }

    # Layout configuration
    width = 800
    row_height = 40
    top_margin = 100
    bottom_margin = 100  # increased to give footer more breathing room
    height = top_margin + bottom_margin + row_height * (len(top5) + 3)

    img = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    try:
        header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        regular_font = ImageFont.truetype("DejaVuSans.ttf", 18)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        header_font = ImageFont.load_default()
        regular_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # HEADER section
    header_text = "🌍 Country GDP Summary"
    header_bg_color = "#f0f0f0"
    draw.rectangle([(0, 0), (width, 70)], fill=header_bg_color)
    text_width = draw.textlength(header_text, font=header_font)
    draw.text(
        ((width - text_width) / 2, 20), header_text, fill="black", font=header_font
    )

    # BODY section
    y = top_margin
    draw.text(
        (40, y), f"Total countries in DB: {total}", fill="black", font=regular_font
    )
    y += 40
    draw.text(
        (40, y), "Top 5 countries by estimated GDP:", fill="black", font=regular_font
    )
    y += 50

    # Column headers
    draw.text((60, y), "Country", fill="#333333", font=small_font)
    draw.text((width - 220, y), "Estimated GDP (USD)", fill="#333333", font=small_font)
    y += 40

    # DATA rows
    for idx, c in enumerate(top5, start=1):
        gdp = getattr(c, "estimated_gdp", None)
        if isinstance(gdp, (int, float)):
            gdp_str = f"${gdp:,.2f}"  # ✅ added dollar sign
        else:
            gdp_str = "N/A"

        country_name = getattr(c, "name", "N/A")

        # draw left: country, right: GDP value
        draw.text((60, y), f"{idx}. {country_name}", fill="black", font=regular_font)
        text_width = draw.textlength(gdp_str, font=regular_font)
        draw.text(
            (width - 60 - text_width, y), gdp_str, fill="black", font=regular_font
        )
        y += row_height

    # ✅ Add spacing before footer
    y += 40

    # FOOTER section
    last_refreshed_at = (
        getattr(countries[0], "last_refreshed_at", None)
        if countries
        else datetime.now().isoformat()
    )
    draw.text(
        (40, y),
        f"Last refreshed: {last_refreshed_at}",
        fill="#555555",
        font=small_font,
    )

    # Save the image
    os.makedirs("cache", exist_ok=True)
    output_path = "cache/summary.png"
    img.save(output_path)

    return {
        "total": total,
        "top5": [getattr(c, "name", None) for c in top5],
        "image_path": output_path,
    }
