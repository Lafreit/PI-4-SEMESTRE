// static/corrida/js/solicitar_carona.js
// Responsável unicamente por solicitar/cancelar — constrói as URLs com prefixo /corrida/
console.log("solicitar_carona.js carregado");

(function () {
  'use strict';

  // pega csrftoken do cookie (fallback caso data-csrf não exista)
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

  function setFeedback(corridaId, text, isError) {
    const el = document.getElementById(`feedback-${corridaId}`);
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('feedback-error', !!isError);
  }

  function getCorridaId(el) {
    if (!el) return null;
    return el.dataset.corridaId || el.dataset.id || el.getAttribute('data-corrida-id') || null;
  }

  // delegação de eventos para todo o documento (funciona para botões estáticos e dinâmicos)
  document.addEventListener('click', async function (ev) {
    const target = ev.target.closest('.btn-solicitar, .btn-cancelar');
    if (!target) return;

    ev.preventDefault();

    // descobrir tipo
    const isSolicitar = target.classList.contains('btn-solicitar');
    const isCancelar = target.classList.contains('btn-cancelar');

    const corridaId = getCorridaId(target);
    const solicitacaoIdAttr = target.dataset.solicitacaoId || target.getAttribute('data-solicitacao-id') || '';

    // prioriza data-csrf do botão, se existir
    const btnCsrf = target.dataset.csrf || target.getAttribute('data-csrf');
    const token = btnCsrf || csrftoken;

    if (isSolicitar) {
      if (!corridaId) {
        console.warn('corridaId ausente no botão solicitar');
        return;
      }
      target.disabled = true;
      setFeedback(corridaId, 'Enviando solicitação...', false);

      try {
        const res = await fetch(`/corrida/${corridaId}/solicitar/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': token,
            'Accept': 'application/json'
          },
          credentials: 'same-origin'
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          // esconder solicitar e mostrar cancelar (preenchendo solicitacaoId se retornado)
          target.style.display = 'none';
          target.disabled = true;

          const cancelarBtn = document.querySelector(`.btn-cancelar[data-id="${corridaId}"], .btn-cancelar[data-corrida-id="${corridaId}"]`);
          if (cancelarBtn) {
            if (data.id) {
              cancelarBtn.dataset.solicitacaoId = String(data.id);
              cancelarBtn.setAttribute('data-solicitacao-id', String(data.id));
            }
            cancelarBtn.style.display = 'inline-block';
            cancelarBtn.disabled = false;
          }

          setFeedback(corridaId, 'Solicitação enviada.', false);
        } else {
          const msg = (data && data.erro) ? data.erro : `Erro (${res.status})`;
          setFeedback(corridaId, msg, true);
          target.disabled = false;
        }
      } catch (err) {
        console.error('Erro ao solicitar:', err);
        setFeedback(corridaId, 'Erro de rede. Tente novamente.', true);
        target.disabled = false;
      }

      return;
    }

    if (isCancelar) {
      // precisa de solicitacaoId
      const solicitacaoId = solicitacaoIdAttr || target.dataset.solicitacaoId || '';
      if (!solicitacaoId) {
        setFeedback(corridaId || '0', 'ID de solicitação não disponível.', true);
        return;
      }

      target.disabled = true;
      setFeedback(corridaId, 'Cancelando solicitação...', false);

      try {
        // <<-- usa prefixo /corrida/ para casar com suas URLs
        const res = await fetch(`/corrida/solicitacao/${solicitacaoId}/cancelar/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': token,
            'Accept': 'application/json'
          },
          credentials: 'same-origin'
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          // esconder cancelar e mostrar solicitar
          target.style.display = 'none';
          target.dataset.solicitacaoId = '';
          target.removeAttribute('data-solicitacao-id');

          const solicitarBtn = document.querySelector(`.btn-solicitar[data-id="${corridaId}"], .btn-solicitar[data-corrida-id="${corridaId}"]`);
          if (solicitarBtn) {
            solicitarBtn.style.display = 'inline-block';
            solicitarBtn.disabled = false;
          }

          setFeedback(corridaId, 'Solicitação cancelada.', false);
        } else {
          const msg = (data && data.erro) ? data.erro : `Erro (${res.status})`;
          setFeedback(corridaId, msg, true);
          target.disabled = false;
        }
      } catch (err) {
        console.error('Erro ao cancelar solicitação:', err);
        setFeedback(corridaId, 'Erro de rede. Tente novamente.', true);
        target.disabled = false;
      }

      return;
    }
  });

})();
