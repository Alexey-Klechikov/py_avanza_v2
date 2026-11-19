def backoff_seconds(attempt: int, base_seconds: float, cap_seconds: float) -> float:
    return min(base_seconds * 2**attempt, cap_seconds)
