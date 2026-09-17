import json
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape


API_URL = "https://baw.nfz.gov.pl/api/documents/GetDocumentsNewGrid"

payload = {
    "AdditionalId": 0,
    "Asc": 1,
    "ColumnId": -1,
    "DevExtremeGridOptions": {
        "group": None,
        "requireTotalCount": True,
        "searchOperation": "contains",
        "searchValue": None,
        "skip": 0,
        "sort": None,
        "take": 100,
        "userData": {}
    },
    "hideAmendingActs": False,
    "InstitutionId": 4,
    "isBlocked": True,
    "pageNumber": 0,
    "PageNumber": 0,
    "pageSize": 100,
    "PageSize": 100,
    "SearchForType": 22,
    "searchInContentWithElasticSearch": False,
    "searchText": "",
    "SearchText": "",
    "SearchTextInPdf": False
}


def parse_date(value):
    if not value:
        return ""

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

    except Exception:
        return ""


# Pobranie danych z BAW
data = json.dumps(payload).encode("utf-8")

request = urllib.request.Request(
    API_URL,
    data=data,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    },
    method="POST"
)

with urllib.request.urlopen(request, timeout=60) as response:
    result = json.loads(response.read().decode("utf-8"))


documents = result.get("DevExtremeDocuments", {}).get("data", [])

# Sortowanie od najnowszych
documents.sort(
    key=lambda x: (
        x.get("PublishedDate") or "",
        x.get("Id") or 0
    ),
    reverse=True
)

# Maksymalnie 100 pozycji
documents = documents[:100]


# Generowanie RSS
items = []

for doc in documents:

    doc_id = doc.get("Id")
    number = doc.get("ActNumber", "")
    subject = doc.get("Subject", "")
    link = doc.get("LinkUrl", "")

    if not link:
        link = f"https://baw.nfz.gov.pl/NFZ/document/{doc_id}/Document"

    pub_date = parse_date(doc.get("PublishedDate") or doc.get("ActDate"))

    status = doc.get("LegalActStatusDescription", "")

    description = (
        f"<p><strong>{escape(number)}</strong></p>"
        f"<p>{escape(subject)}</p>"
        f"<p>Status: {escape(status)}</p>"
        f"<p><a href=\"{escape(link)}\">Otwórz dokument w BAW NFZ</a></p>"
    )

    item = f"""
    <item>
        <title>{escape(number)} – NFZ</title>
        <description><![CDATA[{description}]]></description>
        <link>{escape(link)}</link>
        <guid isPermaLink="false">NFZ-BAW-{doc_id}</guid>
        <pubDate>{pub_date}</pubDate>
    </item>
    """

    items.append(item)


now = datetime.now(timezone.utc).strftime(
    "%a, %d %b %Y %H:%M:%S GMT"
)

rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>NFZ – Baza Aktów Własnych</title>
        <link>https://baw.nfz.gov.pl/NFZ/tabBrowser/mainPage</link>
        <description>Nowe zarządzenia Prezesa Narodowego Funduszu Zdrowia z Bazy Aktów Własnych</description>
        <language>pl-PL</language>
        <lastBuildDate>{now}</lastBuildDate>
        {''.join(items)}
    </channel>
</rss>
"""


with open("nfz.xml", "w", encoding="utf-8") as f:
    f.write(rss)

print(f"Wygenerowano RSS: {len(documents)} dokumentów")
