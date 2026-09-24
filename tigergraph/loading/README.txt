1. Run prepare_identity_profiles.py with the project tf_dml interpreter. It streams identity.csv and writes only data/processed/identity_profiles_for_tigergraph.csv.
2. Run GSQL with fraud_investigation_schema.gsql, then load_fraud_data.gsql.
3. Execute RUN LOADING JOB load_fraud_data USING transactions="<absolute transactions.csv>", identity_profiles="<absolute generated profile CSV>", closed_cases="<absolute closed_cases_history.csv>", case_pack="<absolute case_pack.csv>".
4. Derive card IDs from authoritative case/closed-case card IDs before production loading. The raw transaction table does not itself contain card_id, so its customer-to-card mapping must not be inferred by this loading job.
