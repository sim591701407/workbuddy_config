/**
 * cdp_driver.js —— 极简 Chrome DevTools Protocol 驱动（零第三方依赖）
 *
 * 依赖：Node 18+（内置 fetch / WebSocket）。不需要 puppeteer / playwright / ws。
 *
 * 用法：
 *   const CdpDriver = require("./cdp_driver.js");
 *   const cdp = await CdpDriver.connect(9333);        // 端口与 --remote-debugging-port 一致
 *   cdp.onException(e => console.error(e));
 *   await cdp.navigate("http://localhost:8766/");
 *   const v = await cdp.eval("document.title");
 *   await cdp.screenshot("out.png");
 *   await cdp.close();
 *
 * 起浏览器（在调用本脚本之前）：
 *   chrome --headless=new --disable-gpu --no-first-run --no-default-browser-check \
 *          --remote-debugging-port=9333 --user-data-dir="<独立临时目录>" about:blank
 */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getPageTarget(port, tries = 40) {
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/list`);
      const list = await res.json();
      const page = list.find((t) => t.type === "page" && t.webSocketDebuggerUrl);
      if (page) return page;
    } catch (e) {
      /* 浏览器还没起来，继续等 */
    }
    await sleep(300);
  }
  throw new Error(
    `CDP :${port} 未就绪。确认 Chrome 已用 --remote-debugging-port=${port} 启动，` +
    `且未被已有实例复用（需独立的 --user-data-dir）。`
  );
}

class CdpDriver {
  constructor(ws) {
    this.ws = ws;
    this._id = 0;
    this._pending = new Map();
    this._exceptionHandlers = [];
  }

  static async connect(port = 9333) {
    const target = await getPageTarget(port);
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((res, rej) => {
      ws.onopen = res;
      ws.onerror = () => rej(new Error("CDP WebSocket 连接失败"));
    });
    const d = new CdpDriver(ws);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && d._pending.has(m.id)) {
        const { res, rej } = d._pending.get(m.id);
        d._pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
        return;
      }
      if (m.method === "Runtime.exceptionThrown") {
        const ex = m.params.exceptionDetails || {};
        const desc = (ex.exception && ex.exception.description) || ex.text || "";
        d._exceptionHandlers.forEach((h) => h(desc));
      }
    };
    await d.send("Runtime.enable");
    await d.send("Page.enable");
    return d;
  }

  send(method, params = {}, timeoutMs = 120000) {
    const id = ++this._id;
    return new Promise((res, rej) => {
      this._pending.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this._pending.has(id)) {
          this._pending.delete(id);
          rej(new Error("CDP 超时: " + method));
        }
      }, timeoutMs);
    });
  }

  /** 在页面里求值。注意：页面顶层 let/const 不挂 window，表达式里请用裸标识符。 */
  async eval(expression, awaitPromise = true) {
    const r = await this.send("Runtime.evaluate", {
      expression, awaitPromise, returnByValue: true,
    });
    if (r.exceptionDetails) {
      const ex = r.exceptionDetails;
      throw new Error("页面 JS 异常: " + ((ex.exception && ex.exception.description) || ex.text));
    }
    return r.result.value;
  }

  /** 轮询断言，避免死等。fn 返回真值即结束。 */
  async waitFor(expression, { tries = 60, intervalMs = 300 } = {}) {
    for (let i = 0; i < tries; i++) {
      const v = await this.eval(expression);
      if (v) return v;
      await sleep(intervalMs);
    }
    return null;
  }

  onException(handler) { this._exceptionHandlers.push(handler); }

  async navigate(url) {
    await this.send("Page.navigate", { url });
    await sleep(800);
  }

  async screenshot(filePath, { fullPage = true } = {}) {
    const shot = await this.send("Page.captureScreenshot", {
      format: "png", captureBeyondViewport: fullPage,
    });
    require("fs").writeFileSync(filePath, Buffer.from(shot.data, "base64"));
    return filePath;
  }

  async close() {
    try { this.ws.close(); } catch (e) { /* ignore */ }
  }
}

module.exports = CdpDriver;
module.exports.sleep = sleep;
