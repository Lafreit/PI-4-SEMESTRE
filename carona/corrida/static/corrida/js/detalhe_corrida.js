// static/corrida/js/detalhe_corrida.js
(function () {
  'use strict';

  function qs(sel, el = document) { return el.querySelector(sel); }
  function qsa(sel, el = document) { return Array.from(el.querySelectorAll(sel)); }

  // ----------------------------
  // Aceitar solicitação de carona
  // ----------------------------
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btn-aceitar');
    if (!btn) return;

    const corridaId = btn.dataset.corrida;
    const solicitacaoId = btn.dataset.solicitacao;

    if (!corridaId || !solicitacaoId) return;

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

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.erro) {
        console.error('Erro ao aceitar solicitação', res.status, data.erro);
        btn.disabled = false;
        return;
      }

      // Atualiza visualmente a solicitação
      const item = btn.closest('.solicitacao-item');
      if (item) {
        item.classList.remove('pendente');
        item.classList.add('aceita');
        btn.remove();
      }

      // Atualiza badge de notificações
      atualizarBadge();

    } catch (err) {
      console.error('Erro de rede ao aceitar solicitação', err);
      btn.disabled = false;
    }
  });

  // ----------------------------
  // Atualizar badge de notificações
  // ----------------------------
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

      // Atualiza automaticamente solicitações aceitas se vierem do backend
      if (js.atualizar_solicitacoes && Array.isArray(js.atualizar_solicitacoes)) {
        js.atualizar_solicitacoes.forEach(id => {
          const item = qs(`.solicitacao-item[data-solicitacao="${id}"]`);
          if (item && item.classList.contains('pendente')) {
            item.classList.remove('pendente');
            item.classList.add('aceita');
            const btn = qs('.btn-aceitar', item);
            if (btn) btn.remove();
          }
        });
      }

    } catch (err) {
      console.error('Erro ao atualizar badge', err);
    }
  }

  // Atualiza ao carregar a página e a cada 20s
  document.addEventListener('DOMContentLoaded', () => {
    atualizarBadge();
    setInterval(atualizarBadge, 20000);
  });

})();
