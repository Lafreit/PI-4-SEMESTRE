/* static/corrida/js/detalhe_corrida.js */
(function () {
  'use strict';

  function qs(sel, el = document) { return (el || document).querySelector(sel); }
  function qsa(sel, el = document) { return Array.from((el || document).querySelectorAll(sel)); }

  // Pega CSRF token do cookie padrão do Django
  function getCookie(name) {
    if (!document.cookie) return null;
    const cookies = document.cookie.split(';').map(c => c.trim());
    for (let cookie of cookies) {
      if (cookie.startsWith(name + '=')) return decodeURIComponent(cookie.split('=')[1]);
    }
    return null;
  }
  const CSRF_TOKEN = getCookie('csrftoken');

  // rota responder (fazer o replace se RESPONDER_URL_TEMPLATE existir)
  function responderUrlFor(solicitacaoId) {
    if (typeof RESPONDER_URL_TEMPLATE !== 'undefined' && RESPONDER_URL_TEMPLATE) {
      return RESPONDER_URL_TEMPLATE.replace(/0\/?$/, `${solicitacaoId}/`);
    }
    return `/corrida/solicitacao/${solicitacaoId}/responder/`;
  }

  // rota iniciar / encerrar templates: se URL_TEMPLATE existir usa, senão usa path relativa
  function iniciarUrl() {
    if (typeof URL_INICIAR_TEMPLATE !== 'undefined' && URL_INICIAR_TEMPLATE) return URL_INICIAR_TEMPLATE;
    // fallback: /corrida/<id>/iniciar/ (obtém id do container)
    const id = qs('#corrida-detalhe').dataset.corridaId;
    return `/corrida/${id}/iniciar/`;
  }
  function encerrarUrl() {
    if (typeof URL_ENCERRAR_TEMPLATE !== 'undefined' && URL_ENCERRAR_TEMPLATE) return URL_ENCERRAR_TEMPLATE;
    const id = qs('#corrida-detalhe').dataset.corridaId;
    return `/corrida/${id}/encerrar/`;
  }

  // Atualiza badge (opcional)
  async function atualizarBadge() {
    if (typeof URL_CONTAGEM === 'undefined') return;
    try {
      const res = await fetch(URL_CONTAGEM + "?_=" + Date.now(), { credentials: 'same-origin' });
      if (!res.ok) return;
      const js = await res.json();
      const badge = qs('#notif-badge');
      if (badge) badge.textContent = js.unread ? `${js.unread}` : '';
    } catch (err) {
      console.error('Erro atualizarBadge', err);
    }
  }

  const STATUS_DISPLAY = {
    'PENDENTE': 'Pendente',
    'ACEITA': 'Aceita',
    'RECUSADA': 'Recusada',
    'CANCELADA': 'Cancelada',
    'ativa': 'Ativa',
    'em_andamento': 'Em andamento',
    'finalizada': 'Finalizada'
  };

  // (Reaproveitados) funções de controle de botões
  function atualizarBotoesSolicitacoes() {
    const items = qsa('.solicitacao-item');
    items.forEach(item => {
      const status = (item.dataset.status || '').toUpperCase();
      const btnAceitar = qs('.btn-aceitar', item);
      const btnRejeitar = qs('.btn-rejeitar', item);

      if (status === 'PENDENTE') {
        if (btnAceitar) { btnAceitar.disabled = false; btnAceitar.classList.remove('disabled'); }
        if (btnRejeitar) { btnRejeitar.disabled = true; btnRejeitar.classList.add('disabled'); }
      } else if (status === 'ACEITA') {
        if (btnAceitar) { btnAceitar.disabled = true; btnAceitar.classList.add('disabled'); }
        if (btnRejeitar) { btnRejeitar.disabled = false; btnRejeitar.classList.remove('disabled'); }
      } else {
        if (btnAceitar) { btnAceitar.disabled = true; btnAceitar.classList.add('disabled'); }
        if (btnRejeitar) { btnRejeitar.disabled = true; btnRejeitar.classList.add('disabled'); }
      }
    });
  }

  function atualizarBotoesCorrida() {
    const container = qs('#corrida-detalhe');
    if (!container) return;
    let corridaStatus = (container.dataset.corridaStatus || '').toString();
    const btnIniciar = qs('#btn-iniciar');
    const btnEncerrar = qs('#btn-encerrar');
    const btnFinalizar = qs('#btn-finalizar');

    const acceptedCount = qsa('.solicitacao-item.aceita').length;

    // Iniciar habilitado se status != em_andamento e não finalizada
    if (btnIniciar) {
      if (corridaStatus !== 'em_andamento' && corridaStatus !== 'finalizada' && acceptedCount > 0) {
        btnIniciar.disabled = false;
        btnIniciar.classList.remove('disabled');
      } else {
        btnIniciar.disabled = true;
        btnIniciar.classList.add('disabled');
      }
    }

    // Encerrar temporário habilitado se em_andamento
    if (btnEncerrar) {
      if (corridaStatus === 'em_andamento') {
        btnEncerrar.disabled = false;
        btnEncerrar.classList.remove('disabled');
      } else {
        btnEncerrar.disabled = true;
        btnEncerrar.classList.add('disabled');
      }
    }

    // Finalizar permanente: habilita quando em_andamento (ou sempre visível e ativo)
    if (btnFinalizar) {
      if (corridaStatus === 'em_andamento') {
        btnFinalizar.disabled = false;
        btnFinalizar.classList.remove('disabled');
      } else {
        btnFinalizar.disabled = false; // permitimos finalizar mesmo se não em andamento
        btnFinalizar.classList.remove('disabled');
      }
    }
  }

  // Atualiza o status da corrida no DOM (data attribute + texto + vagas se fornecido)
  function atualizarStatusCorridaNoDOM(novoStatus, vagas = null) {
    const container = qs('#corrida-detalhe');
    if (!container) return;
    container.dataset.corridaStatus = novoStatus;
    const span = qs('#corrida-status-text');
    if (span) span.textContent = STATUS_DISPLAY[novoStatus] || novoStatus;
    if (vagas !== null) {
      const vagasSpan = qs('#corrida-vagas');
      if (vagasSpan) vagasSpan.textContent = vagas;
    }
    atualizarBotoesCorrida();
  }

  // Marcar solicitação no DOM (reaproveitado)
  function marcarSolicitacaoNoDOM(solicitacaoId, novoStatus) {
    const item = qs(`.solicitacao-item[data-solicitacao="${solicitacaoId}"]`);
    if (!item) return;
    const statusCode = (novoStatus || '').toUpperCase();
    item.dataset.status = statusCode;
    item.classList.remove('pendente', 'aceita', 'outros');
    if (statusCode === 'PENDENTE') item.classList.add('pendente');
    else if (statusCode === 'ACEITA') item.classList.add('aceita');
    else item.classList.add('outros');
    const statusSpan = qs('.status-text', item);
    if (statusSpan) statusSpan.textContent = STATUS_DISPLAY[statusCode] || statusCode;
    atualizarBotoesSolicitacoes();
    atualizarBotoesCorrida();
  }

  // responder solicitacao (mesma lógica)
  async function responderSolicitacao(solicitacaoId, action, button) {
    if (!solicitacaoId || !action) return;
    const url = responderUrlFor(solicitacaoId);
    const originalText = button ? button.textContent : null;
    if (button) { button.disabled = true; button.classList.add('loading'); }
    try {
      const form = new FormData();
      form.append('action', action);
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' },
        body: form
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.erro) {
        console.error('Erro ao responder solicitação', res.status, data.erro || data);
        if (button) { button.disabled = false; button.classList.remove('loading'); }
        alert(data.erro || 'Erro ao processar a solicitação. Veja console.');
        return;
      }

      let novoStatus = data.status || ((action === 'aceitar') ? 'ACEITA' : 'RECUSADA');
      marcarSolicitacaoNoDOM(solicitacaoId, novoStatus);

      // se backend devolveu status da corrida/vagas, aplica
      if (data.corrida_status) {
        atualizarStatusCorridaNoDOM(data.corrida_status, data.vagas_disponiveis || null);
      }

      atualizarBadge();

    } catch (err) {
      console.error('Erro de rede ao responder solicitacao', err);
      if (button) { button.disabled = false; button.classList.remove('loading'); }
      alert('Erro de rede. Tente novamente.');
    } finally {
      if (button && originalText) { button.classList.remove('loading'); button.textContent = originalText; }
    }
  }

  // funções iniciar/encerrar via AJAX
  async function iniciarCorridaAJAX(button) {
    if (!confirm('Deseja iniciar a corrida agora?')) return;
    const url = iniciarUrl();
    if (button) { button.disabled = true; button.classList.add('loading'); }
    try {
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' },
        body: new FormData() // apenas CSRF no cabeçalho já resolve
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.erro) {
        alert(data.erro || 'Erro ao iniciar a corrida.');
        if (button) { button.disabled = false; button.classList.remove('loading'); }
        return;
      }
      // atualiza DOM com novo status
      const novoStatus = data.status || 'em_andamento';
      atualizarStatusCorridaNoDOM(novoStatus, data.vagas_disponiveis || null);
      atualizarBadge();
    } catch (err) {
      console.error('Erro ao iniciar corrida', err);
      alert('Erro de rede ao iniciar. Tente novamente.');
      if (button) { button.disabled = false; button.classList.remove('loading'); }
    } finally {
      if (button) { button.classList.remove('loading'); }
    }
  }

  async function encerrarCorridaAJAX(button, finalizar = false) {
    if (finalizar) {
      if (!confirm('Finalizar corrida definitivamente? Esta ação não poderá ser revertida.')) return;
    } else {
      if (!confirm('Encerrar corrida (temporário)?')) return;
    }

    const url = encerrarUrl();
    const form = new FormData();
    if (finalizar) form.append('finalize', '1');

    if (button) { button.disabled = true; button.classList.add('loading'); }

    try {
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': CSRF_TOKEN, 'Accept': 'application/json' },
        body: form
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.erro) {
        alert(data.erro || 'Erro ao encerrar a corrida.');
        if (button) { button.disabled = false; button.classList.remove('loading'); }
        return;
      }
      const novoStatus = data.status || (finalizar ? 'finalizada' : 'ativa');
      atualizarStatusCorridaNoDOM(novoStatus, data.vagas_disponiveis || null);
      atualizarBadge();
    } catch (err) {
      console.error('Erro ao encerrar corrida', err);
      alert('Erro de rede ao encerrar. Tente novamente.');
      if (button) { button.disabled = false; button.classList.remove('loading'); }
    } finally {
      if (button) { button.classList.remove('loading'); }
    }
  }

  // delegação de cliques (responder, iniciar, encerrar)
  document.addEventListener('click', function (e) {
    const btnSolic = e.target.closest('.btn-aceitar, .btn-rejeitar');
    if (btnSolic) {
      const solicitacaoId = btnSolic.dataset.solicitacao;
      const action = btnSolic.dataset.action;
      if (!solicitacaoId || !action) return;
      if (action === 'rejeitar') {
        if (!confirm('Confirma cancelar/recusar esta solicitação?')) return;
      } else if (action === 'aceitar') {
        if (!confirm('Confirma aceitar esta solicitação?')) return;
      }
      responderSolicitacao(solicitacaoId, action, btnSolic);
      return;
    }

    const btnIniciar = e.target.closest('#btn-iniciar');
    if (btnIniciar) {
      iniciarCorridaAJAX(btnIniciar);
      return;
    }

    const btnEncerrar = e.target.closest('#btn-encerrar');
    if (btnEncerrar) {
      encerrarCorridaAJAX(btnEncerrar, false);
      return;
    }

    const btnFinalizar = e.target.closest('#btn-finalizar');
    if (btnFinalizar) {
      encerrarCorridaAJAX(btnFinalizar, true);
      return;
    }
  });

  // init
  document.addEventListener('DOMContentLoaded', function () {
    atualizarBotoesSolicitacoes();
    atualizarBotoesCorrida();
    atualizarBadge();
    if (typeof URL_CONTAGEM !== 'undefined') setInterval(atualizarBadge, 20000);
  });

})();
