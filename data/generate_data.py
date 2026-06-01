"""
AnalytIQ – Dataset Generator
Produces 7 realistic CSVs grounded in Compass Group campus food-service operations
+ E-commerce orders + SaaS subscriptions (hybrid domain).
Run: python scripts/generate_data.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ── CONFIG ─────────────────────────────────────────────────────────────────────
START = datetime(2024, 1, 1)
END   = datetime(2024, 12, 31)
DATES = [START + timedelta(days=i) for i in range((END - START).days + 1)]

OUTLETS = [
    "Dining Commons", "Taco Bell", "Starbucks",
    "Panda Express", "Einstein Bros", "Micro Market", "Fry Shack",
]

CATEGORIES = {
    "Dining Commons": ["Produce", "Dairy", "Proteins", "Grains", "Beverages", "Desserts"],
    "Taco Bell":      ["Proteins", "Grains", "Produce", "Dairy", "Beverages"],
    "Starbucks":      ["Bakery", "Beverages", "Dairy", "Packaged Snacks"],
    "Panda Express":  ["Proteins", "Grains", "Produce", "Beverages"],
    "Einstein Bros":  ["Bakery", "Dairy", "Beverages", "Packaged Snacks"],
    "Micro Market":   ["Packaged Snacks", "Beverages", "Dairy", "Packaged Meals"],
    "Fry Shack":      ["Proteins", "Produce", "Packaged Snacks", "Beverages"],
}

SKUS = {
    "Produce":         ["Lettuce", "Tomatoes", "Onions", "Bell Peppers", "Cucumbers", "Avocados"],
    "Dairy":           ["Whole Milk", "Shredded Cheese", "Sour Cream", "Yogurt Cups", "Butter"],
    "Proteins":        ["Chicken Strips", "Ground Beef", "Grilled Chicken", "Tofu", "Eggs"],
    "Grains":          ["White Rice", "Tortillas", "Burger Buns", "Pasta", "Bagels"],
    "Beverages":       ["Bottled Water", "Orange Juice", "Energy Drinks", "Lemonade", "Iced Tea"],
    "Desserts":        ["Cookies", "Brownies", "Fruit Cups", "Ice Cream Cups"],
    "Bakery":          ["Croissants", "Muffins", "Bagels", "Cinnamon Rolls", "Scones"],
    "Packaged Snacks": ["Chips", "Granola Bars", "Trail Mix", "Crackers", "Popcorn"],
    "Packaged Meals":  ["Sandwiches", "Salad Kits", "Sushi Packs", "Wraps"],
}

SUPPLIERS = {
    "Produce":         "FreshFarm Co.",
    "Dairy":           "DairyCrest Supply",
    "Proteins":        "Sysco",
    "Grains":          "Sysco",
    "Beverages":       "Beverage Distributors Inc.",
    "Desserts":        "Sweet Provisions",
    "Bakery":          "Local Bakery Vendor",
    "Packaged Snacks": "Snack Nation",
    "Packaged Meals":  "Campus Fresh Co.",
}

UNIT_PRICE = {
    "Produce": 8.5, "Dairy": 6.2, "Proteins": 12.0, "Grains": 4.5,
    "Beverages": 3.8, "Desserts": 5.0, "Bakery": 4.2,
    "Packaged Snacks": 3.5, "Packaged Meals": 9.8,
}

BASE_DAILY = {
    "Dining Commons": 850, "Taco Bell": 280, "Starbucks": 320,
    "Panda Express": 220, "Einstein Bros": 180, "Micro Market": 410, "Fry Shack": 150,
}

PAR_LEVELS = {
    "Dining Commons": 200, "Taco Bell": 80, "Starbucks": 90,
    "Panda Express": 70, "Einstein Bros": 60, "Micro Market": 120, "Fry Shack": 50,
}

SUPPLIER_LEAD = {
    "Sysco": 2, "FreshFarm Co.": 1, "DairyCrest Supply": 2,
    "Beverage Distributors Inc.": 3, "Sweet Provisions": 2,
    "Local Bakery Vendor": 1, "Snack Nation": 4, "Campus Fresh Co.": 1,
}


# ── 1. ACADEMIC CALENDAR ───────────────────────────────────────────────────────
def build_calendar():
    print("Generating academic_calendar.csv ...")
    rows = []
    holiday_map = {
        (1, 1): "New Year's Day",    (1, 15): "MLK Day",
        (2, 19): "Presidents Day",   (5, 27): "Memorial Day",
        (7, 4): "Independence Day",  (9, 2): "Labor Day",
        (11, 28): "Thanksgiving",    (11, 29): "Black Friday",
        (12, 24): "Christmas Eve",   (12, 25): "Christmas Day",
        (12, 31): "New Year's Eve",
    }
    event_map = {
        (1, 20): "Spring Welcome Week",      (2, 14): "Valentine's Special",
        (3, 17): "St. Patrick's Day Event",  (4, 5): "Spring Carnival",
        (8, 26): "Fall Welcome Week",        (9, 15): "Homecoming Weekend",
        (10, 31): "Halloween Festival",      (11, 15): "International Food Fair",
        (12, 6): "End of Semester Celebration",
    }

    for d in DATES:
        m, day, dow = d.month, d.day, d.weekday()
        is_weekend = dow >= 5

        spring = (m == 1 and day >= 16) or m in [2, 3, 4] or (m == 5 and day <= 10)
        summer = (m == 5 and day >= 13) or m in [6, 7] or (m == 8 and day <= 9)
        fall   = (m == 8 and day >= 26) or m in [9, 10, 11] or (m == 12 and day <= 13)
        semester = "Spring" if spring else "Summer" if summer else "Fall" if fall else "Break"

        exam = (
            (m == 4 and day >= 25) or (m == 5 and day <= 10) or
            (m == 7 and day >= 28) or (m == 8 and day <= 9) or
            (m == 12 and 2 <= day <= 13)
        )

        holiday      = holiday_map.get((m, day), "")
        campus_event = event_map.get((m, day), "")
        promotion    = day in {1, 15} and not is_weekend

        base = 1.0
        if is_weekend:               base *= 0.55
        if exam:                     base *= 1.35
        if semester == "Break":      base *= 0.30
        if semester == "Summer":     base *= 0.65
        if holiday:                  base *= 0.20
        if campus_event:             base *= 1.45
        if promotion:                base *= 1.20
        if dow == 4:                 base *= 1.10   # Friday bump

        rows.append({
            "date":              d.strftime("%Y-%m-%d"),
            "day_of_week":       d.strftime("%A"),
            "is_weekend":        is_weekend,
            "semester":          semester,
            "is_exam_period":    exam,
            "is_break":          semester == "Break",
            "holiday":           holiday,
            "campus_event":      campus_event,
            "promotion_active":  promotion,
            "traffic_multiplier": round(base, 3),
        })

    df = pd.DataFrame(rows)
    df.to_csv(f"{DATA_DIR}/academic_calendar.csv", index=False)
    print(f"  → {len(df):,} rows")
    return df.set_index("date")["traffic_multiplier"].to_dict()


# ── 2. SALES TRANSACTIONS ──────────────────────────────────────────────────────
def build_sales(cal):
    print("Generating sales_transactions.csv ...")
    rows = []
    for d in DATES:
        ds   = d.strftime("%Y-%m-%d")
        mult = cal.get(ds, 1.0)
        for outlet in OUTLETS:
            cats = CATEGORIES[outlet]
            for cat in cats:
                skus = SKUS.get(cat, ["Generic Item"])
                for sku in skus:
                    base_qty = int(BASE_DAILY[outlet] / (len(cats) * len(skus)) * mult)
                    qty      = max(0, int(base_qty * np.random.normal(1.0, 0.12)))
                    price    = UNIT_PRICE.get(cat, 5.0) * np.random.uniform(0.9, 1.1)
                    waste_r  = np.random.uniform(0.01, 0.08) if cat in ["Produce","Dairy","Bakery"] else np.random.uniform(0, 0.02)
                    rows.append({
                        "date": ds, "outlet": outlet, "category": cat, "sku": sku,
                        "qty_sold": qty, "unit_price": round(price, 2),
                        "revenue": round(qty * price, 2),
                        "waste_qty": int(qty * waste_r),
                        "traffic_multiplier": mult,
                    })
    df = pd.DataFrame(rows)
    df.to_csv(f"{DATA_DIR}/sales_transactions.csv", index=False)
    print(f"  → {len(df):,} rows")


# ── 3. INVENTORY LEVELS ────────────────────────────────────────────────────────
def build_inventory(cal):
    print("Generating inventory_levels.csv ...")
    rows = []
    for d in DATES:
        ds   = d.strftime("%Y-%m-%d")
        mult = cal.get(ds, 1.0)
        for outlet in OUTLETS:
            for cat in CATEGORIES[outlet]:
                par      = PAR_LEVELS[outlet]
                on_hand  = int(par * np.random.uniform(0.4, 1.8))
                avg_use  = max(1, int(par * mult * 0.35))
                doh      = round(on_hand / avg_use, 2)
                status   = (
                    "Overstock"     if doh > 7  else
                    "Stockout Risk" if doh < 1.5 else
                    "Watch"         if doh < 3   else "Healthy"
                )
                rows.append({
                    "date": ds, "outlet": outlet, "category": cat,
                    "on_hand_qty": on_hand, "par_level": par,
                    "avg_daily_usage": avg_use, "days_on_hand": doh,
                    "inventory_status": status,
                    "overstock_flag": status == "Overstock",
                    "stockout_risk_flag": status == "Stockout Risk",
                })
    df = pd.DataFrame(rows)
    df.to_csv(f"{DATA_DIR}/inventory_levels.csv", index=False)
    print(f"  → {len(df):,} rows")


# ── 4. FORECAST VS ACTUAL ──────────────────────────────────────────────────────
def build_forecast(cal):
    print("Generating forecast_vs_actual.csv ...")
    rows = []
    for d in DATES:
        ds   = d.strftime("%Y-%m-%d")
        mult = cal.get(ds, 1.0)
        for outlet in OUTLETS:
            for cat in CATEGORIES[outlet]:
                base  = BASE_DAILY[outlet] / len(CATEGORIES[outlet])
                fc    = round(base, 1)
                act   = round(base * mult * np.random.normal(1.0, 0.10), 1)
                var   = round(act - fc, 1)
                rows.append({
                    "date": ds, "outlet": outlet, "category": cat,
                    "forecast_qty": fc, "actual_qty": act,
                    "variance": var,
                    "variance_pct": round((var / fc) * 100, 2) if fc else 0,
                    "traffic_multiplier": mult,
                })
    df = pd.DataFrame(rows)
    df.to_csv(f"{DATA_DIR}/forecast_vs_actual.csv", index=False)
    print(f"  → {len(df):,} rows")


# ── 5. SUPPLIER ORDERS ─────────────────────────────────────────────────────────
def build_supplier_orders():
    print("Generating supplier_orders.csv ...")
    rows, oid = [], 1000
    for d in DATES[::3]:
        ds = d.strftime("%Y-%m-%d")
        for cat, supplier in SUPPLIERS.items():
            lead     = SUPPLIER_LEAD.get(supplier, 2)
            delivery = d + timedelta(days=lead + random.randint(0, 1))
            fill     = round(np.random.uniform(0.88, 1.0), 3)
            qty      = random.randint(50, 300)
            rows.append({
                "order_id":             f"ORD-{oid}",
                "order_date":           ds,
                "delivery_date":        delivery.strftime("%Y-%m-%d"),
                "supplier":             supplier,
                "category":             cat,
                "order_qty":            qty,
                "received_qty":         int(qty * fill),
                "fill_rate":            fill,
                "on_time_delivery":     random.random() > 0.08,
                "lead_time_days":       lead,
                "substitution_occurred": random.random() < 0.05,
                "unit_cost":            round(UNIT_PRICE.get(cat, 5.0) * 0.6, 2),
            })
            oid += 1
    df = pd.DataFrame(rows)
    df.to_csv(f"{DATA_DIR}/supplier_orders.csv", index=False)
    print(f"  → {len(df):,} rows")


# ── 6. E-COMMERCE ORDERS ──────────────────────────────────────────────────────
def build_orders(cal):
    print("Generating orders.csv ...")
    ecom_cats = ["Electronics","Apparel","Home & Kitchen","Beauty","Sports","Books","Toys"]
    channels  = ["Web","Mobile App","Mobile App","Web","In-Store"]
    segments  = ["Student","Faculty","Staff","Alumni","Public"]
    rows, oid = [], 5000
    for d in DATES:
        ds   = d.strftime("%Y-%m-%d")
        mult = cal.get(ds, 1.0)
        for _ in range(int(np.random.poisson(max(1, 12 * mult)))):
            cat    = random.choice(ecom_cats)
            aov    = round(np.random.lognormal(3.5, 0.6), 2)
            status = random.choices(
                ["Completed","Refunded","Cancelled"],
                weights=[80, 12, 8]
            )[0]
            rows.append({
                "order_id":          f"EC-{oid}",
                "order_date":        ds,
                "category":          cat,
                "channel":           random.choice(channels),
                "customer_segment":  random.choice(segments),
                "order_value":       aov,
                "status":            status,
                "refund_amount":     round(aov * np.random.uniform(0.5, 1.0), 2) if status == "Refunded" else 0,
                "units":             random.randint(1, 5),
            })
            oid += 1
    df = pd.DataFrame(rows)
    df.to_csv(f"{DATA_DIR}/orders.csv", index=False)
    print(f"  → {len(df):,} rows")


# ── 7. SAAS SUBSCRIPTIONS ─────────────────────────────────────────────────────
def build_subscriptions():
    print("Generating subscriptions.csv ...")
    plans  = {"Starter": 29, "Growth": 79, "Pro": 149, "Enterprise": 399}
    events = ["new","upgrade","downgrade","churn","reactivation"]
    w_evts = [35, 10, 8, 20, 12]
    rows, sid = [], 1

    for month_num in range(1, 13):
        mstart   = datetime(2024, month_num, 1)
        n_users  = random.randint(40, 120)
        for _ in range(n_users):
            plan     = random.choices(list(plans), weights=[40, 30, 20, 10])[0]
            event    = random.choices(events, weights=w_evts)[0]
            ev_date  = mstart + timedelta(days=random.randint(0, 27))
            mrr      = plans[plan]
            if event == "upgrade":
                mrr = plans[random.choice(["Growth","Pro","Enterprise"])]
            elif event == "churn":
                mrr = 0
            elif event == "downgrade":
                mrr = plans["Starter"]

            rows.append({
                "subscription_id":  f"SUB-{sid:05d}",
                "event_date":       ev_date.strftime("%Y-%m-%d"),
                "cohort_month":     mstart.strftime("%Y-%m"),
                "plan":             plan,
                "event_type":       event,
                "mrr":              mrr,
                "customer_segment": random.choice(["SMB","Mid-Market","Enterprise","Startup"]),
                "trial_converted":  random.random() > 0.35,
            })
            sid += 1

    df = pd.DataFrame(rows)
    df.to_csv(f"{DATA_DIR}/subscriptions.csv", index=False)
    print(f"  → {len(df):,} rows")


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cal = build_calendar()
    build_sales(cal)
    build_inventory(cal)
    build_forecast(cal)
    build_supplier_orders()
    build_orders(cal)
    build_subscriptions()
    print("\n✅  All 7 datasets generated in /data/")
