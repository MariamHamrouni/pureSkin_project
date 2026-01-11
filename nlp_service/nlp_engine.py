import pandas as pd
import numpy as np
import torch
import re
import warnings
import logging
import hashlib
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from transformers import pipeline, AutoTokenizer
from sentence_transformers import SentenceTransformer, util

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TruncationConfig:
    max_tokens: int = 400
    preserve_end: bool = True
    preserve_key_sections: bool = True

class SmartTextProcessor:
    def __init__(self):
        # Utilisation d'un tokenizer standard pour le calcul des limites de tokens
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased", use_fast=True)
    
    def smart_truncate(self, text: str, config: TruncationConfig = None) -> str:
        if config is None: 
            config = TruncationConfig()
        text = str(text)
        tokens = self.tokenizer.tokenize(text)
        if len(tokens) <= config.max_tokens: 
            return text
        
        tokens_begin = int(config.max_tokens * 0.7)
        tokens_end = config.max_tokens - tokens_begin
        begin_text = self.tokenizer.convert_tokens_to_string(tokens[:tokens_begin])
        end_text = self.tokenizer.convert_tokens_to_string(tokens[-tokens_end:])
        return f"{begin_text} ... {end_text}"

class PureSkinNLPEngine:
    def __init__(self, enable_cache: bool = True):
        logger.info("🚀 Initialisation PureSkin NLP Engine (V7.1 - SciBERT Optimized)")
        self.text_processor = SmartTextProcessor()
        self.enable_cache = enable_cache
        self.embedding_cache = {} if enable_cache else None
        
        self.product_embeddings = None
        self.products_df_indexed = None 
        
        # Modèle spécialisé dans les publications scientifiques/chimiques
        # Note: Le warning "Creating a new one with mean pooling" est normal pour ce modèle
        self.model_name = 'allenai/scibert_scivocab_uncased'
        self._load_models()
    
    def _get_cached_embedding(self, text: str):
        """Récupère un embedding depuis le cache mémoire"""
        if not self.enable_cache or self.embedding_cache is None:
            return None
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return self.embedding_cache.get(text_hash)
    
    def _cache_embedding(self, text: str, embedding):
        """Stocke un embedding dans le cache"""
        if self.enable_cache and self.embedding_cache is not None:
            text_hash = hashlib.md5(text.encode()).hexdigest()
            self.embedding_cache[text_hash] = embedding

    def _load_models(self):
        try:
            # 1. Analyse de Sentiment
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=-1,
                truncation=True,
                max_length=512
            )
            # 2. Modèle de similarité Biochimique
            logger.info(f"🧪 Chargement du modèle scientifique : {self.model_name}")
            self.similarity_model = SentenceTransformer(self.model_name)
            self.similarity_model.max_seq_length = 512
            logger.info("✅ Modèles IA chargés avec succès.")
        except Exception as e:
            logger.error(f"❌ Erreur chargement modèles: {e}")
            # Fallback en cas d'erreur
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')

    def clean_and_weight_ingredients(self, text: str) -> str:
        """
        Nettoie la liste INCI pour l'analyse vectorielle.
        SciBERT préfère une liste propre sans répétition artificielle.
        """
        if not text or pd.isna(text): 
            return "unknown"
        
        text = str(text).lower()
        
        # 1. Normalisation des synonymes fréquents (Standardisation)
        replacements = {
            'aqua': 'water', 'eau': 'water', 
            'parfum': 'fragrance',
            'alcohol denat.': 'alcohol',
            'l-ascorbic acid': 'ascorbic acid', # Vitamin C
            'tocopherol': 'vitamin e'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # 2. Suppression des concentrations (ex: 10%, 2.5%)
        text = re.sub(r'\d+(\.\d+)?%', '', text)
        
        # 3. Découpage
        parts = [p.strip() for p in text.split(',')]
        
        # 4. Nettoyage Regex : On garde lettres, chiffres, tirets et parenthèses (chimie)
        parts = [re.sub(r'[^a-z0-9 /()+-]', '', p) for p in parts]
        
        # 5. Filtrage du "bruit" (ingrédients neutres ultra-fréquents)
        noise = {'water', 'glycerin', 'glycerine', 'phenoxyethanol', 'alcohol'}
        cleaned = [p.strip() for p in parts if p.strip() not in noise and len(p) > 2]
        
        if not cleaned: return "unknown"

        # Note: Pour SciBERT, on évite la duplication (poids * 2) car le modèle
        # comprend le contexte global de la formule.
        return " ".join(cleaned)

    def detect_categories(self, product_name: str, ingredients: str = "") -> Tuple[str, str]:
        """Identifie la catégorie primaire et secondaire par analyse sémantique et regex."""
        text = f"{product_name} {ingredients}".lower()
        
        # Détection Primaire
        primary = "Skincare"
        if re.search(r'\b(shampoo|conditioner|hair|cheveux|scalp)\b', text):
            primary = "Haircare"
        elif re.search(r'\b(foundation|makeup|maquillage|lipstick|mascara)\b', text):
            primary = "Makeup"
        elif re.search(r'\b(shower gel|body wash|savon|soap|body)\b', text):
            primary = "Bodycare"
        elif re.search(r'\b(parfum|perfume|fragrance|scent)\b', text):
            primary = "Fragrance"

        # Détection Secondaire (Type de produit)
        secondary_patterns = {
            'cream': r'\b(cream|crème|moisturizer|hydratant|lotion|balm|baume)\b',
            'serum': r'\b(serum|sérum|concentrate|concentré|ampoule)\b',
            'cleanser': r'\b(cleanser|nettoyant|wash|gel nettoyant|mousse|micellar)\b',
            'toner': r'\b(toner|tonique|lotion tonique)\b',
            'mask': r'\b(mask|masque|patch)\b',
            'sunscreen': r'\b(sunscreen|spf|écran|solaire|uv)\b',
            'oil': r'\b(oil|huile)\b',
            'scrub': r'\b(scrub|gommage|exfoliant|peeling)\b'
        }
        
        secondary = 'unknown'
        for s_type, pattern in secondary_patterns.items():
            if re.search(pattern, text):
                secondary = s_type
                break
        return primary, secondary

    def load_and_vectorize_data(self, df: pd.DataFrame):
        """Prépare le dataset et calcule les embeddings pour la recherche."""
        logger.info(f"⚙️ Préparation de {len(df)} produits avec SciBERT...")
        self.products_df_indexed = df.reset_index(drop=True).copy()
        
        # Assurer que les colonnes existent
        for col in ['product_name', 'ingredients', 'brand_name']:
            if col not in self.products_df_indexed.columns:
                self.products_df_indexed[col] = ''

        # Calcul automatique des catégories
        cats = self.products_df_indexed.apply(lambda r: self.detect_categories(
            str(r.get('product_name', '')), 
            str(r.get('ingredients', ''))
        ), axis=1)
        self.products_df_indexed['primary_category'] = [c[0] for c in cats]
        self.products_df_indexed['secondary_category'] = [c[1] for c in cats]
        
        # Calcul des vecteurs sémantiques
        texts_to_embed = self.products_df_indexed['ingredients'].apply(
            self.clean_and_weight_ingredients
        ).tolist()
        
        self.product_embeddings = self.similarity_model.encode(
            texts_to_embed, 
            convert_to_tensor=True, 
            show_progress_bar=True, 
            normalize_embeddings=True,
            batch_size=32
        )
        logger.info("✅ Indexation biochimique terminée.")

    def find_similar_products(self, target_ingredients: str, target_price: float = 0, 
                             top_n: int = 5, primary: Optional[str] = None, 
                             secondary: Optional[str] = None) -> List[Dict]:
        """Recherche les dupes par similarité cosinus."""
        if self.product_embeddings is None:
            logger.warning("Tentative de recherche sur un moteur non initialisé.")
            return []
        
        # 1. Filtres de catégorie (Optionnels mais recommandés pour la précision)
        mask = pd.Series([True] * len(self.products_df_indexed))
        if primary and primary != "All":
            mask &= (self.products_df_indexed['primary_category'] == primary)
        if secondary and secondary != "unknown":
            mask &= (self.products_df_indexed['secondary_category'] == secondary)
        
        # Filtre Prix (Si spécifié)
        if target_price > 0:
            # On cherche des produits moins chers ou dans une gamme similaire (+/- 50%)
            price_vals = pd.to_numeric(self.products_df_indexed['price_usd'], errors='coerce').fillna(0)
            mask &= (price_vals <= (target_price * 1.5))

        valid_indices = self.products_df_indexed.index[mask].tolist()
        if not valid_indices: 
            # Si aucun produit ne correspond aux filtres, on cherche dans tout le catalogue
            valid_indices = self.products_df_indexed.index.tolist()
        
        # 2. Gestion du Cache & Encodage Requête
        cleaned_query = self.clean_and_weight_ingredients(target_ingredients)
        cached_emb = self._get_cached_embedding(cleaned_query)
        
        if cached_emb is not None:
            query_emb = cached_emb
        else:
            query_emb = self.similarity_model.encode(
                cleaned_query, 
                convert_to_tensor=True, 
                normalize_embeddings=True
            )
            self._cache_embedding(cleaned_query, query_emb)
        
        # 3. Calcul de Similarité (Cosinus)
        filtered_embs = self.product_embeddings[valid_indices]
        cos_scores = util.cos_sim(query_emb, filtered_embs)[0]
        
        # Récupération du Top K
        actual_top_k = min(top_n, len(valid_indices))
        top_results = torch.topk(cos_scores, k=actual_top_k)

        results = []
        for score, local_idx in zip(top_results.values, top_results.indices):
            idx = valid_indices[local_idx.item()]
            product = self.products_df_indexed.iloc[idx]
            
            # Conversion sécurisée du prix
            try:
                price = float(product.get('price_usd', 0))
            except:
                price = 0.0

            results.append({
                'product_id': str(product.get('product_id', '')),
                'product_name': str(product.get('product_name', '')),
                'brand_name': str(product.get('brand_name', '')),
                'price': price,
                'similarity': round(float(score.item()), 3),
                'secondary_category': product.get('secondary_category', 'unknown'),
                'rating': float(product.get('rating', 0) or 0),
                'reviews': int(product.get('reviews', 0) or 0),
                # Debug info
                'ingredients_preview': str(product.get('ingredients', ''))[:100]
            })
        
        return results

    def get_full_product_report(self, product_name: str, ingredients: str, brand: str = "") -> Dict:
        """Génère le rapport complet pour l'API."""
        primary, secondary = self.detect_categories(product_name, ingredients)
        safety = self.analyze_ingredients_safety(ingredients)
        similar = self.find_similar_products(ingredients, secondary=secondary, top_n=5)
        
        # Calcul statistiques marché
        avg_price = 0
        if similar:
            prices = [p['price'] for p in similar if p['price'] > 0]
            if prices:
                avg_price = sum(prices) / len(prices)

        return {
            "identification": {
                "product_name": product_name,
                "brand": brand,
                "detected_category": secondary,
                "primary_category": primary
            },
            "ingredients_analysis": safety,
            "market_analysis": {
                "average_similar_price": round(avg_price, 2),
                "similar_count": len(similar)
            },
            "top_similar_products": similar
        }

    def analyze_ingredients_safety(self, ingredients: str) -> Dict:
        """Analyse basique des risques."""
        ing_lower = str(ingredients).lower()
        hazards = {
            "comedogenic": ['isopropyl myristate', 'coconut oil', 'sodium chloride', 'lanolin'],
            "irritants": ['fragrance', 'parfum', 'alcohol denat', 'menthol', 'linalool'],
            "check_list": ['paraben', 'sulfate', 'phthalate', 'formaldehyde']
        }
        
        found = {cat: [i for i in lst if i in ing_lower] for cat, lst in hazards.items()}
        total_hazards = sum(len(v) for v in found.values())
        
        score = "Excellent" if total_hazards == 0 else "Good" if total_hazards <= 2 else "Caution"
        found["safety_score"] = score
        return found

    def get_product_recommendations(self, skin_type: str = "all") -> List[Dict]:
        """Retourne les top produits (mockup intelligent basé sur le rating)."""
        if self.products_df_indexed is None: return []
        
        df = self.products_df_indexed
        # Filtrage basique par mot-clé dans les highlights si dispo
        if skin_type != "all" and 'highlights' in df.columns:
            mask = df['highlights'].astype(str).str.contains(skin_type, case=False, na=False)
            if mask.any():
                df = df[mask]
            
        return df.sort_values(by=['rating', 'reviews'], ascending=False).head(10).to_dict('records')

    def analyze_review(self, text: str, skin_type: str = "all") -> Dict:
        """Analyse de sentiment pour les avis."""
        try:
            res = self.sentiment_pipeline(text[:512])[0]
            return {
                "sentiment": res['label'],
                "confidence": round(res['score'], 3),
                "skin_type_mentioned": skin_type if skin_type in text.lower() else "none"
            }
        except:
            return {"sentiment": "NEUTRAL", "confidence": 0.0}

    def save_engine(self, path: str = "pure_skin_engine.pt"):
        data = {
            'embeddings': self.product_embeddings, 
            'df': self.products_df_indexed,
            'config': {'model': self.model_name}
        }
        torch.save(data, path)
        logger.info(f"💾 Moteur sauvegardé vers {path}")

    def load_engine(self, path: str = "pure_skin_engine.pt"):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        try:
            # Note: weights_only=False nécessaire pour charger des DataFrames pandas stockés
            data = torch.load(path, map_location=device, weights_only=False)
            self.product_embeddings = data['embeddings']
            self.products_df_indexed = data['df']
            logger.info(f"📂 Moteur chargé avec {len(self.products_df_indexed)} produits.")
        except Exception as e:
            logger.error(f"❌ Erreur chargement : {e}")
            raise e