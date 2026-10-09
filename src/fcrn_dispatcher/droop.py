F_REF_HZ = 50.0
DF_MAX_HZ = 0.1


def droop(f_hz: float, capacity_w: float) -> float:
    return max(-capacity_w, min(capacity_w, capacity_w / DF_MAX_HZ * (F_REF_HZ - f_hz)))
