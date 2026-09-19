#!/usr/bin/env node
import fs from 'node:fs/promises'
import path from 'node:path'
import { createRequire } from 'node:module'

const requireFromFrontend = createRequire(
  path.resolve('D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3/package.json')
)
const { chromium } = requireFromFrontend('playwright')

const requiredEnv = ['BASE_URL', 'TENANT', 'USERNAME', 'PASSWORD', 'CONTROLLED_FILE_ID', 'ARTIFACT_DIR']
for (const key of requiredEnv) {
  if (!process.env[key]) {
    throw new Error(`Missing env ${key}`)
  }
}

const baseUrl = new URL(process.env.BASE_URL)
const controlledFileId = process.env.CONTROLLED_FILE_ID
const timeout = Number(process.env.TIMEOUT || 120000)
const artifactDir = process.env.ARTIFACT_DIR
const targetPath = `/dcc/controlled-file/detail/${controlledFileId}?viewer=1&from=project-code`
const unauthorizedText = '\u6ca1\u6709\u8be5\u64cd\u4f5c\u6743\u9650'

const result = {
  baseUrl: baseUrl.origin,
  username: process.env.USERNAME,
  controlledFileId,
  targetPath,
  finalUrl: '',
  login: null,
  permissionInfo: null,
  previewMetadata: null,
  preview: null,
  previewLayoutVisible: false,
  apiResponses: [],
  nonSuccessApiResponses: [],
  pageMessages: [],
  consoleErrors: [],
  assertions: {}
}

const browser = await chromium.launch({
  headless: true,
  args: ['--disable-dev-shm-usage'],
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined
})

try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } })
  const page = await context.newPage()
  page.setDefaultTimeout(timeout)
  page.setDefaultNavigationTimeout(timeout)

  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) {
      result.consoleErrors.push({ type: msg.type(), text: msg.text().slice(0, 800) })
    }
  })

  page.on('response', async (response) => {
    const url = response.url()
    if (!url.includes('/admin-api/')) {
      return
    }
    const contentType = response.headers()['content-type'] || ''
    let body = null
    if (contentType.includes('application/json')) {
      body = await response.json().catch(() => null)
    }
    const entry = {
      url,
      method: response.request().method(),
      status: response.status(),
      contentType,
      code: body && typeof body === 'object' ? body.code : undefined,
      msg: body && typeof body === 'object' ? body.msg : undefined
    }
    result.apiResponses.push(entry)
    if (url.includes('/system/auth/get-permission-info') && body && typeof body === 'object') {
      const serialized = JSON.stringify(body)
      result.permissionInfo = {
        status: response.status(),
        code: body.code,
        hasControlledFileQuery: serialized.includes('dcc:controlled-file:query'),
        hasProjectCodeQuery: serialized.includes('dcc:project-code:query'),
        hasFormInstanceCreate: serialized.includes('form:instance:create'),
        hasSignatureManage: serialized.includes('dcc:controlled-file:signature:manage')
      }
    }
    if (url.includes(`/dcc/controlled-files/${controlledFileId}/preview-metadata`)) {
      result.previewMetadata = entry
    }
    if (url.includes(`/dcc/controlled-files/${controlledFileId}/preview`) && !url.includes('preview-metadata')) {
      result.preview = entry
    }
    if (response.status() >= 400 || (entry.code !== undefined && ![0, 200].includes(entry.code))) {
      result.nonSuccessApiResponses.push(entry)
    }
  })

  const loginUrl = new URL('/login', baseUrl.origin)
  loginUrl.searchParams.set('redirect', '/index')
  await page.goto(loginUrl.toString(), { waitUntil: 'commit' })

  const form = page.locator('form.login-form:visible').first()
  await form.waitFor({ state: 'visible' })
  const tenantSelect = form.locator('.el-select').first()
  const selectedTenantText = await tenantSelect.innerText().catch(() => '')
  if (!selectedTenantText.includes(process.env.TENANT)) {
    const tenantInput = form.locator('.el-select input[role="combobox"]:visible, input.el-select__input:visible').first()
    if (await tenantInput.count()) {
      await tenantInput.click()
      await tenantInput.fill(process.env.TENANT)
      await page.keyboard.press('Enter')
      await page.waitForTimeout(300)
      const tenantOption = page.locator('.el-select-dropdown__item:visible').filter({ hasText: process.env.TENANT }).first()
      if (await tenantOption.isVisible().catch(() => false)) {
        await tenantOption.click()
      }
    } else {
      await form.locator('input.el-input__inner').nth(0).fill(process.env.TENANT)
    }
  }

  await form.locator('input.el-input__inner:not([role="combobox"]):visible').first().fill(process.env.USERNAME)
  await form.locator('input[type="password"]').first().fill(process.env.PASSWORD)

  const loginResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/system/auth/login') && response.request().method() === 'POST',
    { timeout }
  )
  await form.getByRole('button', { name: '\u767b\u5f55' }).click()
  const loginResponse = await loginResponsePromise
  const loginPayload = await loginResponse.json()
  result.login = {
    status: loginResponse.status(),
    code: loginPayload.code,
    hasAccessToken: Boolean(loginPayload?.data?.accessToken)
  }
  if (!loginResponse.ok() || ![0, 200].includes(loginPayload.code)) {
    throw new Error(`Login failed: HTTP ${loginResponse.status()} ${loginPayload.msg || ''}`)
  }

  await page.waitForURL((current) => !current.pathname.includes('/login'), {
    timeout,
    waitUntil: 'commit'
  })
  await page.goto(new URL(targetPath, baseUrl.origin).toString(), { waitUntil: 'commit' })
  await page.locator('[data-testid="dcc-controlled-preview-layout"]').waitFor({ state: 'visible', timeout })
  await page.waitForResponse(
    (response) => response.url().includes(`/dcc/controlled-files/${controlledFileId}/preview`) && !response.url().includes('preview-metadata'),
    { timeout }
  )
  await page.waitForTimeout(3000)

  result.finalUrl = page.url()
  result.previewLayoutVisible = await page.locator('[data-testid="dcc-controlled-preview-layout"]').isVisible()
  result.pageMessages = await page.locator('.el-message, .el-message__content').evaluateAll((nodes) =>
    nodes.map((node) => node.textContent || '').filter(Boolean)
  ).catch(() => [])

  const urls = result.apiResponses.map((entry) => entry.url)
  result.assertions = {
    loginOk: result.login?.code === 0 && result.login?.hasAccessToken === true,
    permissionBaselineOk:
      result.permissionInfo?.hasControlledFileQuery === true &&
      result.permissionInfo?.hasProjectCodeQuery === true &&
      result.permissionInfo?.hasFormInstanceCreate === false &&
      result.permissionInfo?.hasSignatureManage === false,
    previewMetadataOk: result.previewMetadata?.status === 200 && [0, 200].includes(result.previewMetadata?.code),
    previewPdfOk: result.preview?.status === 200 && String(result.preview?.contentType || '').includes('application/pdf'),
    noActiveInstanceCall: !urls.some((url) => url.includes('/form-center/actions/active-instance')),
    noSignatureManagePageCall: !urls.some((url) => url.includes('/dcc/electronic-signatures/page')),
    noRoundedControlledFileId: !urls.some((url) => url.includes('2054545668044081200')),
    noUnauthorizedMessage: !result.pageMessages.some((message) => message.includes(unauthorizedText)),
    noFailedAdminApi: result.nonSuccessApiResponses.length === 0,
    previewLayoutVisible: result.previewLayoutVisible
  }

  const failed = Object.entries(result.assertions)
    .filter(([, passed]) => passed !== true)
    .map(([name]) => name)

  await fs.mkdir(artifactDir, { recursive: true })
  const artifactPath = path.join(artifactDir, 'assert-controlled-viewer-result.json')
  await fs.writeFile(artifactPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8')

  console.log(JSON.stringify({ artifactPath, assertions: result.assertions, failed }, null, 2))
  if (failed.length > 0) {
    process.exitCode = 1
  }
} finally {
  await browser.close()
}
