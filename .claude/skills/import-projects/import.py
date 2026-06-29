#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Импорт проектов из выгрузки WooCommerce (CSV) в статический сайт HotWell.kz.
- Картинки берутся ССЫЛКАМИ с hotwell.kz (хотлинк), к нам не скачиваются.
- Генерирует: страницу каждого проекта (site/proekty/<slug>.html, Product-разметка),
  каталог с фильтрами (site/proekty.html), site/projects.json, sitemap.xml, robots.txt,
  и врезку избранных проектов в index.html (между маркерами FEATURED).

Запуск:
    python3 import.py --csv путь/к/wc-product-export.csv
    python3 import.py            # возьмёт source.csv рядом со скриптом, если есть
"""
import os, sys, csv, re, json, argparse, hashlib, html as _html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SITE = os.path.join(ROOT, "site")
PROEKTY_DIR = os.path.join(SITE, "proekty")
INDEX = os.path.join(SITE, "index.html")
BASE_URL = os.environ.get("SITE_BASE_URL", "https://hotwellkz.kz").rstrip("/")

TRANSLIT = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
 'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t',
 'у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'',
 'э':'e','ю':'yu','я':'ya'}

GROUP_RULES = [
 ("Построенные", "Построенные объекты"), ("Модульные", "Модульные"),
 ("Проекты", "Проекты"), ("Домокомплект", "Домокомплекты"),
 ("Бани", "Бани"), ("Коммерческие", "Коммерческие"),
 ("Откатные", "Ворота"), ("СИП панели", "СИП-панели"),
 ("Цены", "Проекты"), ("Строим", "Строим сейчас"),
]


def esc(s):
    return _html.escape(s or "", quote=True)


def slugify(text):
    text = (text or "").lower().strip()
    out = []
    for ch in text:
        if ch in TRANSLIT: out.append(TRANSLIT[ch])
        elif ch.isalnum() and ord(ch) < 128: out.append(ch)
        elif ch in " -_/.": out.append("-")
    s = re.sub(r"-+", "-", "".join(out)).strip("-")
    return s or "proekt"


def clean_attr(v):
    return (v or "").replace("\\,", ",").replace("\\", "").strip()


def first_num(s):
    m = re.search(r"\d+(?:[.,]\d+)?", s or "")
    return float(m.group(0).replace(",", ".")) if m else None


def fmt_price(n):
    return format(int(n), ",").replace(",", " ") + " ₸" if n else ""


def clean_name(s):
    s = (s or "").replace('"', "").strip().strip("«»").strip()
    s = re.sub(r"\s*\(?\s*копировать\s*\)?", "", s, flags=re.IGNORECASE)  # убрать «(Копировать)»
    return re.sub(r"\s+", " ", s).strip(" -–—")


def detect_group(cats):
    for token, name in GROUP_RULES:
        for c in cats:
            if c.strip().startswith(token):
                return name
    return "Разное"


def parse_csv(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig", newline="")))
    items, seen = [], set()
    for r in rows:
        name = clean_name(r.get("Имя"))
        if not name:
            continue
        cats = [c.strip() for c in (r.get("Категории") or "").split(",") if c.strip()]
        # исключаем ворота и модульные дома
        low = " | ".join(cats).lower()
        if "ворот" in low or any(c.lower().startswith("модульн") for c in cats):
            continue
        # ошибочный дубль А-100 с ценой 108 863 700 ₸
        if (r.get("Базовая цена") or "").strip() == "108863700":
            continue
        attrs = {}
        for i in range(1, 8):
            nm = clean_attr(r.get("Название атрибута %d" % i)).rstrip(":")
            vl = clean_attr(r.get("Значения атрибутов %d" % i))
            if nm and vl:
                attrs[nm] = vl
        imgs = [u.strip() for u in (r.get("Изображения") or "").split(",") if u.strip()]
        base = slugify(r.get("Артикул") or name)
        slug = base; n = 2
        while slug in seen:
            slug = "%s-%d" % (base, n); n += 1
        seen.add(slug)

        def find(*keys, exclude=()):
            for k in attrs:
                kl = k.lower()
                if any(t in kl for t in keys) and not any(x in kl for x in exclude):
                    return attrs[k]
            return ""
        area = first_num(find("площад"))
        # этажность — строго из «Этажность»; высотные атрибуты («Высота 1 этажа») исключаем
        floors = find("этажность") or find("этаж", exclude=("высот", "потолк"))
        bedrooms = first_num(find("спал", "комнат"))
        dims = find("габарит", "размер")
        height = find("высот", "потолк")
        items.append({
            "name": name, "slug": slug, "sku": (r.get("Артикул") or "").strip(),
            "price": int(first_num(r.get("Базовая цена")) or 0),
            "short": (r.get("Краткое описание") or "").strip(),
            "desc": (r.get("Описание") or "").strip(),
            "group": detect_group(cats), "cats": cats, "attrs": attrs,
            "area": area, "floors_txt": floors, "floors": first_num(floors),
            "bedrooms": int(bedrooms) if bedrooms else None,
            "dims": dims, "height": height,
            "images": imgs, "img": imgs[0] if imgs else "",
        })
    return items


# ---------- общие куски страниц ----------
SPRITE = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
 '<symbol id="i-house" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/></symbol>'
 '<symbol id="i-phone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.1-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.7a2 2 0 0 1-.5 2.1L8 9.6a16 16 0 0 0 6 6l1.1-1.1a2 2 0 0 1 2.1-.5c.9.3 1.8.5 2.7.6a2 2 0 0 1 1.7 2z"/></symbol>'
 '<symbol id="i-wa" viewBox="0 0 32 32"><path fill="currentColor" d="M16 .5C7.4.5.5 7.4.5 16c0 2.8.7 5.4 2 7.8L.5 31.5l7.9-2.1c2.3 1.2 4.9 1.9 7.6 1.9 8.6 0 15.5-6.9 15.5-15.5S24.6.5 16 .5zm0 28c-2.4 0-4.7-.6-6.7-1.8l-.5-.3-4.7 1.2 1.3-4.6-.3-.5C3.9 20.5 3.2 18.3 3.2 16 3.2 8.9 8.9 3.2 16 3.2S28.8 8.9 28.8 16 23.1 28.5 16 28.5z"/></symbol>'
 '<symbol id="i-filter" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M7 12h10M10 18h4"/></symbol>'
 '</svg>')

def header(prefix):
    return ('<header class="header"><div class="container">'
     '<a href="%sindex.html" class="logo"><svg width="24" height="24"><use href="#i-house"/></svg>'
     '<span class="brand">Hot<b>Well</b>.kz</span></a>'
     '<a href="tel:+77477434343" class="header-phone"><svg width="17"><use href="#i-phone"/></svg>+7 747 743 43 43</a>'
     '</div></header>') % prefix

def footer(prefix):
    return ('<footer class="footer"><div class="container"><div class="footer-bottom">'
     '<span>© 2026 ТОО «HOTWELL.KZ» (БИН 180440039034) — дома из СИП-панелей по всему Казахстану</span>'
     '<span class="footer-legal">'
     '<a href="%spolitika-konfidencialnosti.html" style="color:#fff">Политика конфиденциальности</a>'
     '<a href="%spolzovatelskoe-soglashenie.html" style="color:#fff">Пользовательское соглашение</a>'
     '<a href="%sindex.html#contacts" style="color:#fff">Контакты</a>'
     '</span>'
     '</div></div></footer>') % (prefix, prefix, prefix)


def wa_link(name):
    import urllib.parse
    txt = "Здравствуйте! Интересует проект «%s». Подскажите по стоимости и срокам." % name
    return "https://wa.me/77477434343?text=" + urllib.parse.quote(txt)


def mobile_bar(prefix):
    import urllib.parse
    wa = "https://wa.me/77477434343?text=" + urllib.parse.quote("Здравствуйте! Я по поводу домов из СИП-панелей.")
    return ('<a href="%s" target="_blank" rel="noopener" class="fab-wa" aria-label="WhatsApp"><svg><use href="#i-wa"/></svg></a>'
            '<div class="mobile-bar">'
            '<a href="%sproekty.html" class="btn btn--soft"><svg><use href="#i-house"/></svg> Проекты</a>'
            '<a href="tel:+77477434343" class="btn btn--primary"><svg><use href="#i-phone"/></svg> Звонок</a>'
            '<a href="%s" target="_blank" rel="noopener" class="btn btn--wa"><svg><use href="#i-wa"/></svg> WhatsApp</a>'
            '</div>') % (wa, prefix, wa)


# ---------- комплектация «черновая отделка» (одинаковая для всех проектов) ----------
INCLUDES_ROWS = [
 ("g", "Гарантия"),
 ("r", "Гарантия", "1 год"),
 ("g", "Проектирование"),
 ("r", "Архитектурный проект", "Индивидуальный"),
 ("r", "Рабочее проектирование", "yes"),
 ("r", "3D-визуализация дома", "yes"),
 ("g", "Фундамент"),
 ("r", "Фундамент свайно-ленточный, железобетонный. Наполнение ПГС, поверх стяжка 80 мм.", "yes"),
 ("g", "Обвязка фундамента"),
 ("r", "Брус обвязки фундамента", "45×140 мм"),
 ("g", "Стены"),
 ("r", "Внешние и внутренние несущие стены из СИП-панелей Hotwell.KZ 158 мм (OSB-3 толщина 9 мм, пенополистирол ПСБ-С-20Ф)", "yes"),
 ("r", "Ненесущие перегородки — металлический профиль 50×75 мм, обшитый гипсокартоном. Наполнение минвата.", "yes"),
 ("g", "Межэтажное перекрытие"),
 ("r", "Межэтажное перекрытие — балочное (45×190 мм), с устройством пола из ОСБ 18 мм", "yes"),
 ("r", "Утепление пенополистиролом 140 мм по периметру межэтажного перекрытия (для двухэтажных домов)", "yes"),
 ("g", "Чердачное перекрытие и крыша"),
 ("r", "Чердачное перекрытие из деревянных балок", "yes"),
 ("r", "Стропильная система крыши", "yes"),
 ("r", "Утепление чердачного перекрытия", "Пенополистирол ПСБ-С-20Ф 140 мм"),
 ("r", "Пароизоляция чердачного перекрытия или крыши", "yes"),
 ("g", "Кровля и обрешётка"),
 ("r", "Металлочерепица", "yes"),
 ("r", "Утепление кровли* — пенополистирол ПСБ-С-20Ф слоем 140 мм", "yes"),
 ("g", "Доставка и монтаж"),
 ("r", "Монтаж штатными мастерами HotWell.kz", "yes"),
 ("r", "Фотоотчёты со стройки", "Бесплатно"),
 ("r", "Сроки сборки**", "30 дней"),
 ("r", "Доставка комплекта дома и всех необходимых материалов", "yes"),
 ("r", "Организация проживания бригады", "yes"),
]
INCLUDES_NOTES = [
 "*Утепление и пароизоляция стропильной системы крыши производятся при наличии мансардного этажа.",
 "**Срок сборки ориентировочный и зависит от погодных условий.",
 "*** Стоимость указана без учёта террас.",
]

def includes_table():
    parts = []
    for row in INCLUDES_ROWS:
        if row[0] == "g":
            parts.append('<div class="ispec-group">%s</div>' % esc(row[1]))
        else:
            val = '<b class="yes" aria-label="входит в стоимость">✓</b>' if row[2] == "yes" else '<b>%s</b>' % esc(row[2])
            parts.append('<div class="ispec-row"><span>%s</span>%s</div>' % (esc(row[1]), val))
    notes = "".join("<li>%s</li>" % esc(n) for n in INCLUDES_NOTES)
    return ('<section class="includes-spec">'
            '<h2>Что входит в стоимость <span class="accent">(черновая отделка)</span></h2>'
            '<div class="ispec"><div class="ispec-head"><span>Комплектация</span><b>Черновая отделка</b></div>'
            + "".join(parts) + '</div>'
            '<ul class="ispec-notes">' + notes + '</ul></section>')


# ---------- страница проекта ----------
def thumb_block(p, href):
    """Ссылка-обложка карточки: основное фото + второе фото, проявляющееся при наведении."""
    main = ('<img class="thumb-i" src="%s" alt="%s" loading="lazy">'
            % (esc(p["img"]), esc(p["name"]))) if p.get("img") else ''
    alt = ''
    imgs = p.get("images") or []
    if len(imgs) > 1 and imgs[1]:
        alt = ('<img class="thumb-i thumb-i--alt" src="%s" alt="" loading="lazy" aria-hidden="true">'
               % esc(imgs[1]))
    return '<a class="thumb" href="%s">%s%s</a>' % (href, main, alt)


def proj_card(p):
    meta = []
    if p["area"]:
        meta.append('<span>%s м²</span>' % (int(p["area"]) if float(p["area"]) == int(p["area"]) else p["area"]))
    if p["floors_txt"]:
        meta.append('<span>%s</span>' % esc(p["floors_txt"]))
    if p["bedrooms"]:
        meta.append('<span>%d сп.</span>' % p["bedrooms"])
    price = ('от %s' % fmt_price(p["price"])) if p["price"] else 'Цена по запросу'
    return ('<article class="project">%s'
            '<div class="body"><div class="price">%s</div><h3><a href="%s.html">%s</a></h3>'
            '<div class="meta">%s</div><a class="more" href="%s.html">Подробнее &rarr;</a></div></article>'
            % (thumb_block(p, p["slug"] + ".html"), price, p["slug"], esc(p["name"]), "".join(meta), p["slug"]))


# ---------- генерация уникального SEO-описания и FAQ ----------
# Тексты собираются из достоверных характеристик проекта с ротацией формулировок
# по хешу слага, чтобы 550 страниц не были одинаковыми (защита от «тонкого»/
# дублирующего контента). Никаких выдумок: только реальные поля проекта и факты
# о технологии HotWell.kz (совпадают с таблицей «Что входит в стоимость»).

GEO_CITIES = ("Алматы", "Астане", "Шымкенте", "Караганде", "Актобе", "Таразе",
              "Павлодаре", "Усть-Каменогорске", "Костанае", "Кокшетау")


def _load_ai_descriptions():
    """AI-переписанные описания (необязательно). Генерируются gen_descriptions.py
    в GitHub Action и складываются в ai-descriptions.json: {slug: {"desc": "<p>…</p>"}}.
    Если файла нет — используется детерминированный генератор ниже."""
    path = os.path.join(HERE, "ai-descriptions.json")
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8")) or {}
        except Exception as e:
            print("⚠ ai-descriptions.json не прочитан:", e)
    return {}


AI_DESCRIPTIONS = _load_ai_descriptions()


def _seed(slug):
    return int(hashlib.md5(("hw:" + slug).encode("utf-8")).hexdigest(), 16)


def _pick(pool, seed, shift):
    return pool[(seed >> shift) % len(pool)]


def _area_int(a):
    if not a:
        return None
    return int(a) if float(a) == int(a) else a


def project_kind(p):
    """Назначение объекта — для корректной подачи описания."""
    nm = (p.get("name") or "").lower()
    grp = (p.get("group") or "").lower()
    if "бан" in nm or "бан" in grp:
        return "баня"
    if "гараж" in nm:
        return "гараж"
    if any(w in nm for w in ("склад", "ангар", "цех", "коммерч", "офис", "магазин")) or "коммерч" in grp:
        return "коммерческий объект"
    if "модул" in nm or "модул" in grp:
        return "модульный дом"
    if "дач" in nm:
        return "дачный дом"
    return "дом"


def build_description(p):
    """Возвращает HTML-абзацы описания (~150–220 слов), уникальные на проект.
    Приоритет — AI-текст из ai-descriptions.json; иначе детерминированный генератор."""
    ai = AI_DESCRIPTIONS.get(p["slug"])
    if ai and ai.get("desc"):
        return ai["desc"]
    seed = _seed(p["slug"])
    kind = project_kind(p)
    nm = p["name"]
    area = _area_int(p.get("area"))

    # 1) Вводное предложение — реальные характеристики проекта
    facts = []
    if area:
        facts.append("общей площадью %s м²" % area)
    if p.get("floors_txt"):
        facts.append(p["floors_txt"].rstrip(". ").lower())
    intro_tpl = _pick([
        "«%s» — %s из СИП-панелей%s.",
        "Проект «%s» — %s по технологии СИП%s.",
        "«%s» — готовый %s из СИП-панелей HotWell.kz%s.",
        "%s — %s из СИП-панелей под ключ%s.",
    ], seed, 0)
    tail = (", " + ", ".join(facts)) if facts else ""
    intro = intro_tpl % (nm, kind, tail)

    # 2) Планировка — только если есть данные
    plan_bits = []
    if p.get("bedrooms"):
        plan_bits.append("%d спальни" % p["bedrooms"] if 2 <= p["bedrooms"] <= 4 else "%d спален" % p["bedrooms"])
    if p.get("dims"):
        plan_bits.append("габариты %s м" % p["dims"].rstrip(". "))
    if p.get("height"):
        plan_bits.append("высота этажей %s" % p["height"].rstrip(". "))
    plan = ""
    if plan_bits:
        plan = _pick([
            " Планировка предусматривает %s.",
            " В проекте — %s.",
            " Характеристики: %s.",
        ], seed, 8) % ", ".join(plan_bits)

    # 3) Технология СИП — пул преимуществ
    tech = _pick([
        "Несущие стены собираются из СИП-панелей толщиной 158 мм (OSB-3 и пенополистирол ПСБ-С-20Ф): такой контур держит тепло зимой и прохладу летом, а счета за отопление выходят заметно ниже, чем у кирпича и газоблока.",
        "Дом возводится из заводских СИП-панелей 158 мм — это сплошной утеплённый контур без мостиков холода, поэтому отопление обходится дешевле, а внутри тепло даже в сильные морозы.",
        "СИП-панель толщиной 158 мм совмещает несущую стену и утеплитель: лёгкий вес снижает нагрузку на фундамент, а высокая энергоэффективность экономит на отоплении каждый сезон.",
        "Стены из СИП-панелей 158 мм дают ровные поверхности под чистовую отделку и отличную теплоизоляцию — комфортный микроклимат сохраняется круглый год без переплат за энергоносители.",
    ], seed, 16)

    # 4) Сроки и комплектация
    build = _pick([
        "Каркас собирается примерно за 30 дней, а в стоимость уже входят фундамент, индивидуальный проект, 3D-визуализация, кровля из металлочерепицы, доставка домокомплекта и монтаж штатными бригадами HotWell.kz.",
        "Сборка занимает около месяца. В цену включены свайно-ленточный фундамент, рабочее проектирование, металлочерепица, доставка комплекта и работа собственных бригад — без скрытых доплат.",
        "Дом сдаётся в черновой отделке за ориентировочные 30 дней: фундамент, проект, крыша, доставка и монтаж уже учтены в стоимости, а на каждый объект даётся гарантия.",
    ], seed, 24)

    # 5) География — локальный SEO-сигнал
    c1 = _pick(GEO_CITIES, seed, 32)
    c2 = _pick(GEO_CITIES, seed, 40)
    if c2 == c1:
        c2 = GEO_CITIES[(GEO_CITIES.index(c1) + 1) % len(GEO_CITIES)]
    geo = _pick([
        " Строим «%s» в %s, %s и других городах Казахстана с доставкой домокомплекта по всей стране.",
        " Возводим проект в %s, %s и любом регионе Казахстана.",
        " Доступно для строительства в %s, %s и по всему Казахстану.",
    ], seed, 48)
    if "%s" in geo and geo.count("%s") == 3:
        geo = geo % (nm, c1, c2)
    else:
        geo = geo % (c1, c2)

    # 6) Призыв к действию
    cta = _pick([
        "Рассчитайте точную стоимость онлайн за 5 минут или напишите в WhatsApp — зафиксируем цену и сроки в договоре.",
        "Узнайте итоговую цену под ваш участок и комплектацию — расчёт онлайн за 5 минут, цена и сроки закрепляются договором.",
        "Оставьте заявку, чтобы получить смету и график строительства; стоимость и сроки фиксируем в договоре.",
    ], seed, 56)

    p1 = intro + plan + " " + tech
    p2 = build + geo + " " + cta
    return "<p>%s</p><p>%s</p>" % (p1, p2)


def build_faq(p):
    """FAQ-блок (HTML) + данные для FAQPage-разметки. Ответы фактологичны."""
    area = _area_int(p.get("area"))
    price_txt = ("от %s" % fmt_price(p["price"])) if p.get("price") else "по запросу после расчёта"
    qa = [
        ("Сколько стоит построить проект «%s»?" % p["name"],
         "Стоимость — %s в черновой отделке. Точную цену рассчитываем под ваш участок и комплектацию онлайн за 5 минут и фиксируем в договоре." % price_txt),
        ("Что входит в стоимость?",
         "Свайно-ленточный фундамент, индивидуальный архитектурный проект, рабочее проектирование, 3D-визуализация, стены из СИП-панелей 158 мм, кровля из металлочерепицы, доставка домокомплекта и монтаж штатными бригадами HotWell.kz. На объект действует гарантия 1 год."),
        ("Сколько длится строительство?",
         "Сборка домокомплекта занимает около 30 дней (срок зависит от погоды и сложности проекта). Вы получаете фотоотчёты со стройки на каждом этапе."),
        ("В каких городах вы строите?",
         "Работаем по всему Казахстану: Алматы, Астана, Шымкент, Караганда, Актобе и другие регионы. Домокомплект доставляем в любую точку страны."),
    ]
    if area:
        qa.insert(1, ("Какая площадь дома «%s»?" % p["name"],
                      "Общая площадь проекта — %s м²%s." % (
                          area,
                          (", " + p["floors_txt"].rstrip(". ").lower()) if p.get("floors_txt") else "")))
    rows = "".join(
        '<details class="faq-item"><summary>%s</summary><div class="faq-a">%s</div></details>'
        % (esc(q), esc(a)) for q, a in qa)
    html_block = '<section class="pg-faq"><h2 style="text-transform:none;font-size:1.4rem">Частые вопросы</h2>%s</section>' % rows
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}
    return html_block, faq_ld


def project_page(p, prv=None, nxt=None, sim=None):
    url = "%s/proekty/%s.html" % (BASE_URL, p["slug"])
    specs = []
    if p["area"]: specs.append(("Площадь", "%s м²" % (int(p["area"]) if p["area"]==int(p["area"]) else p["area"])))
    if p["floors_txt"]: specs.append(("Этажность", p["floors_txt"]))
    if p["bedrooms"]: specs.append(("Спальни", str(p["bedrooms"])))
    if p["dims"]: specs.append(("Габариты", p["dims"]))
    if p["height"]: specs.append(("Высота этажей", p["height"]))
    specs_html = "".join('<div class="spec"><span>%s</span><b>%s</b></div>' % (esc(k), esc(v)) for k, v in specs)

    thumbs = "".join(
        '<button class="pg-thumb" data-i="%d"><img src="%s" alt="%s — фото %d" loading="lazy"></button>'
        % (i, esc(u), esc(p["name"]), i + 1)
        for i, u in enumerate(p["images"][:20]))

    nm = p["name"]
    lead = nm if nm.lower().startswith(("проект", "дом")) else ("Проект дома " + nm)
    meta_desc = (lead
                 + (", площадь %d м²" % int(p["area"]) if p["area"] else "")
                 + (", %s" % p["floors_txt"] if p["floors_txt"] else "")
                 + (", спален: %d" % p["bedrooms"] if p["bedrooms"] else "")
                 + (". Цена от %s." % fmt_price(p["price"]) if p["price"] else ". ")
                 + " Строительство из СИП-панелей по всему Казахстану — HotWell.kz.")
    title = "%s — проект дома из СИП-панелей" % p["name"]
    if p["area"]: title += ", %d м²" % int(p["area"])
    title += " | HotWell.kz"

    ld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"],
          "image": p["images"][:6] or [], "description": meta_desc,
          "sku": p["sku"], "brand": {"@type": "Brand", "name": "HotWell.kz"},
          "category": p["group"]}
    if p["price"]:
        ld["offers"] = {"@type": "Offer", "priceCurrency": "KZT", "price": str(p["price"]),
                        "availability": "https://schema.org/InStock", "url": url,
                        "seller": {"@type": "Organization", "name": "HotWell.kz"}}

    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [
                      {"@type": "ListItem", "position": 1, "name": "Главная", "item": BASE_URL + "/"},
                      {"@type": "ListItem", "position": 2, "name": "Каталог проектов", "item": BASE_URL + "/proekty.html"},
                      {"@type": "ListItem", "position": 3, "name": p["name"], "item": url}]}
    ld_list = [ld, breadcrumb]

    price_block = ('<div class="pg-price">от %s</div>' % fmt_price(p["price"])) if p["price"] else \
                  '<div class="pg-price pg-price--ask">Цена по запросу</div>'
    # Уникальное SEO-описание из достоверных характеристик проекта + FAQ с FAQPage-разметкой
    desc_block = ('<div class="pg-desc"><h2 style="text-transform:none;font-size:1.4rem">Описание</h2>%s</div>'
                  % build_description(p))
    faq_block, faq_ld = build_faq(p)
    ld_json = json.dumps(ld_list + [faq_ld], ensure_ascii=False)

    # навигация между проектами + похожие
    nav_html = ""
    if prv or nxt:
        a = ('<a class="proj-nav__a" href="%s.html"><span>&larr; Предыдущий проект</span><b>%s</b></a>'
             % (prv["slug"], esc(prv["name"]))) if prv else '<span></span>'
        b = ('<a class="proj-nav__a proj-nav__a--next" href="%s.html"><span>Следующий проект &rarr;</span><b>%s</b></a>'
             % (nxt["slug"], esc(nxt["name"]))) if nxt else '<span></span>'
        nav_html = '<nav class="proj-nav">%s%s</nav>' % (a, b)
    # компактная навигация вверху (под крошками)
    navtop_html = ""
    if prv or nxt:
        ta = ('<a class="pg-navbtn" href="%s.html">&lsaquo; Предыдущий</a>' % prv["slug"]) if prv else '<span></span>'
        tb = ('<a class="pg-navbtn pg-navbtn--next" href="%s.html">Следующий &rsaquo;</a>' % nxt["slug"]) if nxt else '<span></span>'
        navtop_html = '<div class="pg-nav-top">%s%s</div>' % (ta, tb)
    sim_html = ""
    if sim:
        sim_html = ('<section class="similar"><h2>Похожие проекты</h2><div class="similar-row">%s</div></section>'
                    % "".join(proj_card(s) for s in sim))

    tpl = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<link rel="canonical" href="__URL__">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<meta name="theme-color" content="#FFC400">
<meta property="og:type" content="product">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="__URL__">
<meta property="og:image" content="__OGIMG__">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="../css/style.css">
<script type="application/ld+json">__LD__</script>
</head>
<body>
__SPRITE__
__HEADER__
<section class="section">
  <div class="container">
    <nav class="crumbs"><a href="../index.html">Главная</a> &rsaquo; <a href="../proekty.html">Каталог проектов</a> &rsaquo; __NAME__</nav>
    __NAVTOP__
    <div class="pg">
      <div class="pg-gallery">
        <div class="pg-main"><img id="pgMain" data-i="0" src="__MAIN__" alt="__NAME__ — проект дома из СИП-панелей"></div>
        <div class="pg-thumbs">__THUMBS__</div>
      </div>
      <aside class="pg-info">
        <span class="eyebrow">__GROUP__</span>
        <h1>__NAME__</h1>
        __PRICE__
        <div class="pg-specs">__SPECS__</div>
        <div class="pg-actions">
          <a href="../index.html#calc" class="btn btn--primary btn--lg btn--block">Рассчитать стоимость</a>
          <a href="__WA__" target="_blank" rel="noopener" class="btn btn--wa btn--lg btn--block"><svg width="20"><use href="#i-wa"/></svg> Спросить в WhatsApp</a>
        </div>
        <p class="pg-note">Рассчитаем стоимость онлайн за 5 минут. Цену и сроки фиксируем в договоре.</p>
      </aside>
    </div>
    __INCLUDES__
    __DESCBLOCK__
    __FAQ__
    __SIMILAR__
    __NAV__
    <p style="margin-top:24px"><a href="../proekty.html" class="post-more">&larr; Весь каталог проектов</a></p>
  </div>
</section>
__FOOTER__
__BOTTOM__
<div class="lightbox" id="lb" aria-hidden="true">
  <span class="lb-count"></span>
  <button class="lb-btn lb-close" aria-label="Закрыть">&times;</button>
  <button class="lb-btn lb-prev" aria-label="Назад">&#8249;</button>
  <img class="lb-img" src="" alt="">
  <button class="lb-btn lb-next" aria-label="Вперёд">&#8250;</button>
  <div class="lb-cap"></div>
</div>
<script>
  (function(){
    var GAL=__GALJSON__, NAME=__NAMEJSON__;
    var main=document.getElementById('pgMain'), lb=document.getElementById('lb');
    if(!main||!lb||!GAL.length) return;
    var img=lb.querySelector('.lb-img'), cnt=lb.querySelector('.lb-count'), cap=lb.querySelector('.lb-cap'), idx=0;
    function show(i){ idx=(i+GAL.length)%GAL.length; img.classList.remove('zoomed'); img.src=GAL[idx]; cnt.textContent=(idx+1)+' / '+GAL.length; cap.textContent=NAME; }
    function openLb(i){ show(i); lb.classList.add('open'); document.body.classList.add('no-scroll'); }
    function closeLb(){ lb.classList.remove('open'); document.body.classList.remove('no-scroll'); img.src=''; }
    document.querySelectorAll('.pg-thumb').forEach(function(t){
      t.addEventListener('click', function(){ var i=+t.getAttribute('data-i'); main.src=GAL[i]; main.setAttribute('data-i', i); });
    });
    main.addEventListener('click', function(){ openLb(+(main.getAttribute('data-i')||0)); });
    lb.querySelector('.lb-close').addEventListener('click', closeLb);
    lb.querySelector('.lb-prev').addEventListener('click', function(e){ e.stopPropagation(); show(idx-1); });
    lb.querySelector('.lb-next').addEventListener('click', function(e){ e.stopPropagation(); show(idx+1); });
    lb.addEventListener('click', function(e){ if(e.target===lb) closeLb(); });
    img.addEventListener('click', function(e){ e.stopPropagation(); img.classList.toggle('zoomed'); });
    document.addEventListener('keydown', function(e){ if(!lb.classList.contains('open')) return; if(e.key==='Escape') closeLb(); else if(e.key==='ArrowLeft') show(idx-1); else if(e.key==='ArrowRight') show(idx+1); });
    var x0=null;
    lb.addEventListener('touchstart', function(e){ x0=e.touches[0].clientX; }, {passive:true});
    lb.addEventListener('touchend', function(e){ if(x0===null) return; var dx=e.changedTouches[0].clientX-x0; if(Math.abs(dx)>45) show(dx<0?idx+1:idx-1); x0=null; });
  })();
</script>
</body>
</html>"""
    repl = {
        "__TITLE__": esc(title), "__DESC__": esc(meta_desc), "__URL__": esc(url),
        "__OGIMG__": esc(p["img"]), "__LD__": ld_json,
        "__SPRITE__": SPRITE, "__HEADER__": header("../"), "__FOOTER__": footer("../"),
        "__NAME__": esc(p["name"]), "__MAIN__": esc(p["img"]), "__THUMBS__": thumbs,
        "__GROUP__": esc(p["group"]), "__PRICE__": price_block, "__SPECS__": specs_html,
        "__WA__": esc(wa_link(p["name"])), "__DESCBLOCK__": desc_block,
        "__FAQ__": faq_block,
        "__INCLUDES__": includes_table(), "__BOTTOM__": mobile_bar("../"),
        "__GALJSON__": json.dumps(p["images"][:20], ensure_ascii=False),
        "__NAMEJSON__": json.dumps(p["name"], ensure_ascii=False),
        "__NAV__": nav_html, "__SIMILAR__": sim_html, "__NAVTOP__": navtop_html,
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    return tpl


# ---------- каталог ----------
def _catalog_card_html(p):
    """Статичная карточка каталога — разметка совпадает с JS-функцией card(),
    чтобы при «гидрации» вид не менялся. Нужна для SSR: ссылки на все проекты
    присутствуют в HTML и видны поисковикам (особенно Яндексу, слабому в JS)."""
    img = p["img"]
    img2 = p["images"][1] if len(p["images"]) > 1 and p["images"][1] else ""
    thumbs = ""
    if img:
        thumbs += '<img class="thumb-i" src="%s" alt="%s" loading="lazy">' % (esc(img), esc(p["name"]))
    if img2:
        thumbs += '<img class="thumb-i thumb-i--alt" src="%s" alt="" loading="lazy" aria-hidden="true">' % esc(img2)
    meta = []
    if p["area"]:
        meta.append('<span>%s м²</span>' % (int(p["area"]) if p["area"] == int(p["area"]) else p["area"]))
    if p["floors_txt"]:
        meta.append('<span>%s</span>' % esc(p["floors_txt"]))
    if p["bedrooms"]:
        meta.append('<span>%d сп.</span>' % p["bedrooms"])
    price = ("от %s" % fmt_price(p["price"])) if p["price"] else "Цена по запросу"
    return ('<article class="project"><a class="thumb" href="proekty/%s.html">%s</a>'
            '<div class="body"><div class="price">%s</div>'
            '<h3><a href="proekty/%s.html">%s</a></h3>'
            '<div class="meta">%s</div>'
            '<a href="proekty/%s.html" class="btn btn--outline btn--block">Подробнее</a></div></article>'
            % (p["slug"], thumbs, price, p["slug"], esc(p["name"]), "".join(meta), p["slug"]))


def catalog_page(groups, price_max, area_max, items=None, price_step=100000, area_step=10):
    opts = "".join('<option value="%s">%s</option>' % (esc(g), esc(g)) for g in groups)
    # SSR: карточки всех проектов в порядке сортировки по умолчанию (площадь ↑)
    ssr_items = sorted(items or [], key=lambda p: (p["area"] or 0, p["name"]))
    cards_html = "".join(_catalog_card_html(p) for p in ssr_items)
    tpl = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Каталог проектов домов из СИП-панелей — цены и планировки | HotWell.kz</title>
<meta name="description" content="Каталог готовых проектов домов из СИП-панелей: одноэтажные и двухэтажные, с площадями, планировками и ценами. Фильтр по площади, этажности и бюджету. Строим по всему Казахстану.">
<link rel="canonical" href="__BASE__/proekty.html">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta name="theme-color" content="#FFC400">
<meta property="og:type" content="website">
<meta property="og:site_name" content="HotWell.kz">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="Каталог проектов домов из СИП-панелей — цены и планировки | HotWell.kz">
<meta property="og:description" content="Каталог готовых проектов домов из СИП-панелей: одноэтажные и двухэтажные, с площадями, планировками и ценами. Строим по всему Казахстану.">
<meta property="og:url" content="__BASE__/proekty.html">
<meta property="og:image" content="__BASE__/assets/og-cover.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="css/style.css">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Главная","item":"__BASE__/"},{"@type":"ListItem","position":2,"name":"Каталог проектов","item":"__BASE__/proekty.html"}]}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage","name":"Каталог проектов домов из СИП-панелей","description":"Готовые проекты домов из СИП-панелей с ценами и планировками.","url":"__BASE__/proekty.html","isPartOf":{"@type":"WebSite","name":"HotWell.kz","url":"__BASE__/"}}</script>
</head>
<body>
__SPRITE__
__HEADER__
<section class="section">
  <div class="container">
    <div class="section-head center">
      <span class="eyebrow">Каталог 2025</span>
      <h2 class="section-title">Проекты домов <span class="accent">из СИП-панелей</span></h2>
      <p class="lead">Выберите проект по площади, этажности и бюджету. Точную смету рассчитаем онлайн за несколько минут после обращения.</p>
    </div>
    <div class="catalog-sticky">
      <div class="catalog-toolbar">
        <button id="filtersToggle" class="btn btn--primary filters-toggle"><svg width="18"><use href="#i-filter"/></svg> Фильтры и сортировка<span id="fCountBadge" class="fbadge" hidden></span><span class="ftgl-chev" aria-hidden="true">▾</span></button>
        <span id="catCount" class="cat-count">—</span>
        <label class="toolbar-sort">Сортировка
          <select id="fSort"><option value="area-asc">Площадь ↑</option><option value="area-desc">Площадь ↓</option><option value="price-asc">Цена ↑</option><option value="price-desc">Цена ↓</option></select>
        </label>
      </div>
      <div class="chips" id="quickChips">
        <button class="chip" data-k="floors" data-v="1">1 этаж</button>
        <button class="chip" data-k="floors" data-v="1.5">Мансарда</button>
        <button class="chip" data-k="floors" data-v="2">2 этажа</button>
        <button class="chip" data-k="area" data-v="0-100">до 100 м²</button>
        <button class="chip" data-k="area" data-v="100-150">100–150 м²</button>
        <button class="chip" data-k="area" data-v="150-200">150–200 м²</button>
        <button class="chip" data-k="area" data-v="200-__AREAMAX__">200+ м²</button>
      </div>
    </div>
    <div class="catalog-layout">
      <aside class="filters-panel" id="filtersPanel">
        <div class="sheet-handle" id="sheetHandle"></div>
        <div class="filters-panel__head"><b>Фильтры</b><button id="filtersClose" class="filters-close" aria-label="Закрыть">&times;</button></div>
        <div class="filters-body">
          <label>Раздел<select id="fGroup"><option value="">Все</option>__OPTS__</select></label>
          <label>Этажность<select id="fFloors"><option value="">Любая</option><option value="1">1 этаж</option><option value="1.5">1.5 / мансарда</option><option value="2">2 этажа</option></select></label>
          <label>Спальни<select id="fBed"><option value="">Любое</option><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4+</option></select></label>
          <div class="rangef">
            <div class="rangef-top"><span>Площадь, м²</span><span class="rangef-vals"><b id="areaMinVal">0</b> — <b id="areaMaxVal">…</b></span></div>
            <div class="range-slider">
              <div class="range-track"></div><div class="range-fill" id="areaFill"></div>
              <input type="range" id="fAreaMin" min="0" max="__AREAMAX__" step="__AREASTEP__" value="0" aria-label="Площадь от">
              <input type="range" id="fAreaMax" min="0" max="__AREAMAX__" step="__AREASTEP__" value="__AREAMAX__" aria-label="Площадь до">
            </div>
          </div>
          <div class="rangef">
            <div class="rangef-top"><span>Цена, ₸</span><span class="rangef-vals"><b id="priceMinVal">0</b> — <b id="priceMaxVal">…</b></span></div>
            <div class="range-slider">
              <div class="range-track"></div><div class="range-fill" id="priceFill"></div>
              <input type="range" id="fPriceMin" min="0" max="__PRICEMAX__" step="__PRICESTEP__" value="0" aria-label="Цена от">
              <input type="range" id="fPriceMax" min="0" max="__PRICEMAX__" step="__PRICESTEP__" value="__PRICEMAX__" aria-label="Цена до">
            </div>
          </div>
          <label class="filters-search">Поиск<input type="search" id="fSearch" placeholder="Название проекта…"></label>
          <button id="catReset" class="btn btn--outline filters-reset">Сбросить</button>
        </div>
        <div class="filters-panel__foot">
          <button id="filtersApply" class="btn btn--primary btn--block">Показать <span id="applyCount"></span></button>
        </div>
      </aside>
      <div class="catalog-results">
        <div class="grid cols-3" id="catGrid">__CARDS__</div>
        <div id="catSentinel" aria-hidden="true" style="height:1px"></div>
        <div class="center" style="margin-top:30px"><button id="catMore" class="btn btn--primary btn--lg" hidden>Показать ещё</button></div>
        <p id="catEmpty" class="lead center" hidden style="margin-top:24px">По заданным фильтрам ничего не найдено. Попробуйте смягчить условия.</p>
      </div>
    </div>
    <div class="filters-backdrop" id="filtersBackdrop"></div>
  </div>
</section>
<button class="filter-fab" id="filterFab" aria-label="Открыть фильтры"><svg><use href="#i-filter"/></svg><span class="filter-fab__t">Фильтры</span></button>
__FOOTER__
__BOTTOM__
<script>
const PER=24; let all=[], view=[], shown=0;
const $=function(id){return document.getElementById(id)};
function fmtPrice(n){ return n? (''+n).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ')+' \\u20b8' : 'Цена по запросу'; }
function card(p){
  var meta=[];
  if(p.area) meta.push(p.area+' м²');
  if(p.floors_txt) meta.push(p.floors_txt);
  if(p.bedrooms) meta.push(p.bedrooms+' сп.');
  return '<article class="project">'+
    '<a class="thumb" href="proekty/'+p.slug+'.html">'+(p.img?'<img class="thumb-i" src="'+p.img+'" alt="'+p.name.replace(/"/g,'&quot;')+'" loading="lazy">':'')+(p.img2?'<img class="thumb-i thumb-i--alt" src="'+p.img2+'" alt="" loading="lazy" aria-hidden="true">':'')+'</a>'+
    '<div class="body"><div class="price">'+(p.price?'от '+fmtPrice(p.price):'Цена по запросу')+'</div>'+
    '<h3><a href="proekty/'+p.slug+'.html">'+p.name+'</a></h3>'+
    '<div class="meta">'+meta.map(function(m){return '<span>'+m+'</span>'}).join('')+'</div>'+
    '<a href="proekty/'+p.slug+'.html" class="btn btn--outline btn--block">Подробнее</a></div></article>';
}
function apply(){
  var g=$('fGroup').value, fl=$('fFloors').value, bd=$('fBed').value;
  var amin=+$('fAreaMin').value||0, amax=+$('fAreaMax').value||0;
  var pmin=+$('fPriceMin').value||0, pmax=+$('fPriceMax').value||0, q=$('fSearch').value.trim().toLowerCase();
  view=all.filter(function(p){
    if(g && p.group!==g) return false;
    if(fl && String(p.floors)!==fl) return false;
    if(bd){ if(bd==='4'){ if(!(p.bedrooms>=4)) return false; } else if(String(p.bedrooms)!==bd) return false; }
    if(p.area){ if(p.area<amin||p.area>amax) return false; } else if(amin>0) return false;
    if(p.price){ if(p.price<pmin||p.price>pmax) return false; } else if(pmin>0) return false;
    if(q && p.name.toLowerCase().indexOf(q)<0) return false;
    return true;
  });
  var s=$('fSort').value;
  view.sort(function(a,b){
    if(s==='area-asc') return (a.area||0)-(b.area||0);
    if(s==='area-desc') return (b.area||0)-(a.area||0);
    if(s==='price-asc') return (a.price||0)-(b.price||0);
    if(s==='price-desc') return (b.price||0)-(a.price||0);
    return 0;
  });
  shown=0; $('catGrid').innerHTML='';
  $('catCount').textContent='Найдено: '+view.length;
  $('catEmpty').hidden = view.length>0;
  var ac=activeCount(), b=$('fCountBadge'); b.hidden=ac===0; b.textContent=ac;
  $('applyCount').textContent='('+view.length+')';
  chipActive();
  render();
  autoFill();
}
function render(){
  var slice=view.slice(shown, shown+PER);
  $('catGrid').insertAdjacentHTML('beforeend', slice.map(card).join(''));
  shown+=slice.length;
  $('catMore').hidden = shown>=view.length;
}
// авто-подгрузка: докручиваем порции, пока «сенсор» в зоне видимости (+700px)
function autoFill(){
  if(shown>=view.length) return;
  var s=$('catSentinel'); if(!s) return;
  if(s.getBoundingClientRect().top < window.innerHeight + 700){ render(); requestAnimationFrame(autoFill); }
}
var FIELDS=['fGroup','fFloors','fBed','fSearch'];
function priceActive(){ return (+$('fPriceMin').value>0) || (+$('fPriceMax').value < +$('fPriceMax').max); }
function areaActive(){ return (+$('fAreaMin').value>0) || (+$('fAreaMax').value < +$('fAreaMax').max); }
function activeCount(){ var c=0; FIELDS.forEach(function(id){ if(($(id).value||'').trim()) c++; }); if(priceActive()) c++; if(areaActive()) c++; return c; }
FIELDS.concat(['fSort']).forEach(function(id){ $(id).addEventListener('input', apply); });
// Двойные ползунки (цена + площадь) — общий инициализатор
function initRange(loId, hiId, fillId, minId, maxId){
  var lo=$(loId), hi=$(hiId), fill=$(fillId);
  function pct(el){ return (el.value - el.min)/(el.max - el.min)*100; }
  function num(n){ return (''+(+n)).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' '); }
  function draw(){ var a=pct(lo), b=pct(hi); fill.style.left=a+'%'; fill.style.width=(b-a)+'%';
    $(minId).textContent=num(+lo.value); $(maxId).textContent=num(+hi.value)+(+hi.value>=+hi.max?'+':''); }
  lo.addEventListener('input', function(){ if(+lo.value > +hi.value - (+lo.step)) lo.value=+hi.value-(+lo.step); draw(); apply(); });
  hi.addEventListener('input', function(){ if(+hi.value < +lo.value + (+lo.step)) hi.value=+lo.value+(+lo.step); draw(); apply(); });
  draw();
  return { draw:draw, reset:function(){ lo.value=lo.min; hi.value=hi.max; draw(); } };
}
var priceR=initRange('fPriceMin','fPriceMax','priceFill','priceMinVal','priceMaxVal');
var areaR=initRange('fAreaMin','fAreaMax','areaFill','areaMinVal','areaMaxVal');
// быстрые чипсы (этажность / площадь)
function chipActive(){
  document.querySelectorAll('.chip').forEach(function(c){
    var k=c.getAttribute('data-k'), v=c.getAttribute('data-v'), on=false;
    if(k==='floors') on=$('fFloors').value===v;
    if(k==='area'){ var p=v.split('-'); on=$('fAreaMin').value===p[0] && $('fAreaMax').value===p[1]; }
    c.classList.toggle('chip--on', on);
  });
}
document.querySelectorAll('.chip').forEach(function(c){
  c.addEventListener('click', function(){
    var k=c.getAttribute('data-k'), v=c.getAttribute('data-v');
    if(k==='floors'){ $('fFloors').value = ($('fFloors').value===v ? '' : v); }
    if(k==='area'){ var p=v.split('-'), lo=$('fAreaMin'), hi=$('fAreaMax');
      if(lo.value===p[0] && hi.value===p[1]){ lo.value=lo.min; hi.value=hi.max; }
      else { lo.value=p[0]; hi.value=p[1]; }
      areaR.draw(); }
    apply();
  });
});
$('catMore').addEventListener('click', render);
// бесконечная подгрузка вместо кнопки (если поддерживается)
(function(){ var s=$('catSentinel'), more=$('catMore');
  if(!s || !('IntersectionObserver' in window)) return;
  if(more) more.style.display='none';
  new IntersectionObserver(function(es){ if(es[0].isIntersecting) autoFill(); }, {rootMargin:'700px 0px'}).observe(s);
})();
$('catReset').addEventListener('click', function(){
  FIELDS.forEach(function(id){$(id).value='';}); $('fSort').value='area-asc'; priceR.reset(); areaR.reset(); apply();
});
// Фильтры: панель выезжает сбоку по ТАПУ; edge-tab появляется при прокрутке вниз
var fab=$('filterFab'), toolbarVisible=true, fabTimer=null;
function updateFab(){
  if(!fab) return;
  var show = !toolbarVisible && !$('filtersPanel').classList.contains('open');
  if(show && !fab.classList.contains('show')){
    fab.classList.add('show'); fab.classList.remove('mini');
    clearTimeout(fabTimer); fabTimer=setTimeout(function(){ fab.classList.add('mini'); }, 2600);
  } else if(!show && fab.classList.contains('show')){
    fab.classList.remove('show','mini'); clearTimeout(fabTimer);
  }
}
function openF(){ $('filtersPanel').classList.add('open'); $('filtersBackdrop').classList.add('open'); $('filtersToggle').classList.add('is-open'); document.body.classList.add('no-scroll'); updateFab(); }
function closeF(){ $('filtersPanel').classList.remove('open'); $('filtersBackdrop').classList.remove('open'); $('filtersToggle').classList.remove('is-open'); document.body.classList.remove('no-scroll'); updateFab(); }
$('filtersToggle').addEventListener('click', openF);
var fc=$('filtersClose'); if(fc) fc.addEventListener('click', closeF);
$('filtersBackdrop').addEventListener('click', closeF);
$('filtersApply').addEventListener('click', closeF);
if(fab) fab.addEventListener('click', openF);
(function(){ var sx=null, p=$('filtersPanel');
  p.addEventListener('touchstart', function(e){
    if(e.target.closest('input, select, textarea, .range-slider')){ sx=null; return; }  // не закрывать при работе с ползунком/полями
    sx=e.touches[0].clientX;
  }, {passive:true});
  p.addEventListener('touchmove', function(e){ if(sx===null) return; if(e.touches[0].clientX-sx > 70){ closeF(); sx=null; } }, {passive:true});
  p.addEventListener('touchend', function(){ sx=null; });
})();
(function(){ var anchor=document.querySelector('.catalog-toolbar');
  if(!anchor || !('IntersectionObserver' in window)) return;
  new IntersectionObserver(function(es){ toolbarVisible=es[0].isIntersecting; updateFab(); }, {threshold:0}).observe(anchor);
})();
document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeF(); });
fetch('projects.json').then(function(r){return r.json()}).then(function(d){
  all=d;
  var pg=null; try{ pg=new URLSearchParams(location.search).get('group'); }catch(e){}
  if(pg){ $('fGroup').value=pg; apply(); return; }
  // Карточки уже отрисованы на сервере (SSR) — не перерисовываем, только синхронизируем
  // состояние счётчиков. Перестроение произойдёт при первом изменении фильтра/сортировки.
  view=all.slice().sort(function(a,b){return (a.area||0)-(b.area||0);});
  shown=view.length;
  $('catCount').textContent='Найдено: '+view.length;
  $('applyCount').textContent='('+view.length+')';
  $('catMore').hidden=true;
});
</script>
</body>
</html>"""
    for k, v in {"__BASE__": BASE_URL, "__SPRITE__": SPRITE, "__HEADER__": header(""),
                 "__FOOTER__": footer(""), "__OPTS__": opts, "__BOTTOM__": mobile_bar(""),
                 "__CARDS__": cards_html,
                 "__PRICEMAX__": str(price_max), "__PRICESTEP__": str(price_step),
                 "__AREAMAX__": str(area_max), "__AREASTEP__": str(area_step)}.items():
        tpl = tpl.replace(k, v)
    return tpl


def featured_cards(items, group="Проекты", n=6):
    pool = [p for p in items if p["group"] == group and p["price"] and p["img"]]
    pool.sort(key=lambda p: (p["area"] or 0))
    if not pool:
        return ""
    pick, step = [], max(1, len(pool) // n)
    for i in range(0, len(pool), step):
        pick.append(pool[i])
        if len(pick) >= n: break
    out = []
    for p in pick:
        meta = []
        if p["area"]: meta.append('<span>%d м²</span>' % int(p["area"]))
        if p["floors_txt"]: meta.append('<span>%s</span>' % esc(p["floors_txt"]))
        if p["bedrooms"]: meta.append('<span>%d сп.</span>' % p["bedrooms"])
        out.append(
            '      <article class="project">%s'
            '<div class="body"><div class="price">от %s</div><h3><a href="proekty/%s.html">%s</a></h3>'
            '<div class="meta">%s</div><a href="proekty/%s.html" class="btn btn--outline btn--block">Подробнее</a></div></article>'
            % (thumb_block(p, "proekty/" + p["slug"] + ".html"), fmt_price(p["price"]),
               p["slug"], esc(p["name"]), "".join(meta), p["slug"]))
    return "\n".join(out)


def update_index(items):
    html = open(INDEX, encoding="utf-8").read()
    feat = "<!-- FEATURED:START -->\n" + featured_cards(items, "Проекты", n=9) + "\n      <!-- FEATURED:END -->"
    html = re.sub(r"<!-- FEATURED:START -->.*?<!-- FEATURED:END -->", lambda m: feat, html, flags=re.S)
    built = "<!-- BUILT:START -->\n" + featured_cards(items, "Построенные объекты", n=9) + "\n      <!-- BUILT:END -->"
    html = re.sub(r"<!-- BUILT:START -->.*?<!-- BUILT:END -->", lambda m: built, html, flags=re.S)
    open(INDEX, "w", encoding="utf-8").write(html)


def write_sitemap(items):
    # Собираем карту сайта со ВСЕХ .html на диске (корневые SEO-лендинги по городам,
    # блог, страницы проектов и служебные), чтобы не потерять страницы, которые
    # генерируются другими скиллами. index.html отдаём как корень "/".
    skip = {"404.html"}
    rels = set()
    for root, _dirs, files in os.walk(SITE):
        rel_dir = os.path.relpath(root, SITE)
        if rel_dir.split(os.sep)[0] in ("assets", "css", "js"):
            continue
        for f in files:
            if not f.endswith(".html") or f in skip:
                continue
            # не включаем внутренние/закрытые страницы (noindex)
            try:
                head = open(os.path.join(root, f), encoding="utf-8").read(4000)
            except Exception:
                head = ""
            if "noindex" in head.lower():
                continue
            rels.add(f if rel_dir == "." else rel_dir.replace(os.sep, "/") + "/" + f)
    urls = []
    for rel in sorted(rels):
        urls.append(BASE_URL + "/" if rel == "index.html" else "%s/%s" % (BASE_URL, rel))
    body = "".join("  <url><loc>%s</loc></url>\n" % esc(u) for u in urls)
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n"
    open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % BASE_URL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=os.path.join(HERE, "source.csv"))
    args = ap.parse_args()
    if not os.path.exists(args.csv):
        sys.exit("CSV не найден: %s (укажите --csv путь)" % args.csv)

    items = parse_csv(args.csv)
    print("Прочитано проектов:", len(items))
    by = {}
    for p in items: by[p["group"]] = by.get(p["group"], 0) + 1
    print("По разделам:", by)

    os.makedirs(PROEKTY_DIR, exist_ok=True)
    # очистка старых страниц проектов
    for f in os.listdir(PROEKTY_DIR):
        if f.endswith(".html"):
            os.remove(os.path.join(PROEKTY_DIR, f))

    # группировка для навигации «пред/след» и «похожие» (внутри раздела, по площади)
    groups_map = {}
    for p in items:
        groups_map.setdefault(p["group"], []).append(p)
    for g in groups_map:
        groups_map[g].sort(key=lambda x: (x["area"] or 0, x["name"]))
    posmap = {p["slug"]: (g, i) for g, lst in groups_map.items() for i, p in enumerate(lst)}

    def neighbors(p):
        g, i = posmap[p["slug"]]; lst = groups_map[g]; n = len(lst)
        if n < 2:
            return None, None
        return lst[(i - 1) % n], lst[(i + 1) % n]

    def similar(p, k=6):
        g, _ = posmap[p["slug"]]
        # список группы, отсортированный по площади (None → 0)
        lst = sorted(groups_map[g], key=lambda x: (x["area"] or 0))
        n = len(lst)
        if n <= 1:
            return []
        idx = next(j for j, x in enumerate(lst) if x["slug"] == p["slug"])
        # берём соседей по площади симметрично вокруг проекта — у каждого свой набор
        out, step = [], 1
        while len(out) < k and step < n:
            for j in (idx - step, idx + step):
                if 0 <= j < n and lst[j]["slug"] != p["slug"] and lst[j] not in out:
                    out.append(lst[j])
                    if len(out) >= k:
                        break
            step += 1
        return out[:k]

    for p in items:
        prv, nxt = neighbors(p)
        open(os.path.join(PROEKTY_DIR, p["slug"] + ".html"), "w", encoding="utf-8").write(
            project_page(p, prv, nxt, similar(p)))

    # projects.json (лёгкий, для каталога)
    light = [{"slug": p["slug"], "name": p["name"], "price": p["price"], "img": p["img"],
              "img2": (p["images"][1] if len(p["images"]) > 1 and p["images"][1] else ""),
              "area": (int(p["area"]) if p["area"] and p["area"] == int(p["area"]) else p["area"]),
              "floors": p["floors"], "floors_txt": p["floors_txt"], "bedrooms": p["bedrooms"],
              "group": p["group"]} for p in items]
    json.dump(light, open(os.path.join(SITE, "projects.json"), "w", encoding="utf-8"), ensure_ascii=False)

    groups = sorted({p["group"] for p in items})
    maxp = max((p["price"] for p in items if p["price"]), default=0)
    price_max = int((maxp // 1_000_000 + 1) * 1_000_000) if maxp else 50_000_000
    maxa = max((p["area"] for p in items if p["area"]), default=0)
    area_max = int((maxa // 50 + 1) * 50) if maxa else 500
    open(os.path.join(SITE, "proekty.html"), "w", encoding="utf-8").write(catalog_page(groups, price_max, area_max, items=items))
    update_index(items)
    write_sitemap(items)

    print("\n✓ Готово:")
    print("  • %d страниц проектов в site/proekty/" % len(items))
    print("  • site/proekty.html (каталог с фильтрами)")
    print("  • site/projects.json, sitemap.xml, robots.txt")
    print("  • избранные проекты встроены в index.html")


if __name__ == "__main__":
    main()
