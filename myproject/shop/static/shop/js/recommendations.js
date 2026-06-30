function loadRecommendations(type, containerId, title, extraParams = "") {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let url = `/api/recommendations/?type=${type}${extraParams}`;
    
    fetch(url, { cache: 'no-store' })
        .then(response => response.json())
        .then(data => {
            if (data.recommendations && data.recommendations.length > 0) {
                let html = `
                <div class="rec-section" data-aos="fade-up">
                    <h2 class="rec-header">${title}</h2>
                    <div class="rec-carousel">
                `;
                
                data.recommendations.forEach(product => {
                    html += `
                        <a href="/product/${product.id}/" class="rec-card">
                            <img src="${product.image}" alt="${product.name}">
                            <div class="rec-info">
                                <h4 class="rec-title" title="${product.name}">${product.name}</h4>
                                <div class="rec-rating">⭐ ${parseFloat(product.rating || 0).toFixed(1)}</div>
                                <div class="rec-price">₹${product.price}</div>
                                <button class="rec-cart-btn" onclick="event.preventDefault(); window.location.href='/add-to-cart/${product.id}/'">ADD TO CART</button>
                            </div>
                        </a>
                    `;
                });
                html += `
                    </div>
                </div>`;
                container.innerHTML = html;
            } else {
                container.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error loading recommendations:', error);
            container.style.display = 'none';
        });
}
