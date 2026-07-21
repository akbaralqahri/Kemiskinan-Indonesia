import { chromium } from "playwright";

const url = process.argv[2];
if (!url) throw new Error("Usage: node diagnose_bps.mjs <url>");

const browser = await chromium.launch({
  headless: true,
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
});
const page = await browser.newPage({
  locale: "id-ID",
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
});

const interesting = [];
page.on("response", (response) => {
  const responseUrl = response.url();
  if (/api|json|statistic|table|web-api/i.test(responseUrl)) {
    interesting.push({ status: response.status(), url: responseUrl });
  }
});

const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 90_000 });
await page.waitForTimeout(8_000);
console.log(JSON.stringify({
  navigationStatus: response?.status(),
  finalUrl: page.url(),
  title: await page.title(),
  tables: await page.locator("table").count(),
  rows: await page.locator("table tbody tr").count(),
  interesting,
}, null, 2));

const firstRows = await page.locator("table tbody tr").evaluateAll((rows) =>
  rows.slice(0, 3).map((row) =>
    [...row.querySelectorAll("th,td")].map((cell) => cell.textContent?.trim() ?? ""),
  ),
);
console.log(JSON.stringify({ firstRows }, null, 2));

await browser.close();
