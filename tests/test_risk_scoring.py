from predict_churn import ChurnPredictor


def _predictor() -> ChurnPredictor:
    # Bypass runtime-only initialization for pure risk scoring tests.
    return ChurnPredictor.__new__(ChurnPredictor)


def test_calculate_churn_risk_high_risk_case():
    predictor = _predictor()
    score = predictor.calculate_churn_risk(
        {
            "subscription_status": "past_due",
            "cancel_at_period_end": True,
            "failed_charges": 2,
            "total_charges": 4,
            "days_until_renewal": 3,
            "default_source": False,
            "customer_age_days": 10,
        }
    )
    assert score >= 80


def test_calculate_churn_risk_caps_at_100():
    predictor = _predictor()
    score = predictor.calculate_churn_risk(
        {
            "subscription_status": "canceled",
            "cancel_at_period_end": True,
            "failed_charges": 10,
            "total_charges": 10,
            "days_until_renewal": -5,
            "default_source": False,
            "customer_age_days": 1,
        }
    )
    assert score == 100
