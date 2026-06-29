#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-генерация уникальных SEO-описаний для страниц проектов HotWell.kz.

Берёт характеристики каждого проекта из выгрузки WooCommerce (через parse_csv
из import.py), просит OpenAI написать уникальное описание на 150–220 слов и
складывает результат в ai-descriptions.json рядом со скриптом:

    {"<slug>": {"desc": "<p>…</p><p>…</p>", "hash": "...", "model": "..."}}

import.py при следующем запуске подхватывает эти тексты вместо детерминированных.

Запуск (обычно из GitHub Action):
    OPENAI_API_KEY=... python3 gen_descriptions.py            # все проекты
    OPENAI_API_KEY=... python3 gen_descriptions.py --limit 10 # пилот на 10
    OPENAI_API_KEY=... python3 gen_descriptions.py --force     # перегенерировать всё

Инкрементально: проект пропускается, если он уже есть в кэше с тем же хешем
характеристик (повторный запуск ничего не стоит). --force игнорирует кэш.
"""
import os, sys, json, time, hashlib, argparse, importlib.util
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "ai-descriptions.json")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def load_import_module():
    """Загружает соседний import.py как модуль (имя 'import' — ключевое слово)."""
    spec = importlib.util.spec_from_file_location("hw_import", os.path.join(HERE, "import.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def facts_of(p, imp):
    """Достоверные характеристики проекта для промпта (без выдумок)."""
    f = {"Название": p["name"], "Назначение": imp.project_kind(p), "Раздел": p.get("group")}
    a = imp._area_int(p.get("area"))
    if a:
        f["Площадь, м²"] = a
    if p.get("floors_txt"):
        f["Этажность"] = p["floors_txt"].rstrip(". ")
    if p.get("bedrooms"):
        f["Спальни"] = p["bedrooms"]
    if p.get("dims"):
        f["Габариты, м"] = p["dims"].rstrip(". ")
    if p.get("height"):
        f["Высота этажей"] = p["height"].rstrip(". ")
    if p.get("price"):
        f["Цена"] = "от %s" % imp.fmt_price(p["price"])
    return f


SYSTEM = (
    "Ты — копирайтер строительной компании HotWell.kz (Казахстан), которая строит "
    "дома, бани и коммерческие объекты из СИП-панелей. Пишешь уникальные продающие "
    "SEO-описания для карточек проектов на русском языке."
)

PROMPT_TPL = """Напиши уникальное описание проекта для его страницы на сайте.

Характеристики проекта (используй ТОЛЬКО их, ничего не выдумывай — не указывай
количество комнат, год, город или материалы, которых нет в данных):
{facts}

Факты о технологии и условиях HotWell.kz (можно использовать):
- Стены из СИП-панелей 158 мм (OSB-3 + пенополистирол ПСБ-С-20Ф): тёплый контур
  без мостиков холода, экономия на отоплении, комфорт в климате Казахстана.
- В стоимость входят: свайно-ленточный фундамент, индивидуальный проект,
  рабочее проектирование, 3D-визуализация, кровля из металлочерепицы, доставка
  домокомплекта и монтаж штатными бригадами. Гарантия 1 год.
- Сборка домокомплекта — около 30 дней. Строим по всему Казахстану.

Требования к тексту:
- Объём 150–220 слов, ровно два абзаца.
- Естественно вплети характеристики проекта (площадь, этажность и т.п.).
- Без воды, без преувеличений, без выдуманных деталей.
- Заверши мягким призывом рассчитать стоимость онлайн / написать в WhatsApp.
- Не повторяй заголовок дословно в начале каждого предложения.
- Верни ТОЛЬКО HTML: два абзаца вида <p>...</p><p>...</p>. Без markdown,
  без заголовков, без обратных кавычек."""


def hash_facts(facts, model):
    raw = json.dumps(facts, ensure_ascii=False, sort_keys=True) + "|" + model
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def clean_html(s):
    s = (s or "").strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lstrip().lower().startswith("html"):
            s = s.lstrip()[4:]
    s = s.strip()
    # схлопываем возможные переводы строк между абзацами
    s = s.replace("\n", " ").replace("  ", " ")
    if "<p>" not in s:
        s = "<p>%s</p>" % s
    return s.strip()


def call_openai(facts, model, key, temperature, retries=4):
    payload = {
        "model": model, "temperature": temperature,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": PROMPT_TPL.format(
                facts=json.dumps(facts, ensure_ascii=False, indent=2))},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(OPENAI_URL, data=data, headers={
                "Authorization": "Bearer " + key, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.load(r)
            return clean_html(body["choices"][0]["message"]["content"]), body.get("usage", {})
        except urllib.error.HTTPError as e:
            last = "HTTP %s: %s" % (e.code, e.read().decode()[:200])
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            break
        except Exception as e:  # noqa
            last = "%s: %s" % (type(e).__name__, e)
            time.sleep(2 ** attempt)
    raise RuntimeError("OpenAI call failed: %s" % last)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=os.path.join(HERE, "source.csv"))
    ap.add_argument("--model", default=os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o-mini"))
    ap.add_argument("--limit", type=int, default=0, help="обработать только N проектов (пилот)")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--force", action="store_true", help="игнорировать кэш и перегенерировать")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("ОШИБКА: не задан OPENAI_API_KEY")
    if not os.path.exists(args.csv):
        sys.exit("CSV не найден: %s" % args.csv)

    imp = load_import_module()
    items = imp.parse_csv(args.csv)
    print("Проектов в выгрузке: %d | модель: %s" % (len(items), args.model))

    cache = {}
    if os.path.exists(CACHE) and not args.force:
        try:
            cache = json.load(open(CACHE, encoding="utf-8")) or {}
        except Exception:
            cache = {}

    done = skipped = failed = 0
    in_tok = out_tok = 0
    processed = 0
    for p in items:
        if args.limit and processed >= args.limit:
            break
        slug = p["slug"]
        facts = facts_of(p, imp)
        h = hash_facts(facts, args.model)
        if not args.force and cache.get(slug, {}).get("hash") == h:
            skipped += 1
            continue
        processed += 1
        try:
            desc, usage = call_openai(facts, args.model, key, args.temperature)
            cache[slug] = {"desc": desc, "hash": h, "model": args.model}
            in_tok += usage.get("prompt_tokens", 0)
            out_tok += usage.get("completion_tokens", 0)
            done += 1
            print("✓ %s (%d слов)" % (slug, len(imp.re.sub(r'<[^>]+>', ' ', desc).split())))
            # периодически сохраняем, чтобы не потерять прогресс при сбое
            if done % 20 == 0:
                json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception as e:  # noqa
            failed += 1
            print("✗ %s — %s" % (slug, e))

    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nИтог: сгенерировано %d, пропущено (кэш) %d, ошибок %d" % (done, skipped, failed))
    print("Токены: prompt=%d, completion=%d" % (in_tok, out_tok))
    print("Кэш: %s (всего записей: %d)" % (CACHE, len(cache)))


if __name__ == "__main__":
    main()
