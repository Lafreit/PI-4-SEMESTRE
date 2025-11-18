document.addEventListener("DOMContentLoaded", function () {

    const map = L.map("map").setView([-22.3, -47.3], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors"
    }).addTo(map);

    let origemMarker = null;
    let destinoMarker = null;
    let rotaLayer = null;

    const origemInput = document.getElementById("origem");
    const destinoInput = document.getElementById("destino");

    async function gerarRota(lat1, lon1, lat2, lon2) {
        const url = `/api/rota/?lat1=${lat1}&lon1=${lon1}&lat2=${lat2}&lon2=${lon2}`;
        const resp = await fetch(url);
        return resp.json();
    }

    function colocarMarker(markerRef, lat, lon, label) {
        if (markerRef) map.removeLayer(markerRef);
        return L.marker([lat, lon]).addTo(map).bindPopup(label);
    }

    destinoInput.addEventListener("blur", async () => {
        const latD = destinoInput.dataset.lat;
        const lonD = destinoInput.dataset.lon;
        const latO = origemInput.dataset.lat;
        const lonO = origemInput.dataset.lon;

        if (!latD || !latO) return;

        destinoMarker = colocarMarker(destinoMarker, latD, lonD, "Destino");
        origemMarker = colocarMarker(origemMarker, latO, lonO, "Origem");

        const data = await gerarRota(latO, lonO, latD, lonD);

        if (rotaLayer) map.removeLayer(rotaLayer);

        const coords = data.features[0].geometry.coordinates.map(c => [c[1], c[0]]);
        rotaLayer = L.polyline(coords, { color: "blue" }).addTo(map);

        map.fitBounds(L.latLngBounds(coords), { padding: [30, 30] });
    });
});
