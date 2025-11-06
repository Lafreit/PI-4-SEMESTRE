document.addEventListener("DOMContentLoaded", function () {
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

    // Atualiza texto do slide
    toleranciaRange.addEventListener("input", () => {
        toleranciaValor.textContent = toleranciaRange.value;
    });

    // Função de busca (simula o backend)
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

        // Aqui você faria uma requisição real:
        // const response = await fetch(`/buscar_corridas_api/?origem=${origem}&destino=${destino}&tol=${tolerancia}`);
        // const data = await response.json();

        // Simulação de retorno:
        const data = [
            {
                origem: "Santo André",
                destino: "Nova Odessa",
                origem_lat: -23.682,
                origem_lon: -46.510,
                destino_lat: -22.784,
                destino_lon: -47.303,
                valor: 55,
                horario_saida: "08:30"
            },
            {
                origem: "São Paulo",
                destino: "Campinas",
                origem_lat: -23.55,
                origem_lon: -46.63,
                destino_lat: -22.90,
                destino_lon: -47.06,
                valor: 65,
                horario_saida: "10:00"
            }
        ];

        if (data.length === 0) {
            corridasContainer.innerHTML = "<p>Nenhuma corrida encontrada.</p>";
            return;
        }

        data.forEach((c, i) => {
            // Adiciona markers e rota
            const origem = [c.origem_lat, c.origem_lon];
            const destino = [c.destino_lat, c.destino_lon];
            const polyline = L.polyline([origem, destino], { color: "blue", weight: 4 }).addTo(map);

            L.marker(origem).addTo(map).bindPopup(`<strong>${c.origem}</strong>`);
            L.marker(destino).addTo(map).bindPopup(`<strong>${c.destino}</strong>`);

            // Card da corrida
            const card = document.createElement("div");
            card.className = "corrida-card";
            card.innerHTML = `
                <strong>${c.origem} → ${c.destino}</strong><br>
                Saída: ${c.horario_saida}<br>
                Valor: R$ ${c.valor}
            `;
            card.addEventListener("click", () => {
                map.fitBounds(polyline.getBounds(), { padding: [20, 20] });
            });
            corridasContainer.appendChild(card);
        });

        map.fitBounds(L.latLngBounds(data.map(c => [c.origem_lat, c.origem_lon])));
    });
});
