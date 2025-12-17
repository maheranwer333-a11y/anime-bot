import json, time, requests, os, random, urllib.parse
from groq import Groq
from gnews import GNews
from flask import Flask
from threading import Thread

# --- 1. إعداد السيرفر الوهمي للبقاء حياً 24/7 ---
app = Flask('')
@app.route('/')
def home(): 
    return "Manhuw Bot is Running!"

def run(): 
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. الإعدادات والروابط ---
GROQ_API_KEY = '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'
# ملاحظة: تأكد أن secret=12345 هو الصحيح في موقعك
WP_ENDPOINT = 'https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345'
MEMORY_FILE = "published_urls.txt"

client = Groq(api_key=GROQ_API_KEY)

# --- 3. الدوال المساعدة ---
def is_already_published(url):
    if not os.path.exists(MEMORY_FILE): return False
    with open(MEMORY_FILE, "r") as f: 
        return url in f.read().splitlines()

def mark_as_published(url):
    with open(MEMORY_FILE, "a") as f: 
        f.write(url + "\n")

def generate_pro_article(title, task_type):
    prompt = f"""
    Write a 1500-word professional SEO article in English about: {title}.
    Category: {task_type}.
    
    INSTRUCTIONS:
    - Structure: Use H2 and H3 subheadings (Min 6).
    - Content: Professional, deep, and investigative.
    - NO JP/KR characters.
    
    DYNAMIC COMMENTS SECTION:
    At the very end of the article, create a UNIQUE and ENGAGING 'Join the Discussion' section. 
    It should encourage readers to comment based on this specific news.
    
    Use this HTML template for the section:
    <div style="background:#f0faff; border-top:5px solid #00aeef; padding:30px; margin-top:50px; border-radius:15px; font-family:sans-serif; text-align:center;">
        <h3 style="color:#0078a3;">💬 What's Your Take?</h3>
        <p style="color:#333; font-size:17px; line-height:1.6;">[WRITE_A_UNIQUE_ENGAGING_MESSAGE_RELATED_TO_THE_CONTENT_HERE]</p>
        <p style="color:#555; font-weight:bold;">Drop your thoughts in the comments below, we’d love to hear from you!</p>
    </div>

    Return ONLY JSON: {{"post_title": "..", "post_content": "..", "post_excerpt": "..", "yoast_seo_title": "..", "yoast_focus_keyword": ".."}}
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return None

def start_mission():
    print("🌟 Launching Manhuw Dynamic Content Engine (13 Articles)...")
    
    tasks = [
        {'type': 'Breaking News & Leaks', 'cat': 382, 'count': 7, 'query': 'anime manga leaks spoilers'},
        {'type': 'Anime Comparison', 'cat': 381, 'count': 2, 'query': 'trending anime series review'},
        {'type': 'Manga Review', 'cat': 379, 'count': 2, 'query': 'manga chapter analysis'},
        {'type': 'Manhwa Review', 'cat': 281, 'count': 2, 'query': 'popular manhwa webtoon'}
    ]
    
    total = 0
    for task in tasks:
        print(f"\n🔍 Category {task['cat']}: Searching for topics...")
        gn = GNews(language='en', period='7d')
        news = gn.get_news(task['query'])
        
        count = 0
        for item in news:
            if count >= task['count']: break
            if is_already_published(item['url']): continue

            print(f"📡 Generating Elite Article: {item['title'][:45]}...")
            data = generate_pro_article(item['title'], task['type'])
            
            if data:
                data['categories'] = [task['cat']]
                topic = data.get('yoast_focus_keyword', item['title'])
                safe_topic = urllib.parse.quote(f"{topic} anime manga high quality")
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{safe_topic}?width=1280&height=720&nologo=true&seed={random.randint(1,9999)}.jpg"

                try:
                    res = requests.post(WP_ENDPOINT, json=data, verify=False, timeout=60)
                    if res.status_code == 200:
                        mark_as_published(item['url'])
                        total += 1
                        count += 1
                        print(f"✅ Published {total}/13 - Category: {task['cat']}")
                    else:
                        print(f"❌ WP Error: {res.status_code}")
                except Exception as e:
                    print(f"Post Error: {e}")
            time.sleep(12)

# --- 4. التشغيل اللانهائي ---
if __name__ == "__main__":
    keep_alive() # تشغيل السيرفر للبقاء حياً على Render
    while True:
        try:
            start_mission()
            print(f"\n🏁 Finished! Cycle complete at {time.ctime()}. Sleeping 24h...")
            time.sleep(86400) # الانتظار لمدة 24 ساعة
        except Exception as e:
            print(f"Global Error: {e}")
            time.sleep(600)
