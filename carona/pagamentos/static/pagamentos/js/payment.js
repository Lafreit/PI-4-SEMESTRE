document.addEventListener('DOMContentLoaded', function() {
  // Botão copiar BR Code
  const copyBtn = document.getElementById('copy-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', function() {
      const brcode = document.getElementById('brcode');
      brcode.select();
      brcode.setSelectionRange(0, 99999); // Para mobile
      document.execCommand('copy');
      alert('Código copiado!');
    });
  }

  const paymentIdEl = document.getElementById('payment-id');
  if (!paymentIdEl) return;
  const paymentId = paymentIdEl.value;

  const statusEl = document.getElementById('status');
  const qrImg = document.getElementById('pix-qrcode');
  const brCodeEl = document.getElementById('brcode');
  const countdownEl = document.getElementById('countdown');

  // Pega tempo restante
  let expiresIn = parseInt(document.getElementById('expires-in')?.value || 3600);
  let countdownInterval;

  const showExpiredNotice = () => {
    if (!statusEl) return;
    statusEl.textContent = "QR Code expirou, atualizando...";
    statusEl.style.color = "red";
    countdownEl.textContent = "";
  };

  const updateCountdown = () => {
    if (expiresIn <= 0) {
      clearInterval(countdownInterval);
      showExpiredNotice();
      return;
    }
    let minutes = Math.floor(expiresIn / 60);
    let seconds = expiresIn % 60;
    countdownEl.textContent = `Expira em: ${minutes}m ${seconds}s`;
    expiresIn -= 1;
  };

  countdownInterval = setInterval(updateCountdown, 1000);
  updateCountdown();

  // Atualiza QR Code automaticamente quando expira ou falha
  const refreshQr = async () => {
    showExpiredNotice(); // aviso visual
    try {
      const res = await fetch(`/pagamentos/refresh_qr/${paymentId}/`);
      if (!res.ok) return;

      const data = await res.json();
      if (data.ok && data.data) {
        if (data.data.brCodeBase64 && qrImg) qrImg.src = "data:image/png;base64," + data.data.brCodeBase64;
        if (data.data.brCode && brCodeEl) brCodeEl.value = data.data.brCode;
        if (statusEl) {
          statusEl.textContent = data.status;
          statusEl.style.color = "orange"; // atualizado
        }
        // reset timer
        expiresIn = data.data.expires_in || 3600;
        clearInterval(countdownInterval);
        countdownInterval = setInterval(updateCountdown, 1000);
        updateCountdown();
        console.log("QR Code expirado foi atualizado!");
      }
    } catch (err) {
      console.error("Erro atualizando QR Code:", err);
    }
  };

  // Checa status do pagamento a cada 3s
  const checkStatus = async () => {
    try {
      const res = await fetch(`/pagamentos/status/${paymentId}/`);
      if (!res.ok) return;

      const data = await res.json();
      if (data.status && statusEl) statusEl.textContent = data.status;

      if (data.status === "EXPIRED" || data.status === "FAILED") {
        refreshQr();
      }
    } catch (err) {
      console.error("Erro checando status:", err);
    }
  };

  setInterval(checkStatus, 3000);
});
