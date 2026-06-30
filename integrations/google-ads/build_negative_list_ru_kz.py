#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Локализованный Shared Negative Keyword List «Универсальные минус-слова RU+KZ v1»
— русско-казахский аналог universal-negative-keywords.md (секции A.1–A.7),
адаптированный под строительную нишу Казахстана.

Принцип: высокая точность, НЕ блокируем покупательские сигналы.
Намеренно НЕ добавлены: цена, стоимость, недорого, доступный, заказать, купить,
рядом, лучший, под ключ, проект, отзывы, а также голое «работа/работы»/«жұмыс»
(в стройке = «строительные работы», «құрылыс жұмыстары» — это покупатели).

Match type: BROAD для всех (нет терминов в кавычках/скобках). Парсер поддержит
"phrase" и [exact], если появятся.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "23991449173")
camp_rn = "customers/%s/campaigns/%s" % (CID, CAMPAIGN_ID)
LIST_NAME = "Универсальные минус-слова RU+KZ v1"

# ===================== РУССКИЙ =====================
# A.1 Поиск работы / найм (без голого «работа/работы» — это и стройработы)
RU_JOB = ["вакансия", "вакансии", "вакансий", "резюме", "зарплата", "зарплату", "оклад",
          "подработка", "вахта", "вахтовик", "вахтовый", "трудоустройство", "грузчик",
          "разнорабочий", "ищу работу", "нужна работа", "требуется монтажник",
          "требуется рабочий", "hh"]
# A.2 DIY / как сделать / самостоятельно
RU_DIY = ["своими руками", "самостоятельно", "как построить", "как сделать", "как собрать",
          "как смонтировать", "как утеплить", "чертёж", "чертежи", "инструкция",
          "мастер класс", "видео", "видеоурок", "ютуб", "youtube"]
# A.3 Обучение / курсы / учёба
RU_EDU = ["курсы", "курс", "обучение", "колледж", "университет", "техникум", "диплом",
          "как стать", "реферат", "курсовая", "доклад"]
# A.4 Бесплатно / скачать
RU_FREE = ["бесплатно", "бесплатный", "скачать", "торрент", "даром", "халява"]
# A.5 Информационные / определения
RU_INFO = ["что такое", "что это", "определение", "значение", "википедия", "вики",
           "форум", "форумы"]
# A.6 Поддержка / существующие клиенты
RU_SUPPORT = ["рекламация", "претензия", "жалоба", "вернуть деньги", "личный кабинет"]
# A.7 Запрещённое / мусор
RU_RESTRICTED = ["казино", "ставки", "букмекер", "крипта", "криптовалюта", "биткоин",
                 "порно", "секс", "наркотики"]

# ===================== ҚАЗАҚША =====================
KZ_JOB = ["бос орын", "жалақы", "түйіндеме", "жұмыс іздеймін", "жұмысшы керек"]
KZ_DIY = ["өз қолыммен", "қалай салу", "қалай жасау", "сызба", "нұсқаулық"]
KZ_EDU = ["оқыту", "оқу курсы", "колледж", "университет", "диплом"]
KZ_FREE = ["тегін", "жүктеу"]
KZ_INFO = ["деген не", "википедия", "форум", "реферат"]
KZ_RESTRICTED = ["казино", "бәс тігу", "крипто"]

SECTIONS = (RU_JOB + RU_DIY + RU_EDU + RU_FREE + RU_INFO + RU_SUPPORT + RU_RESTRICTED +
            KZ_JOB + KZ_DIY + KZ_EDU + KZ_FREE + KZ_INFO + KZ_RESTRICTED)


def parse_term(t):
    t = t.strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        return t[1:-1].strip(), "PHRASE"
    if len(t) >= 2 and t[0] == '[' and t[-1] == ']':
        return t[1:-1].strip(), "EXACT"
    return t, "BROAD"


seen = set()
TERMS = []
for raw in SECTIONS:
    text, mt = parse_term(raw)
    key = (text.lower(), mt)
    if key in seen:
        continue
    seen.add(key)
    TERMS.append((text, mt))

errs = [f"term too long/many words: {t!r}" for t, _ in TERMS if len(t) > 80 or len(t.split()) > 10]
if errs:
    sys.exit("Невалидные термины:\n  " + "\n  ".join(errs))

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)


def run():
    by_mt = {}
    for _, mt in TERMS:
        by_mt[mt] = by_mt.get(mt, 0) + 1
    print("Терминов после дедупа: %d  %s" % (len(TERMS), by_mt))

    ssvc = client.get_service("SharedSetService")
    sop = client.get_type("SharedSetOperation")
    sop.create.name = LIST_NAME
    sop.create.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
    ss_rn = ssvc.mutate_shared_sets(customer_id=CID, operations=[sop]).results[0].resource_name
    print(" ✓ Shared set:", ss_rn)

    scsvc = client.get_service("SharedCriterionService")
    ops = []
    for text, mt in TERMS:
        op = client.get_type("SharedCriterionOperation")
        op.create.shared_set = ss_rn
        op.create.keyword.text = text
        op.create.keyword.match_type = client.enums.KeywordMatchTypeEnum[mt]
        ops.append(op)
    added = 0
    for i in range(0, len(ops), 1000):
        res = scsvc.mutate_shared_criteria(customer_id=CID, operations=ops[i:i + 1000])
        added += len(res.results)
    print(" ✓ Добавлено минус-слов: %d" % added)

    cssvc = client.get_service("CampaignSharedSetService")
    cop = client.get_type("CampaignSharedSetOperation")
    cop.create.campaign = camp_rn
    cop.create.shared_set = ss_rn
    cssvc.mutate_campaign_shared_sets(customer_id=CID, operations=[cop])
    print(" ✓ Список прикреплён к кампании", CAMPAIGN_ID)
    print("\n Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % CAMPAIGN_ID)


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
