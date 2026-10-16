"""Real browser login, menu/query/view/download; no API/SQL or mocked responses."""
from pathlib import Path
from urllib.parse import urlsplit

from core import fields, need, integer, text, sha, digest, raw_file
from collect_data import secret_environment


def origin(value):
    url = urlsplit(text(value))
    need(url.scheme in ("http", "https") and bool(url.hostname) and not url.username and not url.password,
         "BROWSER_ORIGIN_REQUIRED")
    return url.scheme + "://" + url.netloc


def validate_browser_settings(settings, identity):
    fields(settings, "baseUrl allowedOrigins browserExecutable username passwordEnv login paths")
    need(settings["username"] == "aoteman" and origin(settings["baseUrl"]) == identity["frontendOrigin"],
         "BROWSER_TARGET_OR_USER_MISMATCH")
    need(type(settings["allowedOrigins"]) is list and bool(settings["allowedOrigins"]), "ALLOWED_ORIGINS_REQUIRED")
    need(all(origin(value) == value for value in settings["allowedOrigins"])
         and identity["frontendOrigin"] in settings["allowedOrigins"], "ISOLATED_ORIGIN_SCOPE_REQUIRED")
    executable = Path(text(settings["browserExecutable"]))
    need(executable.is_absolute() and executable.is_file(), "EXPLICIT_BROWSER_EXECUTABLE_REQUIRED")
    fields(settings["login"], "tenantSelector usernameSelector passwordSelector submitSelector "
           "tenantIdSelector tenantNameSelector identityUsernameSelector")
    for selector in settings["login"].values():
        text(selector)
    need(type(settings["paths"]) is list and bool(settings["paths"]), "REAL_PAGE_PATHS_REQUIRED")
    names = []
    for flow in settings["paths"]:
        fields(flow, "pathId entrySelector steps")
        text(flow["entrySelector"])
        names.append(text(flow["pathId"]))
        need(type(flow["steps"]) is list and bool(flow["steps"]), "REAL_PAGE_STEPS_REQUIRED")
        assertions = 0
        for step in flow["steps"]:
            need(type(step) is dict and "kind" in step, "BROWSER_STEP_REQUIRED")
            kind = step["kind"]
            required = {"click": "kind selector", "fill": "kind selector value",
                        "text": "kind selector expected", "visible": "kind selector",
                        "image": "kind selector", "download": "kind selector expectedBytes expectedSha256"}
            need(kind in required, "UNSUPPORTED_BROWSER_STEP")
            fields(step, required[kind])
            text(step["selector"])
            if kind in ("text", "visible", "image"):
                assertions += 1
            if kind == "text":
                text(step["expected"])
            if kind == "fill":
                need(type(step["value"]) is str, "BROWSER_FILL_TEXT_REQUIRED")
            if kind == "download":
                need(flow["pathId"] == "download", "DOWNLOAD_PATH_REQUIRED")
                integer(step["expectedBytes"], 1)
                sha(step["expectedSha256"])
        need(assertions > 0, "BROWSER_ASSERTIONS_REQUIRED")
        count = sum(step["kind"] == "download" for step in flow["steps"])
        need(count == (1 if flow["pathId"] == "download" else 0), "DOWNLOAD_STEP_COUNT")
    need(len(set(names)) == len(names) and set(names) >= {"query", "view", "download"}
         and "login" not in names, "BROWSER_REQUIRED_PATHS")


def collect_playwright(settings, identity, evidence_root, deadline):
    validate_browser_settings(settings, identity)
    # Explicit dependency; missing packages/browser fail before any login operation.
    from playwright.sync_api import sync_playwright
    root = Path(evidence_root)
    need(root.is_absolute() and root.is_dir(), "BROWSER_EVIDENCE_DIRECTORY_REQUIRED")
    login = settings["login"]
    secret = secret_environment(settings["passwordEnv"])
    allowed = set(settings["allowedOrigins"])
    counters = {"blocked": 0, "errors": 0, "failures": 0}
    paths = []

    def artifact(path):
        from core import file_pin
        return file_pin(str(path), deadline)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=settings["browserExecutable"], headless=True,
                                             timeout=int(deadline.remaining() * 1000))
        try:
            context = browser.new_context(accept_downloads=True, service_workers="block")
            def guard(route):
                url = route.request.url
                parsed = urlsplit(url)
                if parsed.scheme in ("data", "blob", "about") or origin(url) in allowed:
                    route.continue_()
                else:
                    counters["blocked"] += 1
                    route.abort("blockedbyclient")
            context.route("**/*", guard)
            # WebSocket traffic is an external side effect too; never permit an uninspected socket.
            context.route_web_socket("**/*", lambda socket: socket.close())
            page = context.new_page()
            page.on("pageerror", lambda _: counters.__setitem__("errors", counters["errors"] + 1))
            page.on("response", lambda response: counters.__setitem__("failures", counters["failures"] +
                                                                      int(response.status >= 400)))
            def failed(request):
                if urlsplit(request.url).scheme in ("http", "https") and origin(request.url) in allowed:
                    counters["failures"] += 1
            page.on("requestfailed", failed)

            def budget():
                page.set_default_timeout(max(1, int(deadline.remaining() * 1000)))
                page.set_default_navigation_timeout(max(1, int(deadline.remaining() * 1000)))
                need(origin(page.url) == identity["frontendOrigin"], "BROWSER_LEFT_ISOLATED_TARGET")

            def tenant_assertions():
                checks = []
                for selector, expected in ((login["tenantIdSelector"], "122"),
                                           (login["tenantNameSelector"], "测试租户"),
                                           (login["identityUsernameSelector"], "aoteman")):
                    locator = page.locator(selector)
                    locator.wait_for(state="visible")
                    observed = locator.inner_text().strip()
                    need(observed == expected, "BROWSER_TENANT_IDENTITY_NOT_PROVED")
                    checks.append({"selector": selector, "kind": "text", "expected": expected, "observed": observed})
                return checks

            def capture(index):
                path = root / ("browser-" + str(index) + ".png")
                need(not path.exists(), "BROWSER_ARTIFACT_EXISTS")
                page.screenshot(path=str(path), full_page=True,
                                mask=[page.locator(login["passwordSelector"])])
                return artifact(path)

            page.goto(settings["baseUrl"], wait_until="domcontentloaded", timeout=int(deadline.remaining() * 1000))
            budget()
            page.locator(login["tenantSelector"]).fill("测试租户")
            page.locator(login["usernameSelector"]).fill("aoteman")
            page.locator(login["passwordSelector"]).fill(secret)
            page.locator(login["submitSelector"]).click()
            budget()
            assertions = tenant_assertions()
            paths.append({"pathId": "login", "entrySelector": login["submitSelector"],
                          "assertions": assertions, "screenshotPin": capture(0), "download": None})
            for index, flow in enumerate(settings["paths"], 1):
                budget()
                tenant_assertions()  # Check immediately before each user path.
                page.locator(flow["entrySelector"]).click()
                assertions, downloaded = [], None
                for step in flow["steps"]:
                    budget()
                    locator, kind = page.locator(step["selector"]), step["kind"]
                    if kind == "click":
                        locator.click()
                    elif kind == "fill":
                        locator.fill(step["value"])
                    elif kind in ("text", "visible", "image"):
                        locator.wait_for(state="visible")
                        if kind == "text":
                            # Wait for actual query content, not the initial empty table.
                            from playwright.sync_api import expect
                            expect(locator).to_have_text(step["expected"], timeout=int(deadline.remaining() * 1000))
                            expected, observed = step["expected"], locator.inner_text()
                        elif kind == "image":
                            page.wait_for_function("s => { const e = document.querySelector(s); return e && "
                                                   "e.complete && e.naturalWidth > 0 && e.getBoundingClientRect().width > 0; }",
                                                   arg=step["selector"], timeout=int(deadline.remaining() * 1000))
                            expected, observed = True, locator.is_visible()
                        else:
                            expected, observed = True, locator.is_visible()
                        need(observed == expected, "REAL_USER_ASSERTION_FAILED", "FAILED")
                        assertions.append({"selector": step["selector"], "kind": kind,
                                           "expected": expected, "observed": observed})
                    elif kind == "download":
                        destination = root / ("download-" + str(index) + ".bin")
                        need(not destination.exists(), "DOWNLOAD_ARTIFACT_EXISTS")
                        with page.expect_download(timeout=int(deadline.remaining() * 1000)) as event:
                            locator.click()
                        download = event.value
                        need(download.failure() is None, "REAL_DOWNLOAD_FAILED", "FAILED")
                        download.save_as(str(destination))
                        pin = artifact(destination)
                        need(pin["bytes"] == step["expectedBytes"] and pin["sha256"] == step["expectedSha256"],
                             "REAL_DOWNLOAD_BYTES_MISMATCH", "FAILED")
                        downloaded = {"expectedBytes": step["expectedBytes"], "expectedSha256": step["expectedSha256"],
                                      "actualBytes": pin["bytes"], "actualSha256": pin["sha256"], "contentPin": pin}
                budget()
                assertions.extend(tenant_assertions())
                paths.append({"pathId": flow["pathId"], "entrySelector": flow["entrySelector"],
                              "assertions": assertions, "screenshotPin": capture(index), "download": downloaded})
            need(counters["errors"] == 0 and counters["failures"] == 0, "BROWSER_BUSINESS_FAILURE", "FAILED")
            context.close()
        finally:
            browser.close()
    return {"engine": "playwright", "targetOrigin": identity["frontendOrigin"], "tenantId": 122,
            "tenantName": "测试租户", "username": "aoteman", "paths": paths,
            "blockedExternalRequests": counters["blocked"], "pageErrorCount": counters["errors"],
            "businessFailureCount": counters["failures"]}
