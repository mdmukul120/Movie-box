import os
import json
import httpx
import asyncio

# API সিক্রেট বা ইউআরএল গিটহাব এনভায়রনমেন্ট সিক্রেট থেকে রিড করবে
API_BASE = os.environ.get("MOVIEBOX_API_BASE", "https://h5-api.aoneroom.com/wefeed-h5api-bff")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0 Safari/537.36",
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

async def get_all_by_tab(tab_id: int, total_pages: int = 3):
    """মুভি, টিভি শো বা এনিমেশনের সকল পেজের ডাটা কালেকশন"""
    all_items = []
    for page in range(1, total_pages + 1):
        url = f"{API_BASE}/subject/filter"
        payload = {
            "tabId": tab_id, 
            "filter": {"sort": "RECOMMEND", "genre": "ALL", "country": "ALL", "language": "ALL"}, 
            "page": page, 
            "perPage": 30
        }
        data = await fetch_api(url, method="POST", payload=payload)
        raw_items = data.get("data", {}).get("items", [])
        
        for sub in raw_items:
            all_items.append({
                "title": sub.get("title"),
                "subject_id": sub.get("subjectId"),
                "slug": sub.get("detailPath"),
                "poster": sub.get("cover", {}).get("url"),
                "rating": sub.get("imdbRatingValue"),
                "corner_tag": sub.get("corner"),
                "year": sub.get("releaseDate", "")[:4] if sub.get("releaseDate") else None,
                # প্লেয়ার লিংক রিট্রাইভ করার জন্য স্ট্রাকচার তৈরি করা
                "player_api_endpoint": f"/api/stream/{sub.get('subjectId')}?detail_path={sub.get('detailPath')}"
            })
    return all_items

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

async def main():
    print("🔄 Category-wise Data Collection Processing...")
    
    # ১. হোমপেজ ফিচার্ড ডাটা
    home = await get_home_data()
    
    # ২. বিভিন্ন ক্যাটাগরির ডাটা (Tab 2=Movies, Tab 5=TV Series, Tab 8=Anime)
    movies = await get_all_by_tab(tab_id=2, total_pages=3)
    tv_series = await get_all_by_tab(tab_id=5, total_pages=3)
    anime = await get_all_by_tab(tab_id=8, total_pages=3)

    # ক্যাটাগরি ফোল্ডারে ফাইল আলাদা করে সেভ করা
    os.makedirs("data/categories", exist_ok=True)
    
    with open("data/home.json", "w", encoding="utf-8") as f:
        json.dump(home, f, indent=2, ensure_ascii=False)
        
    with open("data/categories/movies.json", "w", encoding="utf-8") as f:
        json.dump(movies, f, indent=2, ensure_ascii=False)
        
    with open("data/categories/tv_series.json", "w", encoding="utf-8") as f:
        json.dump(tv_series, f, indent=2, ensure_ascii=False)
        
    with open("data/categories/anime.json", "w", encoding="utf-8") as f:
        json.dump(anime, f, indent=2, ensure_ascii=False)

    print("📁 All categories (Movies, Series, Anime) saved into /data/categories!")

if __name__ == "__main__":
    asyncio.run(main())
