from dataclasses import dataclass
@dataclass(frozen=True)
class MonitoringWindow: start:int; end:int; role:str
def make_windows(n,window=168,stride=24,role="DEVELOPMENT"):
    if n<window or window<=0 or stride<=0:return []
    return [MonitoringWindow(i,i+window,role) for i in range(0,n-window+1,stride)]
def validate_development_role(fold):
    roles={"F01":"CALIBRATION","F02":"CALIBRATION","F03":"CALIBRATION","F04":"CONTROL","F05":"NATURAL_MONITORING","F06":"NATURAL_MONITORING"}
    if fold not in roles:raise ValueError("final-test or unknown fold is forbidden")
    return roles[fold]
