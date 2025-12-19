import json, time, requests, os, random, urllib.parse, feedparser, pytumblr
from groq import Groq
from gnews import GNews
from requests.auth import HTTPBasicAuth
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# سيرفر المنفذ لـ Render
class Health(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Bot Active")
def run_p(): 
    try: HTTPServer(('', int(os.environ.get("PORT", 8080))), Health).serve_forever()
    except: pass

CONFIG = {
    "GROQ_KEY": "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",
    "WP_ENDPOINT": "https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345",
    "DSC_WEBHOOK": "https://discord.com/api/webhooks/1451099896387080355/G1WqUdvGFVjfJMH5aJnbt_PxOlkm2X-yM1mWwows7hWMwGz4DMIUcEff8GGEReYBCFPr",
    "TUMBLR_BLOG": "manhuw",
    "TUMBLR_KEYS": {"ck": "zantmn4dLmmHc3tJKrUpgSJpc9HG2KU1H07OQS4gBr29fn8tXG", "cs": "AJdDLCxUpFTJDRsSLOzsau7ZplUSmNJOPPDl1hqRycfd7XICb8", "tk": "cJQOHlnE5uhjTENcRzwPyuNSQZKafa9HVdq44Z0BMm2Ksp17l6", "ts": "M4uN8gV9FJYq6wTW9D4vujJX4mPnMzqsRFy9Te4yVCkbQZQHki"},
    "RSS": "https://manhuw.com/manhwa-reviews-2/feed/",
    "MEM_WP": "wp_final_v4.txt", "MEM_SOC": "soc_final_v4.txt"
}

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

client = Groq(api_key=CONFIG["GROQ_KEY"])
tumblr_cl = pytumblr.TumblrRestClient(CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"], CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"])

def check_m(f, v): return os.path.exists(f) and str(v) in open(f).read()
def save_m(f, v): open(f, "a").write(str(v) + "\n")

def run_mission():
    print("🚀 Starting Mission with Subheadings & Blue Call-to-Action...")
    tasks = [{'c': 382, 'n': 7, 'q': 'anime news'}, {'c': 381, 'n': 2, 'q': 'anime review'}, {'c': 379, 'n': 2, 'q': 'manga'}, {'c': 281, 'n': 2, 'q': 'manhwa'}]
    
    for t in tasks:
        news = GNews(language='en', period='5d').get_news(t['q'])
        count = 0
        for n in news:
            if count >= t['n'] or check_m(CONFIG["MEM_WP"], n['url']): continue
            try:
                # البرومبت المحدث لإضافة التنسيق المطلوب
                prompt = f"""
                Write a professional 1500-word SEO article about: {n['title']}.
                REQUIREMENTS:
                1. Include at least 3 subheadings (H2 or H3).
                2. At the very end, add this EXACT HTML code for the blue box:
                <div style="background:#e0f7fa; border:2px solid #00bcd4; padding:25px; margin-top:30px; border-radius:15px; text-align:center; font-family:sans-serif;">
                    <h3 style="color:#00838f; margin-top:0;">💬 We want to hear from you!</h3>
                    <p style="color:#006064; font-size:16px;">What do you think about this news? Share your thoughts and join the discussion in the comments below!</p>
                </div>
                Return ONLY JSON: post_title, post_content, yoast_focus_keyword.
                """
                
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                data = json.loads(res.choices[0].message.content)
                data['categories'] = [t['c']]
                topic = urllib.parse.quote(data.get('yoast_focus_keyword', n['title']))
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{topic}?width=1280&height=720&seed={random.randint(1,999)}.jpg"
                
                headers = {"User-Agent": random.choice(UA_LIST)}
                r = requests.post(CONFIG["WP_ENDPOINT"], json=data, headers=headers, verify=False, timeout=60)
                
                if r.status_code == 200:
                    save_m(CONFIG["MEM_WP"], n['url']); count += 1; print(f"✅ WP Success: {n['title'][:30]}")
                    time.sleep(40) # تقليل الانتظار قليلاً للتسريع مع الحفاظ على الأمان
                else:
                    print(f"⚠️ WP Refused ({r.status_code}).")
                    time.sleep(60)
            except Exception as e: print(f"❌ Error: {e}"); time.sleep(5)

    # قسم السوشيال ميديا
    try:
        feed = feedparser.parse(CONFIG["RSS"])
        for e in feed.entries[:3]:
            if check_m(CONFIG["MEM_SOC"], e.link): continue
            t_res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Tumblr post for: {e.title}. Link: {e.link}. JSON: title, body"}], response_format={"type": "json_object"})
            t_data = json.loads(t_res.choices[0].message.content)
            tumblr_cl.create_text(CONFIG["T_BLOG"], title=t_data['title'], body=t_data['body'])
            requests.post(CONFIG["DSC_WEBHOOK"], json={"content": f"📢 New Update: {e.title}\n{e.link}"})
            save_m(CONFIG["MEM_SOC"], e.link); print(f"✅ Social Success")
    except: pass

if __name__ == "__main__":
    threading.Thread(target=run_p, daemon=True).start()
    while True:
        run_mission()
        time.sleep(21600) # فحص كل 6 ساعات
