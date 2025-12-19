import json, time, requests, os, random, urllib.parse, feedparser, pytumblr, urllib3
from groq import Groq
from gnews import GNews
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# إخفاء تحذيرات الشهادة الأمنية لتنظيف سجلات Render
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- سيرفر المنفذ لضمان استمرار الخدمة على Render ---
class Health(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Manhuw Bot Active")
def run_p(): 
    try: HTTPServer(('', int(os.environ.get("PORT", 8080))), Health).serve_forever()
    except: pass

# ==========================================
# 🔑 الإعدادات (باستخدام معلوماتك الصحيحة)
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
    "MEM_WP": "wp_history_v5.txt", 
    "MEM_SOC": "soc_history_v5.txt"
}

# --- تهيئة العملاء ---
client = Groq(api_key=CONFIG["GROQ_KEY"])
tumblr_cl = pytumblr.TumblrRestClient(CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"], CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"])

def check_m(f, v): return os.path.exists(f) and str(v) in open(f).read()
def save_m(f, v): open(f, "a").write(str(v) + "\n")

# ==========================================
# 📝 محرك ووردبريس (13 مقال + تصميم احترافي)
# ==========================================
def run_wp_mission():
    print("📡 Starting WP Engine (Cloudflare Pass Mode)...")
    tasks = [
        {'cat': 382, 'n': 7, 'q': 'anime leaks spoilers'}, 
        {'cat': 381, 'n': 2, 'q': 'anime review'}, 
        {'cat': 379, 'n': 2, 'q': 'manga news'}, 
        {'cat': 281, 'n': 2, 'q': 'manhwa popular'}
    ]
    
    for t in tasks:
        news = GNews(language='en', period='5d').get_news(t['q'])
        count = 0
        for n in news:
            if count >= t['n'] or check_m(CONFIG["MEM_WP"], n['url']): continue
            try:
                # البرومبت لإنشاء العناوين والمربع الأزرق
                prompt = f"""
                Write a 1500-word SEO article in English about: {n['title']}.
                - Use at least 3 subheadings (H2/H3).
                - End the article with this EXACT HTML block:
                <div style="background:#e0f7fa; border:2px solid #00bcd4; padding:25px; margin-top:30px; border-radius:15px; text-align:center;">
                    <h3 style="color:#00838f;">💬 Join the Discussion!</h3>
                    <p style="color:#006064;">We'd love to hear your thoughts on this! Drop a comment below.</p>
                </div>
                Return ONLY JSON: post_title, post_content, yoast_focus_keyword.
                """
                
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                data = json.loads(res.choices[0].message.content)
                data['categories'] = [t['cat']]
                
                # صورة مميزة
                topic = urllib.parse.quote(data.get('yoast_focus_keyword', n['title']))
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{topic}?width=1280&height=720&nologo=true&seed={random.randint(1,999)}.jpg"
                
                # إرسال مع User-Agent المخصص لـ Cloudflare
                headers = {"User-Agent": "Manhuw-Render-Bot"}
                r = requests.post(CONFIG["WP_ENDPOINT"], json=data, headers=headers, verify=False, timeout=60)
                
                if r.status_code == 200:
                    save_m(CONFIG["MEM_WP"], n['url']); count += 1; print(f"✅ Published: {data['post_title'][:30]}")
                    time.sleep(30)
                else:
                    print(f"⚠️ Failed: {r.status_code}. Check Cloudflare WAF.")
            except Exception as e: print(f"❌ WP Error: {e}"); time.sleep(5)

# ==========================================
# 📢 محرك السوشيال ميديا (Tumblr & Discord)
# ==========================================
def run_social_mission():
    print("🎨 Starting Social Media Syndication...")
    try:
        feed = feedparser.parse(CONFIG["RSS_FEED"])
        for e in feed.entries[:3]:
            if check_m(CONFIG["MEM_SOC"], e.link): continue
            
            # محتوى تامبلر عبر Groq
            t_res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Tumblr post for: {e.title}. Link: {e.link}. JSON: title, body"}], response_format={"type": "json_object"})
            t_data = json.loads(t_res.choices[0].message.content)
            
            tumblr_cl.create_text(CONFIG["T_BLOG"], title=t_data['title'], body=t_data['body'], tags=["anime", "manhua"])
            requests.post(CONFIG["DSC_WEBHOOK"], json={"content": f"🚀 New on Manhuw: **{e.title}**\n{e.link}"})
            
            save_m(CONFIG["MEM_SOC"], e.link); print(f"✅ Social Sync Done")
            time.sleep(10)
    except Exception as e: print(f"❌ Social Error: {e}")

# ==========================================
# 🚀 الحلقة الرئيسية
# ==========================================
if __name__ == "__main__":
    # تشغيل سيرفر المنفذ في الخلفية
    threading.Thread(target=run_p, daemon=True).start()
    
    while True:
        run_wp_mission()
        run_social_mission()
        print("😴 Cycle finished. Waiting 6 hours...")
        time.sleep(21600)
