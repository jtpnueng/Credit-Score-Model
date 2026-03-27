import os
import requests
import streamlit as st

st.set_page_config(page_title="Credit Default Predictor", page_icon="💳", layout="centered")

API_URL = os.environ.get(
    "API_GATEWAY_URL",
    "https://i0rcibotud.execute-api.us-east-1.amazonaws.com"
).rstrip("/")

# ── Encoding maps (match Lending Club dataset encoding) ───────────────────────
GRADE_MAP        = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6}
TERM_MAP         = {"36 months": 36.0, "60 months": 60.0}
HOME_MAP         = {"MORTGAGE": 0, "NONE": 1, "OTHER": 2, "OWN": 3, "RENT": 4}
VERIF_MAP        = {"Not Verified": 0, "Source Verified": 1, "Verified": 2}
PURPOSE_MAP      = {
    "Debt Consolidation": 0, "Credit Card": 1, "Home Improvement": 2,
    "Other": 3, "Major Purchase": 4, "Medical": 5, "Small Business": 6,
    "Car": 7, "Vacation": 8, "Moving": 9, "House": 10,
    "Wedding": 11, "Educational": 12, "Renewable Energy": 13,
}

st.title("💳 Credit Default Predictor")
st.markdown("Enter loan application details to predict the likelihood of default.")
st.markdown("---")

with st.form("prediction_form"):
    st.subheader("Loan Details")
    col1, col2 = st.columns(2)

    with col1:
        loan_amnt   = st.number_input("Loan Amount ($)", min_value=500, max_value=40000, value=10000, step=500)
        term        = st.selectbox("Term", list(TERM_MAP.keys()))
        int_rate    = st.number_input("Interest Rate (%)", min_value=5.0, max_value=30.0, value=12.0, step=0.1)
        installment = st.number_input("Monthly Installment ($)", min_value=10.0, max_value=1500.0, value=300.0, step=5.0)
        grade       = st.selectbox("Loan Grade", list(GRADE_MAP.keys()))
        sub_grade_n = st.selectbox("Sub Grade (1-5)", [1, 2, 3, 4, 5], index=0)
        purpose     = st.selectbox("Loan Purpose", list(PURPOSE_MAP.keys()))
        dti         = st.number_input("Debt-to-Income Ratio", min_value=0.0, max_value=40.0, value=15.0, step=0.1)

    with col2:
        annual_inc          = st.number_input("Annual Income ($)", min_value=10000, max_value=500000, value=60000, step=1000)
        emp_length          = st.slider("Employment Length (years)", min_value=0, max_value=10, value=3)
        home_ownership      = st.selectbox("Home Ownership", list(HOME_MAP.keys()))
        verification_status = st.selectbox("Income Verification", list(VERIF_MAP.keys()))
        revol_bal           = st.number_input("Revolving Balance ($)", min_value=0, max_value=100000, value=5000, step=500)
        revol_util          = st.number_input("Revolving Utilisation (%)", min_value=0.0, max_value=100.0, value=40.0, step=1.0)
        open_acc            = st.number_input("Open Credit Lines", min_value=0, max_value=30, value=8)
        total_acc           = st.number_input("Total Credit Lines", min_value=1, max_value=80, value=20)

    st.subheader("Credit History")
    c1, c2, c3 = st.columns(3)
    with c1:
        delinq_2yrs  = st.number_input("Delinquencies (2yr)", min_value=0, max_value=10, value=0)
    with c2:
        inq_last_6mths = st.number_input("Credit Inquiries (6mo)", min_value=0, max_value=10, value=1)
    with c3:
        pub_rec      = st.number_input("Public Records", min_value=0, max_value=5, value=0)

    submitted = st.form_submit_button("🔍 Predict Default Risk", use_container_width=True)

if submitted:
    # Convert human-readable → encoded values
    sub_grade_encoded = GRADE_MAP[grade] * 5 + (sub_grade_n - 1)

    payload = {
        "loan_amnt":           float(loan_amnt),
        "term":                TERM_MAP[term],
        "int_rate":            float(int_rate),
        "installment":         float(installment),
        "grade":               GRADE_MAP[grade],
        "sub_grade":           sub_grade_encoded,
        "emp_length":          float(emp_length),
        "home_ownership":      HOME_MAP[home_ownership],
        "annual_inc":          float(annual_inc),
        "verification_status": VERIF_MAP[verification_status],
        "purpose":             PURPOSE_MAP[purpose],
        "dti":                 float(dti),
        "delinq_2yrs":         float(delinq_2yrs),
        "inq_last_6mths":      float(inq_last_6mths),
        "open_acc":            float(open_acc),
        "pub_rec":             float(pub_rec),
        "revol_bal":           float(revol_bal),
        "revol_util":          float(revol_util),
        "total_acc":           float(total_acc),
    }

    with st.spinner("Analysing loan application..."):
        try:
            resp = requests.post(f"{API_URL}/predict", json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            prediction = result.get("prediction", result.get("label", "Unknown"))
            label      = result.get("label", str(prediction))
            prob       = result.get("default_probability")

            st.markdown("---")

            RESULT_CONFIG = {
                0: {
                    "label": "No Default",
                    "badge": "LOW RISK",
                    "emoji": "🟢",
                    "color": "#1f7a1f",
                    "bar": 1.0 - (prob or 0.3),
                    "summary": "This applicant is likely to repay the loan. Strong candidate for approval.",
                    "tips": [
                        "Qualifies for standard loan terms",
                        "Consider offering lower interest rate to retain customer",
                        "Good candidate for credit limit increase",
                    ],
                },
                1: {
                    "label": "Default",
                    "badge": "HIGH RISK",
                    "emoji": "🔴",
                    "color": "#a10000",
                    "bar": prob or 0.7,
                    "summary": "This applicant shows elevated default risk. Review before approval.",
                    "tips": [
                        "Consider requiring collateral or co-signer",
                        "Reduce loan amount or shorten term to mitigate risk",
                        "Request additional income verification",
                    ],
                },
            }

            pred_key = int(prediction) if str(prediction).isdigit() else (0 if "No" in label else 1)
            cfg = RESULT_CONFIG.get(pred_key, RESULT_CONFIG[1])

            st.markdown(
                f"<h2 style='color:{cfg['color']}'>"
                f"{cfg['emoji']} Prediction: {cfg['label']} &nbsp;"
                f"<span style='font-size:0.55em; background:{cfg['color']}; "
                f"color:white; padding:3px 10px; border-radius:12px;'>"
                f"{cfg['badge']}</span></h2>",
                unsafe_allow_html=True,
            )

            if prob is not None:
                st.metric("Default Probability", f"{prob:.1%}")

            st.progress(cfg["bar"])
            st.markdown(f"**{cfg['summary']}**")
            st.markdown("---")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 📋 Loan Summary")
                st.markdown(f"""
| Field | Value |
|---|---|
| Loan Amount | ${loan_amnt:,} |
| Term | {term} |
| Interest Rate | {int_rate}% |
| Grade | {grade}{sub_grade_n} |
| Purpose | {purpose} |
| DTI | {dti}% |
| Annual Income | ${annual_inc:,} |
""")
            with c2:
                st.markdown("#### 💡 Recommendations")
                for tip in cfg["tips"]:
                    st.markdown(f"- {tip}")

        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out — the API may be cold-starting. Try again in 30 seconds.")
        except requests.exceptions.HTTPError:
            st.error(f"API error {resp.status_code}: {resp.text}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

st.markdown("---")
st.caption(f"Powered by AWS SageMaker · ECS · API Gateway | Model: LogisticRegression · AUC 0.702 | `{API_URL}`")
