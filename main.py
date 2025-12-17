import json, time, requests, os, random, urllib.parse, pytumblr
from groq import Groq
from gnews import GNews
from flask import Flask
from threading import Thread

# --- 1. سيرفر البقاء حياً ---
app = Flask('')
@app.route('/')
def home(): return "Manhuw Elite Bot (Relevant Images) is Live!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. الإعدادات والمفاتيح ---
GROQ_API_KEY = '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'
MODEL_NAME = "llama-3.3-70b-versatile"
client_groq = Groq(api_key=GROQ_API_KEY)

# إعدادات ووردبريس وتومبلر
WP_ENDPOINT = 'https://manhuw.com/wp-json/external/v1/manga/import-review?secret=12345'
TUMBLR_BLOG_NAME = 'manhuw'
TUMBLR_KEYS = {
    "consumer_key": 'zantmn4dLmmHc3tJKrUpgSJpc9HG2KU1H07OQS4gBr29fn8tXG',
    "consumer_secret": 'AJdDLCxUpFTJDRsSLOzsau7ZplUSmNJOPPDl1hqRycfd7XICb8',
    "oauth_token": 'cJQOHlnE5uhjTENcRzwPyuNSQZKafa9HVdq44Z0BMm2Ksp17l6',
    "oauth_secret": 'M4uN8gV9FJYq6wTW9D4vujJX4mPnMzqsRFy9Te4yVCkbQZQHki'
}
MEMORY_FILE = "published_urls.txt"

# --- 3. دالة توليد المقالة (1200 كلمة + قسم التعليقات) ---
def generate_pro_article(title, task_type):
    prompt = f"""
    Write a 1200-word professional SEO article in English about: {title}.
    Category: {task_type}.
    
    INSTRUCTIONS:
    - Structure: Use H2 and H3 subheadings (Min 6).
    - Content: Professional, deep, and investigative.
    - NO JP/KR characters.
    
    DYNAMIC COMMENTS SECTION:
    At the very end, include this EXACT HTML:
    <div style="background:#f0faff; border-top:5px solid #00aeef; padding:30px; margin-top:50px; border-radius:15px; font-family:sans-serif; text-align:center;">
        <h3 style="color:#0078a3;">💬 What's Your Take?</h3>
        <p style="color:#333; font-size:17px; line-height:1.6;">[WRITE_A_UNIQUE_ENGAGING_MESSAGE_FOR_THIS_TOPIC]</p>
        <p style="color:#555; font-weight:bold;">Drop your thoughts in the comments below, we’d love to hear from you!</p>
    </div>

    Return ONLY JSON: {{"post_title": "..", "post_content": "..", "post_excerpt": "..", "yoast_focus_keyword": ".."}}
    """
    try:
        completion = client_groq.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

# --- 4. المهمة الشاملة ---
def start_mission():
    print("🚀 Starting Manhuw Engine (Relevant Images Focus)...")
    
    tasks = [
        {'type': 'Breaking News & Leaks', 'cat': 382, 'count': 7, 'query': 'anime manga leaks spoilers'},
        {'type': 'Anime Comparison', 'cat': 381, 'count': 2, 'query': 'trending anime series review'},
        {'type': 'Manga Review', 'cat': 379, 'count': 2, 'query': 'manga chapter analysis'},
        {'type': 'Manhwa Review', 'cat': 281, 'count': 2, 'query': 'popular manhwa webtoon'}
    ]
    
    total_published = 0
    for task in tasks:
        gn = GNews(language='en', period='3d')
        news = gn.get_news(task['query'])
        
        category_count = 0
        for item in news:
            if category_count >= task['count']: break
            if os.path.exists(MEMORY_FILE) and item['url'] in open(MEMORY_FILE).read(): continue

            print(f"📡 Generating for Category {task['cat']}: {item['title'][:40]}...")
            data = generate_pro_article(item['title'], task['type'])
            
            if data:
                # --- تعديل جوهري لضمان صلة الصورة بالموضوع ---
                # نستخدم الكلمة المفتاحية الدقيقة أو عنوان الخبر مباشرة بدون إضافات عامة
                topic_for_image = data.get('yoast_focus_keyword', item['title'])
                safe_topic = urllib.parse.quote(topic_for_image)
                # أزلنا random seed لكي يعطينا أنسب صورة للموضوع دائماً
                data['featured_image_url'] = f"https://image.pollinations.ai/prompt/{safe_topic}?width=1280&height=720&nologo=true"
                
                data['categories'] = [task['cat']]

                try:
                    res = requests.post(WP_ENDPOINT, json=data, verify=False, timeout=60)
                    if res.status_code == 200:
                        post_id = res.json().get('id', 'latest')
                        article_link = f"https://manhuw.com/?p={post_id}"
                        print(f"✅ WP Live (Relevant Image): {data['post_title']}")

                        # تسويق تومبلر
                        t_prompt = f"Create a short Tumblr teaser for: {data['post_title']}. Call to action link: {article_link}. Return JSON: {{\"title\":\"..\", \"body\":\"..\", \"tags\":[\"..\"]}}"
                        t_res = client_groq.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": t_prompt}], response_format={"type": "json_object"})
                        t_data = json.loads(t_res.choices[0].message.content)
                        
                        if t_data:
                            t_client = pytumblr.TumblrRestClient(TUMBLR_KEYS["consumer_key"], TUMBLR_KEYS["consumer_secret"], TUMBLR_KEYS["oauth_token"], TUMBLR_KEYS["oauth_secret"])
                            t_client.create_text(TUMBLR_BLOG_NAME, state="published", title=t_data['title'], body=t_data['body'] + f"<br><br><a href='{article_link}'>Read Full 1200+ Words Article Here</a>", tags=t_data['tags'])
                            print(f"✅ Tumblr Teaser Active!")

                        with open(MEMORY_FILE, "a") as f: f.write(item['url'] + "\n")
                        category_count += 1
                        total_published += 1
                        print("Sleeping 5 mins to avoid 429 error...")
                        time.sleep(300) 
                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    while True:
        try:
            start_mission()
            print("🏁 Finished all 13 articles. Sleeping 24h...")
            time.sleep(86400)
        except Exception as e:
            print(f"Global Error: {e}")
            time.sleep(600)
