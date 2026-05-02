const OVERLAY_ID = "focus-buddy-overlay";
const ASK_POPUP_ID = "focus-buddy-ask-popup";

chrome.runtime.onMessage.addListener((request) => {
    if (request.action === "hard_ban") {
        showHardBan(request);
        return;
    }

    if (request.action === "ask_user") {
        showAskUser(request);
    }
});

function removeFocusBuddyUi() {
    document.getElementById(OVERLAY_ID)?.remove();
    document.getElementById(ASK_POPUP_ID)?.remove();
    document.documentElement.style.overflow = "";
    document.body.style.overflow = "";
}

function showAskUser(details) {
    removeFocusBuddyUi();

    const popup = document.createElement("aside");
    popup.id = ASK_POPUP_ID;
    popup.setAttribute("role", "dialog");
    popup.setAttribute("aria-live", "polite");
    popup.style.cssText = `
        position: fixed;
        top: 84px;
        right: 18px;
        width: min(340px, calc(100vw - 36px));
        box-sizing: border-box;
        z-index: 2147483647;
        padding: 16px;
        border: 1px solid #dfe3ea;
        border-radius: 12px;
        background: #ffffff;
        color: #202124;
        box-shadow: 0 18px 48px rgba(32, 33, 36, 0.22);
        font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    `;

    const title = makeElement("h2", "Are you procrastinating?", `
        margin: 0 28px 8px 0;
        font-size: 17px;
        line-height: 1.25;
        font-weight: 650;
        color: #202124;
    `);

    const closeButton = makeElement("button", "x", `
        position: absolute;
        top: 10px;
        right: 10px;
        width: 28px;
        height: 28px;
        border: 0;
        border-radius: 50%;
        background: transparent;
        color: #5f6368;
        cursor: pointer;
        font-size: 18px;
        line-height: 28px;
    `);
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "Dismiss");
    closeButton.addEventListener("click", () => popup.remove());

    const message = makeElement("p", buildAskMessage(details), `
        margin: 0 0 14px;
        color: #4b5563;
        font-size: 13px;
        line-height: 1.45;
    `);

    const actions = document.createElement("div");
    actions.style.cssText = `
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    `;

    const yesButton = makeButton("Yes", true);
    const noButton = makeButton("No", false);
    yesButton.addEventListener("click", () => showReminderStep(popup, details));
    noButton.addEventListener("click", () => popup.remove());

    actions.append(yesButton, noButton);
    popup.append(title, closeButton, message, actions);
    document.documentElement.appendChild(popup);
}

function showReminderStep(popup, details) {
    popup.replaceChildren();

    const title = makeElement("h2", "Want a reminder?", `
        margin: 0 0 8px;
        font-size: 17px;
        line-height: 1.25;
        font-weight: 650;
        color: #202124;
    `);
    const message = makeElement("p", "Choose when Focus Buddy should nudge you back.", `
        margin: 0 0 14px;
        color: #4b5563;
        font-size: 13px;
        line-height: 1.45;
    `);

    const options = document.createElement("div");
    options.style.cssText = `
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
    `;

    [
        { label: "5 min", minutes: 5 },
        { label: "10 min", minutes: 10 },
        { label: "20 min", minutes: 20 },
    ].forEach(({ label, minutes }) => {
        const button = makeButton(label, true);
        button.addEventListener("click", () => scheduleReminder(minutes, details));
        options.appendChild(button);
    });

    const skipButton = makeButton("No reminder", false);
    skipButton.style.marginTop = "8px";
    skipButton.addEventListener("click", () => popup.remove());

    popup.append(title, message, options, skipButton);
}

function scheduleReminder(minutes, details) {
    const popup = document.getElementById(ASK_POPUP_ID);
    if (popup) {
        popup.replaceChildren(
            makeElement("h2", "Reminder set", `
                margin: 0 0 8px;
                font-size: 17px;
                line-height: 1.25;
                font-weight: 650;
                color: #202124;
            `),
            makeElement("p", `I'll check back in ${minutes} minutes.`, `
                margin: 0;
                color: #4b5563;
                font-size: 13px;
                line-height: 1.45;
            `),
        );

        window.setTimeout(() => popup.remove(), 1800);
    }

    window.setTimeout(() => {
        showAskUser({
            ...details,
            reason: "Reminder: are you still procrastinating?",
        });
    }, minutes * 60 * 1000);
}

function showHardBan(details) {
    removeFocusBuddyUi();

    const overlay = document.createElement("div");
    overlay.id = OVERLAY_ID;
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        z-index: 2147483647;
        display: grid;
        place-items: center;
        box-sizing: border-box;
        padding: 24px;
        background: #f8fafc;
        color: #202124;
        font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    `;

    const panel = document.createElement("section");
    panel.style.cssText = `
        width: min(460px, 100%);
        box-sizing: border-box;
        padding: 28px;
        border: 1px solid #d9dee8;
        border-radius: 12px;
        background: #ffffff;
        box-shadow: 0 22px 60px rgba(32, 33, 36, 0.2);
        text-align: center;
    `;

    const title = makeElement("h1", "This page is blocked", `
        margin: 0 0 10px;
        font-size: 24px;
        line-height: 1.2;
        font-weight: 700;
        color: #111827;
    `);
    const message = makeElement("p", details.reason || "Focus Buddy blocked this tab for your current session.", `
        margin: 0 0 18px;
        color: #4b5563;
        font-size: 14px;
        line-height: 1.5;
    `);

    const meta = makeElement("p", buildMetaText(details), `
        margin: 0 0 20px;
        color: #6b7280;
        font-size: 12px;
        line-height: 1.4;
    `);

    const closeTabButton = makeButton("Close tab", true);
    closeTabButton.style.width = "100%";
    closeTabButton.addEventListener("click", () => {
        chrome.runtime.sendMessage({ closeTab: true });
    });

    const dashboardLink = document.createElement("a");
    dashboardLink.textContent = "Open dashboard";
    dashboardLink.href = details.web_url || "#";
    dashboardLink.target = "_blank";
    dashboardLink.rel = "noopener noreferrer";
    dashboardLink.style.cssText = `
        display: inline-block;
        margin-top: 14px;
        color: #1a73e8;
        font-size: 13px;
        font-weight: 600;
        text-decoration: none;
    `;

    panel.append(title, message, meta, closeTabButton, dashboardLink);
    overlay.appendChild(panel);
    document.documentElement.appendChild(overlay);

    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
}

function buildAskMessage({ reason, classification, confidence }) {
    if (reason) return reason;

    const confidenceText =
        typeof confidence === "number" ? `${Math.round(confidence * 100)}% AI confidence` : "unknown AI confidence";
    return `This page looks ${classification || "uncertain"} with ${confidenceText}.`;
}

function buildMetaText({ classification, confidence, sessionType }) {
    const parts = [];
    if (classification) parts.push(`Classification: ${classification}`);
    if (typeof confidence === "number") parts.push(`AI confidence: ${Math.round(confidence * 100)}%`);
    if (sessionType) parts.push(`Session: ${sessionType}`);
    return parts.join(" | ");
}

function makeButton(label, primary) {
    const button = makeElement("button", label, `
        min-height: 38px;
        border: 1px solid ${primary ? "#1a73e8" : "#d1d5db"};
        border-radius: 8px;
        background: ${primary ? "#1a73e8" : "#ffffff"};
        color: ${primary ? "#ffffff" : "#374151"};
        cursor: pointer;
        font-size: 13px;
        font-weight: 650;
        font-family: inherit;
    `);
    button.type = "button";
    return button;
}

function makeElement(tagName, text, cssText) {
    const element = document.createElement(tagName);
    element.textContent = text;
    element.style.cssText = cssText;
    return element;
}
