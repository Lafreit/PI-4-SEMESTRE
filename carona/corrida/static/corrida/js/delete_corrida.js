// helper para ler cookie (padrão Django)
function getCookie(name) {
    const value = `; ${document.cookie || ''}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function mostrarToast(mensagem) {
    // simples alert — substitua por toast se tiver
    alert(mensagem);
}

async function deletarCorridaAJAX(url, corridaId, btn) {
    const csrftoken = getCookie('csrftoken');
    if (!csrftoken) {
        console.error("CSRF token not found (cookie 'csrftoken').");
        mostrarToast("Erro: token CSRF ausente. Faça login novamente e tente de novo.");
        return;
    }

    try {
        const confirmed = confirm("Tem certeza que deseja excluir esta corrida?");
        if (!confirmed) return;

        btn.disabled = true;
        const originalText = btn.innerText;
        btn.innerText = "Excluindo...";

        console.debug("DELETE: sending POST to", url, "for corrida", corridaId);

        const resp = await fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrftoken,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
            credentials: "same-origin",
        });

        console.debug("DELETE: response status", resp.status);

        if (resp.ok) {
            const data = await resp.json().catch(() => null);
            if (data && data.ok) {
                const row = document.getElementById(`corrida-row-${corridaId}`);
                if (row) row.remove();
                mostrarToast("Corrida excluída com sucesso.");
                return;
            } else {
                // resposta ok mas sem {ok: true}
                console.warn("DELETE: resposta OK mas payload inesperado:", data);
                mostrarToast(data?.error || "Não foi possível excluir a corrida.");
                return;
            }
        }

        // não ok (status >= 400)
        if (resp.status === 403) {
            mostrarToast("Você não tem permissão para excluir essa corrida.");
            return;
        }

        // tenta extrair erro do body
        let text;
        try {
            const json = await resp.json();
            text = json.error || JSON.stringify(json);
        } catch (e) {
            text = await resp.text();
        }
        console.error("DELETE: erro do servidor:", resp.status, text);
        mostrarToast("Erro ao excluir: " + text);

    } catch (err) {
        console.error("Erro ao excluir corrida:", err);
        mostrarToast("Erro de rede ao tentar excluir. Tente novamente.");
    } finally {
        btn.disabled = false;
        btn.innerText = btn.dataset.originalText || "Excluir";
    }
}

// Delegação: captura clicks em qualquer botão .btn-delete-corrida (funciona mesmo se DOM mudar)
document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-delete-corrida");
    if (!btn) return;

    e.preventDefault();

    // prepara id / url
    const corridaId = btn.dataset.corridaId || btn.getAttribute("data-corrida-id");
    const dataUrl = btn.dataset.url || btn.getAttribute("data-url");

    // prioridade: data-url (setado via template com {% url %}), senão monta pela rota padrão
    let url = null;
    if (dataUrl) {
        url = dataUrl;
    } else if (corridaId) {
        url = `/corrida/deletar/${corridaId}/`;
    } else {
        console.error("Botão de deletar sem data-corrida-id nem data-url:", btn);
        mostrarToast("Erro interno: id da corrida não encontrado.");
        return;
    }

    // guarda texto original caso precise restaurar
    if (!btn.dataset.originalText) btn.dataset.originalText = btn.innerText;

    // chama a função
    deletarCorridaAJAX(url, corridaId, btn);
});
