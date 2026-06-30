const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

(async () => {
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
    }
})();
