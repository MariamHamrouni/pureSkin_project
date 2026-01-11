from nlp_engine import PureSkinNLPEngine
import pandas as pd

# 1. Chargement du moteur
print("⏳ Chargement du cerveau IA...")
engine = PureSkinNLPEngine()
engine.load_engine("pure_skin_engine.pt")

# 2. Définition de produits DE LUXE (Inputs externes)
# On se fiche de la marque, on veut juste voir si l'IA trouve une alternative pas chère
expensive_targets = [
    {
        "name": "Sérum Luxe Vitamine C (180$)",
        "price": 180.0,
        "ingredients": "Water, Ethoxydiglycol, L-Ascorbic Acid, Propylene Glycol, Glycerin, Laureth-23, Phenoxyethanol, Tocopherol, Triethanolamine, Ferulic Acid, Panthenol, Sodium Hyaluronate",
        "category": "serum"
    },
    {
        "name": "Crème Hydratante Haut de Gamme (85$)",
        "price": 85.0,
        "ingredients": "Aqua/Water/Eau, Saccharomyces/Camellia Sinensis Leaf/Cladosiphon Okamuranus/Rice Ferment Filtrate, Dimethicone, Propanediol, Glycerin, Diglycerin, Diphenylsiloxy Phenyl Trimethicone, Gold, Hydrolyzed Silk",
        "category": "cream"
    },
    {
        "name": "Exfoliant BHA Culte (45$)",
        "price": 45.0,
        "ingredients": "Water, Methylpropanediol, Butylene Glycol, Salicylic Acid, Polysorbate 20, Camellia Oleifera Leaf Extract, Sodium Hydroxide, Tetrasodium EDTA",
        "category": "toner"
    }
]

print(f"\n🚀 RECHERCHE DE DUPES ÉCONOMIQUES")
print("=" * 60)

for target in expensive_targets:
    print(f"\n💎 CIBLE : {target['name']}")
    print(f"   🧪 Ingrédients clés : {target['ingredients'][:60]}...")
    
    # Recherche dans TA base de données
    results = engine.find_similar_products(
        target_ingredients=target['ingredients'],
        secondary=target['category'],
        top_n=10  # On cherche large pour trouver le moins cher
    )
    
    found_dupe = False
    best_deal = None
    
    # Filtrage intelligent : On cherche haute similarité ET bas prix
    for res in results:
        # Critères du DUPE PARFAIT :
        # 1. Similarité chimique > 70% (C'est la même chose)
        # 2. Prix nettement inférieur (au moins 30% moins cher)
        if res['similarity'] > 0.70 and res['price'] < (target['price'] * 0.7):
            
            saving = target['price'] - res['price']
            print(f"   ✅ DUPE TROUVÉ : {res['brand_name']} - {res['product_name']}")
            print(f"      💰 Prix : {res['price']}$ (Économie: -{saving:.0f}$ !)")
            print(f"      🧪 Similarité : {res['similarity']*100:.1f}%")
            found_dupe = True
            
            # On s'arrête au premier bon dupe trouvé (souvent le meilleur ranké)
            break
            
    if not found_dupe:
        # Si on a pas trouvé de "Vrai" dupe, on montre juste le plus proche chimiquement
        best = results[0]
        print(f"   ⚠️ Pas de dupe 'parfait' bon marché trouvé.")
        print(f"      Le plus proche chimiquement est : {best['brand_name']} ({best['price']}$)")
        print(f"      Similarité : {best['similarity']*100:.1f}%")

print("\n" + "="*60)