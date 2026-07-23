import json
import psycopg2
import os
from dotenv import load_dotenv

def fast_sql_load():
    load_dotenv()
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Set DATABASE_URL")
        return
        
    print(f"Connecting to {db_url}")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    with open('datadump_filtered.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    cats = [d for d in data if d['model'] == 'shop.category']
    prods = [d for d in data if d['model'] == 'shop.product']
    
    print("Skipping truncate to avoid locks...")
    
    print(f"Inserting {len(cats)} categories...")
    for c in cats:
        f = c['fields']
        cur.execute("INSERT INTO shop_category (id, name, slug) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING;", (c['pk'], f['name'], f.get('slug', f['name'].lower().replace(' ', '-'))))
        
    print(f"Inserting {len(prods)} products...")
    for p in prods:
        f = p['fields']
        cur.execute("INSERT INTO shop_product (id, category, category_fk_id, name, description, price, stock, image, early_access_only, popularity_score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;", (p['pk'], f['category'], f['category_fk'], f['name'], f.get('description', ''), f['price'], f['stock'], f.get('image', ''), f.get('early_access_only', False), f.get('popularity_score', 0.0)))
        
    conn.commit()
    cur.close()
    conn.close()
    print("Done bulk SQL load!")

if __name__ == '__main__':
    fast_sql_load()
