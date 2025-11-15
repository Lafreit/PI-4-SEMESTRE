// static/corrida/js/solicitar_carona.js
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

  function setFeedback(corridaId, text, isError) {
    const el = document.getElementById(`feedback-${corridaId}`);
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('feedback-error', !!isError);
  }

  const container = document.getElementById('corridasContainer');
  if (!container) return;

  container.addEventListener('click', async function (evt) {
    const target = evt.target;

    // ====== SOLICITAR ======
    if (target.matches('.btn-solicitar')) {

      // 🔥 CORREÇÃO AQUI
      const corridaId = target.dataset.id;
      if (!corridaId) return;

      target.disabled = true;
      setFeedback(corridaId, 'Enviando solicitação...', false);

      try {
        const res = await fetch(`/corrida/${corridaId}/solicitar/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'Accept': 'application/json'
          },
          credentials: 'same-origin'
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          setFeedback(corridaId, 'Solicitação enviada.', false);
          target.style.display = 'none';

          // tenta mostrar botão cancelar
          const cancelar = container.querySelector(`.btn-cancelar[data-id="${corridaId}"]`);
          if (cancelar) {
            if (data.id) cancelar.dataset.solicitacaoId = data.id;
            cancelar.style.display = 'inline-block';
          }

        } else {
          setFeedback(corridaId, data.erro || 'Erro ao solicitar.', true);
          target.disabled = false;
        }

      } catch (err) {
        setFeedback(corridaId, 'Erro de rede. Tente novamente.', true);
        target.disabled = false;
      }

      return;
    }


    // ====== CANCELAR ======
    if (target.matches('.btn-cancelar')) {

      const corridaId = target.dataset.id;
      const solicitacaoId = target.dataset.solicitacaoId;

      if (!corridaId || !solicitacaoId) {
        setFeedback(corridaId || '0', 'ID de solicitação não disponível.', true);
        return;
      }

      target.disabled = true;
      setFeedback(corridaId, 'Cancelando solicitação...', false);

      try {
        const res = await fetch(`/solicitacao/${solicitacaoId}/cancelar/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'Accept': 'application/json'
          },
          credentials: 'same-origin'
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          setFeedback(corridaId, 'Solicitação cancelada.', false);

          const solicitarBtn = container.querySelector(`.btn-solicitar[data-id="${corridaId}"]`);
          if (solicitarBtn) {
            solicitarBtn.style.display = 'inline-block';
            solicitarBtn.disabled = false;
          }

          target.style.display = 'none';

        } else {
          setFeedback(corridaId, data.erro || 'Erro ao cancelar.', true);
          target.disabled = false;
        }

      } catch (err) {
        setFeedback(corridaId, 'Erro de rede. Tente novamente.', true);
        target.disabled = false;
      }
    }
  });
})();
