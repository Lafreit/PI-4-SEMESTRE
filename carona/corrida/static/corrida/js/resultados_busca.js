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

    // Helper: mostra texto loading simples
    function showLoading(msg = "Buscando...") {
        corridasContainer.innerHTML = `<div class="loading">${msg}</div>`;
    }

    // Helper: cria elemento card para uma corrida
    function criarCardCorrida(c, map) {
        const origem = [c.origem_lat, c.origem_lon];
        const destino = [c.destino_lat, c.destino_lon];

        const polyline = L.polyline([origem, destino], { weight: 4 }).addTo(map);

        L.marker(origem).addTo(map).bindPopup(`<strong>${escapeHtml(c.origem)}</strong>`);
        L.marker(destino).addTo(map).bindPopup(`<strong>${escapeHtml(c.destino)}</strong>`);

        const card = document.createElement("div");
        card.className = "corrida-card";
        card.innerHTML = `
            <strong>${escapeHtml(c.origem)} → ${escapeHtml(c.destino)}</strong><br>
            Saída: ${c.horario_saida || '--:--'}<br>
            Valor: R$ ${Number(c.valor || 0).toFixed(2)}<br>
            <button class="btn-solicitar" data-id="${c.id}" data-url="${c.data_url || ''}">Solicitar corrida</button>
        `;

        // clicar no card foca a rota
        card.addEventListener("click", () => {
            map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
        });

        // configurar botão solicitar
        const btn = card.querySelector(".btn-solicitar");
        if (btn) {
            // closure captura c corretamente se usarmos let aqui (c já é let no forEach)
            btn.addEventListener("click", async (ev) => {
                ev.stopPropagation();
                const originalText = btn.textContent;
                btn.disabled = true;
                btn.textContent = "Enviando...";

                // URL preferencialmente do atributo data-url (setado no template). fallback para rotas prováveis.
                const fallbackUrls = [
                    `/corrida/solicitar_carona/${c.id}/`,
                    `/corrida/solicitar/${c.id}/`,
                    `/corrida/solicitar_corrida/${c.id}/`
                ];
                const url = (btn.dataset.url && btn.dataset.url.trim()) ? btn.dataset.url.trim() : fallbackUrls[0];

                try {
                    const r = await fetch(url, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrftoken,
                            "Accept": "application/json"
                        },
                        credentials: "same-origin" // garante envio de cookie em contextos same-origin
                    });

                    // tratar códigos comuns
                    if (r.status === 403) {
                        alert("Requisição bloqueada (CSRF). Faça login novamente e tente.");
                        btn.disabled = false;
                        btn.textContent = originalText;
                        return;
                    }
                    if (r.status === 405) {
                        alert("Método não permitido. O servidor espera POST.");
                        btn.disabled = false;
                        btn.textContent = originalText;
                        return;
                    }

                    // tenta parse do JSON com fallback
                    let jr = null;
                    try {
                        jr = await r.clone().json();
                    } catch (e) {
                        jr = null;
                    }

                    if (!r.ok) {
                        const msg = jr?.erro || jr?.message || `Erro ${r.status}`;
                        alert(msg);
                        btn.disabled = false;
                        btn.textContent = originalText;
                        return;
                    }

                    // sucesso
                    if (jr && (jr.ok === true || jr.status)) {
                        btn.textContent = "Solicitação enviada";
                        btn.classList.add("btn-solicitado");
                        btn.disabled = true;
                    } else {
                        // resposta inesperada, mas tratar como sucesso visual
                        btn.textContent = "Solicitação enviada";
                        btn.classList.add("btn-solicitado");
                        btn.disabled = true;
                    }
                } catch (e) {
                    console.error("Erro na requisição de solicitar:", e);
                    alert("Erro de conexão ao enviar solicitação. Tente novamente.");
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });
        }

        return card;
    }

    // escape simples para evitar injeção no innerHTML
    function escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return "";
        return String(unsafe)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // ====== Evento de busca REAL (fetch para o backend) ======
    if (buscarBtn) {
        buscarBtn.addEventListener("click", async () => {
            const origem = origemInput ? origemInput.value.trim() : "";
            const destino = destinoInput ? destinoInput.value.trim() : "";
            const tolerancia = toleranciaRange ? parseInt(toleranciaRange.value) : 5000;

            if (!origem || !destino) {
                alert("Por favor, informe origem e destino.");
                return;
            }

            // remove marcadores/lines, mas preserva a tileLayer (filtra por tipos)
            map.eachLayer(layer => {
                if (layer instanceof L.Marker || layer instanceof L.Polyline) {
                    map.removeLayer(layer);
                }
            });
            corridasContainer.innerHTML = "";

            showLoading("Buscando corridas...");

            // monta querystring (encode)
            const params = new URLSearchParams({
                origem: origem,
                destino: destino,
                tol: String(tolerancia)
            });

            try {
                const resp = await fetch(`/corrida/api/buscar_corridas/?${params.toString()}`, {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    },
                    credentials: "same-origin"
                });

                if (!resp.ok) {
                    const err = await resp.json().catch(() => null);
                    const msg = (err && err.erro) ? err.erro : `Erro ${resp.status}`;
                    corridasContainer.innerHTML = `<p class="erro">Erro: ${escapeHtml(msg)}</p>`;
                    return;
                }

                const payload = await resp.json();

                if (!payload || payload.ok !== true) {
                    corridasContainer.innerHTML = `<p class="erro">Erro: ${escapeHtml(payload?.erro || 'Resposta inválida')}</p>`;
                    return;
                }

                const data = Array.isArray(payload.corridas) ? payload.corridas : [];

                if (data.length === 0) {
                    corridasContainer.innerHTML = "<p>Nenhuma corrida encontrada.</p>";
                    if (payload.coords && payload.coords.lat && payload.coords.lon) {
                        map.setView([payload.coords.lat, payload.coords.lon], 13);
                    }
                    return;
                }

                // renderiza resultados
                corridasContainer.innerHTML = "";
                // garantir que usamos let no forEach para closure correta
                data.forEach((c) => {
                    // garantir tipos numéricos
                    c.origem_lat = Number(c.origem_lat) || 0;
                    c.origem_lon = Number(c.origem_lon) || 0;
                    c.destino_lat = Number(c.destino_lat) || 0;
                    c.destino_lon = Number(c.destino_lon) || 0;
                    // passar opcional data_url para botão (se a API fornecer)
                    // criar o card e adicionar
                    const card = criarCardCorrida(c, map);
                    corridasContainer.appendChild(card);
                });

                // ajusta mapa para mostrar todas as origens (ou centraliza no primeiro)
                try {
                    const bounds = L.latLngBounds(data.map(c => [c.origem_lat, c.origem_lon]));
                    if (bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40] });
                } catch (e) {
                    if (payload.coords) map.setView([payload.coords.lat, payload.coords.lon], 13);
                }

            } catch (err) {
                console.error("Erro fetch buscar_corridas_api:", err);
                corridasContainer.innerHTML = "<p class='erro'>Erro ao buscar corridas. Tente novamente.</p>";
            }
        });
    }

    // ---------- UX: desabilitar submit até ter coords válidas ----------
    document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.form-corrida');
    if (!form) return;

    // seleciona botão de submit (compatível com seu HTML)
    const submitBtn = form.querySelector('button[type="submit"].action-btn') || form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true; // start disabled

    // aviso leve (aparece abaixo do botão) - só cria se não existir
    let smallAviso = document.getElementById('coords-small-warning');
    if (!smallAviso) {
        smallAviso = document.createElement('div');
        smallAviso.id = 'coords-small-warning';
        smallAviso.style.display = 'none';
        smallAviso.style.marginTop = '8px';
        smallAviso.style.fontSize = '0.9rem';
        smallAviso.style.color = '#b00020';
        smallAviso.textContent = 'Selecione sugestões válidas para origem e destino.';
        // insere após o botão de submit (ou no final do form)
        if (submitBtn && submitBtn.parentNode) {
        submitBtn.parentNode.insertBefore(smallAviso, submitBtn.nextSibling);
        } else {
        form.appendChild(smallAviso);
        }
    }

    // util: verifica se os 4 campos de coords têm valor
    function coordsPreenchidas() {
        const oLat = document.getElementById('id_origem_lat');
        const oLon = document.getElementById('id_origem_lon');
        const dLat = document.getElementById('id_destino_lat');
        const dLon = document.getElementById('id_destino_lon');

        const tem = el => el && String(el.value || '').trim().length > 0;
        return tem(oLat) && tem(oLon) && tem(dLat) && tem(dLon);
    }

    // atualizar estado do botão/aviso
    function atualizarEstado() {
        const ok = coordsPreenchidas();
        if (submitBtn) submitBtn.disabled = !ok;
        smallAviso.style.display = ok ? 'none' : 'block';
    }

    // observar mudanças nos campos hidden (caso preenchidos via JS)
    const targets = [
        document.getElementById('id_origem_lat'),
        document.getElementById('id_origem_lon'),
        document.getElementById('id_destino_lat'),
        document.getElementById('id_destino_lon')
    ].filter(Boolean);

    // se não existirem ainda, checa periodicamente rápido (alguns setups geram inputs depois)
    if (!targets.length) {
        let tries = 0;
        const interval = setInterval(() => {
        tries += 1;
        const found = [
            document.getElementById('id_origem_lat'),
            document.getElementById('id_origem_lon'),
            document.getElementById('id_destino_lat'),
            document.getElementById('id_destino_lon')
        ].filter(Boolean);
        if (found.length) {
            clearInterval(interval);
            setupObservers(found);
            atualizarEstado();
        } else if (tries > 20) {
            clearInterval(interval);
        }
        }, 150);
    } else {
        setupObservers(targets);
        atualizarEstado();
    }

    function setupObservers(elems) {
        elems.forEach(el => {
        // observer para quando valor é alterado por script
        const obs = new MutationObserver(() => atualizarEstado());
        obs.observe(el, { attributes: true, attributeFilter: ['value'] });

        // também escuta eventos input/change para mudanças diretas
        el.addEventListener('input', atualizarEstado);
        el.addEventListener('change', atualizarEstado);
        });

        // Além disso, observa typing nos campos visíveis para limpar botão caso usuário edite manualmente o texto (autocomplete limpa coords)
        const visibleOrig = document.getElementById('id_origem');
        const visibleDest = document.getElementById('id_destino');
        [visibleOrig, visibleDest].forEach(visible => {
        if (!visible) return;
        visible.addEventListener('input', () => {
            // ao digitar, desabilita submit (coords serão limpas pelo seu autocomplete.js)
            if (submitBtn) submitBtn.disabled = true;
            smallAviso.style.display = 'block';
        });
        });
    }

    // se o usuário tentar submeter (retomamos validação extra como backup)
    form.addEventListener('submit', (e) => {
        if (!coordsPreenchidas()) {
        e.preventDefault();
        // foco no primeiro campo não preenchido
        const oLat = document.getElementById('id_origem_lat');
        const oLon = document.getElementById('id_origem_lon');
        const dLat = document.getElementById('id_destino_lat');
        const dLon = document.getElementById('id_destino_lon');

        if (!oLat || !oLat.value) {
            document.getElementById('id_origem')?.focus();
        } else if (!dLat || !dLat.value) {
            document.getElementById('id_destino')?.focus();
        }
        smallAviso.style.display = 'block';
        }
    });

    });


}); // DOMContentLoaded end
