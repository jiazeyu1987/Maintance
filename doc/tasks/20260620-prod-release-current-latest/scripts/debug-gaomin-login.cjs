const path = require('path')
const { createRequire } = require('module')

const frontendRequire = createRequire(path.join('D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3', 'package.json'))
const { chromium } = frontendRequire('playwright')

async function settle(page, timeout = 12000) {
  await page.waitForLoadState('domcontentloaded', { timeout }).catch(() => {})
  await page.waitForLoadState('networkidle', { timeout }).catch(() => {})
  await page.waitForTimeout(500)
}

async function fillFirstVisible(locator, value, label) {
  const count = await locator.count()
  for (let index = 0; index < count; index += 1) {
    const input = locator.nth(index)
    if (await input.isVisible().catch(() => false)) {
      await input.click().catch(() => {})
      await input.fill('')
      await input.fill(value)
      const actual = await input.inputValue().catch(() => '')
      if (actual !== value) {
        throw new Error(`${label} 输入回读不匹配: expected=${value}, actual=${actual}`)
      }
      return
    }
  }
  throw new Error(`未找到可见${label}输入框`)
}

async function main() {
  const username = process.env.DEBUG_LOGIN_USERNAME || 'gaomin'
  const verifyPassword = process.env.DEBUG_LOGIN_PASSWORD || '111111'
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  const baseUrl = 'http://172.30.30.58:8081'

  try {
    await page.goto(`${baseUrl}/login?redirect=%2Findex`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    })
    await settle(page, 15000)
    const form = page.locator('form.login-form:visible').first()
    await form.waitFor({ state: 'visible', timeout: 30000 })

    const tenantSelect = form.locator('.el-select').first()
    await tenantSelect.click()
    const tenantInput = form.locator('.el-select input[role="combobox"], input.el-select__input').first()
    await tenantInput.fill('')
    await tenantInput.fill('芋道源码')
    const option = page.locator('.el-select-dropdown__item').filter({ hasText: '芋道源码' }).first()
    if (await option.count()) {
      await option.click({ timeout: 5000 }).catch(async () => tenantInput.press('Enter'))
    } else {
      await tenantInput.press('Enter')
    }

    const allInputs = await form.locator('input').evaluateAll((nodes) =>
      nodes.map((node) => ({
        type: node.getAttribute('type') || '',
        placeholder: node.getAttribute('placeholder') || '',
        value: node.value || '',
        visible: (() => {
          const rect = node.getBoundingClientRect()
          const style = window.getComputedStyle(node)
          return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden'
        })(),
        rect: (() => {
          const rect = node.getBoundingClientRect()
          return { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
        })(),
        className: node.className || ''
      }))
    )
    console.log('FORM_INPUTS', JSON.stringify(allInputs, null, 2))

    await fillFirstVisible(form.locator('input[placeholder="请输入用户名"], input[placeholder="请输入账号"]'), username, '用户名')
    await fillFirstVisible(form.locator('input[placeholder="请输入密码"], input[type="password"]'), verifyPassword, '密码')

    const filledInputs = await form.locator('input').evaluateAll((nodes) =>
      nodes.map((node) => ({
        type: node.getAttribute('type') || '',
        placeholder: node.getAttribute('placeholder') || '',
        value: node.value || ''
      }))
    )
    console.log('FILLED_INPUTS', JSON.stringify(filledInputs, null, 2))

    const loginResponsePromise = page.waitForResponse(
      (response) => response.url().includes('/admin-api/system/auth/login') && response.request().method() === 'POST',
      { timeout: 60000 }
    )
    await form.getByRole('button', { name: '登录' }).click()
    const loginResponse = await loginResponsePromise
    const loginPayload = await loginResponse.json().catch(async () => ({ raw: await loginResponse.text().catch(() => '') }))
    console.log('LOGIN_RESPONSE', username, loginResponse.status(), JSON.stringify(loginPayload).slice(0, 800))

    await page.waitForURL((url) => !url.href.includes('/login'), { timeout: 60000 }).catch((error) => {
      console.log('WAIT_URL_ERROR', error.message)
    })
    await settle(page, 15000)

    console.log('URL', page.url())
    console.log('TITLE', await page.title())
    const bodyText = await page.locator('body').innerText().catch(() => '')
    console.log('BODY', bodyText.replace(/\s+/g, ' ').slice(0, 1200))

    const menuFetch = await page.evaluate(async () => {
      try {
        const response = await fetch('/admin-api/system/menu/list', {
          method: 'GET',
          credentials: 'include',
          headers: {
            Accept: 'application/json, text/plain, */*'
          }
        })
        const text = await response.text()
        return {
          ok: response.ok,
          status: response.status,
          text: text.slice(0, 1200)
        }
      } catch (error) {
        return { error: error.message }
      }
    })
    console.log('MENU_FETCH', JSON.stringify(menuFetch, null, 2))

    const storage = await page.evaluate(() => ({
      localStorageKeys: Object.keys(localStorage),
      sessionStorageKeys: Object.keys(sessionStorage),
      roleRouters: localStorage.getItem('roleRouters')
    }))
    console.log('STORAGE_KEYS', JSON.stringify(storage, null, 2))
  } finally {
    await context.close()
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
