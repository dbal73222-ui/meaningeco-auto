import dataclasses

from agent_selection.applicant_parser import Applicant
from agent_selection.xfile_client import EXPECTED_COLUMNS

# custom_option_1/2는 parse_applicant_row에서 role_type/participation_count로
# 변환되어 저장되므로 Applicant 필드명과 1:1로 일치하지 않는 것이 의도된 설계임
TRANSFORMED_KEYS = {"custom_option_1", "custom_option_2"}


def test_expected_columns_keys_match_applicant_fields():
    # xfile_client.py의 컬럼 키와 applicant_parser.py가 읽는 키가 어긋나면
    # parse_applicant_row가 예외 없이 빈 값을 채우므로, 라이브 사이트 없이도 조기에 잡아냄
    applicant_fields = {f.name for f in dataclasses.fields(Applicant)}
    applicant_fields.discard("posting_url")

    expected_keys = {key for _, key in EXPECTED_COLUMNS}
    passthrough_keys = expected_keys - TRANSFORMED_KEYS

    assert passthrough_keys <= applicant_fields
