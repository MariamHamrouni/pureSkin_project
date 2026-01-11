from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import io
import logging
import traceback
from pathlib import Path
from PIL import Image
from fastapi.middleware.cors import CORSMiddleware
from difflib import SequenceMatcher
import numpy as np

# --- IMPORTS LOCAUX ---
try:
    from nlp_engine import PureSkinNLPEngine
except ImportError:
    # Mock pour tester
    class PureSkinNLPEngine:
        def __init__(self, enable_cache=True):
            self.enable_cache = enable_cache
            self.products_df_indexed = None
            self.product_embeddings = None

        def load_engine(self, path):
            pass

        def load_and_vectorize_data(self, df):
            self.products_df_indexed = df

        def save_engine(self, path):
            pass

        def get_full_product_report(self, product_name, ingredients, brand):
            return {"mock": True, "product": product_name}

        def find_similar_products(self, target_ingredients, target_price, top_n, primary=None, secondary=None):
            return []

        def get_product_recommendations(self, skin_type):
            return []

        def analyze_review(self, text, skin_type):
            return {"mock": True}

try:
    from ocr_service import extract_product_info_enhanced
    OCR_AVAILABLE = True
    print("✅ Module OCR chargé avec succès.")
except ImportError as e:
    OCR_AVAILABLE = False
    print(f"⚠️ Module OCR non disponible (ImportError): {e}")
except Exception as e:
    OCR_AVAILABLE = False
    print(f"⚠️ Erreur chargement OCR: {e}")


# --- CONFIGURATION LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialisation de l'application
app = FastAPI(
    title="PureSkin NLP Service - Intelligent Scanner",
    version="7.1",
    description="API optimisée pour l'analyse cosmétique + OCR + matching DB (rating)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- VARIABLES GLOBALES ---
engine: PureSkinNLPEngine = None

# --- MODÈLES DE DONNÉES ---
class QualityRequest(BaseModel):
    product_name: str
    brand_name: str = ""
    ingredients: str = ""

class DupeRequest(BaseModel):
    ingredients: str
    target_price: float = 0.0
    primary_category: Optional[str] = None
    secondary_category: Optional[str] = None
    top_n: int = 20

class ReviewRequest(BaseModel):
    text: str
    skin_type: Optional[str] = "all"

class RecoRequest(BaseModel):
    skin_type: str
    max_price: Optional[float] = None
    category: Optional[str] = None
class ProductFavorite(BaseModel):
    product_name: str
    brand_name: str
    price: float = 0.0
    similarity: float = 0.0
    primary_category: str = "Unknown"
favorites_db = []


# --- DÉMARRAGE OPTIMISÉ ---
@app.on_event("startup")
async def startup_event():
    global engine
    logger.info("🚀 Démarrage du service PureSkin 7.1...")

    try:
        engine = PureSkinNLPEngine(enable_cache=True)

        # 1) tentative chargement cache
        try:
            logger.info("📂 Chargement du moteur pré-calculé (fast load)...")
            engine.load_engine("pure_skin_engine.pt")
            logger.info("✅ Moteur chargé depuis le cache.")
        except Exception as e:
            logger.warning(f"⚠️ Cache introuvable ou invalide ({e}). Passage au chargement CSV.")

            # 2) fallback CSV
            csv_path = Path("product_info_cleaned.csv")
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                engine.load_and_vectorize_data(df)
                try:
                    engine.save_engine("pure_skin_engine.pt")
                except Exception:
                    logger.warning("⚠️ Sauvegarde du cache impossible (pas bloquant).")
            else:
                logger.warning("⚠️ Fichier CSV introuvable ! Création de données mock.")
                mock_data = {
                    "product_name": ["Crème Hydratante", "Sérum Vitamin C", "Nettoyant Doux"],
                    "brand_name": ["L'ORÉAL", "The Ordinary", "CeraVe"],
                    "ingredients": ["Aqua, Glycerin, Dimethicone", "Ascorbic Acid, Propanediol", "Ceramides, Hyaluronic Acid"],
                    "price_usd": [25.99, 12.50, 15.75],
                    "primary_category": ["Moisturizer", "Serum", "Cleanser"],
                    "rating": [4.2, 4.4, 4.6],
                }
                df = pd.DataFrame(mock_data)
                engine.load_and_vectorize_data(df)

    except Exception as e:
        logger.error(f"❌ Erreur critique au démarrage : {e}")
        logger.error(traceback.format_exc())


# --- ENDPOINTS PRINCIPAUX ---
@app.get("/")
def read_root():
    return {
        "status": "online",
        "version": "7.1",
        "products_indexed": len(engine.products_df_indexed) if engine and engine.products_df_indexed is not None else 0,
        "ocr_available": OCR_AVAILABLE,
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ocr_available": OCR_AVAILABLE,
        "engine_loaded": engine is not None,
        "products_loaded": len(engine.products_df_indexed) if engine and engine.products_df_indexed is not None else 0,
    }

@app.post("/analyze/quality")
async def api_analyze_quality(request: QualityRequest):
    if not engine:
        raise HTTPException(503, "Moteur non prêt")

    return engine.get_full_product_report(
        request.product_name,
        request.ingredients,
        request.brand_name
    )

@app.post("/analyze/find_dupes")
async def find_dupes(req: DupeRequest):
    if not engine:
        raise HTTPException(503, "Moteur non prêt")

    logger.info(f"🔎 Recherche Smart Dupe pour produit à {req.target_price}$")

    candidates = engine.find_similar_products(
        target_ingredients=req.ingredients,
        target_price=0,
        top_n=req.top_n,
        primary=req.primary_category,
        secondary=req.secondary_category
    )

    smart_dupes = []
    for prod in candidates:
        price = prod.get("price", 0) or 0
        similarity = prod.get("similarity", 0) or 0

        is_cheaper = True
        savings = 0.0

        if req.target_price > 0:
            if price > 0 and price < (req.target_price * 0.85):
                savings = req.target_price - price
            else:
                is_cheaper = False

        if similarity > 0.70 and is_cheaper:
            prod["savings_amount"] = round(savings, 2)
            prod["is_economic_dupe"] = True
            smart_dupes.append(prod)

    if smart_dupes:
        smart_dupes.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return {"found_cheaper_dupe": True, "best_dupe": smart_dupes[0], "alternatives": smart_dupes[:5]}

    return {
        "found_cheaper_dupe": False,
        "message": "Aucun dupe significativement moins cher trouvé.",
        "alternatives": candidates[:5] if candidates else []
    }

@app.post("/analyze/ocr_only")
async def ocr_only(file: UploadFile = File(...)):
    """OCR uniquement (retour brut ocr_service)"""
    if not OCR_AVAILABLE:
        raise HTTPException(501, "Module OCR non installé")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        return extract_product_info_enhanced(image, debug_mode=False)
    except Exception as e:
        logger.error(f"Erreur OCR: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, str(e))

@app.post("/analyze/ocr_rating")
async def ocr_rating(file: UploadFile = File(...)):
    """
    OCR + Matching DB via ocr_service (retourne directement rating/prix)
    """
    if not OCR_AVAILABLE:
        raise HTTPException(501, "Module OCR non installé")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        ocr_result = extract_product_info_enhanced(image, debug_mode=False)
        if not ocr_result.get("success"):
            return {"success": False, "error": ocr_result.get("error", "Erreur OCR")}

        return {
            "success": True,
            "ocr_db_match": {
                "brand_name": ocr_result.get("brand", ""),
                "product_name": ocr_result.get("product_name", ""),
                "rating": ocr_result.get("rating", None),
                "price_usd": ocr_result.get("price_usd", None),
                "match_score": ocr_result.get("match_score", 0),
                "confidence": ocr_result.get("confidence", "low"),
                "ocr_type": ocr_result.get("ocr_type", ""),
            }
        }

    except Exception as e:
        logger.error(f"Erreur /analyze/ocr_rating: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Erreur interne: {str(e)}")

@app.post("/analyze/scan")
async def scan_product(file: UploadFile = File(...)):
    """
    Scan complet:
    - OCR (brand + product)
    - Matching DB (dans l'engine) + analyse NLP
    """
    if not OCR_AVAILABLE:
        raise HTTPException(501, "Module OCR non installé. Installez avec: pip install pytesseract pillow")

    if not engine:
        raise HTTPException(503, "Moteur non prêt")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        # 1) OCR
        ocr_result = extract_product_info_enhanced(image, debug_mode=False)
        if not ocr_result.get("success"):
            return {"success": False, "error": ocr_result.get("error", "Erreur OCR")}

        brand = ocr_result.get("brand", "Unknown")
        product_name = ocr_result.get("product_name", "Unknown Product")

        # 2) Recherche DB dans engine (fix brand_name)
        matches = []
        analysis = None

        df = engine.products_df_indexed
        if df is not None and not df.empty:
            search_name = str(product_name).lower().strip()
            search_brand = str(brand).lower().strip()

            for _, row in df.iterrows():
                db_name = str(row.get("product_name", "")).lower()
                # ✅ IMPORTANT: brand_name (fallback brand si existe)
                db_brand = str(row.get("brand_name", row.get("brand", ""))).lower()

                name_similarity = SequenceMatcher(None, search_name, db_name).ratio()
                brand_similarity = SequenceMatcher(None, search_brand, db_brand).ratio()

                if name_similarity > 0.60 or (brand_similarity > 0.80 and name_similarity > 0.30):
                    matches.append({
                        "product_name": row.get("product_name"),
                        "brand_name": row.get("brand_name", row.get("brand", "")),
                        "ingredients": row.get("ingredients", ""),
                        "price_usd": row.get("price_usd", 0),
                        "rating": row.get("rating", None),
                        "primary_category": row.get("primary_category", ""),
                        "similarity_score": round(max(name_similarity, brand_similarity), 2),
                        "match_type": "name_match"
                    })

            if matches:
                matches.sort(key=lambda x: x["similarity_score"], reverse=True)
                best_match = matches[0]

                analysis = engine.get_full_product_report(
                    product_name=best_match["product_name"],
                    ingredients=best_match["ingredients"],
                    brand=best_match["brand_name"]
                )

        return {
            "success": True,
            "ocr_data": {
                "brand": brand,
                "product_name": product_name,
                "confidence": ocr_result.get("confidence", "low"),
                "match_score_from_ocr_service": ocr_result.get("match_score", 0),
                "rating_from_ocr_service": ocr_result.get("rating", None),
                "price_from_ocr_service": ocr_result.get("price_usd", None),
            },
            "database_matches": {
                "count": len(matches),
                "matches": matches[:5]
            },
            "analysis": analysis if analysis else {
                "warning": "Aucun produit correspondant trouvé dans la base de données",
                "suggestion": "Essayez /analyze/ocr_rating (OCR + DB) ou saisissez les ingrédients via /analyze/quality"
            }
        }

    except Exception as e:
        logger.error(f"Erreur Scan: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Erreur interne: {str(e)}")

@app.post("/analyze/recommend")
async def recommend(req: RecoRequest):
    if not engine:
        raise HTTPException(503, "Moteur non prêt")

    recos = engine.get_product_recommendations(req.skin_type) or []

    if req.max_price is not None:
        recos = [r for r in recos if (r.get("price_usd", 0) or 0) <= req.max_price]

    return {"recommendations": recos[:10]}

@app.post("/analyze/review")
async def review_analysis(req: ReviewRequest):
    if not engine:
        raise HTTPException(503, "Moteur non prêt")
    return engine.analyze_review(req.text, req.skin_type)
@app.get("/analyze/filters")
async def get_filters():
    """
    Récupère les listes uniques de catégories et marques depuis la DB chargée.
    """
    if not engine or engine.products_df_indexed is None:
        return {
            "categories": ["Skincare", "Makeup", "Haircare"], # Fallback par défaut
            "brands": [],
            "types": ["Serum", "Cream", "Cleanser", "Toner", "Mask"] # Fallback
        }

    try:
        df = engine.products_df_indexed
        
        # 1. Récupération des Catégories (primary_category)
        # On nettoie : pas de null, title case, trié alphabétiquement
        categories = []
        if "primary_category" in df.columns:
            categories = sorted(df["primary_category"].dropna().astype(str).unique().tolist())
        
        # 2. Récupération des Marques (brand_name)
        brands = []
        if "brand_name" in df.columns:
            # On prend les marques qui ont au moins 2 produits pour éviter le bruit
            # (Optionnel, tu peux retirer value_counts si tu veux tout)
            brands = sorted(df["brand_name"].dropna().astype(str).unique().tolist())

        # 3. Récupération des Types (secondary_category ou inference)
        # Si tu as une colonne 'product_type' ou 'secondary_category', utilise-la.
        # Sinon, on peut scanner les mots clés fréquents dans product_name
        types = []
        if "secondary_category" in df.columns:
             types = sorted(df["secondary_category"].dropna().astype(str).unique().tolist())
        else:
            # Liste dynamique basée sur ce qui existe vraiment
            common_types = ["Serum", "Cream", "Cleanser", "Toner", "Moisturizer", "Mask", "Oil", "Sunscreen"]
            # On ne garde que ceux qui apparaissent dans les noms de produits de la DB
            all_names = " ".join(df["product_name"].astype(str).tolist()).lower()
            types = [t for t in common_types if t.lower() in all_names]

        return {
            "categories": categories,
            "brands": brands,
            "types": types
        }

    except Exception as e:
        logger.error(f"Erreur récupération filtres: {e}")
        return {"categories": [], "brands": [], "types": []}
@app.get("/favorites")
async def get_favorites():
    """Récupère la liste des favoris"""
    return favorites_db

@app.post("/favorites")
async def add_favorite(product: ProductFavorite):
    """Ajoute un produit aux favoris"""
    # Vérifie si déjà présent pour éviter les doublons
    for fav in favorites_db:
        if fav.product_name == product.product_name and fav.brand_name == product.brand_name:
            return {"message": "Déjà dans les favoris"}
    
    favorites_db.append(product)
    return {"message": "Ajouté", "count": len(favorites_db)}

@app.delete("/favorites/{product_name}")
async def remove_favorite(product_name: str):
    """Retire un produit (par son nom pour simplifier)"""
    global favorites_db
    favorites_db = [p for p in favorites_db if p.product_name != product_name]
    return {"message": "Retiré", "count": len(favorites_db)}

# --- DEBUG & VISUALISATION (Optionnel) ---
@app.get("/debug/visualization")
async def trigger_visualization():
    if not engine:
        return {"error": "Engine not loaded"}

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.manifold import TSNE

        if engine.product_embeddings is not None:
            embeddings = engine.product_embeddings.cpu().numpy()
            sample_size = min(500, len(embeddings))
            indices = np.random.choice(len(embeddings), sample_size, replace=False)
            tsne = TSNE(n_components=2, perplexity=30, random_state=42)
            vis_data = tsne.fit_transform(embeddings[indices])

            plt.figure(figsize=(10, 6))
            plt.scatter(vis_data[:, 0], vis_data[:, 1], alpha=0.5)
            plt.title("PureSkin Semantic Map (Sample)")
            plt.xlabel("TSNE Component 1")
            plt.ylabel("TSNE Component 2")

            filename = "debug_map.png"
            plt.savefig(filename)
            plt.close()
            return {"success": True, "file": filename}

        return {"error": "No embeddings available"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Démarrage de l'API PureSkin sur http://0.0.0.0:8000")
    print("📚 Documentation: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
