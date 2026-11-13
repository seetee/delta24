"""Get a schedule picture from Skola24.

The bot only uses fetch_schedule(). To fetch another way (for example with a
headless browser), write a module with the same function and change the
import in bot.py.
"""

import json
import tempfile
import urllib.request
from datetime import datetime, timedelta
from functools import cache
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

HOST = "stenungsund.skola24.se"
UNIT = "Nösnäsgymnasiet"
API = "https://web.skola24.se/api/"
# Not a secret: the Skola24 viewer page sends this same value for everyone.
SCOPE = "8a22163c-8662-4535-9050-bc5e1923df48"


def _post(path, body):
    request = urllib.request.Request(
        API + path,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", "X-Scope": SCOPE, "X-Requested-With": "XMLHttpRequest"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        reply = json.load(response)
    if reply.get("error") or reply.get("validation") or reply.get("data") is None:
        raise LookupError(f"{path}: {reply.get('error') or reply.get('validation') or 'no data'}")
    return reply["data"]


@cache
def _font(size, bold):
    # DejaVu, because Pillow's built-in font has no å, ä, ö.
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)


def fetch_schedule(id: str, week: int | None, whole_week: bool) -> str:
    """Return the path to a PNG of the schedule for a class or teacher signature.

    week=None means the current week. whole_week=False gives today only.
    Raises an exception if Skola24 has no schedule for the id.
    """
    day = datetime.now(ZoneInfo("Europe/Stockholm")).date()
    if day.isoweekday() > 5:  # weekend: show the coming Monday
        day += timedelta(days=8 - day.isoweekday())
    # shortcut: a week number always means the current calendar year, upgrade if
    # people ask for January weeks in December.
    year, this_week, weekday = day.isocalendar()
    width, height = (1200, 800) if whole_week else (500, 800)

    units = _post(
        "services/skola24/get/timetable/viewer/units",
        {"getTimetableViewerUnitsRequest": {"hostName": HOST}},
    )["getTimetableViewerUnitsResponse"]["units"]
    unit = next(u["unitGuid"] for u in units if u["unitId"] == UNIT)
    school_year = _post(
        "get/active/school/years", {"hostName": HOST, "checkSchoolYearsFeatures": False}
    )["activeSchoolYears"][0]["guid"]

    data = _post(
        "render/timetable",
        {
            "renderKey": _post("get/timetable/render/key", None)["key"],
            "host": HOST,
            "unitGuid": unit,
            "schoolYear": school_year,
            "startDate": None,
            "endDate": None,
            "scheduleDay": 0 if whole_week else weekday,  # 0 = whole week, 1-5 = Mon-Fri
            "blackAndWhite": False,
            "width": width,
            "height": height,
            "selectionType": 4,  # 4 = what the "Ange ID" box sends
            "selection": _post("encrypt/signature", {"signature": id})["signature"],
            "showHeader": False,
            "periodText": "",
            "week": week or this_week,
            "year": year,
            "privateFreeTextMode": False,
            "privateSelectionMode": None,
            "customerKey": "",
        },
    )
    if not data.get("boxList"):
        raise LookupError(f"empty schedule for {id}")

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for box in data["boxList"]:
        draw.rectangle(
            (box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"]),
            fill=box["bColor"],
            outline=box["fColor"],
        )
    for line in data.get("lineList") or []:
        draw.line((line["p1x"], line["p1y"], line["p2x"], line["p2y"]), fill=line["color"])
    for text in data.get("textList") or []:
        draw.text((text["x"], text["y"]), text["text"], fill=text["fColor"], font=_font(text["fontsize"], bool(text.get("bold"))))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as file:
        image.save(file, "PNG")
    return file.name
