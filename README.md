# SaaS Churn Predictor

Analyze your Stripe data to predict which customers are at risk of churning. Get actionable insights to reduce churn and improve retention.

## Features

- 📊 Analyze Stripe subscription data
- 🔮 Predict churn risk using ML models
- 📈 Identify churn patterns and trends
- 💡 Get actionable recommendations
- 📧 Export risk reports
- 🔔 Set up alerts for high-risk customers

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file:

```env
STRIPE_SECRET_KEY=sk_live_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here
```

## Usage

### Analyze Churn Risk

```bash
python predict_churn.py
```

### Get Customer Risk Scores

```bash
python predict_churn.py --customer-id cus_xxxxx
```

### Export Risk Report

```bash
python predict_churn.py --export report.csv
```

### Set Up Monitoring

```bash
python monitor.py --interval 24  # Check daily
```

## Churn Risk Factors

The predictor analyzes:
- Payment failures
- Subscription downgrades
- Reduced usage patterns
- Support ticket frequency
- Payment method changes
- Billing cycle changes

## Risk Levels

- **Low (0-30%)**: Healthy customer
- **Medium (30-60%)**: Monitor closely
- **High (60-80%)**: At risk - take action
- **Critical (80-100%)**: Likely to churn

## License

MIT License


