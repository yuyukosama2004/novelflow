from app.services.version_summary import normalize_version_summary


def test_version_summary_is_cleaned_and_capped_to_sixteen_characters() -> None:
    source = "摘要：主角雨夜发现被篡改的遗嘱并决定追查真相。"
    assert normalize_version_summary(source) == "主角雨夜发现被篡改的遗嘱并决定追"
    assert normalize_version_summary("  \n  突遇危机  \n") == "突遇危机"
