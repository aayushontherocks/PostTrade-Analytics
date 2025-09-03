from api import get_db_connection

def optimize_db():
    conn = get_db_connection()
    cur = conn.cursor()

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)",
        "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_trades_trade_date ON trades(trade_date)",
        "CREATE INDEX IF NOT EXISTS idx_trades_value ON trades((quantity * price))",
        "CREATE INDEX IF NOT EXISTS idx_trades_buyer ON trades(buyer_id)",
        "CREATE INDEX IF NOT EXISTS idx_trades_seller ON trades(seller_id)"
    ]

    for sql in indexes:
        cur.execute(sql)
        print(f"✅ {sql}")

    conn.commit()
    cur.close()
    conn.close()
    print("⚡ Indexing complete.")
