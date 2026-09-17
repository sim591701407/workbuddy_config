/**
 * verify_example_ecg_app.js —— 实战范例：验收「心电分析工具」的时间段切分功能
 *
 * 这是 cdp-web-app-verify 技能的参考实现：把真实心电文件塞进页面、调用页面自己的
 * handleFile() 走完整流程，再逐项断言 DOM —— 包括当时那个「时段栏永不显示」的 bug。
 *
 * 环境变量：
 *   CDP_PORT   调试端口（默认 9333）
 *   APP_URL    被测页面（默认 http://localhost:8766/）
 *   ECG_FILE   用作输入的 txt/csv 心电文件（绝对路径）
 *   OUT_JSON   结果写出路径
 *   SHOT_PATH  截图写出路径
 *
 * 运行（在 Git Bash 里给 node 传 Windows 风格路径，否则会被解析成 c:\c\...）：
 *   CDP_PORT=9333 APP_URL=... ECG_FILE='C:\...\x.txt' OUT_JSON='C:\...\out.json' \
 *   SHOT_PATH='C:\...\shot.png' node verify_example_ecg_app.js
 */
const fs = require("fs");
const CdpDriver = require("./cdp_driver.js");

const CDP_PORT = process.env.CDP_PORT || "9333";
const APP_URL = process.env.APP_URL || "http://localhost:8766/";
const ECG_FILE = process.env.ECG_FILE;
const OUT_JSON = process.env.OUT_JSON || "verify_out.json";
const SHOT_PATH = process.env.SHOT_PATH || "verify_shot.png";

(async () => {
  const out = {};
  const cdp = await CdpDriver.connect(CDP_PORT);
  const pageErrors = [];
  cdp.onException((e) => pageErrors.push(e));

  await cdp.navigate(APP_URL);
  out.title = await cdp.eval("document.title");
  // 上传前：容器应当还是 hidden
  out.barBeforeHidden = await cdp.eval("document.querySelector('#ecg-range-bar').hidden");

  // 把文件内容注入页面，再在页面里构造 File 调应用入口 —— 不要碰原生文件选择框
  const b64 = fs.readFileSync(ECG_FILE).toString("base64");
  await cdp.eval(`(() => { window.__b64 = ${JSON.stringify(b64)}; return true; })()`);
  await cdp.eval(`(async () => {
    const bin = atob(window.__b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    await handleFile(new File([arr], "verify_ecg.txt", { type: "text/plain" }));
    return true;
  })()`);

  // 注意：页面顶层 let 不挂 window，这里必须用裸标识符 fullAnalysis
  await cdp.waitFor(
    "!document.querySelector('#result-area').hidden && typeof fullAnalysis !== 'undefined' && !!fullAnalysis"
  );

  // 核心断言：时段栏真的可见了吗（computed style + offsetHeight 双保险）
  out.rangeBar = await cdp.eval(`(() => {
    const bar = document.querySelector('#ecg-range-bar');
    const cs = getComputedStyle(bar);
    return {
      hidden: bar.hidden,
      display: cs.display,
      visible: cs.display !== 'none' && bar.offsetHeight > 0,
      height: bar.offsetHeight,
      chipLabels: [...bar.querySelectorAll('.ecg-range-chip')].map(c => c.textContent),
    };
  })()`);

  out.fullDurMin = await cdp.eval("fullAnalysis.durationMin");
  out.fullRCount = await cdp.eval("fullAnalysis.rCount");

  // 分支 1：快捷片
  out.quickChip = await cdp.eval(`(async () => {
    const chip = [...document.querySelectorAll('.ecg-range-chip')].find(c => c.textContent.includes('前5分钟'));
    if (!chip) return { error: 'chip not found' };
    chip.click();
    for (let i = 0; i < 60; i++) {
      if (typeof rangeActive !== 'undefined' && rangeActive) break;
      await new Promise(r => setTimeout(r, 300));
    }
    return {
      sliceStartSec: currentAnalysis.sliceStartSec,
      sliceEndSec: currentAnalysis.sliceEndSec,
      rCount: currentAnalysis.rCount,
      summaryHasTag: document.querySelector('#ecg-summary').textContent.includes('⏱ 当前时段'),
      activeChipCount: document.querySelectorAll('.ecg-range-chip.active').length,
    };
  })()`);

  // 分支 2：自定义输入（覆盖 分:秒 解析）
  out.customRange = await cdp.eval(`(async () => {
    document.querySelector('#ecg-range-start').value = '10:00';
    document.querySelector('#ecg-range-end').value = '15:00';
    document.querySelector('#btn-ecg-range-apply').click();
    for (let i = 0; i < 60; i++) {
      const a = (typeof rangeActive !== 'undefined') ? rangeActive : null;
      if (a && Math.abs(a.start - 600) < 0.5) break;
      await new Promise(r => setTimeout(r, 300));
    }
    return { rangeActive, durMin: currentAnalysis.durationMin, rCount: currentAnalysis.rCount };
  })()`);

  // 分支 3：解析器三种格式
  out.parseDurInput = await cdp.eval(
    `({ '2:30': parseDurInput('2:30'), '2分30秒': parseDurInput('2分30秒'), '150': parseDurInput('150') })`
  );

  // 分支 4：重置
  out.resetRange = await cdp.eval(`(async () => {
    document.querySelector('#btn-ecg-range-reset').click();
    await new Promise(r => setTimeout(r, 500));
    return {
      rangeActive: (typeof rangeActive !== 'undefined') ? rangeActive : 'undefined',
      durMin: currentAnalysis.durationMin,
      resetHidden: document.querySelector('#btn-ecg-range-reset').hidden,
    };
  })()`);

  // 曲线渲染
  out.chart = await cdp.eval(`(async () => {
    document.querySelector('#btn-ecg-curve-toggle').click();
    await new Promise(r => setTimeout(r, 600));
    const cv = document.querySelector('#ecg-canvas');
    return { canvasHidden: cv.hidden, w: cv.width, h: cv.height };
  })()`);

  await cdp.screenshot(SHOT_PATH);
  out.screenshot = SHOT_PATH;
  out.pageErrors = pageErrors;

  fs.writeFileSync(OUT_JSON, JSON.stringify(out, null, 2), "utf8");
  await cdp.close();

  // 关键断言失败必须退出码非 0，否则 CI/后续步骤会误判成功
  const problems = [];
  if (!out.rangeBar.visible) problems.push('时段选择栏不可见');
  if (!out.rangeBar.chipLabels || out.rangeBar.chipLabels.length < 2) problems.push('快捷片缺失');
  if (out.pageErrors.length) problems.push('页面有 JS 异常');
  if (problems.length) {
    console.error("VERIFY_FAILED: " + problems.join("; "));
    process.exit(1);
  }
  console.log("VERIFY_DONE");
  process.exit(0);
})().catch((e) => {
  fs.writeFileSync(OUT_JSON, JSON.stringify({ fatal: String((e && e.stack) || e) }, null, 2), "utf8");
  console.error("VERIFY_FAILED: " + e);
  process.exit(1);
});
