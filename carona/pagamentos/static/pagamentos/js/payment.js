document.addEventListener('DOMContentLoaded', function() {
  const copyBtn = document.getElementById('copy-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', function() {
      const br = document.getElementById('brcode');
      br.select();
      document.execCommand('copy');
      alert('Código copiado para a área de transferência');
    });
  }

  const paymentIdEl = document.getElementById('payment-id');
  const paymentId = paymentIdEl ? paymentIdEl.value : null;
  if (paymentId) {
    const statusEl = document.getElementById('status');
    const check = async () => {
      try {
        const res = await fetch(`/pagamentos/status/${paymentId}/`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.status && statusEl) statusEl.textContent = data.status;
      } catch (err) {
        console.error('Erro checando status:', err);
      }
    };
    setInterval(check, 3000);
  }
});
