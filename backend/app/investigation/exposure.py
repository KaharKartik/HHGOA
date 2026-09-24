def calculate_exposure(transactions: list[tuple[str, float]]) -> float:
    return round(sum(abs(amount) for _, amount in transactions), 2)
