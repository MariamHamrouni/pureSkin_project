import time
import numpy as np
import pandas as pd
import torch
import logging
from sklearn.metrics import silhouette_score
from nlp_engine import PureSkinNLPEngine

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class PureSkinMetrics:
    def __init__(self, engine: PureSkinNLPEngine):
        self.engine = engine

    def run_accuracy_test(self, test_cases):
        """Calcule le Top-K Accuracy et le MRR (Mean Reciprocal Rank)"""
        print(f"\n🔍 ÉVALUATION DE LA PRÉCISION ({len(test_cases)} produits de référence)")
        print("-" * 80)
        print(f"{'Produit Test':<30} | {'Résultat':<12} | {'Latence':<10}")
        print("-" * 80)
        
        hits_at_1 = 0
        hits_at_5 = 0
        reciprocal_ranks = []
        latencies = []

        for case in test_cases:
            start_time = time.perf_counter()
            
            # Appel avec la structure exacte de ton moteur v7.1
           # Modifie l'appel dans run_accuracy_test :
            results = self.engine.find_similar_products(
                target_ingredients=case['ingredients'],
                target_price=case.get('target_price', 0),
                primary=None,   # On retire le filtre
                secondary=None, # On retire le filtre
                top_n=20
            )
            latency = (time.perf_counter() - start_time) * 1000
            latencies.append(latency)

            # Vérification de la présence de la marque attendue
            found_rank = 0
            for i, res in enumerate(results, 1):
                # On compare en minuscule pour éviter les erreurs de casse
                if case['expected_brand'].lower() in res['brand_name'].lower():
                    found_rank = i
                    break
            
            if found_rank > 0:
                if found_rank == 1: hits_at_1 += 1
                if found_rank <= 5: hits_at_5 += 1
                reciprocal_ranks.append(1.0 / found_rank)
                status = f"✅ Rang #{found_rank}"
            else:
                reciprocal_ranks.append(0.0)
                status = "❌ Non trouvé"
            
            print(f"{case['name'][:30]:<30} | {status:<12} | {latency:6.1f}ms")

        stats = {
            "top1": (hits_at_1 / len(test_cases)) * 100,
            "top5": (hits_at_5 / len(test_cases)) * 100,
            "mrr": np.mean(reciprocal_ranks) if reciprocal_ranks else 0,
            "latency": np.mean(latencies)
        }
        return stats

    def run_semantic_test(self):
        """Calcule la cohérence des clusters (Silhouette Score)"""
        print("\n🧪 ANALYSE DE LA STRUCTURE SÉMANTIQUE (Silhouette)")
        
        if self.engine.product_embeddings is None:
            return "Erreur : Embeddings non chargés"

        emb = self.engine.product_embeddings.cpu().numpy()
        df = self.engine.products_df_indexed
        
        # On utilise la catégorie secondaire pour le clustering
        labels = df['secondary_category'].values
        mask = (labels != 'unknown') & (labels != None) & (labels != "")
        
        if mask.sum() < 20:
            return "Données insuffisantes (catégories non indexées)"

        # Calcul sur un échantillon pour la performance
        sample_size = min(2000, mask.sum())
        idx = np.random.choice(np.where(mask)[0], sample_size, replace=False)
        
        try:
            score = silhouette_score(emb[idx], labels[idx])
            return score
        except Exception as e:
            return f"Erreur calcul : {e}"

if __name__ == "__main__":
    # 1. Initialisation
    engine = PureSkinNLPEngine()
    try:
        engine.load_engine("pure_skin_engine.pt")
    except:
        print("❌ Erreur : Assure-toi que pure_skin_engine.pt est présent.")
        exit()

    # 2. DATASET DE TEST CORRIGÉ (INCI Complets)
    bench_data = [
        {
            "name": "The Ordinary Niacinamide",
            "ingredients": "Aqua (Water), Niacinamide, Pentylene Glycol, Zinc PCA, Dimethyl Isosorbide, Tamarindus Indica Seed Gum, Xanthan Gum, Isoceteth-20, Ethoxydiglycol, Phenoxyethanol, Chlorphenesin",
            "expected_brand": "The Ordinary",
            "target_price": 0,
            "primary_category": "Skincare",
            "secondary_category": "serum"
        },
        {
            "name": "CeraVe Moisturizing Cream",
            "ingredients": "Aqua / Water / Eau, Glycerin, Cetearyl Alcohol, Caprylic/Capric Triglyceride, Cetyl Alcohol, Ceteareth-20, Petrolatum, Potassium Phosphate, Ceramide NP, Ceramide AP, Ceramide EOP, Phytosphingosine, Cholesterol, Hyaluronic Acid",
            "expected_brand": "CeraVe",
            "target_price": 0,
            "primary_category": "Skincare",
            "secondary_category": "cream"
        },
        {
            "name": "La Roche-Posay Effaclar Duo",
            "ingredients": "Aqua / Water, Glycerin, Dimethicone, Isocetyl Stearate, Niacinamide, Isopropyl Lauroyl Sarcosinate, Silica, Ammonium Polyacryloyldimethyl Taurate, Methyl Methacrylate Crosspolymer, Potassium Cetyl Phosphate, Sorbitan Oleate, Zinc PCA",
            "expected_brand": "La Roche-Posay",
            "target_price": 0,
            "primary_category": "Skincare",
            "secondary_category": "cream"
        }
    ]

    # 3. Exécution
    metrics = PureSkinMetrics(engine)
    accuracy_results = metrics.run_accuracy_test(bench_data)
    semantic_score = metrics.run_semantic_test()

    # 4. Rapport Final
    print("\n" + "="*80)
    print("📊 RAPPORT DE PERFORMANCE PURESKIN (V7.1)")
    print("="*80)
    print(f"🎯 Précision Top-1     : {accuracy_results['top1']:.1f}%")
    print(f"🎯 Précision Top-5     : {accuracy_results['top5']:.1f}%")
    print(f"🏆 Score MRR           : {accuracy_results['mrr']:.3f} (Proche de 1 = Excellent)")
    print(f"⚡ Latence Moyenne     : {accuracy_results['latency']:.2f} ms")
    
    if isinstance(semantic_score, float):
        print(f"🧬 Cohérence Sémantique: {semantic_score:.3f}")
        if semantic_score < 0:
            print("   ⚠️  Attention : Les catégories se mélangent. Vérifie ton indexation.")
    else:
        print(f"🧬 Cohérence Sémantique: {semantic_score}")
    print("="*80)