import re

with open('myproject/shop/templates/shop/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('{% if search or category %}', '{% if search or category or collection_name %}')
content = content.replace('{% if search or category or selected_category %}', '{% if search or category or selected_category or collection_name %}')

# We want to add the hidden input for collection_name just after the hidden input for category
hidden_input_category = """{% elif selected_category %}
            <input type="hidden" name="category" value="{{ selected_category }}">
            {% endif %}"""

hidden_input_collection = """{% elif selected_category %}
            <input type="hidden" name="category" value="{{ selected_category }}">
            {% endif %}
            
            {% if collection_name %}
            <input type="hidden" name="collection" value="{{ collection_name }}">
            {% endif %}"""

content = content.replace(hidden_input_category, hidden_input_collection)

with open('myproject/shop/templates/shop/home.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Template fixed.")
