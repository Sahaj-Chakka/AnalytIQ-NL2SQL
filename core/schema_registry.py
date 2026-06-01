"""
Schema Registry
Defines every table's structure + semantic descriptions used to build
the vector store context that guides SQL generation.
"""

SCHEMA_REGISTRY = {
    "academic_calendar": {
        "description": (
            "Campus academic calendar for 2024. Contains one row per day with "
            "context about semester periods, exam weeks, holidays, campus events, "
            "weekday/weekend flags, promotion schedules, and a traffic_multiplier "
            "that reflects how busy campus is on any given day. "
            "Join this table on `date` to contextualize demand, inventory, or sales "
            "patterns by academic period."
        ),
        "columns": {
            "date":               "Calendar date (YYYY-MM-DD). Primary join key.",
            "day_of_week":        "Day name: Monday … Sunday.",
            "is_weekend":         "True if Saturday or Sunday.",
            "semester":           "Academic period: Spring | Summer | Fall | Break.",
            "is_exam_period":     "True during finals weeks (Spring Apr-May, Summer Jul-Aug, Fall Dec).",
            "is_break":           "True during inter-semester breaks (low campus traffic).",
            "holiday":            "Holiday name if applicable, empty string otherwise.",
            "campus_event":       "Named campus event if applicable (e.g. Homecoming Weekend, Spring Carnival).",
            "promotion_active":   "True on promotion days (1st and 15th of each month, weekdays only).",
            "traffic_multiplier": "Relative foot-traffic index. 1.0 = normal weekday. <0.5 = quiet. >1.2 = high.",
        },
        "sample_questions": [
            "How does foot traffic differ between exam periods and regular weeks?",
            "Which campus events drove the highest sales spikes?",
            "Show me the traffic multiplier for every holiday in 2024.",
        ],
    },

    "sales_transactions": {
        "description": (
            "Daily item-level sales for all 7 campus food outlets: "
            "Dining Commons, Taco Bell, Starbucks, Panda Express, "
            "Einstein Bros, Micro Market, and Fry Shack. "
            "Each row is one outlet–category–SKU–day combination. "
            "Use this table for revenue, volume, waste, and outlet performance queries."
        ),
        "columns": {
            "date":                "Sale date (YYYY-MM-DD).",
            "outlet":              "Food outlet name.",
            "category":            "Product category: Produce, Dairy, Proteins, Grains, Beverages, Desserts, Bakery, Packaged Snacks, Packaged Meals.",
            "sku":                 "Stock-keeping unit / item name.",
            "qty_sold":            "Units sold that day.",
            "unit_price":          "Selling price per unit (USD).",
            "revenue":             "Total revenue = qty_sold × unit_price (USD).",
            "waste_qty":           "Units wasted/unsold that day.",
            "traffic_multiplier":  "Foot-traffic index on this date (from academic_calendar).",
        },
        "sample_questions": [
            "Which outlet had the highest revenue last week?",
            "Show me waste quantity by category across all outlets in April.",
            "What were the top 5 SKUs by revenue in the Fall semester?",
            "How did Starbucks sales compare on exam days vs normal days?",
        ],
    },

    "inventory_levels": {
        "description": (
            "Daily inventory health snapshot for every outlet–category combination. "
            "Tracks on-hand quantity, par levels, average daily usage, days-on-hand (DOH), "
            "and inventory status flags (Overstock / Stockout Risk / Watch / Healthy). "
            "Use this table for inventory risk, overstock analysis, and replenishment queries."
        ),
        "columns": {
            "date":                "Snapshot date (YYYY-MM-DD).",
            "outlet":              "Food outlet name.",
            "category":            "Product category.",
            "on_hand_qty":         "Quantity currently in stock.",
            "par_level":           "Target inventory level (units).",
            "avg_daily_usage":     "Average units consumed per day.",
            "days_on_hand":        "Estimated days of stock remaining = on_hand_qty / avg_daily_usage.",
            "inventory_status":    "Status: Overstock | Stockout Risk | Watch | Healthy.",
            "overstock_flag":      "True when days_on_hand > 7.",
            "stockout_risk_flag":  "True when days_on_hand < 1.5.",
        },
        "sample_questions": [
            "Which outlets had the most overstock days in Q3?",
            "Which categories are at stockout risk today?",
            "Show average days-on-hand by outlet for the Fall semester.",
            "How many Stockout Risk events occurred at Micro Market?",
        ],
    },

    "forecast_vs_actual": {
        "description": (
            "Daily demand forecast accuracy table comparing forecasted vs actual "
            "quantities for each outlet–category combination. "
            "Variance = actual − forecast. Positive variance means demand exceeded forecast. "
            "Use for forecast accuracy, demand planning, and seasonality analysis."
        ),
        "columns": {
            "date":               "Date (YYYY-MM-DD).",
            "outlet":             "Food outlet name.",
            "category":           "Product category.",
            "forecast_qty":       "Forecasted demand quantity.",
            "actual_qty":         "Actual demand quantity.",
            "variance":           "Demand variance = actual_qty − forecast_qty.",
            "variance_pct":       "Variance as percentage of forecast.",
            "traffic_multiplier": "Campus foot-traffic index on this date.",
        },
        "sample_questions": [
            "Which outlet had the worst forecast accuracy in December?",
            "Show me average variance by category during exam periods.",
            "Where was demand consistently under-forecast?",
            "How does forecast variance change on campus event days?",
        ],
    },

    "supplier_orders": {
        "description": (
            "Supplier order and delivery records for all product categories. "
            "Captures order quantities, received quantities, fill rates, "
            "on-time delivery, lead times, and substitution incidents. "
            "Key suppliers include Sysco, FreshFarm Co., DairyCrest Supply, "
            "Beverage Distributors Inc., and Local Bakery Vendor."
        ),
        "columns": {
            "order_id":              "Unique order identifier (ORD-XXXX).",
            "order_date":            "Date order was placed (YYYY-MM-DD).",
            "delivery_date":         "Actual delivery date (YYYY-MM-DD).",
            "supplier":              "Supplier name.",
            "category":              "Product category ordered.",
            "order_qty":             "Quantity ordered.",
            "received_qty":          "Quantity actually received.",
            "fill_rate":             "Fraction of order fulfilled (0–1).",
            "on_time_delivery":      "True if delivered on or before scheduled date.",
            "lead_time_days":        "Days between order placement and delivery.",
            "substitution_occurred": "True if supplier substituted an item.",
            "unit_cost":             "Cost per unit (USD).",
        },
        "sample_questions": [
            "What is Sysco's on-time delivery rate for 2024?",
            "Which supplier has the lowest fill rate?",
            "Show me substitution frequency by supplier.",
            "What is the average lead time for each supplier?",
        ],
    },

    "orders": {
        "description": (
            "E-commerce order transactions. Each row is one customer order with "
            "category, channel (Web / Mobile App / In-Store), customer segment, "
            "order value, status (Completed / Refunded / Cancelled), and refund amount. "
            "Use for revenue, AOV, refund rate, and channel performance queries."
        ),
        "columns": {
            "order_id":          "Unique order ID (EC-XXXX).",
            "order_date":        "Order date (YYYY-MM-DD).",
            "category":          "Product category: Electronics, Apparel, Home & Kitchen, Beauty, Sports, Books, Toys.",
            "channel":           "Sales channel: Web | Mobile App | In-Store.",
            "customer_segment":  "Customer type: Student | Faculty | Staff | Alumni | Public.",
            "order_value":       "Order total (USD).",
            "status":            "Order status: Completed | Refunded | Cancelled.",
            "refund_amount":     "Refund issued (USD). 0 if not refunded.",
            "units":             "Number of units in the order.",
        },
        "sample_questions": [
            "What is the average order value by category?",
            "Which channel has the highest refund rate?",
            "Show me monthly revenue trend from e-commerce orders.",
            "Which customer segment spends the most on average?",
        ],
    },

    "subscriptions": {
        "description": (
            "SaaS subscription event log. Each row is a subscription lifecycle event "
            "(new, upgrade, downgrade, churn, reactivation) for a customer. "
            "Includes MRR, plan tier (Starter/Growth/Pro/Enterprise), cohort month, "
            "customer segment, and trial conversion flag. "
            "Use for churn analysis, MRR tracking, cohort retention, and revenue forecasting."
        ),
        "columns": {
            "subscription_id":  "Unique subscription ID (SUB-XXXXX).",
            "event_date":       "Date of the subscription event (YYYY-MM-DD).",
            "cohort_month":     "Month the customer first subscribed (YYYY-MM).",
            "plan":             "Plan tier: Starter ($29) | Growth ($79) | Pro ($149) | Enterprise ($399).",
            "event_type":       "Event: new | upgrade | downgrade | churn | reactivation.",
            "mrr":              "Monthly Recurring Revenue at time of event (USD). 0 if churned.",
            "customer_segment": "Business segment: SMB | Mid-Market | Enterprise | Startup.",
            "trial_converted":  "True if customer converted from a free trial.",
        },
        "sample_questions": [
            "What is the churn rate by plan tier?",
            "Show me MRR growth month over month.",
            "Which customer segment has the highest upgrade rate?",
            "How many customers were reactivated in Q4?",
        ],
    },
}


def get_schema_text(table_name: str) -> str:
    """Return a formatted schema description for a given table."""
    schema = SCHEMA_REGISTRY.get(table_name)
    if not schema:
        return f"Table '{table_name}' not found in registry."

    lines = [
        f"TABLE: {table_name}",
        f"DESCRIPTION: {schema['description']}",
        "COLUMNS:",
    ]
    for col, desc in schema["columns"].items():
        lines.append(f"  - {col}: {desc}")
    lines.append("EXAMPLE QUESTIONS:")
    for q in schema["sample_questions"]:
        lines.append(f"  • {q}")
    return "\n".join(lines)


def get_all_schemas_text() -> str:
    """Return all table schemas concatenated (used for embedding)."""
    return "\n\n" + "="*60 + "\n\n".join(
        get_schema_text(t) for t in SCHEMA_REGISTRY
    )


def get_table_list() -> list[str]:
    return list(SCHEMA_REGISTRY.keys())
