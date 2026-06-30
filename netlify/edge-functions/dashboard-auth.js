// Пароль на /dashboard (и его данные). Работает на любом тарифе Netlify.
// Логин — любой, пароль — 123. Браузер сам покажет окно ввода (HTTP Basic Auth).
export default async (request, context) => {
  const PASSWORD = "123";
  const auth = request.headers.get("authorization") || "";
  let ok = false;
  if (auth.startsWith("Basic ")) {
    try {
      const decoded = atob(auth.slice(6));          // "user:pass"
      const pass = decoded.slice(decoded.indexOf(":") + 1);
      ok = pass === PASSWORD;
    } catch (_) { ok = false; }
  }
  if (!ok) {
    return new Response("Требуется пароль", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="HotWell Dashboard", charset="UTF-8"',
        "Cache-Control": "no-store",
      },
    });
  }
  return context.next();
};

export const config = {
  path: ["/dashboard", "/dashboard/", "/dashboard/*", "/dashboard-data.json"],
};
