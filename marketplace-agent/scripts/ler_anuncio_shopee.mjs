// Le um anuncio publico da Shopee com Chrome headless (CDP) e extrai dados.
// Uso: node scripts/ler_anuncio_shopee.mjs <shopId> <itemId> [saida.json]
// Nao usa login. Se a Shopee mostrar captcha, o resultado vem vazio.
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const shopId = process.argv[2];
const itemId = process.argv[3];
const saida = process.argv[4] || null;
const PORTA = 9333;
const PERFIL = `/tmp/shopee-cdp-${Date.now()}`;

const chrome = spawn(
  "/usr/bin/google-chrome",
  [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--hide-scrollbars",
    "--window-size=1400,950",
    "--lang=pt-BR",
    "--accept-lang=pt-BR",
    `--remote-debugging-port=${PORTA}`,
    `--user-data-dir=${PERFIL}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

async function alvo() {
  for (let i = 0; i < 50; i++) {
    try {
      const resposta = await fetch(`http://127.0.0.1:${PORTA}/json/list`);
      const lista = await resposta.json();
      const pagina = lista.find((t) => t.type === "page");
      if (pagina?.webSocketDebuggerUrl) return pagina.webSocketDebuggerUrl;
    } catch {}
    await dormir(200);
  }
  throw new Error("nao consegui conectar no Chrome headless");
}

const urlWs = await alvo();
const ws = new WebSocket(urlWs);
await new Promise((ok, erro) => {
  ws.onopen = ok;
  ws.onerror = erro;
});

let contador = 0;
const pendentes = new Map();
ws.onmessage = (evento) => {
  const msg = JSON.parse(evento.data);
  if (msg.id && pendentes.has(msg.id)) {
    pendentes.get(msg.id)(msg);
    pendentes.delete(msg.id);
  }
};

function enviar(method, params = {}) {
  return new Promise((ok) => {
    const id = ++contador;
    pendentes.set(id, ok);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function avaliar(expression, awaitPromise = false) {
  const r = await enviar("Runtime.evaluate", {
    expression,
    awaitPromise,
    returnByValue: true,
  });
  return r.result?.result?.value;
}

try {
  await enviar("Page.enable");
  await enviar("Runtime.enable");
  const url = `https://shopee.com.br/product/${shopId}/${itemId}/`;
  await enviar("Page.navigate", { url });
  await dormir(6000);
  // fecha o modal de idioma (se aparecer)
  await avaliar(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => /Portugu/i.test(x.innerText || ''));
    if (b) { b.click(); return 'clicou'; }
    return 'sem modal';
  })()`);
  await dormir(5000);

  const dados = await avaliar(`JSON.stringify({
    url: location.href,
    title: document.title,
    imagens: [...new Set([...document.querySelectorAll('img')]
      .map(i => i.src || '')
      .filter(s => s.includes('susercontent')))],
    og: (document.querySelector('meta[property="og:image"]') || {}).content || null,
    texto: (document.body.innerText || '').slice(0, 1200)
  })`);
  const api = await avaliar(
    `fetch('/api/v4/item/get?itemid=${itemId}&shopid=${shopId}', {credentials:'include'})
       .then(r => r.text()).then(t => t.slice(0, 3000)).catch(e => 'erro: ' + e)`,
    true,
  );

  const saidaDados = { shopId, itemId, dados: JSON.parse(dados || "{}"), api: api || null };
  const texto = JSON.stringify(saidaDados, null, 2);
  if (saida) writeFileSync(saida, texto);
  console.log(texto);
} finally {
  ws.close();
  chrome.kill("SIGKILL");
}
