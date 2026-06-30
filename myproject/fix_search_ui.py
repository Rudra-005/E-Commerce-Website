import os
import re

css_block = """
    /* SEARCH AUTOCOMPLETE */
    .comic-search { position: relative; }
    .search-suggestions {
        position: absolute;
        top: calc(100% + 5px);
        left: 0;
        width: 100%;
        background: #fff;
        border: 4px solid #000;
        box-shadow: 6px 6px 0px #000;
        z-index: 10001;
        display: none;
        max-height: 300px;
        overflow-y: auto;
    }
    .suggestion-item {
        padding: 10px 15px;
        border-bottom: 3px solid #000;
        font-family: 'Comic Neue', cursive;
        font-size: 18px;
        color: #000;
        cursor: pointer;
        display: block;
        transition: all 0.2s ease;
    }
    .suggestion-item:last-child {
        border-bottom: none;
    }
    .suggestion-item:hover {
        background: var(--primary-yellow);
        padding-left: 20px;
    }
    .suggestion-price {
        font-family: 'Bangers', cursive;
        color: var(--primary-red);
        font-size: 20px;
    }
"""

js_block = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById("searchInput");
    const suggestions = document.getElementById("suggestions");
    let debounceTimer;

    if(searchInput && suggestions){
        searchInput.addEventListener("input", function(){
            clearTimeout(debounceTimer);
            const query = this.value.trim();

            if(query.length === 0){
                suggestions.style.display = "none";
                return;
            }

            debounceTimer = setTimeout(()=>{
                fetch(`/search-suggestions/?term=${encodeURIComponent(query)}`)
                .then(res=>res.json())
                .then(data=>{
                    let html = "";
                    if(data.length === 0){
                        html = '<div class="suggestion-item">No products found</div>';
                    } else {
                        data.forEach(product=>{
                            html += `
                            <div class="suggestion-item" onclick="window.location='/product/${product.id}/'">
                                <strong>${product.name}</strong><br>
                                <span class="suggestion-price">₹${product.price}</span>
                            </div>`;
                        });
                    }
                    suggestions.innerHTML = html;
                    suggestions.style.display = "block";
                })
                .catch(err => console.error(err));
            }, 300);
        });

        document.addEventListener("click", function(e){
            if(!searchInput.contains(e.target) && !suggestions.contains(e.target)){
                suggestions.style.display = "none";
            }
        });
    }
});
</script>
"""

templates = [
    "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/shop/templates/shop/home.html",
    "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/shop/templates/shop/product_list.html",
    "c:/Users/rudra/Downloads/E-Commerce-Website/myproject/shop/templates/shop/product_detail.html"
]

for file_path in templates:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Inject CSS if not present
    if "/* SEARCH AUTOCOMPLETE */" not in content:
        content = content.replace("</style>", css_block + "\\n</style>")

    # 2. Fix the input field and search container
    # Find the input field for search and add id="searchInput" autocomplete="off"
    content = re.sub(
        r'(<input[^>]*name="search"[^>]*)>',
        lambda m: m.group(1) + ' id="searchInput" autocomplete="off">' if 'id="searchInput"' not in m.group(1) else m.group(0),
        content
    )
    
    # Check if suggestions div exists, if not, append after </form> within comic-search
    if 'id="suggestions"' not in content:
        # We need to find </form> that is inside <div class="comic-search">
        # This regex replaces the </form> specifically for the search form.
        content = re.sub(
            r'(<div class="comic-search"[^>]*>.*?<form[^>]*>.*?</form>)',
            r'\1\n            <div id="suggestions" class="search-suggestions"></div>',
            content,
            flags=re.DOTALL
        )
    
    # 3. Add JS block if not present
    if "fetch(`/search-suggestions/" not in content:
        content = content.replace("</body>", js_block + "\\n</body>")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Search autocomplete UI updated successfully.")
