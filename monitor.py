#!/usr/bin/env python3
"""
Churn Monitor - Continuously monitor churn risk
"""

import time
import schedule
from predict_churn import ChurnPredictor
import sys

def run_churn_check():
    """Run churn prediction check"""
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running churn check...")
    try:
        predictor = ChurnPredictor()
        customers = predictor.fetch_customer_data()
        results_df = predictor.predict_churn(customers)
        
        # Alert on critical customers
        critical = results_df[results_df['Risk Score'] >= 80]
        if not critical.empty:
            print(f"🚨 ALERT: {len(critical)} critical risk customers found!")
            for _, row in critical.iterrows():
                print(f"   - {row['Email']}: {row['Risk Score']:.1f}% risk")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Churn Monitor')
    parser.add_argument('--interval', type=int, default=24, help='Check interval in hours')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting churn monitor (checking every {args.interval} hours)")
    
    schedule.every(args.interval).hours.do(run_churn_check)
    
    # Initial run
    run_churn_check()
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()


