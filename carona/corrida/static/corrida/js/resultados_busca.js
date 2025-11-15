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
        corridasContainer.innerHTML = `<div class="loading">${msg}</div>`;
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
            <button class="btn-solicitar" data-id="${c.id}">Solicitar corrida</button>
            <span id="feedback-${c.id}" class="feedback"></span>

        `;

        // clicar no card foca a rota
        card.addEventListener("click", () => {
            map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
        });

        // botão de solicitar carona
        const btn = card.querySelector(".btn-solicitar");
        if (btn) {
            btn.addEventListener("click", async (ev) => {
                ev.stopPropagation();

                const originalText = btn.textContent;
                btn.disabled = true;
                btn.textContent = "Enviando...";

                // ★★★★★ URL FINAL CORRETA ★★★★★
                const url = `/corrida/${c.id}/solicitar/`;

                try {
                    const r = await fetch(url, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrftoken,
                            "Accept": "application/json"
                        },
                        credentials: "same-origin"
                    });

                    let jr = null;
                    try { jr = await r.clone().json(); } catch {}

                    if (!r.ok) {
                        alert(jr?.erro || jr?.message || `Erro ${r.status}`);
                        btn.disabled = false;
                        btn.textContent = originalText;
                        return;
                    }

                    btn.textContent = "Solicitação enviada";
                    btn.classList.add("btn-solicitado");
                    btn.disabled = true;

                } catch (e) {
                    console.error("Erro ao solicitar:", e);
                    alert("Erro ao enviar solicitação.");
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });
        }

        return card;
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

            // remove marcadores/lines
            map.eachLayer(layer => {
                if (layer instanceof L.Marker || layer instanceof L.Polyline) {
                    map.removeLayer(layer);
                }
            });
            corridasContainer.innerHTML = "";

            showLoading("Buscando corridas...");

            const params = new URLSearchParams({
                origem: origem,
                destino: destino,
                tol: String(tolerancia)
            });

            try {
                const resp = await fetch(`/corrida/api/buscar_corridas/?${params.toString()}`, {
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

                if (!payload || payload.ok !== true) {
                    corridasContainer.innerHTML = `<p class="erro">Erro: ${escapeHtml(payload?.erro || 'Resposta inválida')}</p>`;
                    return;
                }

                const data = Array.isArray(payload.corridas) ? payload.corridas : [];

                if (data.length === 0) {
                    corridasContainer.innerHTML = "<p>Nenhuma corrida encontrada.</p>";
                    if (payload.coords?.lat && payload.coords?.lon) {
                        map.setView([payload.coords.lat, payload.coords.lon], 13);
                    }
                    return;
                }

                corridasContainer.innerHTML = "";

                data.forEach((c) => {
                    c.origem_lat = Number(c.origem_lat) || 0;
                    c.origem_lon = Number(c.origem_lon) || 0;
                    c.destino_lat = Number(c.destino_lat) || 0;
                    c.destino_lon = Number(c.destino_lon) || 0;

                    const card = criarCardCorrida(c, map);
                    corridasContainer.appendChild(card);
                });

                // ajusta bounds
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

});
