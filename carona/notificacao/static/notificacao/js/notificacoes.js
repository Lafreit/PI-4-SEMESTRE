(function () {
  'use strict';

  function qs(sel, el=document) { return el.querySelector(sel); }
  function qsa(sel, el=document) { return Array.from(el.querySelectorAll(sel)); }

  // marcar como lida
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-marcar-lida');
    if (!btn) return;

    const id = btn.dataset.id;
    if (!id) return;

    btn.disabled = true;

    try {
      const form = new FormData();
      form.append('id', id);

      const res = await fetch(URL_MARCAR_LIDA, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF_TOKEN },
        body: form,
        credentials: 'same-origin'
      });

      if (!res.ok) {
        console.error('Erro ao marcar lida', res.status);
        btn.disabled = false;
        return;
      }

      const item = btn.closest('.notif-item');
      if (item) {
        item.classList.add('marcar-lida');
        btn.remove();
        setTimeout(() => item.remove(), 500);
      }

      atualizarBadge();

    } catch (err) {
      console.error('Erro de rede marcar lida', err);
      btn.disabled = false;
    }
  });

  // aceitar solicitação da corrida
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-aceitar');
    if (!btn) return;

    const corridaId = btn.dataset.corrida;
    const solicitacaoId = btn.dataset.solicitacao;

    btn.disabled = true;

    try {
      const form = new FormData();
      form.append('corrida_id', corridaId);
      form.append('solicitacao_id', solicitacaoId);

      const res = await fetch(URL_ACEITAR, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF_TOKEN },
        body: form,
        credentials: 'same-origin'
      });

      if (!res.ok) {
        console.error('Erro ao aceitar solicitação', res.status);
        btn.disabled = false;
        return;
      }

      // opcional: marcar como lida após aceitar
      const item = btn.closest('.notif-item');
      if (item) {
        item.classList.add('marcar-lida');
        btn.remove();
        setTimeout(() => item.remove(), 500);
      }

      atualizarBadge();

    } catch (err) {
      console.error('Erro de rede aceitar solicitação', err);
      btn.disabled = false;
    }
  });

  // atualizar badge
  async function atualizarBadge() {
    try {
      const res = await fetch(URL_CONTAGEM + "?_=" + Date.now(), {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      });

      if (!res.ok) return;

      const js = await res.json();
      const badge = qs('#notif-badge');
      if (badge) badge.textContent = js.unread ? `${js.unread} não-lida(s)` : 'Sem novas';

    } catch (err) {
      console.error('Erro ao atualizar badge', err);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    atualizarBadge();
    setInterval(atualizarBadge, 20000);
  });

})();
