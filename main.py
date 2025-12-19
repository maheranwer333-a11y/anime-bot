import json, time, requests, os, random, urllib.parse, feedparser, pytumblr, urllib3
from groq import Groq
from gnews import GNews
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# إخفاء تحذيرات الشهادة الأمنية
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Health(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Multi-Key Bot Active")
def run_p(): 
    try: HTTPServer(('', int(os.environ.get("PORT", 8080))), Health).serve_forever()
    except: pass

# ==========================================
# 🔑 الإعدادات (نظام المفاتيح الثلاثة)
# ==========================================
CONFIG = {
    "GROQ_KEYS": [
        "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", # المفتاح 1
        "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", # المفتاح 2 (جديد)
        "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"  # المفتاح 3 (جديد)
    ],
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
    "MEM_WP": "wp_v6.txt", "MEM_SOC": "soc_v6.txt"
}

# وظيفة لاختيار مفتاح Groq عشوائي في كل طلب لتوزيع الضغط
def get_groq_client():
    key = random.choice(CONFIG["GROQ_KEYS"])
    return Groq(api_key=key)

tumblr_cl = pytumblr.TumblrRestClient(CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"], CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"])

def check_m(f, v): return os.path.exists(f) and str(v) in open(f).read()
def save_m(f, v): open(f, "a").write(str(v) + "\n")

# ==========================================
# 📝 محرك ووردبريس (توزيع المفاتيح + التنسيق)
# ==========================================
def run_wp_mission():
    print(f"📡 Launching with {len(CONFIG['GROQ_KEYS'])} keys...")
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
                client = get_groq_client() # اختيار مفتاح جديد
                prompt = f"""
                Write a 1500-word SEO article in English about: {n['title']}.
                - Use at least 3 subheadings.
                - End with the blue discussion box HTML.
                Return ONLY JSON: post_title, post_content, yoast_focus_keyword.
                """
                
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                data = json.loads(res.choices[0].message.content)
                data['categories'] = [t['cat']]
                
                # إضافة المربع الأزرق يدوياً للتأكد من وجوده
                data['post_content'] += '\n\n<div style="background:#e0f7fa; border:2px solid #00bcd4; padding:25px; margin-top:30px; border-radius:15px; text-align:center;"><h3 style="color:#00838f;">💬 Join the Discussion!</h3><p style="color:#006064;">What do you think? Drop a comment below!</p></div>'
                
                topic = urllib.parse.quote(data.get('yoast_focus_keyword', n['title']))
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{topic}?width=1280&height=720&nologo=true&seed={random.randint(1,999)}.jpg"
                
                # Cloudflare Pass
                headers = {"User-Agent": "Manhuw-Render-Bot"}
                r = requests.post(CONFIG["WP_ENDPOINT"], json=data, headers=headers, verify=False, timeout=60)
                
                if r.status_code == 200:
                    save_m(CONFIG["MEM_WP"], n['url']); count += 1; print(f"✅ Success: {data['post_title'][:30]}")
                    time.sleep(20)
                else: print(f"⚠️ Failed: {r.status_code}")
            except Exception as e: print(f"❌ Error: {e}"); time.sleep(5)

# ==========================================
# 📢 محرك السوشيال ميديا
# ==========================================
def run_social_mission():
    try:
        feed = feedparser.parse(CONFIG["RSS_FEED"])
        for e in feed.entries[:3]:
            if check_m(CONFIG["MEM_SOC"], e.link): continue
            client = get_groq_client()
            t_res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Tumblr post for: {e.title}. Link: {e.link}. JSON: title, body"}], response_format={"type": "json_object"})
            t_data = json.loads(t_res.choices[0].message.content)
            tumblr_cl.create_text(CONFIG["T_BLOG"], title=t_data['title'], body=t_data['body'])
            requests.post(CONFIG["DSC_WEBHOOK"], json={"content": f"🚀 New Update: {e.title}\n{e.link}"})
            save_m(CONFIG["MEM_SOC"], e.link); print(f"✅ Social Sync Done")
    except: pass

if __name__ == "__main__":
    threading.Thread(target=run_p, daemon=True).start()
    while True:
        run_wp_mission()
        run_social_mission()
        time.sleep(21600)
