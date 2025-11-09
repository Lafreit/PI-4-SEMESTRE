document.addEventListener("DOMContentLoaded", function () {
    // --- init Leaflet map ---
    if (typeof L === 'undefined') {
        console.warn('Leaflet (L) não encontrado — verifique a ordem dos scripts.');
        return;
    }

    const map = L.map("map").setView([-22.3, -47.3], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors"
    }).addTo(map);

    // --- markers / rota ---
    let origemMarker = null;
    let destinoMarker = null;
    let rotaLayer = null;

    // --- inputs: tenta vários ids compatíveis ---
    const origemInput = document.querySelector("#origem") || document.querySelector("#id_origem");
    const destinoInput = document.querySelector("#destino") || document.querySelector("#id_destino");



    if (!origemInput || !destinoInput) {
        console.warn('Inputs "origem" ou "destino" não encontrados no DOM. Abortando inicialização do mapa/rota.');
        return;
    }

    // --- helpers ---
    function safeParseFloat(v) {
        if (v === undefined || v === null || v === '') return null;
        const n = parseFloat(v);
        return Number.isFinite(n) ? n : null;
    }

    function geocodeEndereco(endereco) {
        // retorna Promise que resolve {lat, lon} ou rejeita
        return fetch(`/corrida/geocode_ajax/?endereco=${encodeURIComponent(endereco)}`)
            .then(res => {
                if (!res.ok) throw new Error('Geocode fetch falhou');
                return res.json();
            })
            .then(data => {
                // espera { lat, lon } ou similar
                const lat = safeParseFloat(data.lat ?? data.latitude ?? data.y);
                const lon = safeParseFloat(data.lon ?? data.longitude ?? data.x);
                if (lat === null || lon === null) throw new Error('Resposta de geocode sem coords');
                return { lat, lon };
            });
    }

    function desenharRota(origem, destino) {
        if (!origem || !destino) {
            console.warn('desenharRota: coordenadas faltando');
            return;
        }
        const url = `/corrida/rota_ajax/?lat_origem=${origem.lat}&lon_origem=${origem.lon}&lat_destino=${destino.lat}&lon_destino=${destino.lon}`;

        return fetch(url)
            .then(res => {
                if (!res.ok) throw new Error('Rota fetch falhou');
                return res.json();
            })
            .then(data => {
                if (!data || !Array.isArray(data.rota)) {
                    throw new Error('Resposta inválida de rota');
                }
                const latlngs = data.rota.map(p => [p[0], p[1]]);

                // remove rota anterior se existir
                if (rotaLayer) {
                    try { map.removeLayer(rotaLayer); } catch (e) { /* ignore */ }
                    rotaLayer = null;
                }

                rotaLayer = L.polyline(latlngs, { color: "blue" }).addTo(map);

                // ajustar bounds para caber a rota no mapa
                try {
                    const bounds = L.latLngBounds(latlngs);
                    map.fitBounds(bounds, { padding: [50, 50] });
                } catch (e) {
                    console.warn('Não foi possível ajustar bounds do mapa:', e);
                }

                return data; // para quem quiser usar distância, etc.
            })
            .catch(err => {
                console.error('Erro ao desenhar rota:', err);
                throw err;
            });
    }

    // atualiza marker (remove anterior se necessário)
    function showMarker(refMarker, lat, lon, label) {
        if (refMarker) {
            try { map.removeLayer(refMarker); } catch (e) { /* ignore */ }
        }
        const m = L.marker([lat, lon]).addTo(map).bindPopup(label || '').openPopup();
        return m;
    }

    // handler seguro para quando destino perde foco (blur)
    destinoInput.addEventListener("blur", function () {
        const enderecoDestino = destinoInput.value.trim();
        const enderecoOrigem = origemInput.value.trim();
        if (!enderecoDestino || !enderecoOrigem) {
            // se não tem ambos, não tenta gerar rota
            return;
        }

        // geocodifica destino primeiro
        geocodeEndereco(enderecoDestino)
            .then(dest => {
                // coloca marker do destino
                if (destinoMarker) {
                    try { map.removeLayer(destinoMarker); } catch (e) { /* ignore */ }
                    destinoMarker = null;
                }
                destinoMarker = showMarker(destinoMarker, dest.lat, dest.lon, "Destino");

                // geocodifica origem e desenha rota
                return geocodeEndereco(enderecoOrigem).then(orig => {
                    if (origemMarker) {
                        try { map.removeLayer(origemMarker); } catch (e) { /* ignore */ }
                        origemMarker = null;
                    }
                    origemMarker = showMarker(origemMarker, orig.lat, orig.lon, "Origem");

                    return desenharRota(orig, dest);
                });
            })
            .catch(err => {
                console.error('Erro no fluxo de geocode/rota:', err);
            });
    });

    // opcional: também atualiza mapa quando usuário seleciona origem (blur)
    origemInput.addEventListener("blur", function () {
        const enderecoOrigem = origemInput.value.trim();
        if (!enderecoOrigem) return;

        geocodeEndereco(enderecoOrigem)
            .then(orig => {
                if (origemMarker) {
                    try { map.removeLayer(origemMarker); } catch (e) { /* ignore */ }
                    origemMarker = null;
                }
                origemMarker = showMarker(origemMarker, orig.lat, orig.lon, "Origem");
            })
            .catch(err => {
                console.warn('Erro ao geocodificar origem:', err);
            });
    });

    // caso queira limpar rota quando usuário apaga um dos campos
    function maybeClearRoute() {
        const o = origemInput.value.trim();
        const d = destinoInput.value.trim();
        if (!o || !d) {
            if (rotaLayer) {
                try { map.removeLayer(rotaLayer); } catch (e) { /* ignore */ }
                rotaLayer = null;
            }
            if (origemMarker) {
                try { map.removeLayer(origemMarker); } catch (e) { /* ignore */ }
                origemMarker = null;
            }
            if (destinoMarker) {
                try { map.removeLayer(destinoMarker); } catch (e) { /* ignore */ }
                destinoMarker = null;
            }
        }
    }

    origemInput.addEventListener('input', maybeClearRoute);
    destinoInput.addEventListener('input', maybeClearRoute);
});
