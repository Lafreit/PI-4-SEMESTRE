document.addEventListener("DOMContentLoaded", function () {

    console.log("JS de notificações carregado. Motorista =", window.USER_IS_MOTORISTA);

    const notifItems = document.querySelectorAll(".notif-item");

    notifItems.forEach(item => {
        const corridaId = item.dataset.corrida;
        const notifId = item.dataset.id;

        /* ==========================================================
           PASSAGEIRO → CARD NÃO CLICA
        ========================================================== */
        if (!window.USER_IS_MOTORISTA) {
            item.style.cursor = "default";

            item.addEventListener("click", (e) => {
                e.stopPropagation(); // previne clique no card
            });

            return; // passageiro sai daqui
        }

        /* ==========================================================
           MOTORISTA → CARD DEVE ABRIR DETALHES
        ========================================================== */
        if (window.USER_IS_MOTORISTA && corridaId) {
            item.style.cursor = "pointer";

            item.addEventListener("click", function (e) {
                // Evita conflito com botões dentro do card
                if (e.target.closest(".btn-acao")) return;

                window.location.href = `/corrida/detalhes/${corridaId}`;
            });
        }

        /* ==========================================================
           BOTÃO MARCAR COMO LIDA
        ========================================================== */
        const btnLida = item.querySelector(".btn-marcar-lida");
        if (btnLida) {
            btnLida.addEventListener("click", function (e) {
                e.stopPropagation();
                marcarComoLida(notifId, item);
            });
        }
    });

    atualizarContagem();
    setInterval(atualizarContagem, 6000);
});

/* ------------------------------ */
function marcarComoLida(id, element) {
    fetch("/notificacao/api/marcar_lida/", {
        method: "POST",
        headers: {
            "X-CSRFToken": getCSRF(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: "id=" + id
    })
    .then(r => r.json())
    .then(() => {
        element.classList.remove("nao-lida");
        const btn = element.querySelector(".btn-marcar-lida");
        if (btn) btn.remove();
        atualizarContagem();
    });
}

/* ------------------------------ */
function atualizarContagem() {
    fetch("/notificacao/api/contagem/")
        .then(r => r.json())
        .then(data => {
            const badge = document.getElementById("notif-badge");
            badge.textContent = data.unread || 0;
        });
}

/* ------------------------------ */
function getCSRF() {
    const name = "csrftoken=";
    const cookies = document.cookie.split(";");
    for (let c of cookies) {
        c = c.trim();
        if (c.startsWith(name)) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}
