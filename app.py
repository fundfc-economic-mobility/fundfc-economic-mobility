import streamlit as st
import pandas as pd
import plotly.express as px

from sqlalchemy import select

from fundfc.db import (
    init_db,
    get_session,
    Youth,
    Transaction,
    Milestone,
    account_balance,
)

from fundfc.finance import (
    NAMES,
    PRESETS,
    MU,
    VOL,
    portfolio_stats,
    optimize_portfolio,
    monte_carlo,
    compare_presets,
)

from fundfc.impact import (
    impact_summary,
    DOMAINS,
)


# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="FundFC | Economic Mobility Engine",
    page_icon="🌱",
    layout="wide",
)

init_db()

st.title("FundFC | Economic Mobility Engine")

st.caption(
    "Youth opportunity accounts + risk-constrained financial sustainability"
)


# --------------------------------------------------
# DATABASE SESSION
# --------------------------------------------------

with get_session() as session:

    youth_rows = session.scalars(
        select(Youth).order_by(Youth.id.desc())
    ).all()

    youth_ids = [y.id for y in youth_rows]

    page = st.sidebar.radio(
        "Workspace",
        [
            "Executive dashboard",
            "Youth profiles",
            "Opportunity accounts",
            "Milestones & outcomes",
            "Financial sustainability",
            "Model assumptions",
        ],
    )


    # --------------------------------------------------
    # EXECUTIVE DASHBOARD
    # --------------------------------------------------

    if page == "Executive dashboard":

        st.header("Executive Dashboard")

        metrics = impact_summary(session)

        total_assets = sum(
            account_balance(session, yid)
            for yid in youth_ids
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Participants",
            metrics["participants"]
        )

        c2.metric(
            "Active participants",
            metrics["active"]
        )

        c3.metric(
            "Opportunity account balances",
            f"${total_assets:,.0f}"
        )

        c4.metric(
            "Verified milestones",
            metrics["milestones_verified"]
        )

        st.subheader("Impact progress")

        st.dataframe(
            metrics["by_domain"],
            width="stretch",
            hide_index=True,
        )

        if not metrics["by_domain"].empty:

            chart_data = metrics["by_domain"].melt(
                id_vars="Domain",
                value_vars=["Completed", "Verified"],
                var_name="Measure",
                value_name="Count",
            )

            chart = px.bar(
                chart_data,
                x="Domain",
                y="Count",
                color="Measure",
                barmode="group",
                title="Milestone Progress by Domain",
            )

            st.plotly_chart(
                chart,
                width="stretch",
            )

        st.info(
            "MVP environment: use synthetic or consented pilot records. "
            "Do not enter unnecessary sensitive case information."
        )


    # --------------------------------------------------
    # YOUTH PROFILES
    # --------------------------------------------------

    elif page == "Youth profiles":

        st.header("Youth Profiles")

        st.subheader("Create participant profile")

        with st.form("new_youth"):

            code = st.text_input(
                "Participant code"
            )

            name = st.text_input(
                "Preferred name"
            )

            age = st.number_input(
                "Age",
                min_value=16,
                max_value=26,
                value=18,
            )

            consent = st.selectbox(
                "Data consent status",
                ["Pending", "Granted", "Declined"],
            )

            status = st.selectbox(
                "Program status",
                ["Active", "Paused", "Completed", "Exited"],
            )

            education = st.text_input(
                "Education goal"
            )

            employment = st.text_input(
                "Employment goal"
            )

            housing = st.text_input(
                "Housing goal"
            )

            submitted = st.form_submit_button(
                "Save profile"
            )

            if submitted:

                if not code.strip() or not name.strip():

                    st.error(
                        "Participant code and preferred name are required."
                    )

                elif session.scalar(
                    select(Youth).where(
                        Youth.participant_code == code.strip()
                    )
                ):

                    st.error(
                        "That participant code already exists."
                    )

                else:

                    session.add(
                        Youth(
                            participant_code=code.strip(),
                            preferred_name=name.strip(),
                            age=int(age),
                            consent_status=consent,
                            status=status,
                            education_goal=education,
                            employment_goal=employment,
                            housing_goal=housing,
                        )
                    )

                    session.commit()

                    st.success(
                        "Participant profile saved."
                    )

                    st.rerun()

        st.subheader("Participant roster")

        roster = []

        for youth in youth_rows:

            roster.append(
                {
                    "Code": youth.participant_code,
                    "Preferred name": youth.preferred_name,
                    "Age": youth.age,
                    "Status": youth.status,
                    "Consent": youth.consent_status,
                    "Account balance": account_balance(
                        session,
                        youth.id,
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(roster),
            width="stretch",
            hide_index=True,
        )


    # --------------------------------------------------
    # OPPORTUNITY ACCOUNTS
    # --------------------------------------------------

    elif page == "Opportunity accounts":

        st.header("Opportunity Accounts")

        if not youth_rows:

            st.warning(
                "Create a participant profile first."
            )

        else:

            options = {
                f"{y.participant_code} | {y.preferred_name}": y.id
                for y in youth_rows
            }

            selected = st.selectbox(
                "Participant",
                list(options),
            )

            youth_id = options[selected]

            balance = account_balance(
                session,
                youth_id,
            )

            st.metric(
                "Current ledger balance",
                f"${balance:,.2f}",
            )

            with st.form("transaction"):

                kind = st.selectbox(
                    "Transaction type",
                    [
                        "Contribution",
                        "Grant",
                        "Distribution",
                        "Fee",
                        "Adjustment In",
                        "Adjustment Out",
                    ],
                )

                amount = st.number_input(
                    "Amount ($)",
                    min_value=0.01,
                    value=100.00,
                    step=25.00,
                )

                category = st.selectbox(
                    "Category",
                    [
                        "Housing",
                        "Education",
                        "Employment",
                        "Transportation",
                        "Emergency",
                        "Financial capability",
                        "General",
                    ],
                )

                description = st.text_input(
                    "Description"
                )

                reference = st.text_input(
                    "Receipt / approval reference"
                )

                save = st.form_submit_button(
                    "Post transaction"
                )

                if save:

                    session.add(
                        Transaction(
                            youth_id=youth_id,
                            transaction_type=kind,
                            amount=float(amount),
                            category=category,
                            description=description,
                            reference=reference,
                        )
                    )

                    session.commit()

                    st.success(
                        "Transaction posted."
                    )

                    st.rerun()

            transactions = session.scalars(
                select(Transaction)
                .where(
                    Transaction.youth_id == youth_id
                )
                .order_by(
                    Transaction.transaction_date.desc()
                )
            ).all()

            transaction_table = pd.DataFrame(
                [
                    {
                        "Date": t.transaction_date,
                        "Type": t.transaction_type,
                        "Category": t.category,
                        "Amount": t.amount,
                        "Description": t.description,
                        "Reference": t.reference,
                    }
                    for t in transactions
                ]
            )

            st.dataframe(
                transaction_table,
                width="stretch",
                hide_index=True,
            )


    # --------------------------------------------------
    # MILESTONES
    # --------------------------------------------------

    elif page == "Milestones & outcomes":

        st.header("Milestones & Outcomes")

        if not youth_rows:

            st.warning(
                "Create a participant profile first."
            )

        else:

            options = {
                f"{y.participant_code} | {y.preferred_name}": y.id
                for y in youth_rows
            }

            selected = st.selectbox(
                "Participant",
                list(options),
            )

            youth_id = options[selected]

            with st.form("milestone"):

                domain = st.selectbox(
                    "Outcome domain",
                    DOMAINS,
                )

                label = st.text_input(
                    "Milestone"
                )

                status = st.selectbox(
                    "Status",
                    [
                        "Not started",
                        "In progress",
                        "Completed",
                    ],
                )

                verified = st.checkbox(
                    "Evidence independently verified"
                )

                due = st.text_input(
                    "Due date (YYYY-MM-DD)"
                )

                notes = st.text_area(
                    "Non-sensitive progress note"
                )

                save = st.form_submit_button(
                    "Save milestone"
                )

                if save:

                    if not label.strip():

                        st.error(
                            "Enter a milestone description."
                        )

                    else:

                        session.add(
                            Milestone(
                                youth_id=youth_id,
                                domain=domain,
                                milestone=label.strip(),
                                status=status,
                                verified=verified,
                                due_date=due,
                                notes=notes,
                            )
                        )

                        session.commit()

                        st.success(
                            "Milestone saved."
                        )

                        st.rerun()

            milestones = session.scalars(
                select(Milestone).where(
                    Milestone.youth_id == youth_id
                )
            ).all()

            milestone_table = pd.DataFrame(
                [
                    {
                        "Domain": m.domain,
                        "Milestone": m.milestone,
                        "Status": m.status,
                        "Verified": m.verified,
                        "Due": m.due_date,
                    }
                    for m in milestones
                ]
            )

            st.dataframe(
                milestone_table,
                width="stretch",
                hide_index=True,
            )


    # --------------------------------------------------
    # FINANCIAL SUSTAINABILITY
    # --------------------------------------------------

    elif page == "Financial sustainability":

        st.header("Financial Sustainability")

        st.write(
            "Model the long-term sustainability of an "
            "individualized opportunity account."
        )

        c1, c2, c3 = st.columns(3)

        initial = c1.number_input(
            "Initial account ($)",
            min_value=0,
            value=10000,
            step=1000,
        )

        monthly = c2.number_input(
            "Monthly contribution ($)",
            min_value=0,
            value=100,
            step=25,
        )

        withdrawal = c3.number_input(
            "Annual withdrawal ($)",
            min_value=0,
            value=1500,
            step=250,
        )

        c4, c5, c6 = st.columns(3)

        years = c4.slider(
            "Projection horizon (years)",
            1,
            50,
            30,
        )

        simulations = c5.select_slider(
            "Simulations",
            options=[
                1000,
                5000,
                10000,
                25000,
            ],
            value=10000,
        )

        fee = (
            c6.number_input(
                "Annual fee assumption (%)",
                min_value=0.0,
                max_value=3.0,
                value=0.30,
                step=0.05,
            )
            / 100
        )

        c7, c8, c9 = st.columns(3)

        start = c7.number_input(
            "Withdrawal start year",
            min_value=1,
            max_value=50,
            value=6,
        )

        end = c8.number_input(
            "Withdrawal end year",
            min_value=int(start),
            max_value=50,
            value=max(10, int(start)),
        )

        inflation = (
            c9.number_input(
                "Annual inflation (%)",
                min_value=0.0,
                max_value=10.0,
                value=2.5,
                step=0.25,
            )
            / 100
        )

        strategy = st.selectbox(
            "Portfolio allocation",
            list(PRESETS.keys()) +
            ["Constrained optimizer"],
        )

        max_vol = st.slider(
            "Optimizer maximum annual volatility",
            0.04,
            0.20,
            0.12,
            0.01,
        )

        if strategy == "Constrained optimizer":

            try:

                weights = optimize_portfolio(
                    max_volatility=max_vol
                )

            except ValueError as error:

                st.error(str(error))

                weights = PRESETS["Balanced"]

        else:

            weights = PRESETS[strategy]

        expected, risk = portfolio_stats(
            weights
        )

        allocation = pd.DataFrame(
            {
                "Asset class": NAMES,
                "Weight": weights,
                "Illustrative expected return": MU,
                "Illustrative volatility": VOL,
            }
        )

        st.subheader("Selected allocation")

        st.dataframe(
            allocation.style.format(
                {
                    "Weight": "{:.1%}",
                    "Illustrative expected return": "{:.1%}",
                    "Illustrative volatility": "{:.1%}",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        st.caption(
            f"Illustrative expected portfolio return: "
            f"{expected:.1%} | "
            f"Annual volatility: {risk:.1%}. "
            "These assumptions are not forecasts."
        )

        if st.button(
            "Run Monte Carlo sustainability model",
            type="primary",
        ):

            with st.spinner(
                "Simulating account paths..."
            ):

                summary, paths, ending = monte_carlo(
                    initial_balance=initial,
                    monthly_contribution=monthly,
                    annual_withdrawal=withdrawal,
                    withdrawal_start_year=int(start),
                    withdrawal_end_year=int(end),
                    years=years,
                    fee_rate=fee,
                    inflation_rate=inflation,
                    simulations=int(simulations),
                    weights=weights,
                )

            x1, x2, x3 = st.columns(3)

            x1.metric(
                "Median ending balance",
                f"${summary['median_ending']:,.0f}",
            )

            x2.metric(
                "10th percentile ending",
                f"${summary['p10_ending']:,.0f}",
            )

            x3.metric(
                "Observed depletion rate",
                f"{summary['depletion_probability']:.1%}",
            )

            st.metric(
                "Median ending balance in today's dollars",
                f"${summary['median_real_ending']:,.0f}",
            )

            path_chart = px.line(
                paths,
                x="Year",
                y=["P10", "Median", "P90"],
                title="Projected Account Balance Range",
            )

            st.plotly_chart(
                path_chart,
                width="stretch",
            )

            st.caption(
                "Percentiles represent simulated paths. "
                "Balances are nominal unless labeled real."
            )

            st.download_button(
                "Download simulation paths (CSV)",
                paths.to_csv(index=False),
                "fundfc_monte_carlo_paths.csv",
                "text/csv",
            )

            histogram = px.histogram(
                x=ending,
                nbins=50,
                labels={
                    "x": "Ending balance"
                },
                title="Monte Carlo Ending Balance Distribution",
            )

            st.plotly_chart(
                histogram,
                width="stretch",
            )

        st.divider()

        st.subheader(
            "Compare model portfolios"
        )

        if st.button(
            "Compare all three strategies"
        ):

            comparison = compare_presets(
                initial_balance=initial,
                monthly_contribution=monthly,
                annual_withdrawal=withdrawal,
                withdrawal_start_year=int(start),
                withdrawal_end_year=int(end),
                years=years,
                fee_rate=fee,
                inflation_rate=inflation,
                simulations=int(simulations),
            )

            st.dataframe(
                comparison.style.format(
                    {
                        "Expected annual return*": "{:.1%}",
                        "Annual volatility*": "{:.1%}",
                        "Median ending balance": "${:,.0f}",
                        "10th percentile ending": "${:,.0f}",
                        "90th percentile ending": "${:,.0f}",
                        "Depletion probability": "{:.1%}",
                    }
                ),
                width="stretch",
                hide_index=True,
            )


    # --------------------------------------------------
    # MODEL ASSUMPTIONS
    # --------------------------------------------------

    elif page == "Model assumptions":

        st.header("Model Assumptions")

        st.warning(
            "These values are illustrative demonstration inputs only. "
            "They are not current market forecasts or investment recommendations."
        )

        assumptions = pd.DataFrame(
            {
                "Asset class": NAMES,
                "Expected annual return": MU,
                "Annual volatility": VOL,
            }
        )

        st.dataframe(
            assumptions.style.format(
                {
                    "Expected annual return": "{:.1%}",
                    "Annual volatility": "{:.1%}",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        st.subheader("Current MVP limitations")

        st.markdown(
            """
- No live market-data feed is enabled.
- Financial assumptions are illustrative.
- No automated eligibility or award decisions are made.
- No trained neural network or reinforcement-learning agent is included.
- Production use would require appropriate authentication, security, audit, consent, governance, and independent validation.
            """
        )