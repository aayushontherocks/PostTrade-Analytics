import uuid
from datetime import datetime, timedelta
import random

def generate_smart_trades(num_trades):
    conn = get_db_connection()
    cur = conn.cursor()

    for i in range(num_trades):
        # Unique trade_id using UUID (12-char suffix for readability)
        trade_id = f"TRD{uuid.uuid4().hex[:12].upper()}"

        symbol = random.choice(["AAPL","MSFT","GOOG","AMZN","TSLA","NVDA","META","NFLX","ADBE","ORCL"])
        quantity = random.randint(1, 5000)
        price = round(random.uniform(5, 3000), 2)
        status = random.choices(["SETTLED", "FAILED", "PENDING"], weights=[0.75, 0.15, 0.10])[0]
        failure_reason = None
        if status == "FAILED":
            failure_reason = random.choice(["INSUFFICIENT_FUNDS", "BAD_SETTLEMENT", "MISSING_DOCS", "COMPLIANCE_HOLD"])

        trade_date = datetime.now() - timedelta(days=random.randint(0, 30))
        settlement_date = trade_date + timedelta(days=random.randint(1, 3))
        actual_settlement_date = settlement_date if status == "SETTLED" else None
        value_at_risk = round(quantity * price * random.uniform(0.001, 0.01), 4)
        is_margin_trade = random.random() < 0.25

        cur.execute("""
            INSERT INTO trades (
                trade_id, symbol, quantity, price, trade_currency,
                trade_date, settlement_date, actual_settlement_date,
                buyer_id, seller_id, status, failure_reason,
                value_at_risk, is_margin_trade
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            trade_id, symbol, quantity, price, 'USD',
            trade_date, settlement_date, actual_settlement_date,
            f"BUY_{random.randint(10000, 99999)}",
            f"SELL_{random.randint(10000, 99999)}",
            status, failure_reason,
            value_at_risk, is_margin_trade
        ))

        if i % 100 == 0:
            print(f"✅ Inserted {i} trades...")

    conn.commit()
    cur.close()
    conn.close()
    print("🎉 Smart trade data generated with realistic failures!")
