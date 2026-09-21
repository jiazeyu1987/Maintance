const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('D:/IntRuoyiWorktree/r260921-prod-release2/a/IntRuoyiFronted/node_modules/playwright')

async function main() {
  const outputDir = 'E:/IntRuoyi/output/runtime/prod-release-3-r10/evidence'
  fs.mkdirSync(outputDir, { recursive: true })
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'E:/Int/DevCache/playwright-browsers/chromium-1223/chrome-win64/chrome.exe'
  })
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
    const network = []
    let consoleErrors = 0
    page.on('response', (response) => {
      const url = new URL(response.url())
      if (url.pathname.startsWith('/admin-api/')) {
        network.push({ method: response.request().method(), path: url.pathname, status: response.status() })
      }
    })
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors += 1
    })
    await page.goto('http://127.0.0.1:8086/login?redirect=/index', {
      waitUntil: 'domcontentloaded'
    })
    await page.waitForSelector('input[placeholder="请输入用户名"]', { state: 'visible', timeout: 20000 })
    await page.waitForTimeout(700)
    await page.screenshot({ path: path.join(outputDir, 'login-before-r10.png'), fullPage: true })
    const inputs = await page.locator('input').evaluateAll((elements) => elements.map((element) => ({
      type: element.getAttribute('type'), placeholder: element.getAttribute('placeholder'),
      autocomplete: element.getAttribute('autocomplete')
    })))
    const buttons = await page.getByRole('button').allTextContents()
    const labels = await page.locator('label').allTextContents()
    const usernameBounds = await page.locator('input[placeholder="请输入用户名"]:visible').first().boundingBox()
    const bodySize = await page.locator('body').evaluate((element) => ({ width: element.scrollWidth, height: element.scrollHeight }))
    console.log(JSON.stringify({ title: await page.title(), path: new URL(page.url()).pathname,
      usernameBounds, bodySize,
      inputs, buttons: buttons.map((value) => value.trim()).filter(Boolean),
      labels: labels.map((value) => value.trim()).filter(Boolean), network, consoleErrors }, null, 2))
    if (process.env.R10_LOGIN_MODE === 'admin') {
      const password = process.env.DCC_ONLYOFFICE_RELEASE_E2E_PASSWORD
      if (!password) throw new Error('ADMIN_CREDENTIAL_MISSING')
      const tenantVisible = await page.getByText('芋道源码', { exact: true }).first().isVisible().catch(() => false)
      if (!tenantVisible) throw new Error('LOGIN_TENANT_NOT_EXPECTED')
      await page.locator('input[placeholder="请输入用户名"]:visible').first().fill('admin')
      await page.locator('input[placeholder="请输入密码"]:visible').first().fill(password)
      await page.getByRole('button', { name: '登录', exact: true }).click()
      try {
        await page.waitForURL((url) => url.pathname !== '/login', { timeout: 20000 })
      } catch {
        const messages = await page.locator('.el-message').allTextContents()
        console.log(JSON.stringify({ loginSucceeded: false, messages: messages.map((value) => value.trim()) }))
        throw new Error('LOGIN_DID_NOT_NAVIGATE')
      }
      await page.waitForTimeout(1800)
      const infrastructureMenu = page.getByText('基础设施', { exact: true }).first()
      if (await infrastructureMenu.isVisible().catch(() => false)) await infrastructureMenu.click()
      const monitoringMenu = page.getByText('监控中心', { exact: true }).first()
      if (await monitoringMenu.isVisible().catch(() => false)) await monitoringMenu.click()
      const runtimeMenu = page.getByText('运行控制台', { exact: true }).first()
      const menuVisible = await runtimeMenu.isVisible().catch(() => false)
      if (menuVisible) {
        await runtimeMenu.click()
        await page.waitForURL((url) => url.pathname !== '/index', { timeout: 20000 })
        await page.getByText('程序包发布工作流', { exact: true }).waitFor({ state: 'visible', timeout: 20000 })
      }
      const workflowToolbar = page.locator('.release-workflow-toolbar')
      const workflowResponse = page.waitForResponse((response) =>
        new URL(response.url()).pathname === '/admin-api/infra/runtime-control/release-workflows',
      { timeout: 20000 })
      await workflowToolbar.getByRole('button', { name: '刷新' }).click()
      const workflowGet = await workflowResponse
      const releaseStatusResponse = await page.waitForResponse((response) =>
        new URL(response.url()).pathname === '/admin-api/infra/runtime-control/release-status',
      { timeout: 25000 }).catch(() => null)
      const buildButton = workflowToolbar.getByRole('button', { name: '构建发布包' })
      const buildDisabledWithoutReason = !(await buildButton.isEnabled())
      await workflowToolbar.getByPlaceholder('发布原因').fill('R10本地只读页面核验')
      const buildEnabledWithReason = await buildButton.isEnabled()
      await workflowToolbar.getByPlaceholder('发布原因').clear()
      const runtimeNav = await page.locator('.el-menu-item, .el-sub-menu__title').evaluateAll((items) =>
        items.map((item) => ({ text: item.textContent.trim(), width: item.getBoundingClientRect().width }))
          .filter((item) => /运行|基础设施|监控/.test(item.text)))
      await page.screenshot({ path: path.join(outputDir, 'runtime-control-admin-r10.png'), fullPage: true })
      const pageState = {
        loginSucceeded: true, tenantLabel: '芋道源码', menuVisible, runtimeNav,
        path: new URL(page.url()).pathname,
        workflowGetStatus: workflowGet.status(), buildDisabledWithoutReason, buildEnabledWithReason,
        releaseStatusGetStatus: releaseStatusResponse?.status() ?? 'PENDING',
        errorVisible: await page.locator('.runtime-error').isVisible().catch(() => false),
        runtimeTitleVisible: await page.getByText('运行控制台', { exact: true }).count(),
        workflowPanelVisible: await page.getByText('程序包发布工作流', { exact: true }).isVisible().catch(() => false),
        productionButtonCount: await page.getByRole('button', { name: '晋级正式服' }).count(),
        genericProductionButtonCount: await page.getByRole('button', { name: '上线已验证发布包' }).count(),
        network, consoleErrors
      }
      fs.writeFileSync(path.join(outputDir, 'runtime-control-admin-network-redacted.json'),
        JSON.stringify(pageState, null, 2), 'utf8')
      console.log(JSON.stringify(pageState, null, 2))
    }
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(/^(LOGIN_|ADMIN_)/.test(error.message) ? error.message : error.name)
  process.exitCode = 1
})
