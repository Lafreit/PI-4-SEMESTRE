document.addEventListener("DOMContentLoaded", function() {
    const btnPagar = document.querySelector(".btn-pagar");
    const mensagensContainer = document.getElementById("mensagens-corrida");

    if (!btnPagar) return;

    btnPagar.addEventListener("click", function() {
        const corridaId = btnPagar.dataset.corridaId;
        const confirmar = window.confirm("Tem certeza que deseja pagar esta corrida?");
        if (!confirmar) return;

        fetch(`/pagamentos/corrida/${corridaId}/pagar/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken"),
            },
        })
        .then(res => res.json())
        .then(data => {
            if (data.ok) {
                mostrarMensagem("Pagamento efetuado com sucesso!", "success");

                // Atualiza o status do pagamento no card
                atualizarStatusPagamento(corridaId);

                // Remove o botão após pagamento
                btnPagar.remove();
            } else {
                mostrarMensagem("Erro: " + (data.error || "desconhecido"), "danger");
            }
        })
        .catch(err => {
            console.error(err);
            mostrarMensagem("Erro ao processar pagamento", "danger");
        });
    });

    function atualizarStatusPagamento(corridaId) {
        fetch(`/pagamentos/corrida/${corridaId}/status/`, {  // endpoint que retorna JSON {status: "PAID"/"PENDING"}
            method: "GET",
            headers: {
                "X-CSRFToken": getCookie("csrftoken"),
                "Accept": "application/json"
            },
        })
        .then(res => res.json())
        .then(data => {
            const statusElem = document.querySelector(".status-badge");
            if (!statusElem) return;

            if (data.status === "PAID") {
                statusElem.textContent = "Pago";
                statusElem.className = "status-badge status-finalizada";
            } else {
                statusElem.textContent = "Pendente";
                statusElem.className = "status-badge status-em_andamento";
            }
        })
        .catch(err => {
            console.error(err);
        });
    }

    function mostrarMensagem(texto, tipo) {
        const div = document.createElement("div");
        div.textContent = texto;
        div.style.padding = "10px 16px";
        div.style.borderRadius = "8px";
        div.style.marginBottom = "8px";
        div.style.color = tipo === "success" ? "#16a34a" : "#ef4444";
        div.style.background = tipo === "success" ? "rgba(22,163,74,0.1)" : "rgba(239,68,68,0.1)";
        div.style.fontWeight = "600";
        mensagensContainer.appendChild(div);
        setTimeout(() => div.remove(), 5000);
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i=0; i<cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length+1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length+1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
