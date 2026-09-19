def assert_no_final_test_access(path=None):
    if path and any(x in str(path).lower() for x in ("final_test","final-test","november","december")):raise ValueError("FINAL_TEST_POLICY_VIOLATION")
