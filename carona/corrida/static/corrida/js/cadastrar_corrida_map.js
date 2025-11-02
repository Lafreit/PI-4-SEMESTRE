document.addEventListener("DOMContentLoaded", function () {
    const map = L.map("map").setView([-22.3, -47.3], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors"
    }).addTo(map);

    let origemMarker, destinoMarker;
    let rotaLayer; // ← NOVO: variável para guardar a rota

    const origemInput = document.querySelector("#id_origem");
    const destinoInput = document.querySelector("#id_destino");

    function geocodeEndereco(endereco, callback) {
        fetch(`/corrida/geocode_ajax/?endereco=${encodeURIComponent(endereco)}`)
            .then(res => res.json())
            .then(data => {
                if (data.lat && data.lon) {
                    callback(data.lat, data.lon);
                }
            });
    }

    function desenharRota(origem, destino) {
        const url = `/corrida/rota_ajax/?lat_origem=${origem.lat}&lon_origem=${origem.lon}&lat_destino=${destino.lat}&lon_destino=${destino.lon}`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                console.log("Rota recebida:", data.rota);

                if (!data.rota || !Array.isArray(data.rota)) {
                    console.warn("Rota inválida recebida:", data);
                    return;
                }

                const latlngs = data.rota.map(p => [p[0], p[1]]);

                if (rotaLayer) {
                    map.removeLayer(rotaLayer); // ← NOVO: remove rota anterior
                }

                rotaLayer = L.polyline(latlngs, { color: "blue" }).addTo(map); // ← NOVO: desenha nova rota
            })
            .catch(err => console.error("Erro ao desenhar rota:", err));
    }

    destinoInput.addEventListener("blur", () => {
        const endereco = destinoInput.value.trim();
        if (!endereco || !origemInput.value.trim()) return;

        geocodeEndereco(endereco, (latDest, lonDest) => {
            if (destinoMarker) map.removeLayer(destinoMarker);
            destinoMarker = L.marker([latDest, lonDest]).addTo(map).bindPopup("Destino").openPopup();

            geocodeEndereco(origemInput.value, (latOrig, lonOrig) => {
                desenharRota(
                    { lat: latOrig, lon: lonOrig },
                    { lat: latDest, lon: lonDest }
                );
            });
        });
    });
});
