#!/usr/bin/env python3
"""
SaaS Churn Predictor
Analyzes Stripe data to predict customer churn risk
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from dotenv import load_dotenv

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    print("⚠️  stripe package not installed. Install with: pip install stripe")

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️  scikit-learn not installed. Using simple heuristic model.")

load_dotenv()

class ChurnPredictor:
    def __init__(self):
        self.stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if not self.stripe_key:
            raise ValueError("STRIPE_SECRET_KEY not found in environment")
        
        if STRIPE_AVAILABLE:
            stripe.api_key = self.stripe_key
        else:
            raise ImportError("stripe package required")
        
        self.model = None
        self.scaler = None
    
    def fetch_customer_data(self, customer_id: Optional[str] = None) -> List[Dict]:
        """Fetch customer data from Stripe"""
        customers = []
        
        if customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                customers.append(self._extract_customer_features(customer))
            except Exception as e:
                print(f"❌ Error fetching customer {customer_id}: {e}")
                return []
        else:
            # Fetch all customers
            try:
                for customer in stripe.Customer.list(limit=100):
                    customers.append(self._extract_customer_features(customer))
            except Exception as e:
                print(f"❌ Error fetching customers: {e}")
                return []
        
        return customers
    
    def _extract_customer_features(self, customer) -> Dict:
        """Extract features from Stripe customer object"""
        features = {
            'customer_id': customer.id,
            'email': customer.email,
            'created': customer.created,
            'currency': customer.currency,
            'default_source': customer.default_source is not None,
        }
        
        # Get subscription data
        subscriptions = stripe.Subscription.list(customer=customer.id, limit=10)
        if subscriptions.data:
            sub = subscriptions.data[0]
            features.update({
                'subscription_status': sub.status,
                'subscription_created': sub.created,
                'current_period_end': sub.current_period_end,
                'cancel_at_period_end': sub.cancel_at_period_end,
                'trial_end': sub.trial_end or 0,
                'days_until_renewal': (sub.current_period_end - datetime.now().timestamp()) / 86400,
            })
            
            # Get payment method info
            if customer.default_source:
                try:
                    payment_method = stripe.PaymentMethod.retrieve(customer.default_source)
                    features['payment_method_type'] = payment_method.type if hasattr(payment_method, 'type') else 'unknown'
                except:
                    features['payment_method_type'] = 'unknown'
        else:
            features.update({
                'subscription_status': 'none',
                'subscription_created': 0,
                'current_period_end': 0,
                'cancel_at_period_end': False,
                'trial_end': 0,
                'days_until_renewal': 0,
                'payment_method_type': 'unknown',
            })
        
        # Get payment history
        charges = stripe.Charge.list(customer=customer.id, limit=10)
        failed_charges = sum(1 for c in charges.data if c.status == 'failed')
        features['failed_charges'] = failed_charges
        features['total_charges'] = len(charges.data)
        
        # Calculate customer age
        customer_age_days = (datetime.now().timestamp() - customer.created) / 86400
        features['customer_age_days'] = customer_age_days
        
        return features
    
    def calculate_churn_risk(self, customer_data: Dict) -> float:
        """Calculate churn risk score (0-100)"""
        risk_score = 0.0
        
        # Subscription status
        status = customer_data.get('subscription_status', 'none')
        if status == 'canceled':
            risk_score += 100
        elif status == 'past_due':
            risk_score += 80
        elif status == 'unpaid':
            risk_score += 90
        elif status == 'trialing':
            risk_score += 20
        elif status == 'none':
            risk_score += 50
        
        # Cancel at period end
        if customer_data.get('cancel_at_period_end', False):
            risk_score += 70
        
        # Payment failures
        failed_charges = customer_data.get('failed_charges', 0)
        total_charges = customer_data.get('total_charges', 1)
        if total_charges > 0:
            failure_rate = failed_charges / total_charges
            risk_score += failure_rate * 40
        
        # Days until renewal (very soon = risk)
        days_until_renewal = customer_data.get('days_until_renewal', 0)
        if 0 < days_until_renewal < 7:
            risk_score += 30
        elif days_until_renewal < 0:
            risk_score += 50
        
        # No payment method
        if not customer_data.get('default_source', False):
            risk_score += 30
        
        # New customer (less than 30 days)
        customer_age = customer_data.get('customer_age_days', 0)
        if customer_age < 30:
            risk_score += 15
        
        return min(100, risk_score)
    
    def predict_churn(self, customers: List[Dict]) -> pd.DataFrame:
        """Predict churn for all customers"""
        results = []
        
        for customer in customers:
            risk_score = self.calculate_churn_risk(customer)
            
            # Categorize risk
            if risk_score < 30:
                risk_level = 'Low'
            elif risk_score < 60:
                risk_level = 'Medium'
            elif risk_score < 80:
                risk_level = 'High'
            else:
                risk_level = 'Critical'
            
            results.append({
                'Customer ID': customer['customer_id'],
                'Email': customer.get('email', 'N/A'),
                'Status': customer.get('subscription_status', 'N/A'),
                'Risk Score': round(risk_score, 2),
                'Risk Level': risk_level,
                'Failed Charges': customer.get('failed_charges', 0),
                'Days Until Renewal': round(customer.get('days_until_renewal', 0), 1),
                'Customer Age (days)': round(customer.get('customer_age_days', 0), 1),
            })
        
        df = pd.DataFrame(results)
        df = df.sort_values('Risk Score', ascending=False)
        return df
    
    def get_recommendations(self, customer_data: Dict, risk_score: float) -> List[str]:
        """Get actionable recommendations based on risk"""
        recommendations = []
        
        if risk_score > 80:
            recommendations.append("🚨 CRITICAL: Immediate intervention required")
            recommendations.append("   - Reach out personally to customer")
            recommendations.append("   - Offer discount or extended trial")
            recommendations.append("   - Review payment method issues")
        
        if customer_data.get('failed_charges', 0) > 0:
            recommendations.append("💳 Payment failures detected - update payment method")
        
        if customer_data.get('cancel_at_period_end', False):
            recommendations.append("⏰ Customer scheduled cancellation - offer retention deal")
        
        if not customer_data.get('default_source', False):
            recommendations.append("💳 No payment method on file - request update")
        
        if customer_data.get('days_until_renewal', 0) < 7 and customer_data.get('days_until_renewal', 0) > 0:
            recommendations.append("📅 Renewal approaching - send reminder and offer")
        
        if customer_data.get('customer_age_days', 0) < 30:
            recommendations.append("🆕 New customer - ensure onboarding is complete")
        
        if not recommendations:
            recommendations.append("✅ Customer appears healthy - maintain engagement")
        
        return recommendations


def main():
    parser = argparse.ArgumentParser(description='SaaS Churn Predictor')
    parser.add_argument('--customer-id', help='Analyze specific customer')
    parser.add_argument('--export', help='Export results to CSV file')
    parser.add_argument('--limit', type=int, default=100, help='Limit number of customers to analyze')
    
    args = parser.parse_args()
    
    try:
        predictor = ChurnPredictor()
        
        print("📊 Fetching customer data from Stripe...")
        customers = predictor.fetch_customer_data(args.customer_id)
        
        if not customers:
            print("❌ No customers found")
            return
        
        print(f"✅ Found {len(customers)} customer(s)")
        print("\n🔮 Predicting churn risk...")
        
        results_df = predictor.predict_churn(customers)
        
        # Display results
        print("\n" + "="*80)
        print("CHURN RISK ANALYSIS")
        print("="*80)
        print(results_df.to_string(index=False))
        
        # Show recommendations for high-risk customers
        high_risk = results_df[results_df['Risk Score'] >= 60]
        if not high_risk.empty:
            print("\n" + "="*80)
            print("HIGH RISK CUSTOMERS - RECOMMENDATIONS")
            print("="*80)
            
            for _, row in high_risk.iterrows():
                customer_id = row['Customer ID']
                customer_data = next((c for c in customers if c['customer_id'] == customer_id), None)
                if customer_data:
                    print(f"\n📧 {row['Email']} (Risk: {row['Risk Score']:.1f}%)")
                    recommendations = predictor.get_recommendations(customer_data, row['Risk Score'])
                    for rec in recommendations:
                        print(f"   {rec}")
        
        # Export if requested
        if args.export:
            results_df.to_csv(args.export, index=False)
            print(f"\n✅ Results exported to {args.export}")
        
        # Summary statistics
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total Customers: {len(customers)}")
        print(f"Low Risk (<30%): {len(results_df[results_df['Risk Score'] < 30])}")
        print(f"Medium Risk (30-60%): {len(results_df[(results_df['Risk Score'] >= 30) & (results_df['Risk Score'] < 60)])}")
        print(f"High Risk (60-80%): {len(results_df[(results_df['Risk Score'] >= 60) & (results_df['Risk Score'] < 80)])}")
        print(f"Critical Risk (80%+): {len(results_df[results_df['Risk Score'] >= 80])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()


