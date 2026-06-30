function detectLocation(btnId, address1Id, cityId, stateId, pincodeId) {
    const btn = document.getElementById(btnId);
    
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    const originalText = btn.innerText;
    btn.innerText = "📍 Detecting...";
    btn.disabled = true;

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            
            // Using OpenStreetMap Nominatim for Reverse Geocoding
            const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1`;
            
            fetch(url, {
                headers: {
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            })
            .then(response => response.json())
            .then(data => {
                const address = data.address;
                
                // Construct Address Line 1
                let addrLine1 = [];
                if (address.house_number) addrLine1.push(address.house_number);
                if (address.road) addrLine1.push(address.road);
                if (address.suburb) addrLine1.push(address.suburb);
                else if (address.neighbourhood) addrLine1.push(address.neighbourhood);
                
                let addrString = addrLine1.join(", ");
                if (!addrString) {
                    addrString = data.display_name.split(",").slice(0, 2).join(", ");
                }
                
                const city = address.city || address.town || address.village || address.state_district || "";
                const state = address.state || "";
                const pincode = address.postcode || "";

                // Populate Fields
                if (document.getElementById(address1Id)) document.getElementById(address1Id).value = addrString;
                if (document.getElementById(cityId)) document.getElementById(cityId).value = city;
                if (document.getElementById(stateId)) document.getElementById(stateId).value = state;
                if (document.getElementById(pincodeId)) document.getElementById(pincodeId).value = pincode;
                
                btn.innerText = "✅ Location Detected";
                setTimeout(() => {
                    btn.innerText = originalText;
                    btn.disabled = false;
                }, 3000);
            })
            .catch(error => {
                console.error("Error fetching location details:", error);
                alert("Failed to get address from location. Please try manually.");
                btn.innerText = originalText;
                btn.disabled = false;
            });
        },
        (error) => {
            console.error("Geolocation Error:", error);
            alert("Location access denied or unavailable. Please fill manually.");
            btn.innerText = originalText;
            btn.disabled = false;
        }
    );
}
