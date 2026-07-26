import os
import json
import httpx
import asyncio

API_BASE = "https://h5-api.aoneroom.com/wefeed-h5api-bff"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Referer": "https://moviebox.ph/",
    "Origin": "https://moviebox.ph",
    "X-Client-Info": '{"timezone":"Asia/Dhaka"}',
    "X-Request-Lang": "en",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

_bearer_token = None

async def get_bearer_token() -> str:
    global _bearer_token
    if _bearer_token:
        return _bearer_token
    async with httpx.AsyncClient(follow_redirects=True, timeout=25) as client:
        resp = await client.get(f"{API_BASE}/home?host=moviebox.ph", headers=DEFAULT_HEADERS)
        x_user = resp.headers.get("x-user")
        if x_user:
            _bearer_token = json.loads(x_user).get("token")
    return _bearer_token or ""

async def fetch_api(url: str, method: str = "GET", payload: dict = None) -> dict:
    token = await get_bearer_token()
    headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {token}" if token else ""}
    async with httpx.AsyncClient(follow_redirects=True, timeout=25) as client:
        if method == "POST":
            resp = await client.post(url, headers=headers, json=payload)
        else:
            resp = await client.get(url, headers=headers)
        return resp.json()

async def get_home_data():
    url = f"{API_BASE}/home?host=moviebox.ph"
    data = await fetch_api(url)
    sections = []
    for op in data.get("data", {}).get("operatingList", []) or []:
        op_type = op.get("type")
        title = op.get("title", "Featured")
        if op_type == "BANNER":
            items = [{
                "name": item.get("title") or (item.get("subject") or {}).get("title"),
                "poster_url": item.get("image", {}).get("url") or (item.get("subject") or {}).get("cover", {}).get("url"),
                "slug": item.get("detailPath") or (item.get("subject") or {}).get("detailPath"),
                "subject_id": (item.get("subject") or {}).get("subjectId"),
            } for item in op.get("banner", {}).get("items", []) if item.get("title")]
            sections.append({"section": "Banner", "count": len(items), "items": items})
        elif op_type in ["SUBJECTS_MOVIE", "SUBJECTS_TV", "SUBJECTS_ANIMATION"]:
            items = [{
                "name": sub.get("title"),
                "poster_url": sub.get("cover", {}).get("url"),
                "slug": sub.get("detailPath"),
                "subject_id": sub.get("subjectId"),
                "rating": sub.get("imdbRatingValue")
            } for sub in op.get("subjects", [])]
            sections.append({"section": title, "count": len(items), "items": items})
    return {"status": "success", "sections": sections}

async def get_category_data(tab_id: int, page: int = 1):
    url = f"{API_BASE}/subject/filter"
    payload = {"tabId": tab_id, "filter": {"sort": "RECOMMEND", "genre": "ALL"}, "page": page, "perPage": 24}
    data = await fetch_api(url, method="POST", payload=payload)
    raw_items = data.get("data", {}).get("items", [])
    return [{
        "name": sub.get("title"),
        "poster_url": sub.get("cover", {}).get("url"),
        "slug": sub.get("detailPath"),
        "subject_id": sub.get("subjectId"),
        "rating": sub.get("imdbRatingValue")
    } for sub in raw_items]

async def main():
    print("🔄 Fetching Latest MovieBox Data...")
    home = await get_home_data()
    movies = await get_category_data(tab_id=2)
    tv_series = await get_category_data(tab_id=5)

    # JSON ফাইল সেভ করা
    os.makedirs("data", exist_ok=True)
    with open("data/home.json", "w", encoding="utf-8") as f:
        json.dump(home, f, indent=2, ensure_ascii=False)
    with open("data/movies.json", "w", encoding="utf-8") as f:
        json.dump(movies, f, indent=2, ensure_ascii=False)
    with open("data/tv_series.json", "w", encoding="utf-8") as f:
        json.dump(tv_series, f, indent=2, ensure_ascii=False)

    print("📁 All endpoints updated successfully in /data folder!")

if __name__ == "__main__":
    asyncio.run(main())
