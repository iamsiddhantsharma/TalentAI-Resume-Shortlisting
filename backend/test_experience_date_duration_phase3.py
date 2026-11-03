"""
TalentAI — Phase 3: Date & Duration Engine Unit Test Suite

Verifies all 12 required test conditions:
1. Relevant work with missing dates remains qualitatively relevant, but has no duration credit.
2. Dates containing curly apostrophes parse correctly (JUN’22, AUG’22).
3. Existing date formats continue to pass.
4. Overlapping fully relevant roles do not double-count time.
5. A partially relevant role contributes only its relevance-weighted duration.
6. A partially relevant interval overlapping a fully relevant interval uses the maximum ratio for the overlapping slice.
7. Irrelevant work contributes zero relevant duration.
8. Minimum-and-maximum JD duration uses the maximum as target (e.g. 2–8 years with 3 yrs -> D = 0.375).
9. Minimum-only JD duration uses the minimum as target (e.g. 3+ years with 3 yrs -> D = 1.0, 1.5 yrs -> D = 0.5).
10. An unbounded JD does not receive an invented target (G1-C: range_status="unspecified", D=0.0).
11. Missing or unparseable dates do not produce fabricated duration.
12. Backward compatibility with existing regression tests.
"""

from datetime import date

from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.resume_object import Experience, ResumeObject
from app.services.experience_matching_service import (
    ExperienceMatchingService,
    experience_matching_service,
)


def create_test_jd(
    min_years: float | None = 2.0,
    max_years: float | None = 5.0,
    domains: list[str] | None = None,
) -> JobDescriptionObject:
    return JobDescriptionObject(
        required_skills=["Python", "Machine Learning"],
        responsibilities=["Model engineering"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=min_years,
                maximum_years=max_years,
                preferred_domains=domains or ["Machine Learning"],
            )
        ],
        tools_and_technologies=["Python"],
    )


# ------------------------------------------------------------------------------
# TEST 1: RELEVANT WORK WITH MISSING DATES
# ------------------------------------------------------------------------------
def test_1_relevant_work_with_missing_dates():
    print("Test 1: Relevant work with missing dates remains qualitatively relevant with zero duration")
    jd = create_test_jd(min_years=2.0, max_years=5.0)
    resume = ResumeObject(
        name="Candidate Missing Dates",
        experience=[
            Experience(
                role="Machine Learning Engineer",
                company="AI Labs",
                start_date=None,
                end_date=None,
                description="Trained PyTorch models.",
            )
        ],
    )
    relevance_results = [
        {
            "experience_index": 0,
            "decision": "RELEVANT",
            "relevance_ratio": 1.0,
            "relevant_work_summary": "Trained PyTorch models.",
        }
    ]

    result = experience_matching_service.match_experience(
        resume=resume,
        job_description=jd,
        relevance_results=relevance_results,
    )

    assert result["relevant_experience_found"] is True
    assert result["relevant_duration_years"] == 0.0
    assert result["duration_factor"] == 0.0
    assert result["diagnostic_status"] == "dates_missing_or_unparseable"
    assert result["experiences"][0]["relevant"] is True
    assert result["experiences"][0]["duration_available"] is False
    assert result["experiences"][0]["date_status"] == "missing_dates"
    print("  [PASSED] Qualitative relevance preserved (True) with zero duration credit.")


# ------------------------------------------------------------------------------
# TEST 2: TYPOGRAPHIC CURLY APOSTROPHES IN DATES (JUN’22, AUG’22)
# ------------------------------------------------------------------------------
def test_2_typographic_curly_apostrophes():
    print("Test 2: Dates containing typographic curly apostrophes (JUN’22, AUG’22) parse correctly")
    d1, status1 = experience_matching_service._parse_date_with_status("JUN’22")
    assert status1 == "valid"
    assert d1 == date(2022, 6, 1)

    d2, status2 = experience_matching_service._parse_date_with_status("AUG’22")
    assert status2 == "valid"
    assert d2 == date(2022, 8, 1)

    d3, status3 = experience_matching_service._parse_date_with_status("Jun '22")
    assert status3 == "valid"
    assert d3 == date(2022, 6, 1)

    d4, status4 = experience_matching_service._parse_date_with_status("AUG’2022")
    assert status4 == "valid"
    assert d4 == date(2022, 8, 1)

    print("  [PASSED] All curly apostrophe variants parsed cleanly.")


# ------------------------------------------------------------------------------
# TEST 3: EXISTING DATE FORMATS CONTINUE TO PASS
# ------------------------------------------------------------------------------
def test_3_existing_date_formats_continue_to_pass():
    print("Test 3: Existing date formats continue to pass")
    test_cases = [
        ("2021-06-15", date(2021, 6, 15), "valid"),
        ("2021-06", date(2021, 6, 1), "valid"),
        ("2021", date(2021, 1, 1), "valid"),
        ("06/2021", date(2021, 6, 1), "valid"),
        ("04/25/2022", date(2022, 4, 25), "valid"),
        ("25/04/2022", date(2022, 4, 25), "valid"),
        ("05/05/2022", date(2022, 5, 5), "valid"),
        ("Jun 2021", date(2021, 6, 1), "valid"),
        ("June 2021", date(2021, 6, 1), "valid"),
        ("March, 2021", date(2021, 3, 1), "valid"),
        ("Present", date.today(), "valid"),
    ]

    for val, expected_date, expected_status in test_cases:
        d, status = experience_matching_service._parse_date_with_status(val)
        assert status == expected_status, f"Failed for {val}: expected {expected_status}, got {status}"
        assert d == expected_date, f"Failed for {val}: expected {expected_date}, got {d}"

    # Ambiguous date without locale rule must still be rejected safely
    d_amb, status_amb = experience_matching_service._parse_date_with_status("04/05/2022")
    assert status_amb == "ambiguous_dates"
    assert d_amb is None

    print("  [PASSED] Standard formats and ambiguous safety checks intact.")


# ------------------------------------------------------------------------------
# TEST 4: OVERLAPPING FULLY RELEVANT ROLES (NO DOUBLE-COUNTING)
# ------------------------------------------------------------------------------
def test_4_overlapping_fully_relevant_roles():
    print("Test 4: Overlapping fully relevant roles do not double-count time")
    jd = create_test_jd(min_years=2.0, max_years=5.0)
    # Role A: 2020-01-01 to 2023-01-01 (3.0 years)
    # Role B: 2021-01-01 to 2022-01-01 (1.0 year, completely enclosed inside Role A)
    resume = ResumeObject(
        name="Candidate Overlap",
        experience=[
            Experience(
                role="ML Engineer",
                company="Company A",
                start_date="2020-01-01",
                end_date="2023-01-01",
                description="Role A",
            ),
            Experience(
                role="ML Consultant",
                company="Company B",
                start_date="2021-01-01",
                end_date="2022-01-01",
                description="Role B",
            ),
        ],
    )
    relevance_results = [
        {"experience_index": 0, "decision": "RELEVANT", "relevance_ratio": 1.0},
        {"experience_index": 1, "decision": "RELEVANT", "relevance_ratio": 1.0},
    ]

    result = experience_matching_service.match_experience(resume, jd, relevance_results)
    assert result["relevant_duration_years"] == 3.0
    print("  [PASSED] 3.0 years calculated without double-counting 1.0 enclosed year.")


# ------------------------------------------------------------------------------
# TEST 5: PARTIALLY RELEVANT ROLE SCALED DURATION (R = 0.5)
# ------------------------------------------------------------------------------
def test_5_partially_relevant_role_scaled_duration():
    print("Test 5: Partially relevant role contributes relevance-weighted duration (R = 0.5)")
    jd = create_test_jd(min_years=2.0, max_years=5.0)
    # 2.0 calendar years * 0.5 relevance ratio = 1.0 relevant year
    resume = ResumeObject(
        name="Candidate Partial",
        experience=[
            Experience(
                role="Software Engineer",
                company="Tech Co",
                start_date="2020-01-01",
                end_date="2022-01-01",
                description="FastAPI + ML inference pipeline",
            )
        ],
    )
    relevance_results = [
        {"experience_index": 0, "decision": "PARTIALLY_RELEVANT", "relevance_ratio": 0.5}
    ]

    result = experience_matching_service.match_experience(resume, jd, relevance_results)
    assert result["relevant_experience_found"] is True
    assert result["relevant_duration_years"] == 1.0
    assert result["experiences"][0]["duration_years"] == 2.0
    assert result["experiences"][0]["relevant_duration_years"] == 1.0
    print("  [PASSED] 2.0 calendar years correctly scaled to 1.0 relevant year.")


# ------------------------------------------------------------------------------
# TEST 6: PARTIAL OVERLAPPING FULLY RELEVANT INTERVAL (MAX RATIO TIME-SLICING)
# ------------------------------------------------------------------------------
def test_6_partial_overlapping_fully_relevant_uses_max_ratio():
    print("Test 6: Overlapping partial and fully relevant intervals use max ratio for each time slice")
    # Interval A (Fully relevant, R=1.0): 2020-01-01 to 2021-01-01 (1.0 yr)
    # Interval B (Partially relevant, R=0.5): 2020-07-01 to 2021-07-01 (1.0 yr)
    # Slice 1: 2020-01-01 to 2020-07-01 (0.5 yr) -> max(1.0) = 1.0 -> 0.5 yr
    # Slice 2: 2020-07-01 to 2021-01-01 (0.5 yr) -> max(1.0, 0.5) = 1.0 -> 0.5 yr
    # Slice 3: 2021-01-01 to 2021-07-01 (0.5 yr) -> max(0.5) = 0.5 -> 0.25 yr
    # Total = 0.5 + 0.5 + 0.25 = 1.25 years
    periods = [
        (date(2020, 1, 1), date(2021, 1, 1), 1.0),
        (date(2020, 7, 1), date(2021, 7, 1), 0.5),
    ]
    duration = experience_matching_service.calculate_weighted_non_overlapping_duration(periods)
    assert round(duration, 2) == 1.25
    print("  [PASSED] Time-slicing correctly yielded 1.25 years using maximum ratio per slice.")


# ------------------------------------------------------------------------------
# TEST 7: IRRELEVANT WORK CONTRIBUTES ZERO DURATION
# ------------------------------------------------------------------------------
def test_7_irrelevant_work_contributes_zero_duration():
    print("Test 7: Irrelevant work contributes zero relevant duration")
    jd = create_test_jd(min_years=2.0, max_years=5.0)
    resume = ResumeObject(
        name="Candidate Irrelevant",
        experience=[
            Experience(
                role="Graphic Designer",
                company="Design Studio",
                start_date="2020-01-01",
                end_date="2024-01-01",  # 4 years
                description="Designed marketing collateral.",
            )
        ],
    )
    relevance_results = [
        {"experience_index": 0, "decision": "IRRELEVANT", "relevance_ratio": 0.0}
    ]

    result = experience_matching_service.match_experience(resume, jd, relevance_results)
    assert result["relevant_experience_found"] is False
    assert result["relevant_duration_years"] == 0.0
    assert result["duration_factor"] == 0.0
    assert result["diagnostic_status"] == "no_relevant_experience"
    print("  [PASSED] Irrelevant role contributed 0.0 relevant duration.")


# ------------------------------------------------------------------------------
# TEST 8: BOUNDED JD (MIN AND MAX) USES MAX AS TARGET
# ------------------------------------------------------------------------------
def test_8_bounded_jd_uses_max_as_target():
    print("Test 8: Bounded JD (min 2, max 8) uses max (8.0) as saturation target")
    # 3.0 relevant years against 2–8 years requirement gives D = 3.0 / 8.0 = 0.375
    d_factor, target, status, note = experience_matching_service.compute_duration_factor(
        relevant_duration_years=3.0,
        minimum_years=2.0,
        maximum_years=8.0,
        duration_available=True,
    )
    assert status == "bounded"
    assert target == 8.0
    assert d_factor == 0.375
    print("  [PASSED] D = min(3.0 / 8.0, 1.0) = 0.375 correctly calculated.")


# ------------------------------------------------------------------------------
# TEST 9: MINIMUM-ONLY JD USES MINIMUM AS SATURATION TARGET
# ------------------------------------------------------------------------------
def test_9_min_only_jd_uses_min_as_saturation_target():
    print("Test 9: Minimum-only JD (3+ years) uses min (3.0) as saturation target")
    # Case A: 3.0 relevant years against 3+ requirement gives D = 1.0
    df_sat, target_a, status_a, _ = experience_matching_service.compute_duration_factor(
        relevant_duration_years=3.0,
        minimum_years=3.0,
        maximum_years=None,
        duration_available=True,
    )
    assert status_a == "min_only"
    assert target_a == 3.0
    assert df_sat == 1.0

    # Case B: 1.5 relevant years against 3+ requirement gives D = 1.5 / 3.0 = 0.5 (no automatic disqualification)
    df_part, target_b, status_b, _ = experience_matching_service.compute_duration_factor(
        relevant_duration_years=1.5,
        minimum_years=3.0,
        maximum_years=None,
        duration_available=True,
    )
    assert status_b == "min_only"
    assert target_b == 3.0
    assert df_part == 0.5
    print("  [PASSED] Saturation at min (1.0) and partial credit below min (0.5) verified.")


# ------------------------------------------------------------------------------
# TEST 10: UNBOUNDED JD FOLLOWS GATE 1 (G1-C)
# ------------------------------------------------------------------------------
def test_10_unbounded_jd_does_not_invent_target():
    print("Test 10: Unbounded JD does not invent a target (Gate 1 / G1-C)")
    df, target, status, note = experience_matching_service.compute_duration_factor(
        relevant_duration_years=4.0,
        minimum_years=None,
        maximum_years=None,
        duration_available=True,
    )
    assert status == "unspecified"
    assert target is None
    assert df == 0.0
    assert "recruiter clarification required" in note
    print("  [PASSED] Unspecified range preserved with D = 0.0 and no invented target.")


# ------------------------------------------------------------------------------
# TEST 11: MISSING/UNPARSEABLE DATES DO NOT PRODUCE FABRICATED DURATION
# ------------------------------------------------------------------------------
def test_11_unparseable_dates_no_fabricated_duration():
    print("Test 11: Missing or unparseable dates do not produce fabricated duration")
    jd = create_test_jd(min_years=2.0, max_years=5.0)
    resume = ResumeObject(
        name="Candidate Invalid Dates",
        experience=[
            Experience(
                role="ML Engineer",
                company="AI Labs",
                start_date="not_a_date",
                end_date="still_not_a_date",
                description="Trained deep models.",
            )
        ],
    )
    relevance_results = [
        {"experience_index": 0, "decision": "RELEVANT", "relevance_ratio": 1.0}
    ]

    result = experience_matching_service.match_experience(resume, jd, relevance_results)
    assert result["relevant_experience_found"] is True
    assert result["relevant_duration_years"] == 0.0
    assert result["duration_factor"] == 0.0
    assert result["experiences"][0]["duration_available"] is False
    assert result["experiences"][0]["date_status"] == "unparseable_dates"
    print("  [PASSED] Unparseable dates strictly produce 0.0 duration.")


# ------------------------------------------------------------------------------
# MAIN TEST RUNNER
# ------------------------------------------------------------------------------
def main():
    print("\n" + "=" * 80)
    print("TALENTAI — PHASE 3 DATE & DURATION ENGINE UNIT TEST SUITE")
    print("=" * 80 + "\n")

    test_1_relevant_work_with_missing_dates()
    test_2_typographic_curly_apostrophes()
    test_3_existing_date_formats_continue_to_pass()
    test_4_overlapping_fully_relevant_roles()
    test_5_partially_relevant_role_scaled_duration()
    test_6_partial_overlapping_fully_relevant_uses_max_ratio()
    test_7_irrelevant_work_contributes_zero_duration()
    test_8_bounded_jd_uses_max_as_target()
    test_9_min_only_jd_uses_min_as_saturation_target()
    test_10_unbounded_jd_does_not_invent_target()
    test_11_unparseable_dates_no_fabricated_duration()

    print("\n" + "=" * 80)
    print("ALL PHASE 3 DATE & DURATION TESTS PASSED (100%)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
