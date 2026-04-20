from uuid import uuid4


def new_job_id() -> str:
    return f"job_{uuid4().hex[:26]}"


def new_report_id() -> str:
    return f"rpt_{uuid4().hex[:26]}"
