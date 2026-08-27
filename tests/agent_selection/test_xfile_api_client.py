from agent_selection.xfile_api_client import extract_job_posting_id


def test_extract_job_posting_id_from_detail_url():
    posting_id = extract_job_posting_id("https://console.ex-pile.com/job-posting/31a6d72d-e9bb")

    assert posting_id == "31a6d72d-e9bb"


def test_extract_job_posting_id_ignores_trailing_slash():
    posting_id = extract_job_posting_id("https://console.ex-pile.com/job-posting/abc123/")

    assert posting_id == "abc123"
