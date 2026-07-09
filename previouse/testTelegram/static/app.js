const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

console.log("Telegram WebApp:", tg);
console.log("initData:", tg.initData);
console.log("initDataUnsafe:", tg.initDataUnsafe);

document.body.innerHTML += `
    <h2>Telegram Debug</h2>

    <h3>initData</h3>
    <pre>${tg.initData}</pre>

    <h3>initDataUnsafe</h3>
    <pre>${JSON.stringify(tg.initDataUnsafe, null, 2)}</pre>
`;

const user = tg.initDataUnsafe.user;

if (user) {
    document.body.innerHTML += `
        <button id="btn">Call API</button>
        <pre id="result"></pre>
    `;

    document.getElementById("btn").onclick = async () => {
        const response = await fetch(`/api/hello/${user.username ?? user.first_name}`);
        const data = await response.json();

        document.getElementById("result").textContent =
            JSON.stringify(data, null, 2);
    };


}