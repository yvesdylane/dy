const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

(async () => {
    try {
        const response = await fetch("/auth/telegram", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                initData: tg.initData
            })
        });

        const result = await response.json();

        if (result.ok) {
            window.location.href = result.redirect;
        } else if (result.needs_registration) {
            window.location.href = "/register";
        } else {
            const el = document.getElementById("errorMsg");
            if (el) {
                el.textContent = result.detail || "Authentication failed";
                el.classList.remove("hidden");
            }
        }
    } catch (e) {
        const el = document.getElementById("errorMsg");
        if (el) {
            el.textContent = "Network error — check your connection";
            el.classList.remove("hidden");
        }
    }
})();
