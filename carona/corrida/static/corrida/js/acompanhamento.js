document.addEventListener("DOMContentLoaded", function() {
    // Seleciona todos os botões de pagamento de corrida
    const btns = document.querySelectorAll(".btn-pagar-corrida");
    if (!btns.length) return;

    btns.forEach(btn => {
        btn.addEventListener("click", function() {
            const corridaId = btn.dataset.corridaId;
            const confirmar = window.confirm("Tem certeza que deseja pagar esta corrida?");
            if (!confirmar) return;

            // envia POST via fetch
            fetch(`/pagamentos/corrida/${corridaId}/pagar/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            })
            .then(res => res.json())
            .then(data => {
                if (data.ok) {
                    alert("Pagamento efetuado com sucesso!");
                    // atualiza status no card sem recarregar a página
                    const card = document.getElementById(`corrida-card-${corridaId}`);
                    if (card) {
                        const statusElem = card.querySelector(".status-corrida");
                        if (statusElem) statusElem.textContent = "Pago";
                        // remove o botão após pagamento
                        btn.remove();
                    }
                } else {
                    alert("Erro ao processar pagamento: " + (data.error || "desconhecido"));
                }
            })
            .catch(err => {
                console.error(err);
                alert("Erro ao processar pagamento");
            });
        });
    });

    // função utilitária para pegar CSRF do cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
