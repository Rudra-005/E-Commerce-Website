import json

def filter_dump():
    print("Filtering datadump.json...")
    with open('datadump.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Keep only essential models
    essential_models = [
        'auth.user', 
        'shop.category', 
        'shop.product', 
        'shop.userprofile',
        'shop.shippingaddress',
        'shop.order',
        'shop.orderitem'
    ]
    
    filtered_data = [item for item in data if item['model'] in essential_models]
    
    with open('datadump_filtered.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f)
        
    print(f"Filtered {len(data)} down to {len(filtered_data)} essential records.")

if __name__ == "__main__":
    filter_dump()
