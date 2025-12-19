import json, time, requests, os, random, urllib.parse, feedparser, pytumblr
from groq import Groq
from gnews import GNews
from requests.auth import HTTPBasicAuth
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- حل مشكلة Render (تثبيت المنفذ) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('', port), HealthCheckHandler).serve_forever()

# --- الإعدادات الأصلية الخاصة بك ---
CONFIG = {
    "GROQ_KEY": "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",
    "WP_USER": "Manhuw",
    "WP_APP_PASS": "lkA0 EVHS rGMI 6Vk6 PX1t tyYa",
    "WP_BASE_URL": "https://manhuw.com/wp-json/wp/v2/posts",
    "WP_IMPORT_URL": "https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345",
    "DSC_WEBHOOK": "https://discord.com/api/webhooks/1451099896387080355/G1WqUdvGFVjfJMH5aJnbt_PxOlkm2X-yM1mWwows7hWMwGz4DMIUcEff8GGEReYBCFPr",
    "MASTODON_TOKEN": "amr7lcgKxY3XGL_ZtWLLpASbPEmwm0SYLTr_ICT0QCA",
    "TUMBLR_KEYS": {
        "ck": "zantmn4dLmmHc3tJKrUpgSJpc9HG2KU1H07OQS4gBr29fn8tXG",
        "cs": "AJdDLCxUpFTJDRsSLOzsau7ZplUSmNJOPPDl1hqRycfd7XICb8",
        "tk": "cJQOHlnE5uhjTENcRzwPyuNSQZKafa9HVdq44Z0BMm2Ksp17l6",
        "ts": "M4uN8gV9FJYq6wTW9D4vujJX4mPnMzqsRFy9Te4yVCkbQZQHki"
    },
    "T_BLOG": "manhuw", "RSS": "https://manhuw.com/manhwa-reviews-2/feed/",
    "MEM_WP": "published_urls.txt", "MEM_SOC": "marketing_history.txt", "MEM_TUM": "posted_links.txt"
}

client = Groq(api_key=CONFIG["GROQ_KEY"])
tumblr = pytumblr.TumblrRestClient(CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"], CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"])

def check(f, i): return os.path.exists(f) and str(i) in open(f).read()
def mark(f, i): open(f, "a").write(str(i) + "\n")

# --- الدورة السريعة (بدون تأخيرات طويلة) ---
def start_mission():
    while True:
        print("🚀 Mission Started...")
        
        # 1. ووردبريس (13 مقال)
        gn = GNews(language='en', period='7d')
        tasks = [{'cat': 382, 'count': 7, 'q': 'anime leaks'}, {'cat': 381, 'count': 2, 'q': 'anime review'}, {'cat': 379, 'count': 2, 'q': 'manga'}, {'cat': 281, 'count': 2, 'q': 'manhwa'}]
        for t in tasks:
            news = gn.get_news(t['q'])
            c = 0
            for n in news:
                if c >= t['count'] or check(CONFIG["MEM_WP"], n['url']): continue
                prompt = f"Write 1500-word SEO article for: {n['title']}. Return ONLY JSON: post_title, post_content, yoast_focus_keyword."
                try:
                    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                    data = json.loads(res.choices[0].message.content)
                    data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(data.get('yoast_focus_keyword', n['title']))}?width=1280&height=720&seed={random.randint(1,999)}.jpg"
                    data['categories'] = [t['cat']]
                    # إرسال سريع
                    if requests.post(CONFIG["WP_IMPORT_URL"], json=data, timeout=30).status_code == 200:
                        mark(CONFIG["MEM_WP"], n['url']); c += 1; print(f"✅ WP: {n['title'][:30]}")
                except: pass
                time.sleep(5) # انتظار قصير جداً

        # 2. السوشيال ميديا (3 مقالات)
        try:
            posts = requests.get(f"{CONFIG['WP_BASE_URL']}?per_page=5", auth=HTTPBasicAuth(CONFIG["WP_USER"], CONFIG["WP_APP_PASS"])).json()
            s = 0
            for p in posts:
                if s >= 3 or check(CONFIG["MEM_SOC"], p['id']): continue
                teaser = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Short teaser for: {p['link']}"}]).choices[0].message.content
                requests.post(CONFIG["DSC_WEBHOOK"], json={"embeds": [{"title": p['title']['rendered'], "url": p['link'], "description": teaser[:300]}]})
                mark(CONFIG["MEM_SOC"], p['id']); s += 1; print(f"📢 Social: {p['id']}")
        except: pass

        # 3. تامبلر (3 مقالات)
        try:
            feed = feedparser.parse(CONFIG["RSS"])
            d = 0
            for e in feed.entries:
                if d >= 3 or check(CONFIG["MEM_TUM"], e.link): continue
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Tumblr post for: {e.link}"}], response_format={"type": "json_object"})
                js = json.loads(res.choices[0].message.content)
                tumblr.create_text(CONFIG["T_BLOG"], title=js['title'], body=js['body'], tags=js.get('tags', []))
                mark(CONFIG["MEM_TUM"], e.link); d += 1; print(f"🎨 Tumblr: {js['title'][:30]}")
        except: pass

        print("😴 Mini-sleep before next check...")
        time.sleep(3600) # فحص كل ساعة بدلاً من يوم كامل

if __name__ == "__main__":
    threading.Thread(target=run_health_check, daemon=True).start()
    start_mission()
