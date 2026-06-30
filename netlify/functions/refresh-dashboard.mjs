// Запланированная функция Netlify: по расписанию дёргает build hook → пересборка
// сайта → скрипт netlify/refresh-dashboard.sh обновляет dashboard-data.json.
// URL build hook берётся из env NETLIFY_BUILD_HOOK_URL (создаётся в Netlify UI).
export default async () => {
  const hook = process.env.NETLIFY_BUILD_HOOK_URL;
  if (!hook) {
    console.log("NETLIFY_BUILD_HOOK_URL не задан — нечего триггерить");
    return new Response("no hook configured", { status: 200 });
  }
  try {
    const r = await fetch(hook, { method: "POST" });
    console.log("Build hook вызван, статус:", r.status);
    return new Response("build triggered", { status: 200 });
  } catch (e) {
    console.log("Ошибка вызова build hook:", String(e));
    return new Response("error", { status: 500 });
  }
};

// Расписание (UTC). Каждые 6 часов: 00:00, 06:00, 12:00, 18:00 UTC.
export const config = { schedule: "0 */6 * * *" };
