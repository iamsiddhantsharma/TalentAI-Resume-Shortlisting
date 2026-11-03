from datetime import date
from app.schemas.resume_object import ResumeObject, Experience
from app.schemas.job_description_object import JobDescriptionObject, ExperienceRequirement
from app.schemas.matching import ExperienceMatchingResult
from app.services.experience_matching_service import experience_matching_service, ExperienceMatchingService


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


def main():
    print("=" * 80)
    print("TALENTAI — PHASE 5.10B EXPERIENCE DATE PARSING & DIAGNOSTICS SUITE")
    print("=" * 80)

    service = experience_matching_service
    all_passed = True

    # --------------------------------------------------------------------------
    # 1. SUPPORTED DATE FORMATS
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 1: COMMON SUPPORTED DATE FORMATS")
    print("=" * 70)

    test_formats = [
        ("YYYY-MM-DD", "2021-06-15", date(2021, 6, 15), "valid"),
        ("YYYY-MM", "2021-06", date(2021, 6, 1), "valid"),
        ("YYYY", "2021", date(2021, 1, 1), "valid"),
        ("MM/YYYY", "06/2021", date(2021, 6, 1), "valid"),
        ("MM/DD/YYYY (unambiguous)", "04/25/2022", date(2022, 4, 25), "valid"),
        ("DD/MM/YYYY (unambiguous)", "25/04/2022", date(2022, 4, 25), "valid"),
        ("Symmetric MM/DD (unambiguous)", "05/05/2022", date(2022, 5, 5), "valid"),
        ("Jun 2021", "Jun 2021", date(2021, 6, 1), "valid"),
        ("June 2021", "June 2021", date(2021, 6, 1), "valid"),
        ("March, 2021", "March, 2021", date(2021, 3, 1), "valid"),
        ("Mar, 2021", "Mar, 2021", date(2021, 3, 1), "valid"),
        ("15 June 2021", "15 June 2021", date(2021, 6, 15), "valid"),
        ("June 15, 2021", "June 15, 2021", date(2021, 6, 15), "valid"),
    ]

    for label, input_str, expected_date, expected_status in test_formats:
        parsed, status = service._parse_date_with_status(input_str)
        passed = (parsed == expected_date) and (status == expected_status)
        if not passed:
            all_passed = False
        print_status(f"Format {label}: '{input_str}' -> {parsed}", passed)

    # --------------------------------------------------------------------------
    # 2. AMBIGUOUS DATES & LOCALE RULES
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 2: AMBIGUOUS NUMERIC DATES & LOCALE RULES")
    print("=" * 70)

    # Ambiguous date with NO locale: strictly rejected to prevent silent misinterpretation
    ambiguous_date, status = service._parse_date_with_status("04/05/2022", date_locale=None)
    passed_ambiguous = (ambiguous_date is None) and (status == "ambiguous_dates")
    if not passed_ambiguous:
        all_passed = False
    print_status("Strict avoidance: '04/05/2022' rejected without locale rule", passed_ambiguous)

    # US locale rule: MM/DD/YYYY -> April 5, 2022
    us_date, us_status = service._parse_date_with_status("04/05/2022", date_locale="en_US")
    passed_us = (us_date == date(2022, 4, 5)) and (us_status == "valid")
    if not passed_us:
        all_passed = False
    print_status("Explicit locale 'en_US': '04/05/2022' -> 2022-04-05", passed_us)

    # UK/IN locale rule: DD/MM/YYYY -> May 4, 2022
    gb_date, gb_status = service._parse_date_with_status("04/05/2022", date_locale="en_GB")
    passed_gb = (gb_date == date(2022, 5, 4)) and (gb_status == "valid")
    if not passed_gb:
        all_passed = False
    print_status("Explicit locale 'en_GB': '04/05/2022' -> 2022-05-04", passed_gb)

    # --------------------------------------------------------------------------
    # 3. ONGOING EMPLOYMENT KEYWORDS
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 3: ONGOING ROLES & PRESENT KEYWORDS")
    print("=" * 70)

    ongoing_keywords = ["Present", "current", "Now", "ongoing", "currently", "till date"]
    today = date.today()
    for kw in ongoing_keywords:
        parsed, status = service._parse_date_with_status(kw)
        passed = (parsed == today) and (status == "valid")
        if not passed:
            all_passed = False
        print_status(f"Ongoing keyword '{kw}' -> today ({today})", passed)

    # --------------------------------------------------------------------------
    # 4. MISSING & UNPARSEABLE DATES
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 4: MISSING & UNPARSEABLE DATES")
    print("=" * 70)

    missing_cases = [None, "", "   "]
    for case in missing_cases:
        parsed, status = service._parse_date_with_status(case)
        passed = (parsed is None) and (status == "missing_dates")
        if not passed:
            all_passed = False
        print_status(f"Missing case '{case}' -> (None, 'missing_dates')", passed)

    unparseable_cases = ["invalid_date_text", "2021-99-99", "abc/def/2020"]
    for case in unparseable_cases:
        parsed, status = service._parse_date_with_status(case)
        passed = (parsed is None) and (status == "unparseable_dates")
        if not passed:
            all_passed = False
        print_status(f"Unparseable case '{case}' -> (None, 'unparseable_dates')", passed)

    # --------------------------------------------------------------------------
    # 5. OVERLAPPING PERIODS MERGING
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 5: OVERLAPPING PERIODS CALCULATION")
    print("=" * 70)

    periods = [
        (date(2020, 1, 1), date(2022, 1, 1)),  # 2 years
        (date(2021, 1, 1), date(2023, 1, 1)),  # 2 years, overlaps by 1 year
    ]
    merged = service.merge_overlapping_periods(periods)
    expected_merged = [(date(2020, 1, 1), date(2023, 1, 1))]  # 3 years total
    passed_merge = merged == expected_merged
    if not passed_merge:
        all_passed = False
    print_status("Overlapping periods merged into single continuous span", passed_merge)

    total_duration = service.calculate_non_overlapping_duration(periods)
    passed_duration = round(total_duration, 1) == 3.0
    if not passed_duration:
        all_passed = False
    print_status(f"Duration calculated non-overlapping: {round(total_duration, 2)} years (expected ~3.0)", passed_duration)

    # --------------------------------------------------------------------------
    # 6. DIAGNOSTIC STATES IN END-TO-END MATCHING
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 6: FOUR DIAGNOSTIC STATES DISTINCTION")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=["Python"],
        responsibilities=[],
        experience_requirements=[
            ExperienceRequirement(minimum_years=2.0, maximum_years=5.0)
        ],
        tools_and_technologies=[],
    )

    # State A: No experience listed
    resume_empty = ResumeObject(
        skills=["Python"],
        experience=[],
        projects=[],
    )
    result_empty = service.match_experience(
        resume=resume_empty,
        job_description=jd,
        relevance_results=[],
    )
    passed_state_a = (
        result_empty["diagnostic_status"] == "no_experience_listed"
        and result_empty["experiences"] == []
        and result_empty["relevant_experience_found"] is False
    )
    if not passed_state_a:
        all_passed = False
    print_status("State 1: 'no_experience_listed' correctly detected", passed_state_a)

    # State B: Experience exists but not relevant
    resume_irrelevant = ResumeObject(
        skills=["Python"],
        experience=[
            Experience(
                role="Graphic Designer",
                company="Agency",
                start_date="2020-01",
                end_date="2023-01",
                description="Designed posters",
            )
        ],
        projects=[],
    )
    result_irrelevant = service.match_experience(
        resume=resume_irrelevant,
        job_description=jd,
        relevance_results=[{"experience_index": 0, "decision": "IRRELEVANT"}],
    )
    passed_state_b = (
        result_irrelevant["diagnostic_status"] == "no_relevant_experience"
        and result_irrelevant["relevant_experience_found"] is False
        and result_irrelevant["relevant_duration_years"] == 0.0
    )
    if not passed_state_b:
        all_passed = False
    print_status("State 2: 'no_relevant_experience' correctly detected", passed_state_b)

    # State C: Relevant experience with missing/unparseable dates
    resume_missing_dates = ResumeObject(
        skills=["Python"],
        experience=[
            Experience(
                role="Software Engineer",
                company="Tech Co",
                start_date=None,
                end_date=None,
                description="Built APIs",
            )
        ],
        projects=[],
    )
    result_missing_dates = service.match_experience(
        resume=resume_missing_dates,
        job_description=jd,
        relevance_results=[{"experience_index": 0, "decision": "RELEVANT"}],
    )
    passed_state_c = (
        result_missing_dates["diagnostic_status"] == "dates_missing_or_unparseable"
        and result_missing_dates["experiences"][0]["relevant"] is True
        and result_missing_dates["experiences"][0]["date_status"] == "missing_dates"
        and result_missing_dates["relevant_duration_years"] == 0.0
    )
    if not passed_state_c:
        all_passed = False
    print_status("State 3: 'dates_missing_or_unparseable' correctly detected", passed_state_c)

    # State C-2: Relevant experience with ambiguous dates without locale
    resume_ambiguous = ResumeObject(
        skills=["Python"],
        experience=[
            Experience(
                role="Software Engineer",
                company="Tech Co",
                start_date="04/05/2021",
                end_date="04/05/2023",
                description="Built APIs",
            )
        ],
        projects=[],
    )
    result_ambiguous = service.match_experience(
        resume=resume_ambiguous,
        job_description=jd,
        relevance_results=[{"experience_index": 0, "decision": "RELEVANT"}],
    )
    passed_state_c2 = (
        result_ambiguous["diagnostic_status"] == "ambiguous_dates"
        and result_ambiguous["experiences"][0]["date_status"] == "ambiguous_dates"
    )
    if not passed_state_c2:
        all_passed = False
    print_status("State 3b: 'ambiguous_dates' diagnostic correctly recorded", passed_state_c2)

    # State D: Relevant experience with valid dates and calculable duration
    resume_valid = ResumeObject(
        skills=["Python"],
        experience=[
            Experience(
                role="Software Engineer",
                company="Tech Co",
                start_date="2020-01",
                end_date="2023-01",
                description="Built APIs",
            )
        ],
        projects=[],
    )
    result_valid = service.match_experience(
        resume=resume_valid,
        job_description=jd,
        relevance_results=[{"experience_index": 0, "decision": "RELEVANT"}],
    )
    passed_state_d = (
        result_valid["diagnostic_status"] == "duration_calculated"
        and result_valid["relevant_experience_found"] is True
        and result_valid["relevant_duration_years"] == 3.0
        and result_valid["experiences"][0]["date_status"] == "valid"
        and result_valid["minimum_duration_satisfied"] is True
    )
    if not passed_state_d:
        all_passed = False
    print_status("State 4: 'duration_calculated' correctly calculated (3.0 years)", passed_state_d)

    # --------------------------------------------------------------------------
    # 7. PYDANTIC SCHEMA VALIDATION
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 7: EXPERIENCE MATCHING RESULT PYDANTIC VALIDATION")
    print("=" * 70)

    try:
        validated = ExperienceMatchingResult.model_validate(result_valid)
        passed_schema = (
            validated.diagnostic_status == "duration_calculated"
            and validated.experiences[0].date_status == "valid"
        )
    except Exception as exc:
        print(f"Schema validation error: {exc}")
        passed_schema = False

    if not passed_schema:
        all_passed = False
    print_status("ExperienceMatchingResult Pydantic schema backward & forward compatibility", passed_schema)

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    if all_passed:
        print("ALL PHASE 5.10B EXPERIENCE DATE & DIAGNOSTIC TESTS PASSED (100%)")
    else:
        print("SOME TESTS FAILED")
    print("=" * 80)


if __name__ == "__main__":
    main()
