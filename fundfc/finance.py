
import numpy as np
import pandas as pd

try:
    from scipy.optimize import minimize
except ImportError:
    minimize = None


# -------------------------------------------------
# Illustrative asset-class assumptions
# -------------------------------------------------

NAMES = np.array([
    "Capital preservation",
    "Income / diversified bonds",
    "Long-term growth"
])

MU = np.array([
    0.035,
    0.045,
    0.075
])

VOL = np.array([
    0.025,
    0.065,
    0.160
])

CORR = np.array([
    [1.00, 0.20, 0.00],
    [0.20, 1.00, 0.15],
    [0.00, 0.15, 1.00]
])

COV = np.outer(VOL, VOL) * CORR


# -------------------------------------------------
# Model portfolios
# -------------------------------------------------

PRESETS = {
    "Capital preservation": np.array([0.70, 0.25, 0.05]),
    "Balanced": np.array([0.30, 0.40, 0.30]),
    "Long-term growth": np.array([0.10, 0.30, 0.60])
}


# -------------------------------------------------
# Portfolio statistics
# -------------------------------------------------

def portfolio_stats(weights):
    weights = np.asarray(weights, dtype=float)

    expected_return = float(weights @ MU)

    volatility = float(
        np.sqrt(weights @ COV @ weights)
    )

    return expected_return, volatility


# -------------------------------------------------
# Risk-constrained portfolio optimizer
# -------------------------------------------------

def optimize_portfolio(max_volatility=0.12):

    if minimize is None:
        raise ValueError(
            "scipy is required for portfolio optimization."
        )

    n = len(MU)

    def objective(weights):
        return -(weights @ MU)

    def volatility_constraint(weights):
        _, volatility = portfolio_stats(weights)
        return max_volatility - volatility

    constraints = [
        {
            "type": "eq",
            "fun": lambda w: np.sum(w) - 1.0
        },
        {
            "type": "ineq",
            "fun": volatility_constraint
        }
    ]

    bounds = [(0.0, 1.0)] * n

    initial = np.ones(n) / n

    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints
    )

    if not result.success:
        raise ValueError(
            "Unable to find a portfolio satisfying the volatility constraint."
        )

    weights = np.asarray(result.x, dtype=float)

    weights = np.clip(weights, 0, 1)
    weights = weights / weights.sum()

    return weights


# -------------------------------------------------
# Monte Carlo sustainability model
# -------------------------------------------------

def monte_carlo(
    initial_balance=10000,
    monthly_contribution=100,
    annual_withdrawal=1500,
    withdrawal_start_year=6,
    withdrawal_end_year=10,
    years=30,
    fee_rate=0.003,
    inflation_rate=0.025,
    simulations=10000,
    weights=None,
    seed=42
):

    if weights is None:
        weights = PRESETS["Balanced"]

    weights = np.asarray(weights, dtype=float)

    if years < 1:
        raise ValueError("years must be at least 1.")

    if simulations < 1:
        raise ValueError("simulations must be at least 1.")

    if withdrawal_end_year < withdrawal_start_year:
        raise ValueError(
            "Withdrawal end year cannot be before withdrawal start year."
        )

    expected_return, volatility = portfolio_stats(weights)

    months = int(years * 12)

    rng = np.random.default_rng(seed)

    # Convert annual assumptions to monthly log-return parameters.
    mu_monthly = (
        np.log1p(expected_return) / 12
        - 0.5 * volatility ** 2 / 12
    )

    sigma_monthly = volatility / np.sqrt(12)

    shocks = rng.normal(
        mu_monthly,
        sigma_monthly,
        size=(int(simulations), months)
    )

    returns = np.exp(shocks) - 1

    # Approximate annual fee as a monthly deduction.
    returns = returns - fee_rate / 12

    balances = np.full(
        int(simulations),
        float(initial_balance)
    )

    depleted = np.zeros(
        int(simulations),
        dtype=bool
    )

    # Record yearly balances.
    yearly = np.zeros(
        (int(simulations), int(years) + 1)
    )

    yearly[:, 0] = balances

    for month in range(months):

        balances = np.maximum(
            0,
            balances * (1 + returns[:, month])
        )

        balances += float(monthly_contribution)

        year_number = month // 12 + 1

        if withdrawal_start_year <= year_number <= withdrawal_end_year:

            # Inflate withdrawals from the first withdrawal year onward.
            withdrawal_year = year_number - withdrawal_start_year

            annual_amount = (
                float(annual_withdrawal)
                * (1 + inflation_rate) ** withdrawal_year
            )

            monthly_withdrawal = annual_amount / 12

            balances -= monthly_withdrawal

            balances = np.maximum(
                balances,
                0
            )

        depleted |= balances <= 0

        if (month + 1) % 12 == 0:

            year_index = (month + 1) // 12

            yearly[:, year_index] = balances


    ending = balances.copy()

    median_ending = float(
        np.median(ending)
    )

    p10_ending = float(
        np.percentile(ending, 10)
    )

    p90_ending = float(
        np.percentile(ending, 90)
    )

    depletion_probability = float(
        depleted.mean()
    )

    real_discount = (
        (1 + inflation_rate) ** years
    )

    median_real_ending = (
        median_ending / real_discount
        if real_discount > 0
        else median_ending
    )

    summary = {
        "median_ending": median_ending,
        "p10_ending": p10_ending,
        "p90_ending": p90_ending,
        "depletion_probability": depletion_probability,
        "median_real_ending": median_real_ending,
        "expected_return": expected_return,
        "volatility": volatility
    }


    paths = pd.DataFrame({
        "Year": np.arange(years + 1),
        "P10": np.percentile(yearly, 10, axis=0),
        "Median": np.percentile(yearly, 50, axis=0),
        "P90": np.percentile(yearly, 90, axis=0)
    })

    return summary, paths, ending


# -------------------------------------------------
# Compare the three model portfolios
# -------------------------------------------------

def compare_presets(
    initial_balance=10000,
    monthly_contribution=100,
    annual_withdrawal=1500,
    withdrawal_start_year=6,
    withdrawal_end_year=10,
    years=30,
    fee_rate=0.003,
    inflation_rate=0.025,
    simulations=10000
):

    rows = []

    for name, weights in PRESETS.items():

        expected_return, volatility = portfolio_stats(weights)

        summary, _, _ = monte_carlo(
            initial_balance=initial_balance,
            monthly_contribution=monthly_contribution,
            annual_withdrawal=annual_withdrawal,
            withdrawal_start_year=withdrawal_start_year,
            withdrawal_end_year=withdrawal_end_year,
            years=years,
            fee_rate=fee_rate,
            inflation_rate=inflation_rate,
            simulations=simulations,
            weights=weights,
            seed=42
        )

        rows.append({
            "Portfolio": name,
            "Expected annual return*": expected_return,
            "Annual volatility*": volatility,
            "Median ending balance": summary["median_ending"],
            "10th percentile ending": summary["p10_ending"],
            "90th percentile ending": summary["p90_ending"],
            "Depletion probability": summary["depletion_probability"]
        })

    return pd.DataFrame(rows)
