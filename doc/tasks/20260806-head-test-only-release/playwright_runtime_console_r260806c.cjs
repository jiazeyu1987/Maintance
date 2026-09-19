const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const taskDir = 'D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260806-head-test-only-release';
const outDir = 'D:/ProjectPackage/Int/IntRuoyiMaintance/output/playwright/r260806c-release';
fs.mkdirSync(outDir, { recursive: true });
const req = createRequire('D:/IntRuoyiWorktree/r260806c-release-app/IntRuoyiFronted/package.json');
const { chromium } = req('playwright');
const releaseTag = 'release-20260806-intmain-head-test-r260806c-r1';
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

async function collectPage(page, url, screenshotName) {
  const consoleErrors = [];
  const failedRequests = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('requestfailed', (req) => failedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText || ''}`));
  const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);
  const title = await page.title();
  const bodyText = (await page.locator('body').innerText({ timeout: 10000 }).catch(() => '')).slice(0, 20000);
  const screenshotPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  return {
    url,
    status: response ? response.status() : null,
    finalUrl: page.url(),
    title,
    bodyTextSample: bodyText.slice(0, 2000),
    consoleErrors,
    failedRequests,
    screenshotPath,
  };
}

async function clickFirstVisible(page, labels) {
  for (const label of labels) {
    const locator = page.getByText(label, { exact: false }).first();
    if (await locator.isVisible({ timeout: 1500 }).catch(() => false)) {
      await locator.click({ timeout: 5000 });
      await page.waitForTimeout(1500);
      return label;
    }
  }
  return null;
}

(async () => {
  const browser = await chromium.launch({ executablePath: chrome, headless: true });
  const frontendPage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const frontend = await collectPage(frontendPage, 'http://172.30.30.58:8081/', 'test-frontend-r260806c.png');

  const consolePage = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
  const runtimeInitial = await collectPage(consolePage, 'http://127.0.0.1:48181/', 'runtime-console-initial-r260806c.png');
  const clicked = await clickFirstVisible(consolePage, ['查看变更', '版本变更', '变更说明', releaseTag]);
  const runtimeText = await consolePage.locator('body').innerText({ timeout: 10000 }).catch(() => '');
  const runtimeDialogScreenshot = path.join(outDir, 'runtime-console-release-info-r260806c.png');
  await consolePage.screenshot({ path: runtimeDialogScreenshot, fullPage: true });
  const runtimeConsoleErrors = [];
  const runtimeFailedRequests = [];
  // Re-open a clean observer page for console/request counts around the runtime screen.
  const observer = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
  observer.on('console', (msg) => { if (msg.type() === 'error') runtimeConsoleErrors.push(msg.text()); });
  observer.on('requestfailed', (req) => runtimeFailedRequests.push(`${req.method()} ${req.url()} ${req.failure()?.errorText || ''}`));
  const observerResp = await observer.goto('http://127.0.0.1:48181/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await observer.waitForTimeout(3000);
  await browser.close();

  const combinedRuntimeText = `${runtimeInitial.bodyTextSample}\n${runtimeText}`;
  const checks = {
    frontendHttp200: frontend.status === 200,
    frontendTitlePresent: Boolean(frontend.title),
    frontendConsoleErrorsZero: frontend.consoleErrors.length === 0,
    frontendFailedRequestsZero: frontend.failedRequests.length === 0,
    runtimeHttp200: runtimeInitial.status === 200 && observerResp && observerResp.status() === 200,
    runtimeReleaseTagVisible: combinedRuntimeText.includes(releaseTag),
    runtimePackageVisible: combinedRuntimeText.includes('发布包') && combinedRuntimeText.includes(releaseTag),
    runtimeComponentVisible: combinedRuntimeText.includes('组件范围') && combinedRuntimeText.includes('intruoyi'),
    runtimeChangeNotesVisible: combinedRuntimeText.includes('发布包：') && combinedRuntimeText.includes('组件范围：intruoyi'),
    runtimeConsoleErrorsZero: runtimeConsoleErrors.length === 0,
    runtimeFailedRequestsZero: runtimeFailedRequests.length === 0,
  };
  const result = {
    status: Object.values(checks).every(Boolean) ? 'passed' : 'failed',
    releaseTag,
    chrome,
    clicked,
    checks,
    frontend,
    runtime: {
      initial: runtimeInitial,
      observerStatus: observerResp ? observerResp.status() : null,
      textSample: combinedRuntimeText.slice(0, 4000),
      consoleErrors: runtimeConsoleErrors,
      failedRequests: runtimeFailedRequests,
      releaseInfoScreenshotPath: runtimeDialogScreenshot,
    },
  };
  fs.writeFileSync(path.join(taskDir, 'playwright-runtime-console-r260806c-r1.json'), JSON.stringify(result, null, 2), 'utf8');
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.status === 'passed' ? 0 : 1);
})().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});