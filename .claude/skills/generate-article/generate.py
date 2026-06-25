#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор SEO-статей для блога HotWell.kz.
- Текст (>=1500 слов) и темы генерирует OpenAI (chat completions).
- 3 изображения (1 главное + 2 в теле) генерирует OpenAI Images (gpt-image-1),
  у каждой картинки — свой alt.
- Создаёт страницу статьи site/blog/<slug>.html и добавляет карточку в блог на index.html.

Запуск:
    python3 generate.py                 # тему придумает сам
    python3 generate.py --topic "..."   # своя тема
    python3 generate.py --no-images     # без картинок (для отладки текста)

Нужна переменная окружения OPENAI_API_KEY (или файл .openai_key рядом со скриптом).
Доп. настройки через env: OPENAI_TEXT_MODEL (по умолч. gpt-4o), OPENAI_IMAGE_MODEL
(gpt-image-1), SITE_BASE_URL (https://hotwellkz.kz).
"""
import os, sys, json, ssl, re, base64, datetime, argparse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SITE = os.path.join(ROOT, "site")
BLOG_DIR = os.path.join(SITE, "blog")
IMG_DIR = os.path.join(SITE, "assets", "blog")
INDEX = os.path.join(SITE, "index.html")
PUBLISHED = os.path.join(HERE, "published.json")
CA = "/root/.ccr/ca-bundle.crt"

TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o")
IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
IMAGE_QUALITY = os.environ.get("OPENAI_IMAGE_QUALITY", "high")
BASE_URL = os.environ.get("SITE_BASE_URL", "https://hotwellkz.kz").rstrip("/")

CTX = ssl.create_default_context(cafile=CA if os.path.exists(CA) else None)
MONTHS = ["", "января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]

TRANSLIT = {
 'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i',
 'й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t',
 'у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'',
 'э':'e','ю':'yu','я':'ya'}


def slugify(text):
    text = text.lower().strip()
    out = []
    for ch in text:
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isalnum() and ord(ch) < 128:
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    s = re.sub(r"-+", "-", "".join(out)).strip("-")
    return (s or "statya")[:70]


def api_key():
    k = os.environ.get("OPENAI_API_KEY")
    if not k:
        p = os.path.join(HERE, ".openai_key")
        if os.path.exists(p):
            k = open(p, encoding="utf-8").read().strip()
    if not k:
        sys.exit("ОШИБКА: не задан OPENAI_API_KEY (env или файл .openai_key рядом со скриптом).")
    return k


def post_raw(url, payload, key, timeout=300):
    """POST к OpenAI; при HTTP-ошибке поднимает RuntimeError с телом ответа."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:600]
        raise RuntimeError("OpenAI API %s: %s" % (e.code, body))


def post(url, payload, key, timeout=300):
    try:
        return post_raw(url, payload, key, timeout)
    except RuntimeError as e:
        sys.exit(str(e))


def load_published():
    if os.path.exists(PUBLISHED):
        try:
            return json.load(open(PUBLISHED, encoding="utf-8"))
        except Exception:
            return []
    return []


def word_count(html):
    return len(re.sub(r"<[^>]+>", " ", html).split())


# ---------- генерация текста ----------
SYS_PROMPT = (
 "Ты — ведущий SEO-копирайтер строительной компании HotWell.kz из Казахстана. "
 "Компания с 2012 года строит дома и домокомплекты из СИП-панелей, имеет собственный "
 "завод в Алматы и офисы в Астане и Алматы, работает по всему Казахстану. "
 "Ты пишешь экспертные, полезные и честные статьи на русском языке, "
 "оптимизированные под поисковый трафик Google и Яндекс по запросам жителей Казахстана."
)

def article_user_prompt(topic, published_titles):
    avoid = ""
    if published_titles:
        avoid = "Не повторяй уже опубликованные темы: " + "; ".join(published_titles[:40]) + ". "
    topic_line = ('Тема статьи: "%s".' % topic) if topic else (
        "Сам придумай актуальную, востребованную SEO-тему о строительстве домов из "
        "СИП-панелей в Казахстане (плюсы/минусы, цены, технология, сравнения, "
        "энергоэффективность, зимнее строительство, выбор проекта и т.п.), "
        "по которой реально ищут люди в Google/Яндекс.")
    return (
     topic_line + " " + avoid +
     "Напиши подробную статью НЕ МЕНЕЕ 1500 слов (лучше 1700–2000). "
     "Структура: цепляющее вступление, далее 5–8 разделов с тегами <h2> (и при "
     "необходимости <h3>), маркированные списки <ul><li>, при уместности — <blockquote>. "
     "Обязательно добавь раздел <h2>Часто задаваемые вопросы</h2> с 3–5 парами "
     "вопрос(<h3>)–ответ(<p>). В конце — мотивирующий вывод с призывом обратиться в HotWell.kz. "
     "Пиши экспертно, по делу, естественно используй ключевые слова (без переспама). "
     "Можно вставлять внутренние ссылки ТОЛЬКО на: ../index.html#calc , "
     "../index.html#projects , ../index.html#works , ../index.html#contacts . "
     "В тексте размести РОВНО два маркера на отдельных строках: [IMAGE_1] — примерно после "
     "первой трети статьи, [IMAGE_2] — примерно после двух третей. НЕ используй тег <h1> "
     "(заголовок выводится отдельно). "
     "Для трёх изображений придумай детальные промпты на АНГЛИЙСКОМ для фотореалистичной "
     "генерации: современный/уютный дом из СИП-панелей в Казахстане, пейзаж должен "
     "соответствовать городу (например, Алматы — горы Заилийского Алатау; Астана — степь/"
     "современная застройка), профессиональная архитектурная фотосъёмка, естественный свет, "
     "высокая детализация, без текста, надписей, водяных знаков и логотипов. "
     "Alt к каждой картинке — на русском, с ключевым словом, описательный. "
     "Верни СТРОГО валидный JSON по схеме: {"
     '"title": str (H1, до 70 симв., с ключом), '
     '"slug": str (латиница-через-дефис), '
     '"meta_title": str (до 60 симв.), '
     '"meta_description": str (140–160 симв., с призывом), '
     '"keywords": [str,...] (6–10 шт), '
     '"excerpt": str (1–2 предложения для карточки), '
     '"city": str (город Казахстана для пейзажа), '
     '"reading_minutes": int, '
     '"body_html": str (HTML тела статьи с [IMAGE_1] и [IMAGE_2]), '
     '"images": [{"role":"main","prompt":str,"alt":str},'
     '{"role":"inline1","prompt":str,"alt":str},'
     '{"role":"inline2","prompt":str,"alt":str}]}'
    )


def gen_article(topic, published, key):
    titles = [p.get("title", "") for p in published]
    payload = {
        "model": TEXT_MODEL,
        "temperature": 0.8,
        "max_tokens": 8000,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": article_user_prompt(topic, titles)},
        ],
    }
    data = gen = post("https://api.openai.com/v1/chat/completions", payload, key)
    art = json.loads(gen["choices"][0]["message"]["content"])

    # если статья короткая — один проход на расширение
    if word_count(art.get("body_html", "")) < 1500:
        print("  · статья короткая (%d слов), расширяю…" % word_count(art["body_html"]))
        expand = {
            "model": TEXT_MODEL, "temperature": 0.7, "max_tokens": 8000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYS_PROMPT},
                {"role": "user", "content":
                 "Вот тело статьи в HTML. Расширь его до 1700+ слов, добавив полезные "
                 "детали, примеры, цифры и разделы, СОХРАНИВ маркеры [IMAGE_1] и [IMAGE_2] "
                 "и структуру тегов. Верни JSON {\"body_html\": str}.\n\n" + art["body_html"]},
            ],
        }
        try:
            ex = post("https://api.openai.com/v1/chat/completions", expand, key)
            nb = json.loads(ex["choices"][0]["message"]["content"]).get("body_html")
            if nb and word_count(nb) > word_count(art["body_html"]):
                art["body_html"] = nb
        except SystemExit:
            pass
    # нормализуем slug
    art["slug"] = slugify(art.get("slug") or art.get("title") or "statya")
    return art


# ---------- генерация картинок ----------
# gpt-image-1 требует верификации организации в OpenAI; если недоступен —
# автоматически откатываемся на dall-e-3.
DALLE_SIZE = {"1536x1024": "1792x1024", "1024x1536": "1024x1792", "1024x1024": "1024x1024"}


def _save_b64(resp, path):
    b64 = resp["data"][0]["b64_json"]
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))


def gen_image(prompt, size, key, path):
    # 1) основной модель (по умолчанию gpt-image-1, webp)
    try:
        payload = {"model": IMAGE_MODEL, "prompt": prompt, "size": size, "n": 1,
                   "quality": IMAGE_QUALITY, "output_format": "webp", "output_compression": 82}
        _save_b64(post_raw("https://api.openai.com/v1/images/generations", payload, key, 420), path)
        return path
    except RuntimeError as e:
        if IMAGE_MODEL != "gpt-image-1":
            sys.exit(str(e))
        print("    (gpt-image-1 недоступен, откат на dall-e-3: %s)" % str(e)[:120])
    # 2) запасной dall-e-3 (png через b64_json) — меняем расширение на .png
    png_path = re.sub(r"\.webp$", ".png", path)
    payload = {"model": "dall-e-3", "prompt": prompt,
               "size": DALLE_SIZE.get(size, "1024x1024"), "n": 1,
               "quality": "hd", "response_format": "b64_json"}
    _save_b64(post_raw("https://api.openai.com/v1/images/generations", payload, key, 420), png_path)
    return png_path


# ---------- сборка страницы ----------
def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def figure(src_rel, alt):
    return ('<figure><img src="%s" alt="%s" loading="lazy"><figcaption>%s</figcaption></figure>'
            % (src_rel, esc(alt), esc(alt)))


def build_page(art, img_files, date_obj):
    slug = art["slug"]
    date_ru = "%d %s %d" % (date_obj.day, MONTHS[date_obj.month], date_obj.year)
    iso = date_obj.isoformat()
    main_alt = art["images"][0]["alt"]
    main_file = img_files["main"]
    url = "%s/blog/%s.html" % (BASE_URL, slug)
    og_img = "%s/assets/blog/%s" % (BASE_URL, main_file)

    body = art["body_html"]
    body = body.replace("[IMAGE_1]", figure("../assets/blog/" + img_files["inline1"], art["images"][1]["alt"]))
    body = body.replace("[IMAGE_2]", figure("../assets/blog/" + img_files["inline2"], art["images"][2]["alt"]))
    # если маркеров не было — добавим картинки в конец, чтобы не потерять их
    if "../assets/blog/" + img_files["inline1"] not in body:
        body += figure("../assets/blog/" + img_files["inline1"], art["images"][1]["alt"])
    if "../assets/blog/" + img_files["inline2"] not in body:
        body += figure("../assets/blog/" + img_files["inline2"], art["images"][2]["alt"])

    keywords = ", ".join(art.get("keywords", []))
    wa = ("https://wa.me/77477434343?text=" +
          urllib.request.quote("Здравствуйте! Я с вашего блога, хочу рассчитать дом из СИП-панелей."))

    ld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": art["title"], "description": art["meta_description"],
        "image": [og_img], "datePublished": iso, "dateModified": iso,
        "author": {"@type": "Organization", "name": "Редакция HotWell.kz",
                   "url": BASE_URL + "/#about",
                   "description": "Специалисты по домам и домокомплектам из СИП-панелей. "
                                  "Собственный завод в Алматы, строительство по всему Казахстану."},
        "publisher": {"@type": "Organization", "name": "HotWell.kz",
                      "logo": {"@type": "ImageObject", "url": BASE_URL + "/favicon.svg"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "keywords": keywords,
    }

    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{meta_title}</title>
<meta name="description" content="{meta_desc}">
<meta name="keywords" content="{keywords}">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<meta name="theme-color" content="#FFC400">
<meta property="og:type" content="article">
<meta property="og:title" content="{meta_title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_img}">
<meta property="article:published_time" content="{iso}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{meta_title}">
<meta name="twitter:description" content="{meta_desc}">
<meta name="twitter:image" content="{og_img}">
<link rel="stylesheet" href="../css/style.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="i-house" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/></symbol>
  <symbol id="i-phone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.1-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.7a2 2 0 0 1-.5 2.1L8 9.6a16 16 0 0 0 6 6l1.1-1.1a2 2 0 0 1 2.1-.5c.9.3 1.8.5 2.7.6a2 2 0 0 1 1.7 2z"/></symbol>
  <symbol id="i-wa" viewBox="0 0 32 32"><path fill="currentColor" d="M16 .5C7.4.5.5 7.4.5 16c0 2.8.7 5.4 2 7.8L.5 31.5l7.9-2.1c2.3 1.2 4.9 1.9 7.6 1.9 8.6 0 15.5-6.9 15.5-15.5S24.6.5 16 .5zm0 28c-2.4 0-4.7-.6-6.7-1.8l-.5-.3-4.7 1.2 1.3-4.6-.3-.5C3.9 20.5 3.2 18.3 3.2 16 3.2 8.9 8.9 3.2 16 3.2S28.8 8.9 28.8 16 23.1 28.5 16 28.5z"/></symbol>
</svg>

<header class="header">
  <div class="container">
    <a href="../index.html" class="logo"><svg width="24" height="24"><use href="#i-house"/></svg><span class="brand">Hot<b>Well</b>.kz</span></a>
    <a href="tel:+77477434343" class="header-phone"><svg width="17"><use href="#i-phone"/></svg>+7 747 743 43 43</a>
  </div>
</header>

<section class="section">
  <div class="container">
    <article class="article">
      <nav class="crumbs"><a href="../index.html">Главная</a> &rsaquo; <a href="../index.html#blog">Блог</a> &rsaquo; {title}</nav>
      <h1>{title}</h1>
      <div class="article-meta"><span>Автор: <b>Редакция HotWell.kz</b></span><span>{date_ru}</span><span>~{minutes} мин чтения</span></div>
      <figure class="article-hero"><img src="../assets/blog/{main_file}" alt="{main_alt}"></figure>
      {body}
      <div class="article-cta">
        <h2 style="text-transform:none;margin-top:0">Хотите такой же дом из СИП-панелей?</h2>
        <p>Бесплатно рассчитаем смету и подберём проект под ваш участок и бюджет.</p>
        <div class="flex" style="justify-content:center;gap:12px;flex-wrap:wrap">
          <a href="../index.html#calc" class="btn btn--primary btn--lg">Рассчитать стоимость</a>
          <a href="{wa}" target="_blank" rel="noopener" class="btn btn--wa btn--lg"><svg width="20"><use href="#i-wa"/></svg> Написать в WhatsApp</a>
        </div>
      </div>
      <div class="article-author">
        <span class="article-author__ic"><svg><use href="#i-house"/></svg></span>
        <div>
          <b>Редакция HotWell.kz</b>
          <span>Материал подготовили специалисты HotWell.kz — производим СИП-панели и домокомплекты на собственном заводе в Алматы и строим дома «в черновую» по всему Казахстану. <a href="../index.html#about">О компании</a> · <a href="../index.html#contacts">Связаться</a></span>
        </div>
      </div>
      <p style="margin-top:24px"><a href="../index.html#blog" class="post-more">&larr; Все статьи</a></p>
    </article>
  </div>
</section>

<footer class="footer">
  <div class="container">
    <div class="footer-bottom">
      <span>© {year} ТОО «HOTWELL.KZ» (БИН 180440039034) — дома из СИП-панелей по всему Казахстану</span>
      <a href="tel:+77477434343" style="color:#fff">+7 747 743 43 43</a>
    </div>
  </div>
</footer>
<a href="{wa}" target="_blank" rel="noopener" class="fab-wa" aria-label="WhatsApp"><svg><use href="#i-wa"/></svg></a>
<div class="mobile-bar">
  <a href="../proekty.html" class="btn btn--soft"><svg><use href="#i-house"/></svg> Проекты</a>
  <a href="tel:+77477434343" class="btn btn--primary"><svg><use href="#i-phone"/></svg> Звонок</a>
  <a href="{wa}" target="_blank" rel="noopener" class="btn btn--wa"><svg><use href="#i-wa"/></svg> WhatsApp</a>
</div>
</body>
</html>""".format(
        meta_title=esc(art.get("meta_title") or art["title"]),
        meta_desc=esc(art["meta_description"]), keywords=esc(keywords),
        url=esc(url), og_img=esc(og_img), iso=iso,
        ld=json.dumps(ld, ensure_ascii=False),
        title=esc(art["title"]), date_ru=date_ru, minutes=art.get("reading_minutes", 8),
        main_file=esc(main_file), main_alt=esc(main_alt), body=body, wa=esc(wa),
        year=date_obj.year)


def add_card_to_index(art, img_files, date_obj):
    html = open(INDEX, encoding="utf-8").read()
    date_ru = "%d %s %d" % (date_obj.day, MONTHS[date_obj.month], date_obj.year)
    slug = art["slug"]
    card = (
     '\n      <article class="post">\n'
     '        <a class="post-thumb" href="blog/%s.html"><img src="assets/blog/%s" alt="%s" loading="lazy"></a>\n'
     '        <div class="post-body">\n'
     '          <span class="post-date">%s</span>\n'
     '          <h3><a href="blog/%s.html">%s</a></h3>\n'
     '          <p>%s</p>\n'
     '          <a class="post-more" href="blog/%s.html">Читать &rarr;</a>\n'
     '        </div>\n'
     '      </article>'
     % (slug, img_files["main"], esc(art["images"][0]["alt"]), date_ru,
        slug, esc(art["title"]), esc(art["excerpt"]), slug))
    # убрать пустое состояние при первой статье
    html = re.sub(r'\s*<div class="blog-empty">.*?</a>\s*</div>', "", html, flags=re.S)
    marker = '<div class="grid cols-3 blog-grid">'
    if marker not in html:
        sys.exit("Не найден блок blog-grid в index.html")
    html = html.replace(marker, marker + card, 1)
    open(INDEX, "w", encoding="utf-8").write(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default=None, help="тема статьи (если не задана — придумает сам)")
    ap.add_argument("--no-images", action="store_true", help="не генерировать картинки")
    args = ap.parse_args()

    key = api_key()
    os.makedirs(BLOG_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    published = load_published()

    print("→ Генерирую текст статьи (%s)…" % TEXT_MODEL)
    art = gen_article(args.topic, published, key)
    slug = art["slug"]
    print('  · «%s» (%d слов, slug=%s, город=%s)'
          % (art["title"], word_count(art["body_html"]), slug, art.get("city", "")))

    roles = {"main": ("main", "1536x1024"), "inline1": ("inline1", "1024x1024"),
             "inline2": ("inline2", "1024x1024")}
    img_files = {"main": slug + "-main.webp", "inline1": slug + "-1.webp", "inline2": slug + "-2.webp"}
    by_role = {im["role"]: im for im in art["images"]}

    if not args.no_images:
        print("→ Генерирую 3 изображения (%s, quality=%s)…" % (IMAGE_MODEL, IMAGE_QUALITY))
        for role, size in [("main", "1536x1024"), ("inline1", "1024x1024"), ("inline2", "1024x1024")]:
            im = by_role[role]
            print("  · %s…" % role)
            saved = gen_image(im["prompt"], size, key, os.path.join(IMG_DIR, img_files[role]))
            img_files[role] = os.path.basename(saved)  # учитываем возможную смену .webp→.png
    else:
        print("→ Пропускаю картинки (--no-images)")

    date_obj = datetime.date.today()
    page = build_page(art, img_files, date_obj)
    open(os.path.join(BLOG_DIR, slug + ".html"), "w", encoding="utf-8").write(page)
    add_card_to_index(art, img_files, date_obj)

    published.insert(0, {"title": art["title"], "slug": slug,
                         "date": date_obj.isoformat(), "keywords": art.get("keywords", [])})
    json.dump(published, open(PUBLISHED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\n✓ Готово:")
    print("  • Статья:  site/blog/%s.html" % slug)
    print("  • Карточка добавлена на index.html (блог)")
    if not args.no_images:
        print("  • Картинки: site/assets/blog/%s, %s, %s"
              % (img_files["main"], img_files["inline1"], img_files["inline2"]))


if __name__ == "__main__":
    main()
