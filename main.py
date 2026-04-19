import base64
import json
import os

import openai
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PRICE_DB = {
    "egg": {"price": 0.30, "unit": "each"},
    "eggs": {"price": 0.30, "unit": "each"},
    "butter": {"price": 0.25, "unit": "tbsp"},
    "milk": {"price": 0.15, "unit": "cup"},
    "heavy cream": {"price": 0.50, "unit": "cup"},
    "cream cheese": {"price": 1.50, "unit": "cup"},
    "sour cream": {"price": 0.40, "unit": "cup"},
    "cheddar cheese": {"price": 1.00, "unit": "cup"},
    "parmesan": {"price": 1.20, "unit": "cup"},
    "mozzarella": {"price": 0.90, "unit": "cup"},
    "yogurt": {"price": 0.80, "unit": "cup"},
    "chicken breast": {"price": 2.00, "unit": "lb"},
    "chicken": {"price": 1.80, "unit": "lb"},
    "ground beef": {"price": 3.00, "unit": "lb"},
    "beef": {"price": 4.00, "unit": "lb"},
    "pork": {"price": 2.50, "unit": "lb"},
    "bacon": {"price": 0.75, "unit": "slice"},
    "salmon": {"price": 5.00, "unit": "lb"},
    "shrimp": {"price": 4.00, "unit": "lb"},
    "tuna": {"price": 1.50, "unit": "can"},
    "onion": {"price": 0.50, "unit": "each"},
    "garlic": {"price": 0.10, "unit": "clove"},
    "tomato": {"price": 0.75, "unit": "each"},
    "tomatoes": {"price": 0.75, "unit": "each"},
    "potato": {"price": 0.50, "unit": "each"},
    "potatoes": {"price": 0.50, "unit": "each"},
    "carrot": {"price": 0.30, "unit": "each"},
    "carrots": {"price": 0.30, "unit": "each"},
    "celery": {"price": 0.20, "unit": "stalk"},
    "bell pepper": {"price": 1.00, "unit": "each"},
    "lemon": {"price": 0.60, "unit": "each"},
    "lime": {"price": 0.40, "unit": "each"},
    "spinach": {"price": 0.20, "unit": "cup"},
    "broccoli": {"price": 0.40, "unit": "cup"},
    "mushrooms": {"price": 0.50, "unit": "cup"},
    "zucchini": {"price": 0.80, "unit": "each"},
    "avocado": {"price": 1.20, "unit": "each"},
    "flour": {"price": 0.05, "unit": "cup"},
    "sugar": {"price": 0.10, "unit": "cup"},
    "brown sugar": {"price": 0.12, "unit": "cup"},
    "olive oil": {"price": 0.20, "unit": "tbsp"},
    "vegetable oil": {"price": 0.10, "unit": "tbsp"},
    "rice": {"price": 0.15, "unit": "cup"},
    "pasta": {"price": 0.30, "unit": "cup"},
    "bread crumbs": {"price": 0.15, "unit": "cup"},
    "panko": {"price": 0.20, "unit": "cup"},
    "oats": {"price": 0.10, "unit": "cup"},
    "honey": {"price": 0.30, "unit": "tbsp"},
    "soy sauce": {"price": 0.10, "unit": "tbsp"},
    "vinegar": {"price": 0.05, "unit": "tbsp"},
    "chicken broth": {"price": 0.50, "unit": "cup"},
    "beef broth": {"price": 0.50, "unit": "cup"},
    "tomato paste": {"price": 0.40, "unit": "tbsp"},
    "canned tomatoes": {"price": 1.20, "unit": "can"},
    "coconut milk": {"price": 1.80, "unit": "can"},
    "beans": {"price": 0.80, "unit": "can"},
    "chickpeas": {"price": 0.80, "unit": "can"},
    "baking powder": {"price": 0.02, "unit": "tsp"},
    "baking soda": {"price": 0.01, "unit": "tsp"},
    "vanilla extract": {"price": 0.25, "unit": "tsp"},
    "cocoa powder": {"price": 0.20, "unit": "tbsp"},
    "chocolate chips": {"price": 0.40, "unit": "cup"},
    "yeast": {"price": 0.30, "unit": "tsp"},
    "salt": {"price": 0.01, "unit": "tsp"},
    "pepper": {"price": 0.02, "unit": "tsp"},
    "cumin": {"price": 0.05, "unit": "tsp"},
    "paprika": {"price": 0.05, "unit": "tsp"},
    "oregano": {"price": 0.04, "unit": "tsp"},
    "thyme": {"price": 0.04, "unit": "tsp"},
    "cinnamon": {"price": 0.04, "unit": "tsp"},
    "chili powder": {"price": 0.05, "unit": "tsp"},
}

UNIT_CONVERSIONS = {
    "tbsp": 1, "tablespoon": 1, "tablespoons": 1,
    "tsp": 1/3, "teaspoon": 1/3, "teaspoons": 1/3,
    "cup": 16, "cups": 16,
    "oz": 2, "ounce": 2, "ounces": 2,
    "lb": 32, "pound": 32, "pounds": 32,
    "can": 1, "each": 1, "clove": 1, "cloves": 1,
    "slice": 1, "slices": 1, "stalk": 1, "stalks": 1,
}


def estimate_cost(ingredients: list[dict]) -> list[dict]:
    results = []
    for ing in ingredients:
        name = ing["name"].lower().strip()
        qty = float(ing.get("quantity", 1))
        unit = ing.get("unit", "each").lower().strip()

        match = None
        for key in PRICE_DB:
            if key in name or name in key:
                match = key
                break

        if match:
            db = PRICE_DB[match]
            qty_units = UNIT_CONVERSIONS.get(unit, 1) * qty
            db_units = UNIT_CONVERSIONS.get(db["unit"], 1)
            item_cost = db["price"] * (qty_units / db_units if db_units else 1)
        else:
            item_cost = 0.50 * qty

        results.append({
            "name": ing["name"],
            "quantity": qty,
            "unit": unit,
            "estimated_cost": round(item_cost, 2),
            "matched": match is not None,
        })
    return results


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    image_bytes = await file.read()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = file.content_type or "image/jpeg"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You are a recipe parser. Extract the recipe name and all ingredients "
                                "from this cookbook image. Return JSON in this exact format:\n"
                                '{"recipe_name": "...", "servings": 4, "ingredients": ['
                                '{"name": "all-purpose flour", "quantity": 2, "unit": "cup"}]}\n'
                                "Use standard units: tsp, tbsp, cup, oz, lb, each, clove, slice, can, stalk. "
                                "Normalize ingredient names to lowercase singular form. "
                                "If servings are not mentioned, estimate based on the recipe type."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )
    except openai.OpenAIError as e:
        raise HTTPException(status_code=502, detail=str(e))

    parsed = json.loads(response.choices[0].message.content)
    ingredients = parsed.get("ingredients", [])
    costed = estimate_cost(ingredients)
    total = sum(i["estimated_cost"] for i in costed)
    servings = parsed.get("servings", 4) or 4

    return {
        "recipe_name": parsed.get("recipe_name", "Unknown Recipe"),
        "servings": servings,
        "ingredients": costed,
        "total": round(total, 2),
        "per_serving": round(total / servings, 2),
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
