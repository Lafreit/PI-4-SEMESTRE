document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("adicionar-saldo-form");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const valorInput = form.querySelector("input[name='valor']");
    const valor = parseFloat(valorInput.value);

    if (isNaN(valor) || valor <= 0) {
      alert("Informe um valor válido para adicionar saldo.");
      valorInput.focus();
      return;
    }

    const btn = form.querySelector("button[type='submit']");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Processando...";
    }

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
          "Accept": "application/json"
        },
        body: new URLSearchParams({ valor: valorInput.value })
      });

      // Garante que sempre lidamos com JSON
      const data = await response.json();

      if (data.success && data.url) {
        // Redireciona para página de pagamento AbacatePay
        window.location.href = data.url;
      } else {
        // Caso de erro, mostra alerta e recarrega para exibir messages do Django
        alert(data.message || "Erro ao processar pagamento");
        window.location.reload();
      }

    } catch (err) {
      alert("Erro ao processar o pagamento. Tente novamente.");
      console.error("Erro no fetch:", err);
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Adicionar";
      }
    }
  });
});
