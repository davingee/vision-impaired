// Safari and Chrome through their scripting dictionaries. Page reading and clicking
// need "Allow JavaScript from Apple Events" in the browser.
ObjC.import("Foundation");

// Runs inside the web page. Fixed code; the request arrives as a JSON literal, never as source.
function inPage(request) {
    const shown = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const label = e => (e.getAttribute("aria-label") || e.innerText || e.title || e.value || "")
        .trim().replace(/\s+/g, " ").slice(0, 120);
    // Pop-ups (like a show's details) come first so their buttons are not cut off.
    // Then the page's main content, so a big site header (Amazon's) cannot crowd it out.
    const inDialog = e => e.closest("[role=dialog], [aria-modal=true]") ? 0
        : e.closest("main, [role=main]") ? 1 : 2;
    const controls = [...document.querySelectorAll(
        "a, button, [role=button], [role=link], [role=tab], input[type=submit]")]
        .filter(shown).sort((a, b) => inDialog(a) - inDialog(b))
        .map(e => [e, label(e)]).filter(c => c[1]);
    if (request.action === "type") {
        // Search boxes built with React ignore a plain value change; use the native setter
        // and fire the events a person's typing would.
        const field = [...document.querySelectorAll("input[type=search], input[type=text], input:not([type])")]
            .filter(shown).find(e => /search/i.test(
                (e.getAttribute("aria-label") || "") + (e.placeholder || "") + e.type + e.name + e.id))
            || document.querySelector("input[type=search]");
        if (!field) return JSON.stringify({status: "no_search_box"});
        field.focus();
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(field, request.text);
        field.dispatchEvent(new Event("input", {bubbles: true}));
        field.dispatchEvent(new Event("change", {bubbles: true}));
        field.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", code: "Enter", keyCode: 13, bubbles: true}));
        return JSON.stringify({status: "typed"});
    }
    if (request.action === "click") {
        const want = request.label.toLowerCase();
        const hit = controls.find(c => c[1].toLowerCase() === want)
            || controls.find(c => c[1].toLowerCase().includes(want));
        if (!hit) return JSON.stringify({status: "not_found",
            controls: [...new Set(controls.map(c => c[1]))].slice(0, 80)});
        hit[0].click();
        return JSON.stringify({status: "clicked", label: hit[1]});
    }
    // Netflix labels the signed-in profile's avatar; "Kids" beside it is only a shortcut.
    const avatar = document.querySelector('[data-uia="navigation+profile-menu+Avatar"]');
    return JSON.stringify({title: document.title, url: location.href,
        active_profile: avatar ? avatar.getAttribute("alt") : undefined,
        // A playing video is proof; some players (Prime) open without a new address.
        video_playing: [...document.querySelectorAll("video")].some(v => !v.paused && v.currentTime > 0),
        text: document.body.innerText.slice(0, request.max_chars),
        controls: [...new Set(controls.map(c => c[1]))].slice(0, 150)});
}

function run(argv) {
    const data = $.NSData.dataWithContentsOfFile(argv[0]);
    if (!data) throw Error("Cannot read request.");
    const request = JSON.parse(ObjC.unwrap(
        $.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding)));
    if (!["Safari", "Google Chrome"].includes(request.app)) throw Error("Unsupported browser.");
    const app = Application(request.app);
    if (!app.running()) throw Error(request.app + " is not open.");
    const chrome = request.app === "Google Chrome";
    if (request.action === "tabs") {
        const tabs = [];
        app.windows().forEach((w, wi) => {
            try {
                w.tabs().forEach((t, ti) => tabs.push({window: wi + 1, tab: ti + 1,
                    title: chrome ? t.title() : t.name(), url: t.url()}));
            } catch (e) {}  // Windows without tabs, such as Settings.
        });
        return JSON.stringify({browser: request.app, tabs: tabs});
    }
    if (!["read", "click", "type", "navigate"].includes(request.action)) throw Error("Unknown browser action.");
    if (app.windows.length === 0) throw Error(request.app + " has no open window.");
    const front = app.windows[0];
    if (request.action === "navigate") {  // Same tab, so a multi-step task leaves one tab.
        if (!/^https?:/.test(request.url)) throw Error("Only web addresses.");
        (chrome ? front.activeTab : front.currentTab).url = request.url;
        return JSON.stringify({status: "navigating"});
    }
    const code = "(" + inPage.toString() + ")(" + JSON.stringify(request) + ")";
    return chrome ? front.activeTab.execute({javascript: code})
                  : app.doJavaScript(code, {in: front.currentTab});
}
