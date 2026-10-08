# Investment Calculator

A Streamlit app with five calculation modes, compound growth, monthly or annual deposits, beginning/end timing, inflation-adjusted balances, interactive charts, and CSV schedules.

## Run locally

Install Python 3.10 or newer. Extract this folder, open a terminal in it, then run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit opens the app in your browser. If it does not open automatically, use the Local URL shown in the terminal, usually http://localhost:8501. Keep that terminal running.

On Windows, `py` can replace `python` if needed. Save the supplied Python code as `app.py`, not `app.py.txt`.

## Deploy to Streamlit Community Cloud

Add `app.py` and `requirements.txt` to your own GitHub repository. In Streamlit Community Cloud, create an app, choose that repository and `app.py` as the entry point, then deploy. This download is runnable source code; no live site has been deployed.

## Calculation conventions

The annual return is nominal. For n compounds per year, monthly growth is `(1 + rate / n) ** (n / 12)`, with rate written as a decimal. Continuous compounding uses `exp(rate / 12)`. Between compounding dates, the model uses equivalent fractional-period growth rather than waiting for an interest-posting date.

All horizons are whole months, from 0 through 1,200. Annual deposits at the beginning occur in months 1, 13, 25, etc.; annual deposits at the end occur in months 12, 24, 36, etc. No recurring deposits occur at a zero-month horizon. Row 0 of each schedule records the starting amount.

The contribution and starting-amount solvers return the minimum nonnegative amount to reach at least the goal. The displayed required amount is rounded up to the next cent; schedules use the exact unrounded solution. Return solving supports -99.9% through 1,000%. Length solving scans month-end balances and returns the first date at or above the goal, within 100 years. This scan also handles declining balances and annual deposit cycles.

Inflation changes buying-power results only. Targets are nominal balances. Calculations assume constant rates and deposits; taxes, fees, withdrawals, and volatility are outside this model.

## Verify

Core tests use Python's standard library:

```bash
python -m unittest discover -s tests -v
```

The interface smoke test additionally uses Streamlit's built-in AppTest framework after installing requirements.
