import json, time, requests, os, random, urllib.parse, feedparser, pytumblr
from groq import Groq
from gnews import GNews
from requests.auth import HTTPBasicAuth
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# --- سيرفر وهمي لإرضاء Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Manhuw Bot is Active")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('', port), SimpleHandler).serve_forever()

# --- إعداداتك الأصلية (WP, Discord, Tumblr) ---
CONFIG = {
    "GROQ_KEY": "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",
    "WP_USER": "Manhuw",
    "WP_APP_PASS": "lkA0 EVHS rGMI 6Vk6 PX1t tyYa",
    "WP_ENDPOINT_IMPORT": 'https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345',
    "WP_BASE_URL": "https://manhuw.com/wp-json/wp/v2/posts",
    "MASTODON_TOKEN": "amr7lcgKxY3XGL_ZtWLLpASbPEmwm0SYLTr_ICT0QCA",
    "DSC_WEBHOOK": "https://discord.com/api/webhooks/1451099896387080355/G1WqUdvGFVjfJMH5aJnbt_PxOlkm2X-yM1mWwows7hWMwGz4DMIUcEff8GGEReYBCFPr",
    "TUMBLR_BLOG": "manhuw",
    "TUMBLR_KEYS": {"ck": "zantmn4dLmmHc3tJKrUpgSJpc9HG2KU1H07OQS4gBr29fn8tXG", "cs": "AJdDLCxUpFTJDRsSLOzsau7ZplUSmNJOPPDl1hqRycfd7XICb8", "tk": "cJQOHlnE5uhjTENcRzwPyuNSQZKafa9HVdq44Z0BMm2Ksp17l6", "ts": "M4uN8gV9FJYq6wTW9D4vujJX4mPnMzqsRFy9Te4yVCkbQZQHki"},
    "RSS_FEED": "https://manhuw.com/manhwa-reviews-2/feed/",
    "MEM_WP": "published_urls.txt", "MEM_SOCIAL": "marketing_history.txt", "MEM_TUMBLR": "posted_links.txt"
}

client = Groq(api_key=CONFIG["GROQ_KEY"])
tumblr_client = pytumblr.TumblrRestClient(CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"], CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"])

def is_published(file, item):
    if not os.path.exists(file): return False
    with open(file, "r") as f: return str(item) in f.read().splitlines()

def mark_published(file, item):
    with open(file, "a") as f: f.write(str(item) + "\n")

# --- المهام الثلاث المدمجة ---
def start_cycle():
    while True:
        print("🚀 Starting Automated Tasks (WP, Social, Tumblr)...")
        # 1. إنتاج 13 مقالاً
        gn = GNews(language='en', period='7d')
        tasks = [{'cat': 382, 'count': 7, 'q': 'anime leaks'}, {'cat': 381, 'count': 2, 'q': 'anime review'}, {'cat': 379, 'count': 2, 'q': 'manga analysis'}, {'cat': 281, 'count': 2, 'q': 'manhwa'}]
        for t in tasks:
            news = gn.get_news(t['q'])
            c = 0
            for n in news:
                if c >= t['count'] or is_published(CONFIG["MEM_WP"], n['url']): continue
                prompt = f"Write a 1500-word SEO article about: {n['title']}. Use H2/H3. Return JSON with post_title, post_content, yoast_focus_keyword."
                try:
                    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                    data = json.loads(res.choices[0].message.content)
                    topic = urllib.parse.quote(data.get('yoast_focus_keyword', n['title']))
                    data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{topic}?width=1280&height=720&seed={random.randint(1,99)}.jpg"
                    data['categories'] = [t['cat']]
                    if requests.post(CONFIG["WP_ENDPOINT_IMPORT"], json=data).status_code == 200:
                        mark_published(CONFIG["MEM_WP"], n['url']); c += 1; print(f"✅ WP: {data['post_title']}")
                except: pass
                time.sleep(15)

        # 2. تسويق (Discord/Mastodon)
        try:
            posts = requests.get(f"{CONFIG['WP_BASE_URL']}?per_page=5", auth=HTTPBasicAuth(CONFIG['WP_USER'], CONFIG['WP_APP_PASS'])).json()
            shared = 0
            for p in posts:
                if shared >= 3 or is_published(CONFIG["MEM_SOCIAL"], p['id']): continue
                teaser = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"300-word teaser for: {p['link']}"}]).choices[0].message.content
                requests.post(CONFIG["DSC_WEBHOOK"], json={"embeds": [{"title": p['title']['rendered'], "url": p['link'], "description": teaser[:300]}]})
                mark_published(CONFIG["MEM_SOCIAL"], p['id']); shared += 1; print(f"📢 Social: {p['id']}")
        except: pass

        # 3. تامبلر
        try:
            feed = feedparser.parse(CONFIG["RSS_FEED"])
            done = 0
            for e in feed.entries:
                if done >= 3 or is_published(CONFIG["MEM_TUMBLR"], e.link): continue
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Tumblr post for: {e.link}"}], response_format={"type": "json_object"})
                d = json.loads(res.choices[0].message.content)
                tumblr_client.create_text(CONFIG["TUMBLR_BLOG"], title=d['title'], body=d['body'], tags=d.get('tags', []))
                mark_published(CONFIG["MEM_TUMBLR"], e.link); done += 1; print(f"🎨 Tumblr: {d['title']}")
        except: pass

        print("😴 Cycle Finished. Sleeping 24h...")
        time.sleep(86400)

if __name__ == "__main__":
    # تشغيل السيرفر الوهمي في خيط منفصل لتجنب إغلاق Render
    threading.Thread(target=run_dummy_server, daemon=True).start()
    start_cycle()
