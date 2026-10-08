"""Investment calculator. Run: streamlit run app.py"""
from dataclasses import dataclass, replace
import math

COMPOUNDING = {
    "Annually": 1, "Semiannually": 2, "Quarterly": 4,
    "Monthly": 12, "Weekly (52/year)": 52, "Daily (365/year)": 365,
    "Continuously": None,
}
MODES = ["Ending balance", "Contribution amount", "Return rate", "Starting amount", "Investment length"]
MAX_MONTHS = 1200


@dataclass(frozen=True)
class Plan:
    starting: float = 20000.0
    contribution: float = 1000.0
    months: int = 120
    rate: float = 6.0  # Nominal annual percentage, not an effective annual rate.
    compounding: str = "Annually"
    frequency: str = "Monthly"
    timing: str = "End"
    inflation: float = 0.0


def validate(p):
    for value in (p.starting, p.contribution, p.rate, p.inflation):
        if not math.isfinite(value):
            raise ValueError("Enter finite numbers in every field.")
    if p.starting < 0 or p.contribution < 0:
        raise ValueError("Starting amount and contributions must be nonnegative.")
    if not isinstance(p.months, int) or not 0 <= p.months <= MAX_MONTHS:
        raise ValueError("Investment length must be 0 to 1,200 whole months.")
    if not -99.9 <= p.rate <= 1000:
        raise ValueError("Annual return must be between -99.9% and 1,000%.")
    if not 0 <= p.inflation <= 30:
        raise ValueError("Inflation must be between 0% and 30%.")
    if p.compounding not in COMPOUNDING or p.frequency not in ("Monthly", "Annually") or p.timing not in ("Beginning", "End"):
        raise ValueError("Choose a supported compounding, contribution frequency, and timing.")


def monthly_log_growth(p):
    n = COMPOUNDING[p.compounding]
    return p.rate / 100 / 12 if n is None else n * math.log1p(p.rate / 100 / n) / 12


def deposit_due(p, month):
    return p.frequency == "Monthly" or (month - (1 if p.timing == "Beginning" else 0)) % 12 == 0


def factors(p):
    """Linear FV coefficients for starting principal and recurring deposits."""
    validate(p)
    log_q = monthly_log_growth(p)
    growth = math.exp(log_q * p.months)
    annuity = math.fsum(
        math.exp(log_q * (p.months - m + (p.timing == "Beginning")))
        for m in range(1, p.months + 1) if deposit_due(p, m)
    )
    return growth, annuity


def future_value(p):
    growth, annuity = factors(p)
    result = p.starting * growth + p.contribution * annuity
    if not math.isfinite(result):
        raise ValueError("The projection exceeds the supported numeric range. Reduce the rate or horizon.")
    return result


def iter_schedule(p):
    validate(p)
    monthly_return = math.expm1(monthly_log_growth(p))
    balance, invested = p.starting, p.starting
    yield {"Month": 0, "Year": 0.0, "Deposit": p.starting, "Interest": 0.0,
             "Ending balance": balance, "Total invested": invested,
             "Cumulative gain": 0.0, "Balance in today's dollars": balance}
    for month in range(1, p.months + 1):
        deposit = p.contribution if deposit_due(p, month) else 0.0
        if p.timing == "Beginning":
            balance += deposit
        interest = balance * monthly_return
        balance += interest
        if p.timing == "End":
            balance += deposit
        invested += deposit
        if not math.isfinite(balance):
            raise ValueError("The projection exceeds the supported numeric range.")
        yield {"Month": month, "Year": month / 12, "Deposit": deposit,
                     "Interest": interest, "Ending balance": balance,
                     "Total invested": invested, "Cumulative gain": balance - invested,
                     "Balance in today's dollars": balance / (1 + p.inflation / 100) ** (month / 12)}


def schedule(p):
    return list(iter_schedule(p))


def solve(p, mode, target):
    validate(p)
    if not math.isfinite(target) or target < 0:
        raise ValueError("Target balance must be a finite, nonnegative amount.")
    if mode == "Ending balance":
        return p, ""
    if mode in ("Contribution amount", "Starting amount"):
        growth, annuity = factors(p)
        if mode == "Contribution amount":
            existing = p.starting * growth
            if existing >= target:
                return replace(p, contribution=0.0), "Your starting investment already reaches this target; no additional contributions are needed."
            if annuity == 0:
                raise ValueError("No contribution dates occur in this horizon. Increase the investment length.")
            return replace(p, contribution=(target - existing) / annuity), ""
        existing = p.contribution * annuity
        if existing >= target:
            return replace(p, starting=0.0), "Your planned contributions already reach this target; no starting investment is needed."
        return replace(p, starting=(target - existing) / growth), ""
    if mode == "Return rate":
        if p.months == 0 or (p.starting == 0 and (p.contribution == 0 or factors(p)[1] == 0)):
            raise ValueError("A return rate cannot be determined without invested money and time.")
        def rate_balance(rate):
            try:
                return future_value(replace(p, rate=rate))
            except OverflowError:
                # A trial rate can exceed the numeric range even when the solution does not.
                return math.inf

        low, high = -99.9, 1000.0
        low_fv, high_fv = rate_balance(low), rate_balance(high)
        if math.isclose(low_fv, high_fv, rel_tol=1e-12, abs_tol=1e-8):
            raise ValueError("The balance is independent of return for these deposit dates; there is no unique rate.")
        if not low_fv <= target <= high_fv:
            raise ValueError("No return rate between -99.9% and 1,000% reaches this target with these inputs.")
        for _ in range(100):
            midpoint = (low + high) / 2
            if rate_balance(midpoint) < target:
                low = midpoint
            else:
                high = midpoint
        return replace(p, rate=(low + high) / 2), ""
    if mode == "Investment length":
        # Scan all reporting dates: negative rates and annual deposits can be nonmonotone.
        for row in iter_schedule(replace(p, months=MAX_MONTHS)):
            if row["Ending balance"] >= target:
                return replace(p, months=row["Month"]), "First month-end reporting date at or above the target. Month 0 is the starting investment before any recurring deposits."
        raise ValueError("The target is not reached at any month-end within 100 years.")
    raise ValueError("Choose a supported calculation mode.")


def main():
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    st.set_page_config(page_title="Investment Calculator", page_icon="📈", layout="wide")
    st.title("Investment Calculator")
    st.caption("Explore compound growth, recurring deposits, and the path to your goal.")

    with st.sidebar:
        st.header("Your investment plan")
        mode = st.selectbox("Calculate", MODES)
        target = st.number_input("Target balance ($)", 0.0, 1e12, 200000.0, 1000.0, format="%.2f", disabled=mode == "Ending balance")
        starting = st.number_input("Starting amount ($)", 0.0, 1e12, 20000.0, 1000.0, format="%.2f", disabled=mode == "Starting amount")
        a, b = st.columns(2)
        years = a.number_input("Years", 0, 100, 10, disabled=mode == "Investment length")
        months = b.number_input("Extra months", 0, 11, 0, disabled=mode == "Investment length")
        rate = st.number_input("Annual return (%)", -99.9, 1000.0, 6.0, 0.1, format="%.4f", disabled=mode == "Return rate")
        compounding = st.selectbox("Compound", list(COMPOUNDING))
        contribution = st.number_input("Additional contribution ($)", 0.0, 1e12, 1000.0, 50.0, format="%.2f", disabled=mode == "Contribution amount")
        frequency = st.selectbox("Contribution frequency", ["Monthly", "Annually"])
        timing = st.radio("Contribute at the", ["Beginning", "End"], index=1, horizontal=True)
        inflation = st.number_input("Annual inflation (%)", 0.0, 30.0, 0.0, 0.1)
        st.caption("Results update when you change an input. Disabled fields are calculated for you.")

    try:
        p = Plan(starting, contribution, years * 12 + months, rate, compounding, frequency, timing, inflation)
        p, note = solve(p, mode, target)
        df = pd.DataFrame(schedule(p))
    except (ValueError, OverflowError) as exc:
        st.error(str(exc) if isinstance(exc, ValueError) else "The calculation exceeds the numeric range. Reduce the rate or investment length.")
        return

    money = lambda value: f"${value:,.2f}"
    if mode == "Contribution amount":
        rounded = math.ceil(p.contribution * 100) / 100
        st.success(f"Required {p.frequency.lower()} contribution: {money(rounded)} (rounded up to the next cent).")
    elif mode == "Starting amount":
        rounded = math.ceil(p.starting * 100) / 100
        st.success(f"Required starting amount: {money(rounded)} (rounded up to the next cent).")
    elif mode == "Return rate":
        st.success(f"Required nominal annual return: {p.rate:.6f}%")
    elif mode == "Investment length":
        st.success(f"Time to target: {p.months // 12} years and {p.months % 12} months")
    if note:
        st.info(note)
    if mode in ("Contribution amount", "Starting amount"):
        st.caption("The charts and schedule use the unrounded solution; the amount above is rounded up for practical deposits.")

    end = df.iloc[-1]
    metrics = st.columns(4)
    metrics[0].metric("Ending balance", money(end["Ending balance"]))
    metrics[1].metric("Starting investment", money(p.starting))
    metrics[2].metric("Additional contributions", money(end["Total invested"] - p.starting))
    metrics[3].metric("Investment gain / loss", money(end["Cumulative gain"]))
    if inflation > 0:
        buying_power = money(end["Balance in today's dollars"])
        st.info(f"At {inflation:g}% annual inflation, the ending balance has buying power of {buying_power} in today's dollars.")

    growth_tab, breakdown_tab, schedule_tab, assumptions_tab = st.tabs(["Growth chart", "Balance breakdown", "Accumulation schedule", "How it works"])
    with growth_tab:
        fig = go.Figure()
        for name, dash, color in [("Ending balance", "solid", "#2563eb"), ("Total invested", "dash", "#64748b")]:
            fig.add_trace(go.Scatter(x=df["Year"], y=df[name], name=name, mode="lines", line=dict(dash=dash, color=color), hovertemplate="Year %{x:.2f}<br>$%{y:,.2f}<extra>%{fullData.name}</extra>"))
        if inflation > 0:
            fig.add_trace(go.Scatter(x=df["Year"], y=df["Balance in today's dollars"], name="Balance in today's dollars", mode="lines", line=dict(dash="dot", color="#7c3aed")))
        fig.update_layout(xaxis_title="Years", yaxis_title="Amount ($)", yaxis_tickprefix="$", yaxis_tickformat=",.0f", legend=dict(orientation="h", y=-0.25), margin=dict(t=20, b=70))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Compare the account balance with your total deposits. Exact monthly values are available in the schedule.")
    with breakdown_tab:
        labels = ["Starting investment", "Additional contributions", "Investment gain / loss"]
        values = [p.starting, end["Total invested"] - p.starting, end["Cumulative gain"]]
        if min(values) >= 0 and sum(values) > 0:
            fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55, sort=False, textinfo="label+percent", hovertemplate="%{label}<br>$%{value:,.2f}<extra></extra>"))
        else:
            fig = go.Figure(go.Bar(x=labels, y=values, text=[money(v) for v in values], textposition="auto"))
            fig.update_layout(yaxis_title="Amount ($)")
            st.caption("A bar chart shows losses or an all-zero balance without misleading pie slices.")
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame({"Component": labels + ["Ending balance"], "Amount": [money(v) for v in values] + [money(end["Ending balance"])]}))
    with schedule_tab:
        granularity = st.radio("Schedule detail", ["Yearly", "Monthly"], horizontal=True)
        if granularity == "Yearly":
            annual = df.copy()
            annual["Year"] = ((annual["Month"] + 11) // 12).astype(int)
            shown = annual.groupby("Year", as_index=False).agg({"Month": "last", "Deposit": "sum", "Interest": "sum", "Ending balance": "last", "Total invested": "last", "Cumulative gain": "last", "Balance in today's dollars": "last"})
        else:
            shown = df.drop(columns="Year")
        st.caption("Row 0 records the starting investment. Deposit totals exclude it in later rows. A final yearly row may cover fewer than 12 months.")
        st.dataframe(shown.style.format({c: "${:,.2f}" for c in shown.columns if c not in ("Month", "Year")}), use_container_width=True, hide_index=True)
        st.download_button("Download displayed schedule (CSV)", shown.to_csv(index=False).encode("utf-8"), "investment_schedule.csv", "text/csv")
        st.download_button("Download full monthly schedule (CSV)", df.to_csv(index=False).encode("utf-8"), "investment_monthly_schedule.csv", "text/csv")
    with assumptions_tab:
        st.markdown("""
        - **Return:** a constant nominal annual rate. Compounding determines the effective annual growth. Negative rates represent losses.
        - **Between compounding dates:** growth uses the equivalent monthly rate, so monthly deposits and reporting work with every compounding choice.
        - **Timing:** beginning-of-month deposits earn that month's return; end-of-month deposits begin earning next month. Annual beginning deposits occur in months 1, 13, 25, …; annual end deposits occur in months 12, 24, 36, ….
        - **Length:** whole months, up to 100 years. The length solver checks each month-end and returns the first balance at or above your target.
        - **Goal solvers:** contributions and starting amounts solve for at least the target, with a minimum of zero. The return solver supports -99.9% to 1,000% nominal annual return.
        - **Inflation:** reduces the displayed buying power; it does not change the account balance or nominal target.
        - **Precision:** calculations retain full precision. Displayed currency is rounded to cents; CSV files retain numeric precision.
        - **Scope:** fixed deposits and a fixed rate; taxes, fees, withdrawals, and market volatility are not modeled. These are hypothetical projections.
        """)
        n = COMPOUNDING[p.compounding]
        st.latex(r"q = e^{r/12}" if n is None else r"q = (1+r/n)^{n/12}")
        st.latex(r"B_m = (B_{m-1}+D_m)q\quad\text{(beginning deposits)}")
        st.latex(r"B_m = B_{m-1}q+D_m\quad\text{(end deposits)}")
        effective = math.expm1(monthly_log_growth(p) * 12) * 100
        st.write(f"Effective annual return for this plan: {effective:,.6f}%")
        st.caption("In the formulas, r is the annual rate as a decimal, n is compounds per year, and D is the deposit due in that month.")
        st.markdown("Feature inspiration: [Calculator.net Investment Calculator](https://www.calculator.net/investment-calculator.html). This app is independently implemented.")


if __name__ == "__main__":
    main()
