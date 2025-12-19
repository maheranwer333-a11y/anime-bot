import json, time, requests, os, random, urllib.parse, feedparser, pytumblr
from groq import Groq
from gnews import GNews
from requests.auth import HTTPBasicAuth
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- جزء ريندر (تثبيت المنفذ لضمان عدم التوقف) ---
class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Active")
def run_port(): 
    try: HTTPServer(('', int(os.environ.get("PORT", 8080))), HealthCheck).serve_forever()
    except: pass

# ==========================================
# 🔑 الإعدادات (باستخدام مفتاح GROQ الموحد)
# ==========================================
CONFIG = {
    "GROQ_KEY": "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",
    "WP_ENDPOINT": "https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345",
    "DSC_WEBHOOK": "https://discord.com/api/webhooks/1451099896387080355/G1WqUdvGFVjfJMH5aJnbt_PxOlkm2X-yM1mWwows7hWMwGz4DMIUcEff8GGEReYBCFPr",
    "TUMBLR_BLOG": "manhuw",
    "TUMBLR_KEYS": {
        "ck": "zantmn4dLmmHc3tJKrUpgSJpc9HG2KU1H07OQS4gBr29fn8tXG",
        "cs": "AJdDLCxUpFTJDRsSLOzsau7ZplUSmNJOPPDl1hqRycfd7XICb8",
        "tk": "cJQOHlnE5uhjTENcRzwPyuNSQZKafa9HVdq44Z0BMm2Ksp17l6",
        "ts": "M4uN8gV9FJYq6wTW9D4vujJX4mPnMzqsRFy9Te4yVCkbQZQHki"
    },
    "RSS_FEED": "https://manhuw.com/manhwa-reviews-2/feed/",
    "MEM_WP": "wp_history.txt", "MEM_TUM": "tum_history.txt"
}

client = Groq(api_key=CONFIG["GROQ_KEY"])
tumblr_cl = pytumblr.TumblrRestClient(CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"], CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"])

def check_mem(file, val): return os.path.exists(file) and str(val) in open(file).read()
def save_mem(file, val): open(file, "a").write(str(val) + "\n")

# ==========================================
# 📝 أولاً: محرك ووردبريس (13 مقال عبر Groq)
# ==========================================
def run_wp():
    print("🌟 Starting WP Engine (Groq)...")
    tasks = [
        {'cat': 382, 'count': 7, 'q': 'anime leaks'}, 
        {'cat': 381, 'count': 2, 'q': 'anime review'}, 
        {'cat': 379, 'count': 2, 'q': 'manga analysis'}, 
        {'cat': 281, 'count': 2, 'q': 'manhwa'}
    ]
    for t in tasks:
        news = GNews(language='en', period='7d').get_news(t['q'])
        c = 0
        for n in news:
            if c >= t['count'] or check_mem(CONFIG["MEM_WP"], n['url']): continue
            prompt = f"Write a 1500-word SEO article about: {n['title']}. Return JSON: post_title, post_content, yoast_focus_keyword."
            try:
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                data = json.loads(res.choices[0].message.content)
                data['categories'] = [t['cat']]
                # صورة ذكية
                topic = urllib.parse.quote(data.get('yoast_focus_keyword', n['title']))
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{topic}?width=1280&height=720&nologo=true&seed={random.randint(1,99)}.jpg"
                
                if requests.post(CONFIG["WP_ENDPOINT"], json=data, verify=False, timeout=60).status_code == 200:
                    save_mem(CONFIG["MEM_WP"], n['url']); c += 1; print(f"✅ WP: {n['title'][:30]}")
            except: pass
            time.sleep(10)

# ==========================================
# 📢 ثانياً: محرك السوشيال وتامبلر (عبر Groq)
# ==========================================
def run_social():
    print("🎨 Starting Social Engine (Groq)...")
    try:
        feed = feedparser.parse(CONFIG["RSS_FEED"])
        for e in feed.entries[:3]: # نشر آخر 3 مقالات من الـ RSS
            if check_mem(CONFIG["MEM_TUM"], e.link): continue
            
            # توليد محتوى تامبلر باستخدام Groq
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "user", "content": f"Create a viral Tumblr post for: {e.title}. Link: {e.link}. Return JSON: title, body."}],
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            
            # النشر الفعلي
            tumblr_cl.create_text(CONFIG["TUMBLR_BLOG"], title=data['title'], body=data['body'], tags=["anime", "manhwa"])
            requests.post(CONFIG["DSC_WEBHOOK"], json={"content": f"🚀 New Post: {e.title}\n{e.link}"})
            
            save_mem(CONFIG["MEM_TUM"], e.link); print(f"✅ Social: {e.title[:30]}")
            time.sleep(15)
    except Exception as ex: print(f"❌ Social Error: {ex}")

# ==========================================
# 🚀 الحلقة اللانهائية
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_port, daemon=True).start()
    while True:
        run_wp()
        run_social()
        print("😴 Cycle finished. Waiting 6 hours...")
        time.sleep(21600)
