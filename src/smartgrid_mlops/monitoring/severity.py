def classify_severity(triggered,quality_critical=False,magnitude=0.0):
    if quality_critical:return "CRITICAL"
    n=len(triggered)
    if n==0:return "NONE"
    if magnitude>=2 or n>=3:return "CRITICAL"
    if n>=2 or magnitude>=1:return "WARNING"
    return "WATCH"
