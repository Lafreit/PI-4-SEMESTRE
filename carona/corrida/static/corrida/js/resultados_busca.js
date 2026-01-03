// static/corrida/js/resultados_busca.js
(function () {
  'use strict';

  console.log('resultados_busca.js carregado — debug');

  document.addEventListener("DOMContentLoaded", function () {

    // ====== Configuração inicial do mapa ======
    let map = L.map("map").setView([-23.55, -46.63], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors"
    }).addTo(map);

    const toleranciaRange = document.getElementById("toleranciaRange");
    const toleranciaValor = document.getElementById("toleranciaValor");
    const buscarBtn = document.getElementById("buscarBtn");
    const origemInput = document.getElementById("origemInput");
    const destinoInput = document.getElementById("destinoInput");
    const corridasContainer = document.getElementById("corridasContainer");

    // ---------------- CSRF ----------------
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
          cookie = cookie.trim();
          if (cookie.startsWith(name + "=")) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }
    const csrftoken = getCookie("csrftoken");

    // Atualiza texto do slide de tolerância
    if (toleranciaRange && toleranciaValor) {
      toleranciaRange.addEventListener("input", () => {
        toleranciaValor.textContent = toleranciaRange.value;
      });
    }

    // Helper: mostra texto loading
    function showLoading(msg = "Buscando...") {
      if (!corridasContainer) return;
      corridasContainer.innerHTML = `<div class="loading">${msg}</div>`;
    }

    // escape simples
    function escapeHtml(unsafe) {
      if (unsafe === null || unsafe === undefined) return "";
      return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    // tolerância para obter corrida id
    function getCorridaIdFromEl(el) {
      if (!el) return null;
      return el.dataset.id || el.dataset.corridaId || el.getAttribute('data-corrida-id') || null;
    }

    // consulta minhas solicitações
    async function fetchMinhasSolicitacoesParaIds(idsArray) {
      if (!idsArray || !idsArray.length) return {};
      try {
        const param = idsArray.join(',');
        const res = await fetch(`/corrida/api/minhas_solicitacoes/?ids=${encodeURIComponent(param)}`, {
          credentials: 'same-origin',
          headers: {'Accept': 'application/json'}
        });
        if (!res.ok) {
          console.warn('minhas_solicitacoes_api retornou status', res.status);
          return {};
        }
        const data = await res.json().catch(() => ({}));
        return data.solicitacoes || {};
      } catch (e) {
        console.error('Erro ao buscar minhas solicitacoes (batch):', e);
        return {};
      }
    }

    // atualiza botões
    function atualizarBotoesParaCorrida(corridaId, solicitacaoId) {
      const solicitarBtn = document.querySelector(`.btn-solicitar[data-id="${corridaId}"], .btn-solicitar[data-corrida-id="${corridaId}"]`);
      const cancelarBtn = document.querySelector(`.btn-cancelar[data-id="${corridaId}"], .btn-cancelar[data-corrida-id="${corridaId}"]`);

      if (solicitacaoId) {
        if (solicitarBtn) {
          solicitarBtn.style.display = 'none';
          solicitarBtn.disabled = true;
        }
        if (cancelarBtn) {
          cancelarBtn.style.display = 'inline-block';
          cancelarBtn.disabled = false;
          cancelarBtn.dataset.solicitacaoId = String(solicitacaoId);
          cancelarBtn.setAttribute('data-solicitacao-id', String(solicitacaoId));
        }
      } else {
        if (solicitarBtn) {
          solicitarBtn.style.display = 'inline-block';
          solicitarBtn.disabled = false;
        }
        if (cancelarBtn) {
          cancelarBtn.style.display = 'none';
          cancelarBtn.dataset.solicitacaoId = '';
          cancelarBtn.removeAttribute('data-solicitacao-id');
        }
      }
    }

    function setFeedback(corridaId, mensagem, isError) {
      const el = document.getElementById(`feedback-${corridaId}`);
      if (!el) return;
      el.textContent = mensagem;
      el.classList.toggle('feedback-error', !!isError);
    }

    // cria card
    function criarCardCorrida(c) {
      const origem = [c.origem_lat, c.origem_lon];
      const destino = [c.destino_lat, c.destino_lon];

      try {
        const polyline = L.polyline([origem, destino], { weight: 4 }).addTo(map);
        L.marker(origem).addTo(map).bindPopup(`<strong>${escapeHtml(c.origem)}</strong>`);
        L.marker(destino).addTo(map).bindPopup(`<strong>${escapeHtml(c.destino)}</strong>`);

        var focusBounds = function () {
          try {
            map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
          } catch (e) { }
        };
      } catch (e) {
        console.warn('Erro ao desenhar rota no mapa:', e);
      }

      const card = document.createElement("div");
      card.className = "corrida-card corrida-item";
      card.id = `corrida-${c.id}`;
      card.setAttribute('data-corrida-id', c.id);
      card.setAttribute('data-id', c.id);

      const valorDisplay = (c.valor !== undefined && c.valor !== null)
        ? `R$ ${Number(c.valor || 0).toFixed(2)}`
        : '';

      card.innerHTML = `
        <div class="corrida-info">
          <div class="corrida-origem-destino">
            <strong>${escapeHtml(c.origem)}</strong> → <strong>${escapeHtml(c.destino)}</strong>
          </div>

          <div class="corrida-meta">
            <span class="corrida-vagas">
              Vagas: <span class="vagas-count">${escapeHtml(String(c.vagas_disponiveis || '0'))}</span>
            </span>

            ${ valorDisplay ? `<span class="corrida-valor">${escapeHtml(valorDisplay)}</span>` : '' }

            <div class="corrida-datas">Saída: ${escapeHtml(c.horario_saida || '--:--')}</div>

            <!-- novos campos -->
            <div class="corrida-motorista">
              Motorista: <strong>${escapeHtml(c.motorista_nome || '—')}</strong>
            </div>

            <div class="corrida-data-inicio">
              Início: ${escapeHtml(c.data || '--/--/----')}
            </div>

            <div class="corrida-periodicidade">
              Periodicidade: <strong>${escapeHtml(c.periodicidade || 'Única')}</strong>
            </div>
          </div>
        </div>


        <div class="corrida-actions">
          <button type="button" class="btn-solicitar btn" data-id="${c.id}" data-corrida-id="${c.id}">Solicitar vaga</button>

          <button type="button" class="btn-cancelar btn" data-id="${c.id}" data-corrida-id="${c.id}" data-solicitacao-id="" style="display:none; background:#c0392b; color:#fff;">
            Cancelar solicitação
          </button>

          <span id="feedback-${c.id}" class="feedback" aria-live="polite"></span>
        </div>
      `;

      card.addEventListener('click', function (ev) {
        if (ev.target.closest('.btn')) return;
        focusBounds && focusBounds();
      });

      return card;
    }

    // sincronização
    async function sincronizarEstadoBotoes() {
      try {
        const itens = Array.from(document.querySelectorAll('.corrida-item'));
        const ids = [...new Set(itens.map(el => el.dataset.corridaId || el.dataset.id).filter(Boolean))];
        if (!ids.length) return;
        const mapping = await fetchMinhasSolicitacoesParaIds(ids);
        console.log('sincronizarEstadoBotoes mapping=', mapping);
        ids.forEach(id => {
          atualizarBotoesParaCorrida(id, mapping[String(id)]);
        });
      } catch (e) {
        console.error('Erro em sincronizarEstadoBotoes:', e);
      }
    }

    // EVENTOS — solicitar / cancelar
    if (corridasContainer) {
      corridasContainer.addEventListener('click', async function (evt) {
        const target = evt.target;

        // SOLICITAR
        if (target.matches('.btn-solicitar')) {
          evt.stopPropagation();
          const corridaId = getCorridaIdFromEl(target);
          if (!corridaId) return;

          const originalText = target.textContent;
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

              const cancelarBtn = document.querySelector(`.btn-cancelar[data-id="${corridaId}"], .btn-cancelar[data-corrida-id="${corridaId}"]`);
              if (cancelarBtn && data.id) {
                cancelarBtn.dataset.solicitacaoId = String(data.id);
                cancelarBtn.style.display = 'inline-block';
              }
            } else {
              const msg = data?.erro || `Erro (${res.status})`;
              setFeedback(corridaId, msg, true);
              target.disabled = false;
              target.textContent = originalText;
            }
          } catch (err) {
            console.error('Erro ao solicitar:', err);
            setFeedback(corridaId, 'Erro de rede. Tente novamente.', true);
            target.disabled = false;
            target.textContent = originalText;
          }
        }

        // CANCELAR
        if (target.matches('.btn-cancelar')) {
          evt.stopPropagation();
          const corridaId = getCorridaIdFromEl(target);
          const solicitacaoId = target.dataset.solicitacaoId;

          if (!corridaId || !solicitacaoId) {
            setFeedback(corridaId, 'ID de solicitação não disponível.', true);
            return;
          }

          target.disabled = true;
          setFeedback(corridaId, 'Cancelando solicitação...', false);

          try {
            const res = await fetch(`/corrida/solicitacao/${solicitacaoId}/cancelar/`, {
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

              const solicitarBtn = document.querySelector(`.btn-solicitar[data-id="${corridaId}"], .btn-solicitar[data-corrida-id="${corridaId}"]`);
              if (solicitarBtn) {
                solicitarBtn.style.display = 'inline-block';
                solicitarBtn.disabled = false;
              }

              target.style.display = 'none';
              target.dataset.solicitacaoId = '';
            } else {
              const msg = data?.erro || `Erro (${res.status})`;
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
    }

    // BUSCA
    if (buscarBtn) {
      buscarBtn.addEventListener("click", async () => {
        const origem = origemInput.value.trim();
        const destino = destinoInput.value.trim();
        const tolerancia = parseInt(toleranciaRange.value);

        if (!origem || !destino) {
          alert("Por favor, informe origem e destino.");
          return;
        }

        map.eachLayer(layer => {
          if (layer instanceof L.Marker || layer instanceof L.Polyline) {
            map.removeLayer(layer);
          }
        });
        corridasContainer.innerHTML = "";

        showLoading("Buscando corridas...");

        const params = new URLSearchParams({
          origem,
          destino,
          tol: String(tolerancia)
        });

        try {
          const resp = await fetch(`/corrida/api/buscar_corridas/?${params}`, {
            method: "GET",
            headers: { "Accept": "application/json" },
            credentials: "same-origin"
          });

          if (!resp.ok) {
            const err = await resp.json().catch(() => null);
            corridasContainer.innerHTML = `<p class="erro">Erro: ${escapeHtml(err?.erro || `Erro ${resp.status}`)}</p>`;
            return;
          }

          const payload = await resp.json();
          const data = payload?.corridas || [];

          if (data.length === 0) {
            corridasContainer.innerHTML = "<p>Nenhuma corrida encontrada.</p>";
            return;
          }

          corridasContainer.innerHTML = "";

          data.forEach(c => {
            c.origem_lat = Number(c.origem_lat);
            c.origem_lon = Number(c.origem_lon);
            c.destino_lat = Number(c.destino_lat);
            c.destino_lon = Number(c.destino_lon);

            const card = criarCardCorrida(c);
            corridasContainer.appendChild(card);
          });

          await sincronizarEstadoBotoes();

        } catch (err) {
          console.error("Erro fetch buscar_corridas_api:", err);
          corridasContainer.innerHTML = "<p class='erro'>Erro ao buscar corridas. Tente novamente.</p>";
        }
      });
    }

    setTimeout(() => sincronizarEstadoBotoes(), 300);

  });

})();
