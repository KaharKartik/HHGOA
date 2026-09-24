# Benchmark Submission Answers (`cases/`)

This directory contains the official submission answers for the Hacker House Goa 20-Case Fraud Investigation Benchmark.

## 📌 Case Mapping & Repository Structure

- **`data/raw/case_pack.csv`** = Benchmark input/reference containing the 20 cases to be investigated.
- **`cases/`** = Official submission answers directory.
- **`cases/HHG-001.json` through `cases/HHG-020.json`** = One answer per benchmark case (HHG-001 through HHG-020).

## 📄 File Details

Each JSON answer file in this folder corresponds to a benchmark case defined in `data/raw/case_pack.csv` and includes:
- **Case Record**: Verdict, status, risk pattern, exposure, evidence list, and similar historical cases.
- **Evidence Requests & Next Best Actions**: Initial recommendations, evidence queries, and final action after evidence evaluation.
- **Suspicious Activity Report (SAR)**: Regulatory SAR filing decision, narrative, subjects, and aggregated transaction totals.
