const path = require('path')
const { createRequire } = require('module')

const frontendRequire = createRequire(path.join('D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3', 'package.json'))
const { chromium } = frontendRequire('playwright')

async function settle(page, timeout = 12000) {
  await page.waitForLoadState('domcontentloaded', { timeout }).catch(() => {})
  await page.waitForLoadState('networkidle', { timeout }).catch(() => {})
  await page.waitForTimeout(500)
}

async function fillFirstVisible(locator, value) {
  const count = await locator.count()
  for (let index = 0; index < count; index += 1) {
    const input = locator.nth(index)
    if (await input.isVisible().catch(() => false)) {
      await input.click().catch(() => {})
      await input.fill('')
      await input.fill(value)
      return
    }
  }
  throw new Error('visible input not found')
}

async function login(page, username, password, tenantName = '芋道源码') {
  const baseUrl = 'http://172.30.30.58:8081'
  await page.goto(`${baseUrl}/login?redirect=%2Findex`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await settle(page, 15000)
  const form = page.locator('form.login-form:visible').first()
  await form.waitFor({ state: 'visible', timeout: 30000 })
  const tenantSelect = form.locator('.el-select').first()
  await tenantSelect.click()
  const tenantInput = form.locator('.el-select input[role="combobox"], input.el-select__input').first()
  await tenantInput.fill('')
  await tenantInput.fill(tenantName)
  const option = page.locator('.el-select-dropdown__item').filter({ hasText: tenantName }).first()
  if (await option.count()) {
    await option.click({ timeout: 5000 }).catch(async () => tenantInput.press('Enter'))
  } else {
    await tenantInput.press('Enter')
  }
  await fillFirstVisible(form.locator('input[placeholder="请输入用户名"], input[placeholder="请输入账号"]'), username)
  await fillFirstVisible(form.locator('input[placeholder="请输入密码"], input[type="password"]'), password)
  const loginResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/admin-api/system/auth/login') && response.request().method() === 'POST',
    { timeout: 60000 }
  )
  await form.getByRole('button', { name: '登录' }).click()
  const loginResponse = await loginResponsePromise
  const payload = await loginResponse.json().catch(async () => ({ raw: await loginResponse.text().catch(() => '') }))
  console.log('LOGIN_PAYLOAD', JSON.stringify(payload).slice(0, 400))
  await page.waitForURL((url) => !url.href.includes('/login'), { timeout: 60000 })
  await settle(page, 15000)
}

async function main() {
  const username = process.env.DEBUG_ROLE_USERNAME || 'zhaojie'
  const password = process.env.DEBUG_ROLE_PASSWORD || '111111'
  const route = process.env.DEBUG_ROLE_ROUTE || '/index'
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  const baseUrl = 'http://172.30.30.58:8081'

  try {
    await login(page, username, password)
    await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await settle(page, 15000)
    const snapshot = await page.evaluate(() => {
      const isVisible = (node) => {
        const rect = node.getBoundingClientRect()
        const style = window.getComputedStyle(node)
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden'
      }
      const selectors = [
        '.layout-menu .el-menu-item',
        '.layout-menu .el-sub-menu__title',
        '.el-menu--horizontal .el-menu-item',
        '.el-menu--horizontal .el-sub-menu__title',
        '.breadcrumb__inner',
        '[role="menuitem"]'
      ]
      const menuTexts = []
      for (const selector of selectors) {
        for (const node of document.querySelectorAll(selector)) {
          if (!isVisible(node)) continue
          const text = (node.textContent || '').replace(/\s+/g, ' ').trim()
          if (text) menuTexts.push({ selector, text, className: node.className })
        }
      }
      const buttons = Array.from(document.querySelectorAll('button'))
        .filter(isVisible)
        .map((node) => ({
          text: (node.innerText || node.getAttribute('aria-label') || node.title || '').replace(/\s+/g, ' ').trim(),
          className: node.className
        }))
        .filter((item) => item.text)
      return {
        title: document.title,
        url: location.href,
        body: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 2000),
        menuTexts,
        buttons
      }
    })
    console.log(JSON.stringify(snapshot, null, 2))
  } finally {
    await context.close()
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
