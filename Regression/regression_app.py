import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


# ----------------------------------
# Linear Regression Function
# ----------------------------------
def linear_regression(x, y):
    # Calculate the necessary sums
    n = len(x)

    if n != len(y):
        raise ValueError("x and y must have the same length.")

    if n < 2:
        raise ValueError("At least two data points are required.")

    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x[i] * y[i] for i in range(n))
    sum_x_squared = sum(xi**2 for xi in x)

    denominator = n * sum_x_squared - sum_x**2

    if denominator == 0:
        raise ValueError(
            "All x values are identical. Regression is undefined."
        )

    # Calculate the slope (b1)
    slope = (
        n * sum_xy - sum_x * sum_y
    ) / denominator

    # Calculate the y-intercept (b0)
    intercept = (sum_y - slope * sum_x) / n

    return slope, intercept


# ----------------------------------
# Read CSV File
# ----------------------------------
def read_file(uploaded_file):
    """Read a CSV file containing columns named x and y."""
    df = pd.read_csv(uploaded_file)

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    if not {"x", "y"}.issubset(df.columns):
        raise ValueError(
            "CSV must contain columns named 'x' and 'y'."
        )

    df = df[["x", "y"]].apply(
        pd.to_numeric, errors="coerce"
    ).dropna()

    if len(df) < 2:
        raise ValueError(
            "The file must contain at least two valid data points."
        )

    return df


# ----------------------------------
# Streamlit Page Configuration
# ----------------------------------
st.set_page_config(
    page_title="Simple Linear Regression",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Simple Linear Regression")
st.write(
    "Calculate a regression line using the "
    "slope and intercept formulas."
)

st.latex(r"\hat{y} = b_0 + b_1x")

st.markdown(
    "Upload a CSV file or enter your own data points below."
)


# ----------------------------------
# Input Data
# ----------------------------------
st.sidebar.header("Input Data")

input_method = st.sidebar.radio(
    "Choose your input method:",
    ["Enter data manually", "Upload CSV file"]
)

df = None

if input_method == "Enter data manually":
    default_x = "1, 2, 3, 4, 5"
    default_y = "2, 4, 5, 4, 6"

    x_input = st.sidebar.text_input(
        "Enter x values (comma-separated):",
        value=default_x
    )

    y_input = st.sidebar.text_input(
        "Enter y values (comma-separated):",
        value=default_y
    )

    try:
        x = [float(value.strip()) for value in x_input.split(",")]
        y = [float(value.strip()) for value in y_input.split(",")]

        if len(x) != len(y):
            st.error("The number of x and y values must match.")
            st.stop()

        if len(x) < 2:
            st.error("Enter at least two data points.")
            st.stop()

        df = pd.DataFrame({"x": x, "y": y})

    except ValueError:
        st.error(
            "Please enter valid numbers separated by commas."
        )
        st.stop()

else:
    uploaded_file = st.sidebar.file_uploader(
        "Upload a CSV file",
        type=["csv"]
    )

    if uploaded_file is None:
        st.info(
            "Upload a CSV file with columns named x and y "
            "to continue."
        )
        st.stop()

    try:
        df = read_file(uploaded_file)
    except (ValueError, pd.errors.ParserError) as error:
        st.error(f"Could not read the CSV file: {error}")
        st.stop()


# ----------------------------------
# Display Input Data
# ----------------------------------
st.subheader("1. Input Data")
st.dataframe(df, use_container_width=True)

x = df["x"].tolist()
y = df["y"].tolist()


# ----------------------------------
# Calculate Regression
# ----------------------------------
try:
    slope, intercept = linear_regression(x, y)
except ValueError as error:
    st.error(str(error))
    st.stop()


# ----------------------------------
# Display Results
# ----------------------------------
st.subheader("2. Regression Results")

col1, col2, col3 = st.columns(3)

col1.metric("Slope (b1)", f"{slope:.4f}")
col2.metric("Intercept (b0)", f"{intercept:.4f}")
col3.metric("Data Points", len(x))

st.success(
    f"Regression equation: ŷ = {intercept:.4f} "
    f"+ ({slope:.4f} × x)"
)


# ----------------------------------
# Plot Regression Line
# ----------------------------------
st.subheader("3. Regression Plot")

x_line = sorted(x)
y_line = [intercept + slope * xi for xi in x_line]

fig, ax = plt.subplots(figsize=(10, 5))

ax.scatter(
    x, y,
    color="royalblue",
    s=70,
    label="Observed data"
)

ax.plot(
    x_line, y_line,
    color="red",
    linewidth=2,
    label="Regression line"
)

ax.set_xlabel("X values")
ax.set_ylabel("Y values")
ax.set_title("Simple Linear Regression")
ax.legend()
ax.grid(True, alpha=0.3)

st.pyplot(fig)
plt.close(fig)


# ----------------------------------
# Predict a New Value
# ----------------------------------
st.subheader("4. Predict a Y Value")

new_x = st.number_input(
    "Enter an x value:",
    value=float(x[0])
)

if st.button("Predict Y", type="primary"):
    predicted_y = intercept + slope * new_x

    st.info(
        f"When x = {new_x:.4f}, "
        f"the predicted y = {predicted_y:.4f}"
    )


# ----------------------------------
# Download Results
# ----------------------------------
st.subheader("5. Download Results")

results = df.copy()
results["predicted_y"] = [
    intercept + slope * xi for xi in x
]
results["residual"] = results["y"] - results["predicted_y"]

csv_data = results.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download regression results as CSV",
    data=csv_data,
    file_name="regression_results.csv",
    mime="text/csv"
)
