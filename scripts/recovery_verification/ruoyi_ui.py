"""Explicit Ruoyi UI profile; observes browser traffic, never makes API calls."""
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from collect_playwright import origin
from collect_data import secret_environment
from core import fields, need, text, integer, sha, read_pin, file_pin


def api_business_body(response):
    """A successful HTTP transport alone cannot establish a business success."""
    need("json" in response.headers.get("content-type", ""), "UI_API_JSON_REQUIRED")
    body = response.json()
    need(type(body) is dict and type(body.get("code")) is int and body["code"] == 0,
         "UI_API_BUSINESS_FAILED")
    return body


def validate_flows(flows, phase):
    required = {"baseline": {"baseline-update", "baseline-delete", "baseline-download"},
                "delta": {"add", "update", "delete", "object-delete"},
                "target": {"query", "view", "download", "deleted"}}[phase]
    need(type(flows) is list and bool(flows), "UI_FLOWS_REQUIRED")
    names = []
    for flow in flows:
        fields(flow, "pathId entrySteps steps")
        name = text(flow["pathId"])
        names.append(name)
        need(type(flow["entrySteps"]) is list and bool(flow["entrySteps"])
             and type(flow["steps"]) is list and bool(flow["steps"]), "UI_STEPS_REQUIRED")
        checks, uploads, downloads = 0, 0, 0
        upload_pins, capture_pins = [], []
        for step in [*flow["entrySteps"], *flow["steps"]]:
            kind = step.get("kind") if type(step) is dict else None
            shapes = {"click": "kind selector", "fill": "kind selector value",
                      "press": "kind selector key", "upload": "kind selector contentPin",
                      "text": "kind selector expected", "value": "kind selector expected",
                      "count": "kind selector expected", "image": "kind selector",
                      "attribute": "kind selector name expected",
                      "captureReference": "kind selector contentPin",
                      "objectReference": "kind selector sourcePathId sourceSelector",
                      "download": "kind selector expectedBytes expectedSha256"}
            need(kind in shapes, "UI_STEP_UNSUPPORTED")
            fields(step, shapes[kind])
            text(step["selector"])
            need(not any(word in step["selector"].lower() for word in ("showroom/", "dcc:")),
                 "UI_PROTECTED_SELECTOR")
            if kind in ("text", "value", "count", "image", "attribute"):
                checks += 1
            if kind in ("text", "value", "attribute"):
                text(step["expected"])
            if kind == "attribute":
                need(step["name"] in ("src", "href"), "UI_REFERENCE_ATTRIBUTE_REQUIRED")
            if kind == "captureReference":
                need(phase != "target", "UI_SOURCE_REFERENCE_CAPTURE_REQUIRED")
                capture_pins.append(step["contentPin"])
            if kind == "objectReference":
                need(phase == "target", "UI_TARGET_REFERENCE_ASSERTION_REQUIRED")
                text(step["sourcePathId"])
                text(step["sourceSelector"])
                checks += 1
            if kind == "count":
                integer(step["expected"])
            if kind == "fill":
                need(type(step["value"]) is str, "UI_FILL_TEXT_REQUIRED")
            if kind == "press":
                need(step["key"] in ("Enter", "Tab", "Escape"), "UI_KEY_UNSUPPORTED")
            if kind == "upload":
                need(phase != "target", "TARGET_BUSINESS_UPLOAD_PROHIBITED")
                uploads += 1
                upload_pins.append(step["contentPin"])
            if kind == "download":
                need(phase == "target" and name == "download", "UI_DOWNLOAD_PHASE_REQUIRED")
                integer(step["expectedBytes"], 1)
                sha(step["expectedSha256"])
                downloads += 1
        need(checks > 0, "UI_SUBSTANTIVE_ASSERTION_REQUIRED")
        if phase == "baseline" or phase == "delta" and name in ("add", "update"):
            need(uploads > 0, "UI_ASSOCIATED_UPLOAD_REQUIRED")
            need(bool(capture_pins) and all(pin in upload_pins for pin in capture_pins),
                 "UI_UPLOADED_REFERENCE_CAPTURE_REQUIRED")
        need(downloads == (1 if phase == "target" and name == "download" else 0),
             "UI_DOWNLOAD_COUNT")
        if phase == "target" and name == "deleted":
            need(any(step["kind"] == "count" and step["expected"] == 0 for step in flow["steps"]),
                 "UI_DELETION_ASSERTION_REQUIRED")
            need(any(step["kind"] == "text" for step in flow["steps"]), "UI_SURVIVOR_ASSERTION_REQUIRED")
        if phase == "target" and name in ("view", "download"):
            need(any(step["kind"] == "objectReference" for step in flow["steps"]), "UI_RESTORED_REFERENCE_CHECK_REQUIRED")
    need(len(names) == len(set(names)) and set(names) == required, "UI_PHASE_PATHS_REQUIRED")


def validate_login(login):
    fields(login, "tenantSelector usernameSelector passwordSelector submitSelector "
           "profileEntrySteps profileUsernameSelector")
    for name in ("tenantSelector", "usernameSelector", "passwordSelector", "submitSelector",
                 "profileUsernameSelector"):
        text(login[name])
    need(type(login["profileEntrySteps"]) is list and bool(login["profileEntrySteps"]),
         "UI_PROFILE_ENTRY_REQUIRED")
    for step in login["profileEntrySteps"]:
        fields(step, "kind selector")
        need(step["kind"] == "click", "UI_PROFILE_CLICK_REQUIRED")
        text(step["selector"])


def request_violation(config, method, url, headers, body, resolved):
    parsed = urlsplit(url)
    if parsed.scheme in ("data", "blob", "about"):
        return None
    host = origin(url)
    if host not in set(config["allowedOrigins"]):
        return "EXTERNAL_ORIGIN"
    path = parsed.path
    if any(word in path.lower() for word in ("/dcc/", "/showroom/", "/yudao/showroom/")):
        return "PROTECTED_PATH"
    if host != config["apiOrigin"]:
        return None if method in ("GET", "HEAD", "OPTIONS") else "UNAPPROVED_OBJECT_WRITE"
    public = path.endswith(("/system/tenant/get-id-by-name", "/system/tenant/get-by-website"))
    if public:
        return None if method == "GET" else "TENANT_CONFIG_WRITE"
    if path.startswith(("/system/", "/infra/", "/mes/", "/crm/", "/admin-api/")):
        if headers.get("tenant-id") != "122" or headers.get("visit-tenant-id", "122") != "122":
            return "WRONG_TENANT"
    if path.endswith("/system/auth/login"):
        if method != "POST" or resolved != 122 or type(body) is not dict or body.get("username") != "aoteman":
            return "WRONG_LOGIN"
        return None
    if method not in ("GET", "HEAD", "OPTIONS"):
        if config["phase"] == "target" or path not in config["writeApiPaths"]:
            return "UNAPPROVED_BUSINESS_WRITE"
    return None


def run_browser(config, root, deadline, source_references):
    def check_authority():
        deadline.remaining()
        if hasattr(deadline, "lab_guard"):
            deadline.lab_guard()
    check_authority()
    from playwright.sync_api import sync_playwright, expect
    login = config["login"]
    validate_login(login)
    api_origin = config["apiOrigin"]
    selected_origin = config["targetOrigin"] if config["phase"] == "target" else config["sourceOrigin"]
    secret = secret_environment(config["passwordEnv"])
    counters = {"blocked": 0, "errors": 0, "failures": 0}
    identity = {"resolved": None, "login": False, "tenantRequests": 0, "lastTenant": None, "violation": False}
    paths, references = [], []
    successful_mutations = {}
    flow_mutations = {"baseline-update": "/mes/md/product-sop/create",
                      "baseline-delete": "/mes/md/product-sop/create",
                      "baseline-download": "/crm/follow-up-record/create", "add": "/mes/md/product-sop/create",
                      "update": "/mes/md/product-sop/update", "delete": "/mes/md/product-sop/delete",
                      "object-delete": "/infra/file/delete"}
    owned_file_ids = set()
    upload_names = {Path(step["contentPin"]["path"]).name for flow in config["flows"]
                    for step in [*flow["entrySteps"], *flow["steps"]] if step["kind"] == "upload"}
    upload_names.update(Path(item["contentPin"]["path"]).name for item in source_references)
    prefixes = ("/system/", "/infra/", "/mes/", "/crm/", "/admin-api/")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=config["browserExecutable"], headless=True,
                                             timeout=int(deadline.remaining() * 1000),
                                             **({"chromium_sandbox": True} if hasattr(deadline, "lab_guard") else {}))
        try:
            context = browser.new_context(accept_downloads=True, service_workers="block")

            def guard_action(route):
                check_authority()
                request, url = route.request, urlsplit(route.request.url)
                path = url.path
                headers = request.all_headers()
                body = request.post_data_json if path.endswith("/system/auth/login") else None
                violation = request_violation(config, request.method, request.url, headers, body, identity["resolved"])
                if violation:
                    counters["blocked"] += int(violation == "EXTERNAL_ORIGIN")
                    identity["violation"] = True
                    route.abort("blockedbyclient")
                    return
                if path.endswith("/infra/file/delete"):
                    requested = parse_qs(url.query).get("id", [])
                    if request.method != "DELETE" or len(requested) != 1 or requested[0] not in owned_file_ids:
                        identity["violation"] = True
                        route.abort("blockedbyclient")
                        return
                if url.scheme in ("http", "https") and origin(request.url) == api_origin and path.startswith(prefixes):
                    public = path.endswith(("/system/tenant/get-id-by-name", "/system/tenant/get-by-website"))
                    if not public:
                        identity["tenantRequests"] += 1
                        identity["lastTenant"] = headers["tenant-id"]
                route.continue_()

            def guard(route):
                try:
                    guard_action(route)
                except Exception as error:
                    identity["eventFailure"] = "UI_REQUEST_EVENT_" + type(error).__name__.upper()
                    counters["failures"] += 1
                    route.abort("blockedbyclient")

            def response_action(response):
                url = urlsplit(response.url)
                if response.status >= 400:
                    counters["failures"] += 1
                if origin(response.url) != api_origin or not url.path.startswith(prefixes):
                    return
                if response.request.method == "OPTIONS":
                    return
                if response.status == 204:
                    return
                body = api_business_body(response)
                if response.request.method not in ("GET", "HEAD", "OPTIONS"):
                    normalized = url.path[len("/admin-api"):] if url.path.startswith("/admin-api/") else url.path
                    successful_mutations[normalized] = successful_mutations.get(normalized, 0) + 1
                if url.path.endswith("/system/tenant/get-id-by-name"):
                    if parse_qs(url.query).get("name") == ["测试租户"]:
                        if type(body.get("data")) is int and body["data"] == 122:
                            identity["resolved"] = body["data"]
                        else:
                            identity["violation"] = True
                if url.path.endswith("/system/auth/login"):
                    identity["login"] = True
                if url.path.endswith("/infra/file/page"):
                    data = body.get("data")
                    need(type(data) is dict and type(data.get("list")) is list, "UI_FILE_LIST_FORMAT_REQUIRED")
                    for item in data["list"]:
                        if item.get("name") in upload_names and item.get("configId") != 28:
                            reference = urlsplit(text(item.get("url")))
                            if origin(item["url"]) in set(config["objectOrigins"]) and "/showroom/" not in reference.path:
                                owned_file_ids.add(str(integer(item["id"], 1)))

            def response_observed(response):
                try:
                    response_action(response)
                except Exception as error:
                    identity["eventFailure"] = "UI_RESPONSE_EVENT_" + type(error).__name__.upper()
                    counters["failures"] += 1

            context.route("**/*", guard)
            context.route_web_socket("**/*", lambda socket: socket.close())
            context.on("page", lambda opened: opened.on("pageerror", lambda _: counters.__setitem__("errors", counters["errors"] + 1)))
            context.on("response", response_observed)
            context.on("requestfailed", lambda _: counters.__setitem__("failures", counters["failures"] + 1))
            page = context.new_page()

            def budget():
                check_authority()
                timeout = max(1, int(deadline.remaining() * 1000))
                page.set_default_timeout(timeout)
                page.set_default_navigation_timeout(timeout)
                need(origin(page.url) == selected_origin, "UI_LEFT_SELECTED_FRONTEND")
                need("eventFailure" not in identity, identity.get("eventFailure", "UI_EVENT_FAILED"), "FAILED")
                need(not identity["violation"], "UI_TENANT_OR_WRITE_SCOPE_VIOLATION", "FAILED")
                need(not any(counters.values()), "UI_BROWSER_OR_BUSINESS_ERROR", "FAILED")
                return timeout

            def capture(index):
                path = root / ("ui-" + str(index) + ".png")
                need(not path.exists(), "UI_SCREENSHOT_EXISTS")
                page.screenshot(path=str(path), full_page=True, timeout=budget(),
                                mask=[page.locator(login["passwordSelector"])])
                return file_pin(str(path), deadline)

            page.goto(config["baseUrl"], wait_until="domcontentloaded", timeout=int(deadline.remaining() * 1000))
            budget()
            tenant = page.locator(login["tenantSelector"])
            tenant.fill("测试租户")
            tenant.press("Enter")  # ElSelect allow-create commits only on selection.
            page.locator(login["usernameSelector"]).fill("aoteman")
            page.locator(login["passwordSelector"]).fill(secret)
            page.locator(login["submitSelector"]).click()
            for step in login["profileEntrySteps"]:
                budget()
                page.locator(step["selector"]).click()
            user = page.locator(login["profileUsernameSelector"])
            expect(user).to_be_visible(timeout=budget())
            expect(user).to_have_text("aoteman", timeout=budget())
            need(identity["resolved"] == 122 and identity["login"] and identity["tenantRequests"] > 0,
                 "UI_LOGIN_IDENTITY_NOT_PROVED")
            # These are observations of the real UI's own requests. They are not injected
            # DOM nodes or separately generated API requests, and contain no credentials.
            paths.append({"pathId": "login", "entrySelector": login["submitSelector"],
                          "assertions": [{"selector": login["profileUsernameSelector"], "kind": "text",
                                          "expected": "aoteman", "observed": user.inner_text()},
                                         {"selector": "ui-request:tenant-name-resolution", "kind": "text",
                                          "expected": "122", "observed": str(identity["resolved"])},
                                         {"selector": "ui-request:authenticated-tenant-header", "kind": "text",
                                          "expected": "122", "observed": identity["lastTenant"]}],
                          "screenshotPin": capture(0), "download": None})
            for index, flow in enumerate(config["flows"], 1):
                assertions, downloaded = [], None
                before_mutations = dict(successful_mutations)
                for step in [*flow["entrySteps"], *flow["steps"]]:
                    timeout = budget()
                    locator, kind = page.locator(step["selector"]), step["kind"]
                    if kind == "click":
                        locator.click()
                    elif kind == "fill":
                        locator.fill(step["value"])
                    elif kind == "press":
                        locator.press(step["key"])
                    elif kind == "upload":
                        read_pin(step["contentPin"], deadline, content=False)
                        locator.set_input_files(step["contentPin"]["path"])
                        read_pin(step["contentPin"], deadline, content=False)
                    elif kind in ("captureReference", "objectReference"):
                        expect(locator).to_be_visible(timeout=timeout)
                        tag = locator.evaluate("e => e.tagName.toLowerCase()")
                        need(tag in ("img", "a"), "UI_REAL_OBJECT_ELEMENT_REQUIRED")
                        actual_url = locator.get_attribute("src" if tag == "img" else "href")
                        parsed = urlsplit(text(actual_url))
                        need(origin(actual_url) in set(config["objectOrigins"]) and not parsed.query
                             and not parsed.fragment and "/showroom/" not in parsed.path,
                             "UI_OBJECT_REFERENCE_OUTSIDE_SCOPE")
                        if kind == "captureReference":
                            read_pin(step["contentPin"], deadline, content=False)
                            references.append({"pathId": flow["pathId"], "selector": step["selector"],
                                               "objectPath": parsed.path, "contentPin": step["contentPin"]})
                        else:
                            matches = [item for item in source_references if item["pathId"] == step["sourcePathId"]
                                       and item["selector"] == step["sourceSelector"]]
                            need(len(matches) == 1, "UI_SOURCE_REFERENCE_AMBIGUOUS")
                            need(parsed.path == matches[0]["objectPath"], "UI_RESTORED_REFERENCE_MISMATCH", "FAILED")
                            assertions.append({"selector": step["selector"], "kind": "text",
                                               "expected": matches[0]["objectPath"], "observed": parsed.path})
                    elif kind == "download":
                        destination = root / ("download-" + str(index) + ".bin")
                        need(not destination.exists(), "UI_DOWNLOAD_EXISTS")
                        with page.expect_download(timeout=timeout) as event:
                            locator.click()
                        download = event.value
                        need(download.failure() is None, "UI_DOWNLOAD_FAILED", "FAILED")
                        download.save_as(str(destination))
                        pin = file_pin(str(destination), deadline)
                        need(pin["bytes"] == step["expectedBytes"] and pin["sha256"] == step["expectedSha256"],
                             "UI_DOWNLOAD_CONTENT_MISMATCH", "FAILED")
                        downloaded = {"expectedBytes": step["expectedBytes"], "expectedSha256": step["expectedSha256"],
                                      "actualBytes": pin["bytes"], "actualSha256": pin["sha256"], "contentPin": pin}
                    else:
                        if kind == "text":
                            expect(locator).to_have_text(step["expected"], timeout=timeout)
                            observed = locator.inner_text()
                        elif kind == "value":
                            expect(locator).to_have_value(step["expected"], timeout=timeout)
                            observed = locator.input_value()
                        elif kind == "count":
                            expect(locator).to_have_count(step["expected"], timeout=timeout)
                            observed = locator.count()
                        elif kind == "attribute":
                            expect(locator).to_have_attribute(step["name"], step["expected"], timeout=timeout)
                            observed = locator.get_attribute(step["name"])
                        else:
                            expect(locator).to_be_visible(timeout=timeout)
                            expect(locator).to_have_js_property("complete", True, timeout=timeout)
                            need(locator.evaluate("e => e.naturalWidth > 0 && e.naturalHeight > 0"),
                                 "UI_IMAGE_NOT_RENDERED", "FAILED")
                            observed = True
                        expected = True if kind == "image" else step["expected"]
                        need(observed == expected, "UI_ASSERTION_FAILED", "FAILED")
                        # Preserve the v1 consumer's assertion shape. The actual step kind
                        # stays in the caller-pinned config, including value/count/attribute.
                        assertions.append({"selector": step["selector"],
                                           "kind": "image" if kind == "image" else "text",
                                           "expected": expected, "observed": observed})
                budget()
                if config["phase"] != "target":
                    mutation = flow_mutations[flow["pathId"]]
                    need(successful_mutations.get(mutation, 0) > before_mutations.get(mutation, 0),
                         "UI_REAL_BUSINESS_MUTATION_NOT_OBSERVED", "FAILED")
                    if any(step["kind"] == "upload" for step in flow["steps"]):
                        need(successful_mutations.get("/infra/file/upload", 0) > before_mutations.get("/infra/file/upload", 0),
                             "UI_REAL_UPLOAD_NOT_OBSERVED", "FAILED")
                paths.append({"pathId": flow["pathId"], "entrySelector": flow["entrySteps"][0]["selector"],
                              "assertions": assertions, "screenshotPin": capture(index), "download": downloaded})
            budget()
            context.close()
        finally:
            browser.close()
    return {"engine": "playwright", "targetOrigin": selected_origin, "tenantId": 122,
            "tenantName": "测试租户", "username": "aoteman", "paths": paths,
            "blockedExternalRequests": counters["blocked"], "pageErrorCount": counters["errors"],
            "businessFailureCount": counters["failures"]}, references
