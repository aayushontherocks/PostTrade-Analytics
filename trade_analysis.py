# trade_analysis.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import psycopg2
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5435,
        dbname="trading_db",
        user="trader",
        password="securepass123"
    )

class TradeAnalyzer:
    def __init__(self):
        self.conn = get_db_connection()
        self.df = self.load_all_trades()
    
    def load_all_trades(self) -> pd.DataFrame:
        """Load all trades from database"""
        query = """
        SELECT * FROM trades 
        WHERE trade_date > CURRENT_DATE - INTERVAL '90 days'
        """
        return pd.read_sql(query, self.conn)
    
    def basic_stats(self) -> Dict[str, Any]:
        """Get basic statistics about trades"""
        stats = {
            'total_trades': len(self.df),
            'failed_trades': len(self.df[self.df['status'] == 'FAILED']),
            'settled_trades': len(self.df[self.df['status'] == 'SETTLED']),
            'total_value': self.df['value_at_risk'].sum(),
            'avg_trade_size': self.df['value_at_risk'].mean(),
            'date_range': {
                'start': self.df['trade_date'].min(),
                'end': self.df['trade_date'].max()
            }
        }
        stats['failure_rate'] = stats['failed_trades'] / stats['total_trades']
        return stats
    
    def failure_analysis_by_symbol(self) -> pd.DataFrame:
        """Analyze failure rates by symbol"""
        result = self.df.groupby('symbol').agg({
            'trade_id': 'count',
            'status': lambda x: (x == 'FAILED').sum(),
            'value_at_risk': ['sum', 'mean']
        }).round(2)
        
        result.columns = ['total_trades', 'failed_trades', 'total_var', 'avg_var']
        result['failure_rate'] = (result['failed_trades'] / result['total_trades']).round(3)
        result = result.sort_values('failure_rate', ascending=False)
        return result
    
    def time_based_analysis(self) -> pd.DataFrame:
        """Analyze patterns by time of day and day of week"""
        self.df['trade_hour'] = self.df['trade_date'].dt.hour
        self.df['trade_day'] = self.df['trade_date'].dt.day_name()
        self.df['trade_date_only'] = self.df['trade_date'].dt.date
        
        # Hourly analysis
        hourly = self.df.groupby('trade_hour').agg({
            'trade_id': 'count',
            'status': lambda x: (x == 'FAILED').sum()
        })
        hourly['failure_rate'] = (hourly['status'] / hourly['trade_id']).round(3)
        
        # Daily analysis
        daily = self.df.groupby('trade_day').agg({
            'trade_id': 'count', 
            'status': lambda x: (x == 'FAILED').sum()
        })
        daily['failure_rate'] = (daily['status'] / daily['trade_id']).round(3)
        
        return {
            'hourly': hourly,
            'daily': daily
        }
    
    def value_at_risk_analysis(self) -> Dict[str, Any]:
        """Analyze Value at Risk patterns"""
        # Risk categories
        var_bins = [0, 1000, 5000, 10000, 50000, float('inf')]
        var_labels = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
        
        self.df['risk_category'] = pd.cut(
            self.df['value_at_risk'], 
            bins=var_bins, 
            labels=var_labels
        )
        
        risk_analysis = self.df.groupby('risk_category').agg({
            'trade_id': 'count',
            'status': lambda x: (x == 'FAILED').sum(),
            'value_at_risk': 'sum'
        })
        risk_analysis['failure_rate'] = (risk_analysis['status'] / risk_analysis['trade_id']).round(3)
        
        return risk_analysis
    
    def settlement_delay_analysis(self) -> pd.DataFrame:
        """Analyze settlement delays"""
        # Calculate delay in days
        delayed_trades = self.df[self.df['actual_settlement_date'].notna()].copy()
        delayed_trades['delay_days'] = (
            delayed_trades['actual_settlement_date'] - delayed_trades['settlement_date']
        ).dt.days
        
        # Only consider positive delays (actual after expected)
        delayed_trades = delayed_trades[delayed_trades['delay_days'] > 0]
        
        delay_analysis = delayed_trades.groupby('symbol').agg({
            'delay_days': ['mean', 'max', 'count']
        }).round(1)
        
        delay_analysis.columns = ['avg_delay', 'max_delay', 'delayed_trades_count']
        return delay_analysis.sort_values('avg_delay', ascending=False)
    
    def correlation_analysis(self) -> pd.DataFrame:
        """Find correlations between trade attributes and failures"""
        # Prepare data for correlation
        corr_df = self.df.copy()
        corr_df['is_failed'] = (corr_df['status'] == 'FAILED').astype(int)
        corr_df['is_sell'] = (corr_df['quantity'] < 0).astype(int)
        corr_df['abs_quantity'] = corr_df['quantity'].abs()
        
        # Select numeric columns for correlation
        numeric_cols = ['quantity', 'price', 'value_at_risk', 'abs_quantity', 'is_failed', 'is_sell']
        correlation_matrix = corr_df[numeric_cols].corr()
        
        return correlation_matrix
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        print("=" * 60)
        print("📊 TRADE ANALYSIS REPORT")
        print("=" * 60)
        
        # Basic stats
        stats = self.basic_stats()
        print(f"\n📈 BASIC STATISTICS:")
        print(f"   Total Trades: {stats['total_trades']:,}")
        print(f"   Failed Trades: {stats['failed_trades']:,}")
        print(f"   Failure Rate: {stats['failure_rate']:.2%}")
        print(f"   Total Value at Risk: ${stats['total_value']:,.2f}")
        print(f"   Date Range: {stats['date_range']['start']} to {stats['date_range']['end']}")
        
        # Symbol analysis
        print(f"\n🔍 FAILURE ANALYSIS BY SYMBOL:")
        symbol_analysis = self.failure_analysis_by_symbol()
        print(symbol_analysis.head(10))
        
        # Risk analysis
        print(f"\n⚠️  VALUE AT RISK ANALYSIS:")
        risk_analysis = self.value_at_risk_analysis()
        print(risk_analysis)
        
        # Correlation analysis
        print(f"\n📈 CORRELATION ANALYSIS:")
        correlations = self.correlation_analysis()
        print(correlations['is_failed'].sort_values(ascending=False))
        
        print("\n" + "=" * 60)
    
    def plot_analysis(self):
        """Create visualization plots"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot 1: Failure rate by symbol
        symbol_analysis = self.failure_analysis_by_symbol()
        axes[0, 0].bar(symbol_analysis.index[:10], symbol_analysis['failure_rate'][:10])
        axes[0, 0].set_title('Top 10 Symbols by Failure Rate')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Plot 2: Failure rate by risk category
        risk_analysis = self.value_at_risk_analysis()
        axes[0, 1].bar(risk_analysis.index.astype(str), risk_analysis['failure_rate'])
        axes[0, 1].set_title('Failure Rate by Risk Category')
        
        # Plot 3: Hourly failure pattern
        time_analysis = self.time_based_analysis()
        axes[1, 0].plot(time_analysis['hourly'].index, time_analysis['hourly']['failure_rate'])
        axes[1, 0].set_title('Failure Rate by Hour of Day')
        axes[1, 0].set_xlabel('Hour')
        axes[1, 0].set_ylabel('Failure Rate')
        
        # Plot 4: Settlement delays
        delay_analysis = self.settlement_delay_analysis()
        if not delay_analysis.empty:
            axes[1, 1].bar(delay_analysis.index[:8], delay_analysis['avg_delay'][:8])
            axes[1, 1].set_title('Average Settlement Delay by Symbol')
            axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.show()

# Example usage
if __name__ == "__main__":
    print("Starting trade analysis...")
    analyzer = TradeAnalyzer()
    analyzer.generate_report()
    analyzer.plot_analysis()
    
    print("Analysis complete! ✅")