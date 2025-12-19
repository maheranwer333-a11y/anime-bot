import json
import time
import requests
import os
import random
import urllib.parse
import feedparser
import pytumblr
from groq import Groq
from gnews import GNews
from requests.auth import HTTPBasicAuth

# ==========================================
# 🔑 الإعدادات والمفاتيح (كلها تعمل عبر Groq)
# ==========================================
CONFIG = {
    "GROQ_KEY": "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",
    "WP_USER": "Manhuw",
    "WP_APP_PASS": "lkA0 EVHS rGMI 6Vk6 PX1t tyYa",
    "WP_ENDPOINT_IMPORT": 'https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345',
    "WP_BASE_URL": "https://manhuw.com/wp-json/wp/v2/posts",
    "MASTODON_TOKEN": "amr7lcgKxY3XGL_ZtWLLpASbPEmwm0SYLTr_ICT0QCA",
    "DSC_WEBHOOK": "https://discord.com/api/webhooks/1451099896387080355/G1WqUdvGFVjfJMH5aJnbt_PxOlkm2X-yM1mWwows7hWMwGz4DMIUcEff8GGEReYBCFPr",
    "TUMBLR_BLOG": "manhuw",
    "TUMBLR_KEYS": {
        "ck": "zantmn4dLmmHc3tJKrUpgSJpc9HG2KU1H07OQS4gBr29fn8tXG",
        "cs": "AJdDLCxUpFTJDRsSLOzsau7ZplUSmNJOPPDl1hqRycfd7XICb8",
        "tk": "cJQOHlnE5uhjTENcRzwPyuNSQZKafa9HVdq44Z0BMm2Ksp17l6",
        "ts": "M4uN8gV9FJYq6wTW9D4vujJX4mPnMzqsRFy9Te4yVCkbQZQHki"
    },
    "RSS_FEED": "https://manhuw.com/manhwa-reviews-2/feed/",
    "MEM_WP": "published_urls.txt",
    "MEM_SOCIAL": "marketing_history.txt",
    "MEM_TUMBLR": "posted_links.txt"
}

# تهيئة العملاء
client = Groq(api_key=CONFIG["GROQ_KEY"])
tumblr_client = pytumblr.TumblrRestClient(
    CONFIG["TUMBLR_KEYS"]["ck"], CONFIG["TUMBLR_KEYS"]["cs"],
    CONFIG["TUMBLR_KEYS"]["tk"], CONFIG["TUMBLR_KEYS"]["ts"]
)

# --- دالات الذاكرة ومنع التكرار ---
def is_published(file, item):
    if not os.path.exists(file): return False
    with open(file, "r") as f: return str(item) in f.read().splitlines()

def mark_published(file, item):
    with open(file, "a") as f: f.write(str(item) + "\n")

# ==========================================
# 📝 1. محرك إنتاج المحتوى الضخم (13 مقالاً)
# ==========================================
def generate_long_articles():
    print("🚀 البدء في توليد 13 مقالاً طويلاً...")
    tasks = [
        {'type': 'Breaking News & Leaks', 'cat': 382, 'count': 7, 'query': 'anime manga leaks spoilers'},
        {'type': 'Anime Comparison', 'cat': 381, 'count': 2, 'query': 'trending anime series review'},
        {'type': 'Manga Review', 'cat': 379, 'count': 2, 'query': 'manga chapter analysis'},
        {'type': 'Manhwa Review', 'cat': 281, 'count': 2, 'query': 'popular manhwa webtoon'}
    ]
    total = 0
    for task in tasks:
        gn = GNews(language='en', period='7d')
        news = gn.get_news(task['query'])
        count = 0
        for item in news:
            if count >= task['count'] or is_published(CONFIG["MEM_WP"], item['url']): continue
            
            prompt = f"Write a 1500-word professional SEO article about: {item['title']}. Use H2/H3 tags. Return ONLY JSON: {{\"post_title\": \"..\", \"post_content\": \"..\", \"yoast_focus_keyword\": \"..\"}}"
            try:
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                data = json.loads(res.choices[0].message.content)
                
                # توليد صورة مطابقة للمحتوى
                topic = data.get('yoast_focus_keyword', item['title'])
                safe_topic = urllib.parse.quote(f"{topic} anime manga high resolution")
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{safe_topic}?width=1280&height=720&seed={random.randint(1,9999)}.jpg"
                data['categories'] = [task['cat']]
                
                wp_res = requests.post(CONFIG["WP_ENDPOINT_IMPORT"], json=data, timeout=60)
                if wp_res.status_code == 200:
                    mark_published(CONFIG["MEM_WP"], item['url'])
                    total += 1
                    count += 1
                    print(f"✅ تم نشر مقال: {data['post_title']} في ووردبريس")
            except Exception as e:
                print(f"❌ خطأ في إنتاج المقال: {e}")
            time.sleep(15)
    print(f"🏁 تم الانتهاء من نشر {total} مقالات بنجاح.")

# ==========================================
# 📢 2. التسويق الاجتماعي (Discord & Mastodon) - 3 يومياً
# ==========================================
def run_social_marketing():
    print("📡 فحص المقالات الجديدة للنشر الاجتماعي (الحد 3)...")
    try:
        res = requests.get(f"{CONFIG['WP_BASE_URL']}?_embed&per_page=10", auth=HTTPBasicAuth(CONFIG["WP_USER"], CONFIG["WP_APP_PASS"]))
        if res.status_code != 200: return
        posts, shared = res.json(), 0
        for post in posts:
            if shared >= 3 or is_published(CONFIG["MEM_SOCIAL"], post['id']): continue
            
            title, link = post['title']['rendered'], post['link']
            teaser_prompt = f"Write a 300-word viral English teaser for: {title}. Focus on mystery and link: {link}"
            teaser = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": teaser_prompt}]).choices[0].message.content
            
            # Mastodon
            requests.post("https://mastodon.social/api/v1/statuses", headers={"Authorization": f"Bearer {CONFIG['MASTODON_TOKEN']}"}, data={"status": f"🔥 {title}\n\n{teaser[:400]}...\n🔗 {link}"})
            # Discord
            requests.post(CONFIG["DSC_WEBHOOK"], json={"embeds": [{"title": title, "url": link, "description": teaser[:350], "color": 15158332}]})
            
            mark_published(CONFIG["MEM_SOCIAL"], post['id'])
            shared += 1
            print(f"📢 تم تسويق: {title}")
            time.sleep(20)
    except Exception as e: print(f"❌ خطأ في التسويق: {e}")

# ==========================================
# 🎨 3. محرك Tumblr (عبر Groq Llama-3) - 3 يومياً
# ==========================================
def run_tumblr_syndication():
    print("🎨 فحص RSS للنشر على Tumblr (الحد 3)...")
    try:
        feed = feedparser.parse(CONFIG["RSS_FEED"])
        processed = 0
        for entry in feed.entries:
            if processed >= 3 or is_published(CONFIG["MEM_TUMBLR"], entry.link): continue
            
            prompt = f"Create a clickbait Tumblr post for: {entry.title}. Link: {entry.link}. Use HTML for clickable links. Return JSON: {{\"title\": \"..\", \"body\": \"..\", \"tags\": [\"..\"]}}"
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
            data = json.loads(res.choices[0].message.content)
            
            tumblr_client.create_text(CONFIG["TUMBLR_BLOG"], state="published", title=data['title'], body=data['body'], tags=data['tags'])
            mark_published(CONFIG["MEM_TUMBLR"], entry.link)
            processed += 1
            print(f"✅ تم النشر على Tumblr: {data['title']}")
            time.sleep(20)
    except Exception as e: print(f"❌ خطأ في تامبلر: {e}")

# ==========================================
# 🚀 الحلقة اللانهائية (Render Background Worker)
# ==========================================
if __name__ == "__main__":
    while True:
        print(f"⏰ بدء الدورة اليومية: {time.ctime()}")
        generate_long_articles()
        run_social_marketing()
        run_tumblr_syndication()
        print("😴 اكتملت المهمة. بانتظار 24 ساعة...")
        time.sleep(86400) # انتظار يوم كامل
