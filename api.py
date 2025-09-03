# api.py (IMPROVED VERSION)
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import psycopg2
from typing import List, Optional
import joblib
import pandas as pd
import os
from datetime import datetime

# Initialize FastAPI with better metadata
app = FastAPI(
    title="LSEG Trade API", 
    version="1.0",
    description="API for post-trade analysis and failure prediction",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Database connection with error handling
def get_db_connection():
    # try:
    #     conn = psycopg2.connect(
    #         host="localhost",       # ← FIX: Use localhost for external connection  
    #         port=5435,             # ← MUST match the external port in docker-compose (5435:5432)
    #         dbname="trading_db",
    #         user="trader",
    #         password="securepass123",
    #         connect_timeout=10
    #     )
    #     return conn
    # except psycopg2.Error as e:
    #     raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
    return psycopg2.connect(os.environ["postgresql://posttrade_db_user:oYkbHMIdiCz0T7y92ModYWGKzf872YMs@dpg-d2s9kj24d50c73dkaldg-a.oregon-postgres.render.com/posttrade_db"])

# Pydantic models with more fields
class Trade(BaseModel):
    trade_id: str
    symbol: str
    quantity: float
    price: float
    status: str
    value_at_risk: Optional[float] = None
    trade_date: Optional[datetime] = None
    failure_reason: Optional[str] = None

    class Config:
        orm_mode = True

class PredictionRequest(BaseModel):
    quantity: float
    price: float
    trade_hour: int
    is_sell_order: bool
    symbol: Optional[str] = None  # Added symbol for better predictions

class HealthCheck(BaseModel):
    status: str
    database: str
    model_loaded: bool
    timestamp: datetime

# Load ML model with better error handling
try:
    model_path = os.path.join(os.path.dirname(__file__), 'failure_predictor.pkl')
    model = joblib.load(model_path)
    MODEL_LOADED = True
except Exception as e:
    model = None
    MODEL_LOADED = False
    print(f"Model loading failed: {e}")

# Routes
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "LSEG Trade API Running - Visit /docs for API documentation"}

@app.get("/trades", response_model=List[Trade])
async def get_trades(
    limit: int = Query(100, ge=1, le=1000, description="Number of trades to return"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    status: Optional[str] = Query(None, description="Filter by status (e.g., FAILED, SETTLED)")
):
    """Get trades with optional filtering"""
    conn = get_db_connection()
    try:
        query = "SELECT trade_id, symbol, quantity, price, status, value_at_risk, trade_date, failure_reason FROM trades"
        conditions = []
        params = []
        
        if symbol:
            conditions.append("symbol = %s")
            params.append(symbol)
        if status:
            conditions.append("status = %s")
            params.append(status)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += f" ORDER BY trade_date DESC LIMIT {limit}"
        
        df = pd.read_sql(query, conn, params=params if params else None)
        return df.to_dict('records')
    finally:
        conn.close()

@app.get("/trades/{trade_id}", response_model=Trade)
async def get_trade(trade_id: str):
    """Get a specific trade by ID"""
    conn = get_db_connection()
    try:
        df = pd.read_sql(
            "SELECT trade_id, symbol, quantity, price, status, value_at_risk, trade_date, failure_reason FROM trades WHERE trade_id = %s",
            conn, 
            params=[trade_id]
        )
        if df.empty:
            raise HTTPException(status_code=404, detail="Trade not found")
        return df.iloc[0].to_dict()
    finally:
        conn.close()

@app.post("/predict-failure")
async def predict_failure(request: PredictionRequest):
    """Predict failure probability for a trade"""
    if not model:
        raise HTTPException(status_code=503, detail="Prediction model not available")
    
    try:
        # Prepare features - enhanced with symbol risk if provided
        features = [[
            request.quantity,
            abs(request.quantity),
            request.price,
            request.trade_hour,
            0,  # dummy day of week (could be improved)
            request.quantity * request.price,
            1 if request.is_sell_order else 0
        ]]
        
        probability = model.predict_proba(features)[0][1]
        return {
            "failure_probability": round(probability, 4),
            "risk_level": "HIGH" if probability > 0.7 else "MEDIUM" if probability > 0.3 else "LOW"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/stats/summary")
async def get_stats_summary():
    """Get summary statistics"""
    conn = get_db_connection()
    try:
        stats = pd.read_sql("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_trades,
                AVG(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failure_rate,
                SUM(value_at_risk) as total_value_at_risk,
                MAX(trade_date) as latest_trade_date
            FROM trades
        """, conn)
        return stats.iloc[0].to_dict()
    finally:
        conn.close()

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    conn = get_db_connection()
    try:
        # Test database connection
        pd.read_sql("SELECT 1", conn)
        db_status = "connected"
    except:
        db_status = "disconnected"
    finally:
        conn.close()
    
    return HealthCheck(
        status="healthy",
        database=db_status,
        model_loaded=MODEL_LOADED,
        timestamp=datetime.now()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
