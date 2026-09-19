def validate_alignment(left: list[str], right: list[str]) -> dict[str, int]:
    return {"matched_timestamps": len(set(left) & set(right)), "unmatched_left": len(set(left) - set(right)), "unmatched_right": len(set(right) - set(left)), "duplicate_left": len(left) - len(set(left)), "duplicate_right": len(right) - len(set(right))}
