const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

(async () => {

    console.log("initData:", tg.initData);

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

    console.log(result);

})();