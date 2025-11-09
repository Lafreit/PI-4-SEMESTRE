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

    // CSRF (não necessário para GET, mas útil para outros endpoints)
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
    toleranciaRange.addEventListener("input", () => {
        toleranciaValor.textContent = toleranciaRange.value;
    });

    // Helper: mostra um texto de loading simples
    function showLoading(msg = "Buscando...") {
        corridasContainer.innerHTML = `<div class="loading">${msg}</div>`;
    }

    // ====== Evento de busca REAL (fetch para o backend) ======
    buscarBtn.addEventListener("click", async () => {
        const origem = origemInput.value.trim();
        const destino = destinoInput.value.trim();
        const tolerancia = parseInt(toleranciaRange.value);

        if (!origem || !destino) {
            alert("Por favor, informe origem e destino.");
            return;
        }

        // Limpa mapa e resultados antigos
        map.eachLayer(layer => {
            if (layer instanceof L.Marker || layer instanceof L.Polyline) map.removeLayer(layer);
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
                    // X-CSRFToken não é necessário para GET
                }
            });

            if (!resp.ok) {
                const err = await resp.json().catch(()=>null);
                const msg = (err && err.erro) ? err.erro : `Erro ${resp.status}`;
                corridasContainer.innerHTML = `<p class="erro">Erro: ${msg}</p>`;
                return;
            }

            const payload = await resp.json();

            if (!payload.ok) {
                corridasContainer.innerHTML = `<p class="erro">Erro: ${payload.erro || 'Resposta inválida'}</p>`;
                return;
            }

            const data = Array.isArray(payload.corridas) ? payload.corridas : [];

            if (data.length === 0) {
                corridasContainer.innerHTML = "<p>Nenhuma corrida encontrada.</p>";
                // centra no ponto do passageiro
                if (payload.coords && payload.coords.lat && payload.coords.lon) {
                    map.setView([payload.coords.lat, payload.coords.lon], 13);
                }
                return;
            }

            // renderiza resultados
            corridasContainer.innerHTML = "";
            data.forEach((c) => {
                const origem = [c.origem_lat, c.origem_lon];
                const destino = [c.destino_lat, c.destino_lon];
                const polyline = L.polyline([origem, destino], { color: "blue", weight: 4 }).addTo(map);

                L.marker(origem).addTo(map).bindPopup(`<strong>${c.origem}</strong>`);
                L.marker(destino).addTo(map).bindPopup(`<strong>${c.destino}</strong>`);

                const card = document.createElement("div");
                card.className = "corrida-card";
                card.innerHTML = `
                    <strong>${c.origem} → ${c.destino}</strong><br>
                    Saída: ${c.horario_saida || '--:--'}<br>
                    Valor: R$ ${c.valor.toFixed(2)}<br>
                    <button class="btn-solicitar" data-id="${c.id}">Solicitar corrida</button>
                `;

                card.addEventListener("click", () => {
                    map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
                });

                // botão solicitar (chama sua rota de solicitação)
                const btn = card.querySelector(".btn-solicitar");
                btn.addEventListener("click", async (ev) => {
                    ev.stopPropagation();
                    btn.disabled = true;
                    btn.textContent = "Enviando...";
                    try {
                        const r = await fetch(`/solicitar_corrida/${c.id}/`, {
                            method: "POST",
                            headers: {
                                "X-CSRFToken": csrftoken
                            }
                        });
                        const jr = await r.json();
                        if (!r.ok) {
                            alert(jr.message || jr.erro || "Erro ao solicitar.");
                            btn.disabled = false;
                            btn.textContent = "Solicitar corrida";
                            return;
                        }
                        btn.textContent = "Solicitação enviada";
                        btn.classList.add("btn-solicitado");
                    } catch (e) {
                        alert("Erro de conexão ao enviar solicitação.");
                        console.error(e);
                        btn.disabled = false;
                        btn.textContent = "Solicitar corrida";
                    }
                });

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
});
