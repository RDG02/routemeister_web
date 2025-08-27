// Location Admin Geolocate JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Zoek het adres veld
    const addressField = document.querySelector('#id_address');
    const latitudeField = document.querySelector('#id_latitude');
    const longitudeField = document.querySelector('#id_longitude');
    
    if (addressField) {
        // Maak geolocate container
        const geolocateContainer = document.createElement('div');
        geolocateContainer.className = 'geolocate-container';
        
        // Maak geolocate knop
        const geolocateButton = document.createElement('button');
        geolocateButton.type = 'button';
        geolocateButton.className = 'geolocate-button';
        geolocateButton.innerHTML = '🌍 Geolocate';
        geolocateButton.title = 'Genereer coördinaten op basis van het adres';
        
        // Maak resultaat div
        const resultDiv = document.createElement('div');
        resultDiv.className = 'geolocate-result';
        resultDiv.style.display = 'none';
        
        // Voeg elementen toe aan container
        geolocateContainer.appendChild(geolocateButton);
        geolocateContainer.appendChild(resultDiv);
        
        // Voeg container toe na het adres veld
        const addressFieldContainer = addressField.closest('.form-row');
        if (addressFieldContainer) {
            addressFieldContainer.appendChild(geolocateContainer);
        }
        
        // Geolocate functionaliteit
        geolocateButton.addEventListener('click', function() {
            const address = addressField.value.trim();
            
            if (!address) {
                showResult('Voer eerst een adres in', 'error');
                return;
            }
            
            // Toon loading state
            geolocateButton.disabled = true;
            geolocateButton.classList.add('loading');
            geolocateButton.innerHTML = '⏳ Zoeken...';
            
            // AJAX request naar geolocate endpoint
            fetch('/admin/planning/location/geolocate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: 'address=' + encodeURIComponent(address)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Vul coördinaten in
                    if (latitudeField) latitudeField.value = data.latitude;
                    if (longitudeField) longitudeField.value = data.longitude;
                    
                    // Toon resultaat
                    showResult(
                        `✅ Coördinaten gevonden: ${data.latitude}, ${data.longitude}`,
                        'success'
                    );
                    
                    // Toon coördinaten display
                    showCoordinates(data.latitude, data.longitude);
                } else {
                    showResult(`❌ ${data.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('Geolocate error:', error);
                showResult('❌ Fout bij geocoding. Probeer het opnieuw.', 'error');
            })
            .finally(() => {
                // Reset button state
                geolocateButton.disabled = false;
                geolocateButton.classList.remove('loading');
                geolocateButton.innerHTML = '🌍 Geolocate';
            });
        });
        
        function showResult(message, type) {
            resultDiv.textContent = message;
            resultDiv.className = 'geolocate-result ' + type;
            resultDiv.style.display = 'block';
            
            // Verberg na 5 seconden
            setTimeout(() => {
                resultDiv.style.display = 'none';
            }, 5000);
        }
        
        function showCoordinates(lat, lng) {
            // Verwijder bestaande coordinates display
            const existingDisplay = document.querySelector('.coordinates-display');
            if (existingDisplay) {
                existingDisplay.remove();
            }
            
            // Maak nieuwe coordinates display
            const coordinatesDisplay = document.createElement('div');
            coordinatesDisplay.className = 'coordinates-display';
            coordinatesDisplay.innerHTML = `📍 ${lat}, ${lng}`;
            
            // Voeg toe na de geolocate container
            geolocateContainer.appendChild(coordinatesDisplay);
        }
        
        // CSRF token helper
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        
        // Auto-geolocate bij adres wijziging (optioneel)
        let geocodeTimeout;
        addressField.addEventListener('input', function() {
            clearTimeout(geocodeTimeout);
            geocodeTimeout = setTimeout(() => {
                const address = addressField.value.trim();
                if (address && (!latitudeField.value || !longitudeField.value)) {
                    // Auto-geolocate als coördinaten leeg zijn
                    geolocateButton.click();
                }
            }, 2000); // 2 seconden delay
        });
    }
});
