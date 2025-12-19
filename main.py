import json, time, requests, os, random, urllib.parse, feedparser, pytumblr, urllib3
from groq import Groq
from gnews import GNews
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# إخفاء تحذيرات SSL لضمان نظافة سجلات Render
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Health(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Manhuw Multi-Platform Active")
def run_p(): 
    try: HTTPServer(('', int(os.environ.get("PORT", 8080))), Health).serve_forever()
    except: pass

# ==========================================
# 🔑 الإعدادات (تم ضبط Mastodon وتوزيع المقالات)
# ==========================================
CONFIG = {
    "GROQ_KEYS": [
        "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",
        "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",
        "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"
    ],
    "WP_ENDPOINT": "https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345",
    "DSC_WEBHOOK": "https://discord.com/api/webhooks/1451099896387080355/G1WqUdvGFVjfJMH5aJnbt_PxOlkm2X-yM1mWwows7hWMwGz4DMIUcEff8GGEReYBCFPr",
    "MASTODON_TOKEN": "amr7lcgKxY3XGL_ZtWLLpASbPEmwm0SYLTr_ICT0QCA",
    "MASTODON_INSTANCE": "https://mastodon.social",
    "TUMBLR_BLOG": "manhuw",
    "TUMBLR_KEYS": {
        "ck": "zantmn4dLmmHc3tJKrUpgSJpc9HG2KU1H07OQS4gBr29fn8tXG",
        "cs": "AJdDLCxUpFTJDRsSLOzsau7ZplUSmNJOPPDl1hqRycfd7XICb8",
        "tk": "cJQOHlnE5uhjTENcRzwPyuNSQZKafa9HVdq44Z0BMm2Ksp17l6",
        "ts": "M4uN8gV9FJYq6wTW9D4vujJX4mPnMzqsRFy9Te4yVCkbQZQHki"
    },
    "RSS_FEED": "https://manhuw.com/manhwa-reviews-2/feed/",
    "MEM_WP": "wp_v_final_13.txt", "MEM_SOC": "soc_v_final_13.txt"
}

def get_groq(): return Groq(api_key=random.choice(CONFIG["GROQ_KEYS"]))
def is_done(f, v): return os.path.exists(f) and str(v) in open(f).read()
def set_done(f, v): open(f, "a").write(str(v) + "\n")

# ==========================================
# 📝 محرك ووردبريس (توزيع 13 مقال بدقة)
# ==========================================
def run_wp():
    print("🛰️ WP Engine Starting: Preparing 13 Articles...")
    # التوزيع: 7 تسريبات (382)، 2 مقارنات (381)، 2 مانجا (379)، 2 مانهوا (281)
    tasks = [
        {'id': 382, 'n': 7, 'q': 'anime manga leaks spoilers news'},   
        {'id': 381, 'n': 2, 'q': 'trending anime series review comparison'}, 
        {'id': 379, 'n': 2, 'q': 'manga chapter review analysis'}, 
        {'id': 281, 'n': 2, 'q': 'popular manhwa webtoon review'}  
    ]
    
    for t in tasks:
        news = GNews(language='en', period='5d').get_news(t['q'])
        count = 0
        for n in news:
            if count >= t['n'] or is_done(CONFIG["MEM_WP"], n['url']): continue
            try:
                client = get_groq()
                prompt = f"Write a 1500-word professional SEO article about: {n['title']}. Structure with H2/H3 subheadings. Return ONLY JSON: post_title, post_content, yoast_focus_keyword."
                
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                data = json.loads(res.choices[0].message.content)
                data['categories'] = [t['id']]
                
                # المربع الأزرق السماوي التفاعلي
                data['post_content'] += f'\n\n<div style="background:#e0f7fa; border:2px solid #00bcd4; padding:25px; margin-top:30px; border-radius:15px; text-align:center;"><h3 style="color:#00838f;">💬 Join the Discussion!</h3><p style="color:#006064;">Share your thoughts on {n["title"]} in the comments below!</p></div>'
                
                # توليد الصورة المميزة
                img_q = urllib.parse.quote(f"{data.get('yoast_focus_keyword', n['title'])} anime")
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{img_q}?width=1280&height=720&nologo=true&seed={random.randint(1,999)}.jpg"

                # النشر (مع تجاوز حماية Cloudflare)
                headers = {
                    "User-Agent": "Manhuw-Render-Bot",
                    "Content-Type": "application/json"
                }
                r = requests.post(CONFIG["WP_ENDPOINT"], json=data, headers=headers, verify=False, timeout=60)
                
                if r.status_code == 200:
                    set_done(CONFIG["MEM_WP"], n['url']); count += 1; print(f"✅ Published Category {t['id']}")
                else:
                    print(f"⚠️ WP Error {r.status_code} for ID {t['id']}")
                time.sleep(30) 
            except Exception as e:
                print(f"❌ WP Processing Error: {e}")

# ==========================================
# 📢 محرك السوشيال (Tumblr + Discord + Mastodon)
# ==========================================
def run_social():
    print("🌍 Social Media Engine Syncing...")
    try:
        feed = feedparser.parse(CONFIG["RSS_FEED"])
        tumblr_cl = pytumblr.TumblrRestClient(CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"], CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"])
        
        for e in feed.entries[:3]:
            if is_done(CONFIG["MEM_SOC"], e.link): continue
            
            client = get_groq()
            soc_res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Create a viral short post for: {e.title}. Link: {e.link}. JSON: title, body"}], response_format={"type": "json_object"})
            soc_data = json.loads(soc_res.choices[0].message.content)
            
            # 1. Tumblr
            tumblr_cl.create_text(CONFIG["TUMBLR_BLOG"], title=soc_data['title'], body=soc_data['body'], tags=["anime", "manhwa"])
            # 2. Discord
            requests.post(CONFIG["DSC_WEBHOOK"], json={"content": f"🔥 **New Update**: {e.title}\n{e.link}"})
            # 3. Mastodon
            mast_headers = {"Authorization": f"Bearer {CONFIG['MASTODON_TOKEN']}"}
            mast_data = {"status": f"🚀 {e.title}\n\nRead more: {e.link} #anime #manga"}
            requests.post(f"{CONFIG['MASTODON_INSTANCE']}/api/v1/statuses", headers=mast_headers, data=mast_data)
            
            set_done(CONFIG["MEM_SOC"], e.link); print("✅ Social Hub Synced")
            time.sleep(15)
    except Exception as ex:
        print(f"❌ Social Sync Error: {ex}")

if __name__ == "__main__":
    threading.Thread(target=run_p, daemon=True).start()
    while True:
        run_wp()
        run_social()
        print("😴 Cycle complete. Sleeping 6 hours...")
        time.sleep(21600)
