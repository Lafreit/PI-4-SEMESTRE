document.addEventListener('DOMContentLoaded', function () {
  // Mensagens desaparecem após 5 segundos
  setTimeout(function () {
    const msgs = document.querySelectorAll('#messages-container .alert');
    msgs.forEach(m => m.remove());
  }, 5000);

  const mapElement = document.getElementById('map');
  const origemInput = document.getElementById('origem');
  const destinoInput = document.getElementById('destino');
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  // Coordenadas iniciais
  const origemLat = parseFloat(mapElement.dataset.origemLat);
  const origemLon = parseFloat(mapElement.dataset.origemLon);
  const destinoLat = parseFloat(mapElement.dataset.destinoLat);
  const destinoLon = parseFloat(mapElement.dataset.destinoLon);

  // Inicializa mapa
  const map = L.map('map').setView([(origemLat + destinoLat) / 2, (origemLon + destinoLon) / 2], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const origemMarker = L.marker([origemLat, origemLon]).addTo(map).bindPopup('Origem').openPopup();
  const destinoMarker = L.marker([destinoLat, destinoLon]).addTo(map).bindPopup('Destino');

  const rotaPolyline = L.polyline([[origemLat, origemLon], [destinoLat, destinoLon]], {
    color: 'blue',
    weight: 4
  }).addTo(map);

  map.fitBounds(rotaPolyline.getBounds());

  // Atualiza mapa com geocoding automático
  function atualizarMapa() {
    const enderecoOrigem = origemInput.value;
    const enderecoDestino = destinoInput.value;
    if (!enderecoOrigem || !enderecoDestino) return;

    function geocode(endereco) {
      return fetch("/corrida/geocode_ajax/", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": csrfToken,
        },
        body: "endereco=" + encodeURIComponent(endereco)
      }).then(resp => resp.json());
    }

    Promise.all([geocode(enderecoOrigem), geocode(enderecoDestino)])
      .then(results => {
        if (results[0].erro || results[1].erro) return;

        const origem = results[0];
        const destino = results[1];

        // Atualiza marcadores
        origemMarker.setLatLng([origem.lat, origem.lon]);
        destinoMarker.setLatLng([destino.lat, destino.lon]);

        // Atualiza rota
        rotaPolyline.setLatLngs([
          [origem.lat, origem.lon],
          [destino.lat, destino.lon]
        ]);
        map.fitBounds(rotaPolyline.getBounds());
      })
      .catch(err => console.error("Erro ao atualizar mapa:", err));
  }

  origemInput.addEventListener('change', atualizarMapa);
  destinoInput.addEventListener('change', atualizarMapa);
});
