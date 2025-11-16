(function () {
  'use strict';

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie('csrftoken');

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

      const res = await fetch('/notificacoes/api/marcar_lida/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        body: form,
        credentials: 'same-origin'
      });

      if (!res.ok) {
        console.error('Erro ao marcar lida', res.status);
        btn.disabled = false;
        return;
      }

      // atualizar UI: remover botão e estilizar
      const item = btn.closest('.notif-item');
      if (item) {
        item.classList.remove('nao-lida');
        btn.remove();
      }
      // atualizar badge
      atualizarBadge();

    } catch (err) {
      console.error('Erro de rede marcar lida', err);
      btn.disabled = false;
    }
  });

  // atualiza badge de não-lidas
  async function atualizarBadge() {
    try {
      const res = await fetch('/notificacoes/api/contagem/?_=' + Date.now(), {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) return;
      const js = await res.json();
      const badge = qs('#notif-badge');
      if (badge) badge.textContent = js.unread ? `${js.unread} não-lida(s)` : 'Sem novas';
    } catch (e) {
      // ignore
    }
  }

  // roda ao carregar e a cada 20s
  document.addEventListener('DOMContentLoaded', () => {
    atualizarBadge();
    setInterval(atualizarBadge, 20000);
  });

})();
