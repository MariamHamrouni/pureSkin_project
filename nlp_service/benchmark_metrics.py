from nlp_engine import PureSkinNLPEngine
import time
import numpy as np

# --- 1. DÉFINITION DU DATASET DE TEST (PRODUITS DE LUXE RÉELS) ---
# Ce sont de vrais produits très chers. On veut voir si l'IA trouve des alternatives dans VOTRE dataset.
LUXURY_BENCHMARK = [
    {
        "name": "La Mer - The Concentrate Serum",
        "price": 425.0,
        "category": "serum",
        "ingredients": "cyclopentasiloxane, algae extract, glycerin, dimethicone, polysilicone-11, isononyl isononanoate, dimethicone/peg-10/15 crosspolymer, cyclohexasiloxane, sesamum indicum (sesame) seed oil, medicago sativa (alfalfa) seed powder, helianthus annuus (sunflower) seedcake, prunus amygdalus dulcis (sweet almond) seed meal, eucalyptus globulus (eucalyptus) leaf oil, sodium gluconate, copper gluconate, calcium gluconate, magnesium gluconate, zinc gluconate, tocopheryl succinate, niacin"
    },
    {
        "name": "SK-II - Ultimate Revival Cream",
        "price": 400.0,
        "category": "cream",
        "ingredients": "aqua (water), glycerin, galactomyces ferment filtrate, niacinamide, phytosteryl/behenyl/octyldodecyl lauroyl glutamate, ethylhexyl isononanoate, butylene glycol, triethylhexanoin, neopentyl glycol diethylhexanoate, simmondsia chinensis (jojoba) seed oil, sucrose polycottonseedate, glyceryl stearate se, myristyl myristate"
    },
    {
        "name": "Dr. Barbara Sturm - Super Anti-Aging Night Cream",
        "price": 395.0,
        "category": "cream",
        "ingredients": "aqua/water/eau, coco-caprylate/caprate, cetyl alcohol, glycerin, helianthus annuus (sunflower) seed oil, prunus amygdalus dulcis (sweet almond) oil, potassium cetyl phosphate, lactobacillus/portulaca oleracea ferment extract, hydrogenated palm glycerides, argania spinosa kernel oil, panthenol, sodium polyglutamate"
    },
    {
        "name": "Augustinus Bader - The Serum with TFC8",
        "price": 390.0,
        "category": "serum",
        "ingredients": "aqua/water/eau, glycerin, 1,2-hexanediol, cellulose, ethylhexyl polyhydroxystearate, resveratrol, squalane, sodium acrylates copolymer, ascorbyl tetraisopalmitate, oryza sativa (rice) bran oil, maltodextrin, lecithin, sodium acetylated hyaluronate, polysorbate 20"
    },
    {
        "name": "SkinCeuticals - C E Ferulic",
        "price": 169.0,
        "category": "serum",
        "ingredients": "Water, Ethoxydiglycol, L-Ascorbic Acid, Propylene Glycol, Glycerin, Laureth-23, Phenoxyethanol, Tocopherol, Triethanolamine, Ferulic Acid"
    }
]

def run_benchmark():
    print("⏳ Chargement du moteur IA...")
    engine = PureSkinNLPEngine()
    engine.load_engine("pure_skin_engine.pt")

    print(f"\n🚀 DÉBUT DU BENCHMARK SCIENTIFIQUE ({len(LUXURY_BENCHMARK)} produits)")
    print("=" * 80)

    latencies = []
    reciprocal_ranks = []
    hits = 0

    for product in LUXURY_BENCHMARK:
        print(f"\n💎 Cible : {product['name']} ({product['price']}$)")
        
        # 1. Mesure de la Latence
        start_time = time.perf_counter()
        results = engine.find_similar_products(
            target_ingredients=product['ingredients'],
            secondary=product['category'],
            top_n=20 # On regarde le top 20 pour calculer le MRR
        )
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

        # 2. Recherche du premier "Vrai Dupe"
        # Critères : Similarité > 70% ET Prix < 80% du prix cible
        first_valid_rank = 0
        found_dupe = None
        
        for i, res in enumerate(results, 1):
            is_cheaper = res['price'] > 0 and res['price'] < (product['price'] * 0.8)
            is_similar = res['similarity'] > 0.70
            
            if is_cheaper and is_similar:
                first_valid_rank = i
                found_dupe = res
                break # On a trouvé le premier (le mieux classé)
        
        # 3. Calcul des scores pour ce produit
        if first_valid_rank > 0:
            hits += 1
            rr = 1.0 / first_valid_rank
            reciprocal_ranks.append(rr)
            print(f"   ✅ Dupe trouvé au rang #{first_valid_rank} : {found_dupe['brand_name']} ({found_dupe['price']}$)")
            print(f"      Score MRR : {rr:.2f}")
        else:
            reciprocal_ranks.append(0.0)
            print("   ❌ Aucun dupe économique valide trouvé dans le Top 20.")

    # --- CALCUL DES MÉTRIQUES GLOBALES ---
    avg_latency = np.mean(latencies)
    mrr_score = np.mean(reciprocal_ranks)
    accuracy = (hits / len(LUXURY_BENCHMARK)) * 100

    print("\n" + "="*80)
    print("📊 RAPPORT DE PERFORMANCE FINAL")
    print("="*80)
    print(f"⚡ Latence Moyenne : {avg_latency:.2f} ms")
    print("-" * 40)
    print(f"🎯 Accuracy (Hit Rate) : {accuracy:.1f}%")
    print("   (Pourcentage de produits chers pour lesquels on trouve une alternative)")
    print("-" * 40)
    print(f"🏆 MRR Score (Classement) : {mrr_score:.3f} / 1.0")
    print("   (Plus c'est proche de 1, plus le dupe apparaît tôt dans la liste)")
    print("="*80)

    # Interprétation
    if mrr_score > 0.6:
        print("✅ CONCLUSION : Le moteur classe les dupes économiques en TÊTE de liste.")
    elif mrr_score > 0.3:
        print("⚠️ CONCLUSION : Le moteur trouve des dupes, mais ils sont parfois bas dans la liste.")
    else:
        print("❌ CONCLUSION : Le moteur a du mal à trouver des alternatives pertinentes.")

if __name__ == "__main__":
    run_benchmark()