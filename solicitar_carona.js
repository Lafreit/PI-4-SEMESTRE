// static/corrida/js/solicitar_carona.js
(function () {
  'use strict';

  /* ------------------ helpers ------------------ */
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

  // tolerância para obter corrida id (aceita data-id e data-corrida-id)
  function getCorridaIdFromEl(el) {
    if (!el) return null;
    return el.dataset.id || el.dataset.corridaId || el.getAttribute('data-corrida-id') || null;
  }

  // consulta o endpoint que retorna {corrida_id: solicitacao_id}
  async function fetchMinhaSolicitacao(corridaId) {
    try {
      const res = await fetch(`/corrida/api/minhas_solicitacoes/?ids=${encodeURIComponent(corridaId)}`, {
        credentials: 'same-origin',
        headers: {'Accept': 'application/json'}
      });
      if (!res.ok) return null;
      const data = await res.json().catch(() => ({}));
      const mapping = data.solicitacoes || {};
      return mapping[String(corridaId)] || null;
    } catch (e) {
      console.error('Erro ao buscar minha solicitacao:', e);
      return null;
    }
  }

  /* ------------------ inicializador (consulta ao servidor) ------------------ */
  (async function initMinhaSolicitacoes() {
    try {
      const itens = Array.from(document.querySelectorAll('[data-corrida-id], [data-id], .corrida-item'));
      const ids = [...new Set(
        itens.map(el => {
          return el.dataset.corridaId || el.dataset.id || el.getAttribute('data-corrida-id') || null;
        }).filter(Boolean)
      )];

      if (!ids.length) return;

      const param = ids.join(',');
      const res = await fetch(`/corrida/api/minhas_solicitacoes/?ids=${encodeURIComponent(param)}`, {
        credentials: 'same-origin',
        headers: {'Accept': 'application/json'}
      });

      if (!res.ok) return;

      const data = await res.json().catch(() => ({}));
      const mapping = data.solicitacoes || {};

      ids.forEach(id => {
        const solicitar = document.querySelector(`.btn-solicitar[data-id="${id}"], .btn-solicitar[data-corrida-id="${id}"]`);
        const cancelar = document.querySelector(`.btn-cancelar[data-id="${id}"], .btn-cancelar[data-corrida-id="${id}"]`);

        if (mapping[id]) {
          if (solicitar) {
            solicitar.style.display = 'none';
            solicitar.disabled = true;
          }
          if (cancelar) {
            cancelar.style.display = 'inline-block';
            cancelar.dataset.solicitacaoId = mapping[id];
            cancelar.setAttribute('data-solicitacao-id', mapping[id]);
            cancelar.disabled = false;
          }
        } else {
          if (solicitar) {
            solicitar.style.display = 'inline-block';
            solicitar.disabled = false;
          }
          if (cancelar) cancelar.style.display = 'none';
        }
      });

      console.log('initMinhaSolicitacoes completed, mapping=', mapping);
    } catch (e) {
      console.error('Erro ao inicializar minhas solicitações:', e);
    }
  })();

  /* ------------------ event delegation ------------------ */
  const container = document.getElementById('corridasContainer') || document.querySelector('.corridas-container') || document.body;
  if (!container) return;

  container.addEventListener('click', async function (evt) {
    const target = evt.target;

    // ====== SOLICITAR ======
    if (target.matches('.btn-solicitar')) {
      const corridaId = getCorridaIdFromEl(target);
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

        // tenta parsear JSON (pode ser vazio)
        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          // sucesso normal: exibir cancelar e esconder solicitar
          setFeedback(corridaId, 'Solicitação enviada.', false);
          target.style.display = 'none';
          target.disabled = true;

          const cancelar = container.querySelector(`.btn-cancelar[data-id="${corridaId}"], .btn-cancelar[data-corrida-id="${corridaId}"]`);
          if (cancelar) {
            if (data.id) {
              cancelar.dataset.solicitacaoId = data.id;
              cancelar.setAttribute('data-solicitacao-id', data.id);
            }
            cancelar.style.display = 'inline-block';
            cancelar.disabled = false;
          }
        } else {
          // trata 400/erro de negócio de forma amigável
          const msg = (data && data.erro) ? data.erro : `Erro (${res.status}).`;
          console.warn('Solicitar carroa retornou erro:', res.status, msg);
          setFeedback(corridaId, msg, true);

          // se já existe solicitação no servidor, busca o id e atualiza o DOM
          if (res.status === 400 && /já solicit/i.test(msg)) {
            const existId = await fetchMinhaSolicitacao(corridaId);
            if (existId) {
              // esconder solicitar e mostrar cancelar com id preenchido
              const cancelar = container.querySelector(`.btn-cancelar[data-id="${corridaId}"], .btn-cancelar[data-corrida-id="${corridaId}"]`);
              const solicitarBtn = container.querySelector(`.btn-solicitar[data-id="${corridaId}"], .btn-solicitar[data-corrida-id="${corridaId}"]`);
              if (solicitarBtn) {
                solicitarBtn.style.display = 'none';
                solicitarBtn.disabled = true;
              }
              if (cancelar) {
                cancelar.dataset.solicitacaoId = existId;
                cancelar.setAttribute('data-solicitacao-id', existId);
                cancelar.style.display = 'inline-block';
                cancelar.disabled = false;
                setFeedback(corridaId, 'Solicitação já existente (sincronizado).', false);
              }
            } else {
              // se não encontrou, sugira recarregar
              setFeedback(corridaId, 'Solicitação já existe — recarregue a página para sincronizar.', true);
            }
          }

          target.disabled = false;
        }

      } catch (err) {
        console.error('Erro na solicitação:', err);
        setFeedback(corridaId, 'Erro de rede. Tente novamente.', true);
        target.disabled = false;
      }

      return;
    }


    // ====== CANCELAR ======
    if (target.matches('.btn-cancelar')) {
      const corridaId = getCorridaIdFromEl(target);
      const solicitacaoId = target.dataset.solicitacaoId || target.getAttribute('data-solicitacao-id');

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

          const solicitarBtn = container.querySelector(`.btn-solicitar[data-id="${corridaId}"], .btn-solicitar[data-corrida-id="${corridaId}"]`);
          if (solicitarBtn) {
            solicitarBtn.style.display = 'inline-block';
            solicitarBtn.disabled = false;
          }

          target.style.display = 'none';
          target.dataset.solicitacaoId = '';
          target.removeAttribute('data-solicitacao-id');

        } else {
          const msg = (data && data.erro) ? data.erro : `Erro (${res.status}).`;
          setFeedback(corridaId, msg, true);
          target.disabled = false;
        }

      } catch (err) {
        console.error('Erro ao cancelar solicitação:', err);
        setFeedback(corridaId, 'Erro de rede. Tente novamente.', true);
        target.disabled = false;
      }
    }
  });
})();
