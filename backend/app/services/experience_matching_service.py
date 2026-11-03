from datetime import date, datetime
import math
import re
from typing import Any

from app.schemas.job_description import JobDescriptionObject
from app.schemas.resume_object import ResumeObject
from app.services.experience_similarity_service import (
    ExperienceSimilarityService,
    experience_similarity_service,
)


class ExperienceMatchingService:
    """
    Matches candidate work experience against the Job Description.

    Responsibilities of this service:

    1. Receive experience relevance decisions from the
       semantic/LLM experience layer.
    2. Identify which candidate experiences are relevant.
    3. Calculate duration only for relevant experiences.
    4. Prevent overlapping experience periods from being
       counted more than once, using maximum relevance ratio
       time-slicing across overlapping intervals.
    5. Compare relevant experience duration with JD
       minimum/maximum requirements and saturation targets.
    6. Keep relevance and duration as strictly separate signals:
       relevant work is recognized even when dates are missing/unparseable.

    This service does NOT:

    - decide semantic relevance using an embedding threshold
    - call the LLM
    - generate embeddings
    - calculate final candidate ranking
    - apply ranking weights
    - reject candidates
    """

    ONGOING_KEYWORDS = {
        "present",
        "current",
        "now",
        "ongoing",
        "currently",
        "till date",
        "to date",
    }

    TEXT_DATE_FORMATS = [
        "%B, %Y",
        "%b, %Y",
        "%B %Y",
        "%b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%b-%Y",
        "%B-%Y",
        "%d-%b-%Y",
        # Formats for 2-digit years and typographic quotes (e.g. JUN'22, AUG'22, Jun '22)
        "%b'%y",
        "%B'%y",
        "%b'%Y",
        "%B'%Y",
        "%b '%y",
        "%B '%y",
        "%b '%Y",
        "%B '%Y",
        "%b %y",
        "%B %y",
        "%b-%y",
        "%B-%y",
    ]

    def __init__(
        self,
        date_locale: str | None = None,
        similarity_service: ExperienceSimilarityService | None = None,
    ):
        self.date_locale = date_locale
        self.similarity_service = (
            similarity_service
            if similarity_service is not None
            else experience_similarity_service
        )

    # --------------------------------------------------
    # DATE PARSING WITH DIAGNOSTIC STATUS
    # --------------------------------------------------

    def _parse_date_with_status(
        self,
        value: str | None,
        date_locale: str | None = None,
    ) -> tuple[date | None, str]:
        """
        Convert a resume experience date string into a Python date object
        and diagnostic status string.

        Supported formats:
            - YYYY-MM-DD (e.g. "2021-06-15")
            - YYYY-MM (e.g. "2021-06")
            - YYYY (e.g. "2021")
            - MM/YYYY (e.g. "06/2021")
            - MM/DD/YYYY (e.g. "04/25/2022")
            - DD/MM/YYYY where unambiguous (e.g. "25/04/2022") or with locale rule
            - Jun 2021 / June 2021 / March, 2021
            - Typographic apostrophe formats: JUN’22, AUG’22, Jun '22
            - Ongoing / Present / Current / Now

        Ambiguity handling:
            Numeric dates where both day and month are <= 12 and unequal
            (e.g. "04/05/2022") cannot be interpreted reliably without an
            established locale rule. Without a locale rule, they return
            (None, "ambiguous_dates") rather than silently guessing.
        """
        if not value:
            return None, "missing_dates"

        cleaned = str(value).strip()
        if not cleaned:
            return None, "missing_dates"

        # Normalize typographic single quotes and curly apostrophes (U+2019, U+2018, `, ´) to standard ASCII '
        cleaned = (
            cleaned.replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("`", "'")
            .replace("´", "'")
        )

        lower_text = cleaned.lower()
        if lower_text in self.ONGOING_KEYWORDS:
            return date.today(), "valid"

        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Textual month formats
        for fmt in self.TEXT_DATE_FORMATS:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.date(), "valid"
            except ValueError:
                pass

        # Regex for single 4-digit Year: YYYY (e.g. 2021)
        if re.fullmatch(r"\d{4}", cleaned):
            year = int(cleaned)
            if 1900 <= year <= 2100:
                return date(year, 1, 1), "valid"
            return None, "unparseable_dates"

        # Delimited numeric dates using '-', '/', or '.'
        parts = re.split(r"[-/.]", cleaned)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) == 2:
            p1, p2 = parts[0], parts[1]
            if p1.isdigit() and p2.isdigit():
                # YYYY-MM, YYYY/MM, YYYY.MM
                if len(p1) == 4 and (1 <= len(p2) <= 2):
                    year, month = int(p1), int(p2)
                    if 1 <= month <= 12 and 1900 <= year <= 2100:
                        return date(year, month, 1), "valid"
                    return None, "unparseable_dates"
                # MM/YYYY, MM-YYYY, MM.YYYY
                elif (1 <= len(p1) <= 2) and len(p2) == 4:
                    month, year = int(p1), int(p2)
                    if 1 <= month <= 12 and 1900 <= year <= 2100:
                        return date(year, month, 1), "valid"
                    return None, "unparseable_dates"

        elif len(parts) == 3:
            p1, p2, p3 = parts[0], parts[1], parts[2]
            if p1.isdigit() and p2.isdigit() and p3.isdigit():
                # Case A: Year first: YYYY-MM-DD (ISO 8601 standard, unambiguous)
                if len(p1) == 4 and (1 <= len(p2) <= 2) and (1 <= len(p3) <= 2):
                    year, month, day = int(p1), int(p2), int(p3)
                    try:
                        return date(year, month, day), "valid"
                    except ValueError:
                        return None, "unparseable_dates"

                # Case B: Year last: p1 / p2 / YYYY
                elif (1 <= len(p1) <= 2) and (1 <= len(p2) <= 2) and len(p3) == 4:
                    v1, v2, year = int(p1), int(p2), int(p3)
                    if not (1900 <= year <= 2100):
                        return None, "unparseable_dates"

                    # Subcase 1: v1 > 12 and 1 <= v2 <= 12 -> Unambiguously DD/MM/YYYY
                    if v1 > 12 and 1 <= v2 <= 12:
                        try:
                            return date(year, v2, v1), "valid"
                        except ValueError:
                            return None, "unparseable_dates"

                    # Subcase 2: 1 <= v1 <= 12 and v2 > 12 -> Unambiguously MM/DD/YYYY
                    elif 1 <= v1 <= 12 and v2 > 12:
                        try:
                            return date(year, v1, v2), "valid"
                        except ValueError:
                            return None, "unparseable_dates"

                    # Subcase 3: v1 == v2 (e.g. 05/05/2022) -> Day and Month are identical, unambiguous
                    elif 1 <= v1 <= 12 and v1 == v2:
                        try:
                            return date(year, v1, v2), "valid"
                        except ValueError:
                            return None, "unparseable_dates"

                    # Subcase 4: 1 <= v1 <= 12 and 1 <= v2 <= 12 and v1 != v2 (e.g. 04/05/2022)
                    # Potentially ambiguous (could be April 5th or May 4th)
                    elif 1 <= v1 <= 12 and 1 <= v2 <= 12 and v1 != v2:
                        active_locale = (
                            date_locale
                            if date_locale is not None
                            else self.date_locale
                        )
                        if active_locale in ("en_US", "US"):
                            try:
                                return date(year, v1, v2), "valid"
                            except ValueError:
                                return None, "unparseable_dates"
                        elif active_locale in (
                            "en_GB",
                            "en_IN",
                            "GB",
                            "IN",
                            "EU",
                        ):
                            try:
                                return date(year, v2, v1), "valid"
                            except ValueError:
                                return None, "unparseable_dates"
                        else:
                            # Strict avoidance of silent ambiguous date interpretation
                            return None, "ambiguous_dates"

        return None, "unparseable_dates"

    def _parse_date(
        self,
        value: str | None,
        date_locale: str | None = None,
    ) -> date | None:
        """
        Convert a resume experience date into a Python date.
        """
        parsed, _ = self._parse_date_with_status(
            value,
            date_locale=date_locale,
        )
        return parsed

    # --------------------------------------------------
    # SINGLE EXPERIENCE DURATION
    # --------------------------------------------------

    def calculate_duration_days(
        self,
        start_date: str | None,
        end_date: str | None,
        date_locale: str | None = None,
    ) -> int:
        """
        Calculate the duration of one experience period.

        If end_date represents an ongoing role, today's date
        is used.

        Returns duration in days.

        If either date cannot be parsed, returns 0.
        """
        start = self._parse_date(start_date, date_locale=date_locale)
        end = self._parse_date(end_date, date_locale=date_locale)

        if start is None or end is None:
            return 0

        if end < start:
            return 0

        return (end - start).days

    # --------------------------------------------------
    # DAYS → YEARS
    # --------------------------------------------------

    def days_to_years(
        self,
        days: int,
    ) -> float:
        """
        Convert duration in days into approximate years.
        """
        if days <= 0:
            return 0.0

        return days / 365.25

    # --------------------------------------------------
    # MERGE OVERLAPPING PERIODS (UNWEIGHTED)
    # --------------------------------------------------

    def merge_overlapping_periods(
        self,
        periods: list[tuple[date, date]],
    ) -> list[tuple[date, date]]:
        """
        Merge overlapping experience periods into continuous spans.
        Preserved for backward-compatibility.
        """
        if not periods:
            return []

        sorted_periods = sorted(
            periods,
            key=lambda period: period[0],
        )

        merged = [sorted_periods[0]]

        for current_start, current_end in sorted_periods[1:]:
            previous_start, previous_end = merged[-1]

            if current_start <= previous_end:
                merged[-1] = (
                    previous_start,
                    max(previous_end, current_end),
                )
            else:
                merged.append((current_start, current_end))

        return merged

    # --------------------------------------------------
    # NON-OVERLAPPING DURATION (UNWEIGHTED)
    # --------------------------------------------------

    def calculate_non_overlapping_duration(
        self,
        periods: list[tuple[date, date]],
    ) -> float:
        """
        Calculate total duration across non-overlapping
        experience periods (assuming ratio 1.0).
        """
        weighted = [(start, end, 1.0) for start, end in periods]
        return self.calculate_weighted_non_overlapping_duration(weighted)

    # --------------------------------------------------
    # WEIGHTED NON-OVERLAPPING DURATION (TIME-SLICED)
    # --------------------------------------------------

    @staticmethod
    def _parse_and_validate_ratio(raw_ratio: Any) -> float | None:
        """
        Safely parse raw_ratio into a validated float.

        Requirements (Stage 5B.1):
        1. Handle None, empty strings, non-numeric strings, NaN, positive infinity,
           and negative infinity without crashing.
        2. Validate that the parsed value is finite.
        3. Clamp valid numeric values to the range [0.0, 1.0].
        4. Return None for invalid, non-numeric, NaN, or infinite values.
        """
        if raw_ratio is None:
            return None
        if isinstance(raw_ratio, str):
            raw_ratio = raw_ratio.strip()
            if not raw_ratio:
                return None
        try:
            val = float(raw_ratio)
            if not math.isfinite(val):
                return None
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return None

    def calculate_weighted_non_overlapping_duration(
        self,
        periods: list[tuple[date, date, float]],
    ) -> float:
        """
        Calculate total duration across non-overlapping experience periods,
        weighting each disjoint time slice by the maximum applicable relevance ratio.

        Where intervals overlap, uses max(r_k) for that time slice rather than
        summing overlapping periods. This preserves the full contribution of a
        fully relevant role while preventing partial overlaps from inflating duration.

        Input:
            periods: list of (start_date, end_date, relevance_ratio)
        """
        valid_intervals: list[tuple[date, date, float]] = []
        for start, end, ratio in periods:
            if start is None or end is None or end <= start:
                continue
            validated_ratio = self._parse_and_validate_ratio(ratio)
            if validated_ratio is not None and validated_ratio > 0.0:
                valid_intervals.append((start, end, validated_ratio))

        if not valid_intervals:
            return 0.0

        # Collect unique critical boundary dates
        critical_dates = sorted(
            list(
                set(start for start, end, _ in valid_intervals)
                | set(end for start, end, _ in valid_intervals)
            )
        )

        total_weighted_days = 0.0

        for i in range(len(critical_dates) - 1):
            slice_start = critical_dates[i]
            slice_end = critical_dates[i + 1]

            if slice_end <= slice_start:
                continue

            # Find all intervals covering this exact time slice
            active_ratios = [
                ratio
                for start, end, ratio in valid_intervals
                if start <= slice_start and end >= slice_end
            ]

            if active_ratios:
                # Use maximum ratio across overlapping roles for this time slice
                slice_ratio = max(active_ratios)
                slice_days = (slice_end - slice_start).days
                total_weighted_days += slice_days * slice_ratio

        return self.days_to_years(int(round(total_weighted_days)))

    # --------------------------------------------------
    # DURATION FACTOR CALCULATION (GATE 1 COMPLIANT)
    # --------------------------------------------------

    def compute_duration_factor(
        self,
        relevant_duration_years: float,
        minimum_years: float | None,
        maximum_years: float | None,
        duration_available: bool = True,
    ) -> tuple[float, float | None, str, str | None]:
        """
        Calculates duration factor D = min(Y_relevant / Y_target, 1.0) according
        to approved architectural rules.

        Rules:
        - Bounded range (min and max): Y_target = maximum_years.
        - Min-only range (min, no max): Y_target = minimum_years (saturation target).
        - Max-only range (no min, max): Y_target = maximum_years.
        - Unbounded range (GATE 1 / G1-C): Do not invent a target. range_status="unspecified",
          duration_factor=0.0, saturation_target_years=None.
        - Missing or invalid dates: duration_factor=0.0; qualitative relevance preserved.

        Returns:
            (duration_factor, saturation_target_years, range_status, diagnostic_note)
        """
        # If dates are missing or invalid, duration credit cannot be awarded
        if not duration_available or relevant_duration_years <= 0.0:
            if minimum_years is not None and maximum_years is not None:
                range_status = "bounded"
                target = maximum_years
            elif minimum_years is not None:
                range_status = "min_only"
                target = minimum_years
            elif maximum_years is not None:
                range_status = "max_only"
                target = maximum_years
            else:
                range_status = "unspecified"
                target = None
            return 0.0, target, range_status, "No validated duration available."

        # Case 1: JD with min and max (bounded)
        if minimum_years is not None and maximum_years is not None:
            range_status = "bounded"
            target = maximum_years
            if target <= 0.0:
                duration_factor = 1.0
            else:
                duration_factor = min(relevant_duration_years / target, 1.0)
            note = (
                f"Evaluated against bounded range ({minimum_years}–{maximum_years} yrs); "
                f"saturation target: {target} yrs."
            )

        # Case 2: JD with min only (no max)
        elif minimum_years is not None and maximum_years is None:
            range_status = "min_only"
            target = minimum_years
            if target <= 0.0:
                duration_factor = 1.0
            else:
                duration_factor = min(relevant_duration_years / target, 1.0)
            note = (
                f"Evaluated against minimum requirement ({minimum_years}+ yrs); "
                f"saturation target: {target} yrs."
            )

        # Case 3: JD with max only (no min)
        elif minimum_years is None and maximum_years is not None:
            range_status = "max_only"
            target = maximum_years
            if target <= 0.0:
                duration_factor = 1.0
            else:
                duration_factor = min(relevant_duration_years / target, 1.0)
            note = (
                f"Evaluated against maximum ceiling ({maximum_years} yrs); "
                f"saturation target: {target} yrs."
            )

        # Case 4: GATE 1 (G1-C) — Neither minimum nor maximum specified
        else:
            range_status = "unspecified"
            target = None
            duration_factor = 0.0
            note = (
                "Job description does not specify minimum or maximum experience duration. "
                "Duration factor marked as unspecified (0.0); recruiter clarification required."
            )

        return round(duration_factor, 4), target, range_status, note

    # --------------------------------------------------
    # EXPERIENCE REQUIREMENTS
    # --------------------------------------------------

    def extract_experience_requirements(
        self,
        job_description: JobDescriptionObject,
    ) -> dict[str, Any]:
        """
        Extract overall experience requirements from the JD.

        If multiple experience requirement objects exist:
        - highest minimum is used
        - lowest maximum is used
        - preferred domains are combined
        """
        minimum_years: float | None = None
        maximum_years: float | None = None
        preferred_domains: list[str] = []

        for requirement in job_description.experience_requirements:
            # Minimum experience
            if requirement.minimum_years is not None:
                if (
                    minimum_years is None
                    or requirement.minimum_years > minimum_years
                ):
                    minimum_years = requirement.minimum_years

            # Maximum experience
            if requirement.maximum_years is not None:
                if (
                    maximum_years is None
                    or requirement.maximum_years < maximum_years
                ):
                    maximum_years = requirement.maximum_years

            # Preferred domains
            for domain in requirement.preferred_domains:
                if domain and domain.strip():
                    cleaned_domain = domain.strip()
                    if not any(
                        existing.lower() == cleaned_domain.lower()
                        for existing in preferred_domains
                    ):
                        preferred_domains.append(cleaned_domain)

        return {
            "minimum_years": minimum_years,
            "maximum_years": maximum_years,
            "preferred_domains": preferred_domains,
        }

    # --------------------------------------------------
    # MEANINGFUL EXPERIENCE REQUIREMENT
    # --------------------------------------------------

    def has_meaningful_experience_requirement(
        self,
        job_description: JobDescriptionObject,
    ) -> bool:
        """
        Determine whether the JD actually contains an
        experience requirement that needs evaluation.
        """
        for requirement in job_description.experience_requirements:
            if requirement.minimum_years is not None:
                return True
            if requirement.maximum_years is not None:
                return True
            if any(
                domain and domain.strip()
                for domain in requirement.preferred_domains
            ):
                return True

        return False

    # --------------------------------------------------
    # EXPERIENCE TEXT
    # --------------------------------------------------

    def build_experience_text(
        self,
        experience: Any,
    ) -> str:
        """
        Convert one Resume experience object into readable
        experience text.
        """
        parts = []

        if hasattr(experience, "role") and experience.role:
            role = experience.role.strip()
            if role:
                parts.append(f"Role: {role}")
        elif isinstance(experience, dict) and experience.get("role"):
            parts.append(f"Role: {experience['role'].strip()}")

        if hasattr(experience, "company") and experience.company:
            company = experience.company.strip()
            if company:
                parts.append(f"Company: {company}")
        elif isinstance(experience, dict) and experience.get("company"):
            parts.append(f"Company: {experience['company'].strip()}")

        if hasattr(experience, "description") and experience.description:
            description = experience.description.strip()
            if description:
                parts.append(f"Work: {description}")
        elif isinstance(experience, dict) and experience.get("description"):
            parts.append(f"Work: {experience['description'].strip()}")

        return " | ".join(parts)

    # --------------------------------------------------
    # DURATION REQUIREMENT EVALUATION
    # --------------------------------------------------

    def evaluate_duration_requirement(
        self,
        relevant_duration_years: float,
        minimum_years: float | None,
        maximum_years: float | None,
    ) -> dict[str, Any]:
        """
        Compare relevant experience duration with the JD.
        Reports whether duration requirements are satisfied.
        Does NOT automatically disqualify candidates.
        """
        minimum_satisfied = True
        maximum_exceeded = False

        if minimum_years is not None:
            minimum_satisfied = relevant_duration_years >= minimum_years

        if maximum_years is not None:
            maximum_exceeded = relevant_duration_years > maximum_years

        return {
            "minimum_years": minimum_years,
            "maximum_years": maximum_years,
            "minimum_duration_satisfied": minimum_satisfied,
            "maximum_duration_exceeded": maximum_exceeded,
        }

    # --------------------------------------------------
    # RELEVANT EXPERIENCE INDEXES
    # --------------------------------------------------

    def get_relevant_experience_indexes(
        self,
        relevance_results: list[dict],
        relevance_threshold: float | None = None,
    ) -> set[int]:
        """
        Extract experience indexes that were classified as RELEVANT
        or PARTIALLY_RELEVANT (or have ratio > 0.0).
        """
        relevant_indexes: set[int] = set()

        for result in relevance_results:
            experience_index = result.get("experience_index")
            if experience_index is None:
                continue

            decision = result.get("decision")
            norm_decision = (
                str(decision).strip().upper()
                if decision is not None
                and isinstance(decision, str)
                and str(decision).strip()
                else None
            )

            # Fix B: Qualitative decision precedence
            # Explicit negative decisions are strictly excluded regardless of any auxiliary ratio
            if norm_decision in (
                "IRRELEVANT",
                "AMBIGUOUS",
                "INSUFFICIENT_INFORMATION",
            ):
                continue

            # Explicit positive decisions are eligible
            if norm_decision in ("RELEVANT", "PARTIALLY_RELEVANT"):
                relevant_indexes.add(experience_index)
            elif norm_decision is None and "relevance_score" in result:
                # Backward-compatibility fallback for tests supplying relevance_score
                cutoff = (
                    relevance_threshold
                    if relevance_threshold is not None
                    else 0.60
                )
                try:
                    score = float(result["relevance_score"])
                    if math.isfinite(score) and score >= cutoff:
                        relevant_indexes.add(experience_index)
                except (ValueError, TypeError):
                    pass

        return relevant_indexes

    # --------------------------------------------------
    # MAIN EXPERIENCE MATCHING
    # --------------------------------------------------

    def match_experience(
        self,
        resume: ResumeObject,
        job_description: JobDescriptionObject,
        relevance_results: list[dict],
        relevance_threshold: float | None = None,
        date_locale: str | None = None,
        tau: float = ExperienceSimilarityService.DEFAULT_TAU,
        candidate_embeddings: dict[int, list[float]] | list[list[float]] | None = None,
        jd_embeddings: dict[str, list[float]] | list[list[float]] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate candidate professional experience against the Job Description.

        Guarantees:
        - Separates qualitative relevance and semantic similarity from date availability.
        - Integrates evidence-based ExperienceSimilarityService (Phase 5B).
        - Computes raw and calibrated semantic similarity for eligible experiences.
        - Enforces zero similarity credit for irrelevant, ambiguous, insufficient,
          missing-summary, and unsupported domain roles.
        - Maps evidence to unique JD domains using max similarity across supporting roles:
          S_m = max(S_k,m)
        - Computes aggregated similarity across unique JD domains (including unsupported as 0.0):
          S_agg = sum(S_m) / M
        - Deduplicates JD domains case-insensitively with deterministic order preserved.
        - Preserves Phase 3 non-overlapping weighted duration via time-slicing.
        - Computes duration factor D = min(Y_relevant / Y_target, 1.0) with Gate 1 compliance.
        - Preserves existing API compatibility, diagnostics, and safe defaults.
        """
        requirements = self.extract_experience_requirements(job_description)
        experience_requirement_present = self.has_meaningful_experience_requirement(
            job_description
        )

        # --------------------------------------------------
        # IF NO EXPERIENCE REQUIREMENT AND NO RELEVANCE RESULTS
        # --------------------------------------------------
        if not experience_requirement_present and not relevance_results:
            return {
                "experience_requirements": {
                    "minimum_years": requirements["minimum_years"],
                    "maximum_years": requirements["maximum_years"],
                    "preferred_domains": requirements["preferred_domains"],
                },
                "experience_requirement_present": False,
                "experiences": [],
                "relevant_experience_found": False,
                "relevant_duration_years": 0.0,
                "minimum_years": requirements["minimum_years"],
                "maximum_years": requirements["maximum_years"],
                "minimum_duration_satisfied": True,
                "maximum_duration_exceeded": False,
                "diagnostic_status": "not_applicable",
                "diagnostic_message": "Job description specifies no experience requirements.",
                "duration_factor": 0.0,
                "saturation_target_years": None,
                "range_status": "no_requirements",
                "aggregated_similarity": 0.0,
                "experience_score": 0.0,
            }

        # --------------------------------------------------
        # IF NO RESUME EXPERIENCE ENTRIES
        # --------------------------------------------------
        if not resume.experience:
            target = (
                requirements["maximum_years"]
                if requirements["maximum_years"] is not None
                else requirements["minimum_years"]
            )
            range_status = (
                "bounded"
                if requirements["minimum_years"] and requirements["maximum_years"]
                else (
                    "min_only"
                    if requirements["minimum_years"]
                    else "unspecified"
                )
            )

            return {
                "experience_requirements": {
                    "minimum_years": requirements["minimum_years"],
                    "maximum_years": requirements["maximum_years"],
                    "preferred_domains": requirements["preferred_domains"],
                },
                "experience_requirement_present": True,
                "experiences": [],
                "relevant_experience_found": False,
                "relevant_duration_years": 0.0,
                "minimum_years": requirements["minimum_years"],
                "maximum_years": requirements["maximum_years"],
                "minimum_duration_satisfied": (
                    requirements["minimum_years"] is None
                    or requirements["minimum_years"] == 0
                ),
                "maximum_duration_exceeded": False,
                "diagnostic_status": "no_experience_listed",
                "diagnostic_message": "No experience entries found on resume.",
                "duration_factor": 0.0,
                "saturation_target_years": target,
                "range_status": range_status,
                "aggregated_similarity": 0.0,
                "experience_score": 0.0,
            }

        # --------------------------------------------------
        # EXTRACT UNIQUE JD DOMAINS (DEDUPLICATED, ORDER PRESERVED)
        # --------------------------------------------------
        unique_jd_domains = list(requirements.get("preferred_domains", []))
        total_unique_domains = len(unique_jd_domains)

        # Prepare JD embeddings lookup if provided
        resolved_jd_embeddings: dict[str, list[float]] | None = None
        if isinstance(jd_embeddings, dict):
            resolved_jd_embeddings = jd_embeddings
        elif isinstance(jd_embeddings, list):
            resolved_jd_embeddings = {
                domain: jd_embeddings[i]
                for i, domain in enumerate(unique_jd_domains)
                if i < len(jd_embeddings)
            }

        # Track calibrated similarity per domain across all supporting roles:
        # domain -> list of calibrated similarity scores S_{k, m}
        domain_role_similarities: dict[str, list[float]] = {
            domain: [] for domain in unique_jd_domains
        }

        # --------------------------------------------------
        # RELEVANT EXPERIENCE INDEXES
        # --------------------------------------------------
        relevant_indexes = self.get_relevant_experience_indexes(
            relevance_results,
            relevance_threshold=relevance_threshold,
        )

        experience_results = []
        weighted_periods: list[tuple[date, date, float]] = []

        active_locale = (
            date_locale if date_locale is not None else self.date_locale
        )

        # --------------------------------------------------
        # PROCESS EVERY RESUME EXPERIENCE
        # --------------------------------------------------
        for experience_index, experience in enumerate(resume.experience):
            matching_result = next(
                (
                    result
                    for result in relevance_results
                    if result.get("experience_index") == experience_index
                ),
                None,
            )
            if matching_result is None and experience_index < len(relevance_results):
                candidate_res = relevance_results[experience_index]
                if "experience_index" not in candidate_res:
                    matching_result = candidate_res

            decision = None
            raw_ratio = None

            if matching_result is not None:
                decision = matching_result.get("decision")
                if "relevance_ratio" in matching_result:
                    raw_ratio = matching_result["relevance_ratio"]

            norm_decision = (
                str(decision).strip().upper()
                if decision is not None
                and isinstance(decision, str)
                and str(decision).strip()
                else None
            )

            # Fix B & Fix A: Strict qualitative decision precedence and ratio validation
            if norm_decision in (
                "IRRELEVANT",
                "AMBIGUOUS",
                "INSUFFICIENT_INFORMATION",
            ):
                is_relevant = False
                ratio = 0.0
                relevance_score = 0.0
            elif norm_decision in ("RELEVANT", "PARTIALLY_RELEVANT"):
                is_relevant = True
                if raw_ratio is not None or (
                    matching_result is not None
                    and "relevance_ratio" in matching_result
                ):
                    parsed_ratio = self._parse_and_validate_ratio(raw_ratio)
                    # For explicitly relevant or partially relevant experience,
                    # use a conservative zero duration ratio if no valid ratio is available.
                    ratio = parsed_ratio if parsed_ratio is not None else 0.0
                elif norm_decision == "RELEVANT":
                    ratio = 1.0
                else:  # PARTIALLY_RELEVANT
                    ratio = 0.5

                if (
                    matching_result is not None
                    and "relevance_score" in matching_result
                ):
                    relevance_score = matching_result.get("relevance_score")
                elif norm_decision == "RELEVANT":
                    relevance_score = 1.0
                else:
                    relevance_score = 0.5
            else:
                # Genuinely missing or None decision: check legacy relevance_score contract
                if (
                    matching_result is not None
                    and "relevance_score" in matching_result
                ):
                    cutoff = (
                        relevance_threshold
                        if relevance_threshold is not None
                        else 0.60
                    )
                    try:
                        score_val = float(matching_result["relevance_score"])
                        if math.isfinite(score_val) and score_val >= cutoff:
                            is_relevant = True
                            relevance_score = score_val
                            if (
                                raw_ratio is not None
                                or "relevance_ratio" in matching_result
                            ):
                                parsed_ratio = self._parse_and_validate_ratio(
                                    raw_ratio
                                )
                                ratio = (
                                    parsed_ratio
                                    if parsed_ratio is not None
                                    else 0.0
                                )
                            else:
                                ratio = 1.0
                        else:
                            is_relevant = False
                            relevance_score = (
                                score_val if math.isfinite(score_val) else 0.0
                            )
                            ratio = 0.0
                    except (ValueError, TypeError):
                        is_relevant = False
                        relevance_score = 0.0
                        ratio = 0.0
                else:
                    # No decision and no legacy relevance_score:
                    # Do not invent positive relevance from an invalid or orphan ratio.
                    is_relevant = False
                    ratio = 0.0
                    relevance_score = 0.0

            # Verified work summary
            raw_summary = (
                matching_result.get("relevant_work_summary")
                if matching_result is not None
                else None
            )
            clean_summary = (
                str(raw_summary).strip()
                if raw_summary and str(raw_summary).strip()
                else None
            )

            # Extract matched domains from matching_result
            raw_matched_domains: list[str] = []
            if matching_result is not None and "matched_domains" in matching_result:
                val = matching_result.get("matched_domains")
                if isinstance(val, list):
                    raw_matched_domains = [
                        str(d).strip() for d in val if d and str(d).strip()
                    ]
                elif isinstance(val, str) and val.strip():
                    raw_matched_domains = [val.strip()]

            # Determine which unique JD domains are supported by this experience
            supported_domains: list[str] = []
            if matching_result is not None and "matched_domains" in matching_result:
                raw_matched_lower = {d.lower() for d in raw_matched_domains}
                for jd_d in unique_jd_domains:
                    if jd_d.lower() in raw_matched_lower:
                        supported_domains.append(jd_d)
            else:
                # Legacy records genuinely lacking matched_domains metadata:
                # With exactly 1 domain in JD, general relevance maps to that domain.
                if total_unique_domains == 1 and is_relevant:
                    supported_domains = list(unique_jd_domains)
                else:
                    # Multiple domains: do not guess across domains
                    supported_domains = []

            # --------------------------------------------------
            # SEMANTIC SIMILARITY EVALUATION (PHASE 5B)
            # --------------------------------------------------
            # Rule 1 & Rule 2:
            # Only RELEVANT or PARTIALLY_RELEVANT with non-empty verified work summaries
            # supporting valid JD domains may receive similarity credit.
            is_similarity_eligible = (
                norm_decision in ("RELEVANT", "PARTIALLY_RELEVANT")
                and clean_summary is not None
                and len(supported_domains) > 0
            )

            role_semantic_sim: float = 0.0
            role_calibrated_sim: float = 0.0

            if is_similarity_eligible and clean_summary:
                # Retrieve candidate precomputed embedding if supplied
                cand_emb: list[float] | None = None
                if isinstance(candidate_embeddings, dict):
                    cand_emb = candidate_embeddings.get(experience_index)
                elif (
                    isinstance(candidate_embeddings, list)
                    and experience_index < len(candidate_embeddings)
                ):
                    cand_emb = candidate_embeddings[experience_index]

                sim_eval = (
                    self.similarity_service.evaluate_experience_similarity(
                        decision=norm_decision,
                        relevant_work_summary=clean_summary,
                        jd_requirements=supported_domains,
                        tau=tau,
                        candidate_embedding=cand_emb,
                        jd_embeddings=resolved_jd_embeddings,
                    )
                )

                role_semantic_sim = float(
                    sim_eval.get("raw_similarity", 0.0)
                )
                role_calibrated_sim = float(
                    sim_eval.get("calibrated_similarity", 0.0)
                )

                # Record per-domain calibrated similarity S_{k,m}
                # Rule 7: Do not multiply by relevance_ratio!
                for item in sim_eval.get("all_domain_similarities", []):
                    req_name = item.get("requirement")
                    req_raw = item.get("raw_similarity", 0.0)
                    req_cal = self.similarity_service.calibrate_similarity(
                        req_raw, tau=tau
                    )
                    for jd_d in unique_jd_domains:
                        if jd_d.lower() == str(req_name).strip().lower():
                            domain_role_similarities[jd_d].append(req_cal)
                            break

            provenance_domains = (
                raw_matched_domains
                if (
                    matching_result is not None
                    and "matched_domains" in matching_result
                )
                else supported_domains
            )

            # Base result dictionary
            experience_result = {
                "experience_index": experience_index,
                "role": experience.role,
                "company": experience.company,
                "description": experience.description,
                "decision": decision,
                "relevant": is_relevant,
                "matched_domains": provenance_domains,
                "duration_years": 0.0,
                "duration_available": False,
                "start_date": experience.start_date,
                "end_date": experience.end_date,
                "date_status": "not_evaluated" if not is_relevant else None,
                "relevance_score": relevance_score,
                "relevance_ratio": ratio,
                "relevant_duration_years": 0.0,
                "semantic_similarity": role_semantic_sim,
                "calibrated_similarity": role_calibrated_sim,
                "relevant_work_summary": clean_summary,
                "confidence": (
                    matching_result.get("confidence")
                    if matching_result is not None
                    else None
                ),
            }

            # If not relevant, append and continue
            if not is_relevant:
                experience_results.append(experience_result)
                continue

            # Relevant experience: date parsing
            start, start_status = self._parse_date_with_status(
                experience.start_date,
                date_locale=active_locale,
            )
            end, end_status = self._parse_date_with_status(
                experience.end_date,
                date_locale=active_locale,
            )

            # Missing dates
            if (
                start_status == "missing_dates"
                or end_status == "missing_dates"
            ):
                experience_result["date_status"] = "missing_dates"
                experience_results.append(experience_result)
                continue

            # Ambiguous dates
            if (
                start_status == "ambiguous_dates"
                or end_status == "ambiguous_dates"
            ):
                experience_result["date_status"] = "ambiguous_dates"
                experience_results.append(experience_result)
                continue

            # Unparseable dates
            if (
                start is None
                or end is None
                or start_status == "unparseable_dates"
                or end_status == "unparseable_dates"
            ):
                experience_result["date_status"] = "unparseable_dates"
                experience_results.append(experience_result)
                continue

            # Invalid range (end < start)
            if end < start:
                experience_result["date_status"] = "invalid_range"
                experience_results.append(experience_result)
                continue

            # Valid dates
            duration_days = (end - start).days
            duration_years = self.days_to_years(duration_days)

            experience_result["duration_years"] = round(duration_years, 2)
            experience_result["duration_available"] = True
            experience_result["date_status"] = "valid"
            clamped_relevant_years = min(
                duration_years, max(0.0, duration_years * ratio)
            )
            experience_result["relevant_duration_years"] = round(
                clamped_relevant_years, 2
            )

            # Add to weighted periods for non-overlapping union
            weighted_periods.append((start, end, ratio))
            experience_results.append(experience_result)

        # --------------------------------------------------
        # TOTAL RELEVANT EXPERIENCE (TIME-SLICED UNION)
        # --------------------------------------------------
        relevant_duration_years = (
            self.calculate_weighted_non_overlapping_duration(weighted_periods)
        )

        # --------------------------------------------------
        # DECOUPLE RELEVANCE FROM DATE AVAILABILITY
        # --------------------------------------------------
        relevant_experience_found = any(
            result["relevant"] for result in experience_results
        )

        # --------------------------------------------------
        # DURATION FACTOR (GATE 1 COMPLIANT)
        # --------------------------------------------------
        duration_available = len(weighted_periods) > 0
        (
            duration_factor,
            saturation_target,
            range_status,
            factor_note,
        ) = self.compute_duration_factor(
            relevant_duration_years=relevant_duration_years,
            minimum_years=requirements["minimum_years"],
            maximum_years=requirements["maximum_years"],
            duration_available=duration_available,
        )

        # Duration requirement satisfaction diagnostic
        duration_result = self.evaluate_duration_requirement(
            relevant_duration_years=relevant_duration_years,
            minimum_years=requirements["minimum_years"],
            maximum_years=requirements["maximum_years"],
        )

        # --------------------------------------------------
        # AGGREGATED SIMILARITY ACROSS UNIQUE JD DOMAINS (PHASE 5B)
        # --------------------------------------------------
        # Rule 3: For each unique JD domain, use max calibrated similarity among eligible supporting roles:
        # S_m = max(S_{k,m})
        # Rule 4: S_agg = sum(S_m) / M, unsupported domains count as 0.0
        if total_unique_domains > 0:
            domain_max_scores: list[float] = []
            for jd_d in unique_jd_domains:
                scores = domain_role_similarities.get(jd_d, [])
                s_m = max(scores) if scores else 0.0
                domain_max_scores.append(s_m)
            aggregated_similarity = round(
                self.similarity_service.clamp(
                    sum(domain_max_scores) / float(total_unique_domains),
                    0.0,
                    1.0,
                ),
                4,
            )
        else:
            aggregated_similarity = 0.0

        # --------------------------------------------------
        # DIAGNOSTIC STATUS & MESSAGE
        # --------------------------------------------------
        if not relevant_experience_found:
            diagnostic_status = "no_relevant_experience"
            diagnostic_message = (
                "Candidate has work experience, but none "
                "satisfied the job description relevance criteria."
            )
        elif len(weighted_periods) > 0 and relevant_duration_years > 0.0:
            diagnostic_status = "duration_calculated"
            diagnostic_message = (
                f"Relevant experience duration successfully "
                f"calculated ({round(relevant_duration_years, 2)} years)."
            )
        else:
            # Relevant experience exists, but dates are missing/unparseable/ambiguous
            relevant_statuses = [
                exp.get("date_status")
                for exp in experience_results
                if exp.get("relevant")
            ]
            if any(s == "ambiguous_dates" for s in relevant_statuses):
                diagnostic_status = "ambiguous_dates"
                diagnostic_message = (
                    "Relevant experience found, but date formats "
                    "are ambiguous and cannot be parsed without "
                    "an explicit locale rule."
                )
            elif any(s == "invalid_range" for s in relevant_statuses):
                diagnostic_status = "invalid_date_range"
                diagnostic_message = (
                    "Relevant experience found, but end date is earlier "
                    "than start date."
                )
            else:
                diagnostic_status = "dates_missing_or_unparseable"
                diagnostic_message = (
                    "Relevant experience found, but dates are missing "
                    "or in an unparseable format."
                )

        # --------------------------------------------------
        # RETURN
        # --------------------------------------------------
        return {
            "experience_requirements": {
                "minimum_years": requirements["minimum_years"],
                "maximum_years": requirements["maximum_years"],
                "preferred_domains": requirements["preferred_domains"],
            },
            "experience_requirement_present": experience_requirement_present,
            "experiences": experience_results,
            "relevant_experience_found": relevant_experience_found,
            "relevant_duration_years": round(relevant_duration_years, 2),
            "duration_factor": duration_factor,
            "saturation_target_years": saturation_target,
            "range_status": range_status,
            "diagnostic_status": diagnostic_status,
            "diagnostic_message": diagnostic_message,
            "minimum_years": requirements["minimum_years"],
            "maximum_years": requirements["maximum_years"],
            "minimum_duration_satisfied": duration_result[
                "minimum_duration_satisfied"
            ],
            "maximum_duration_exceeded": duration_result[
                "maximum_duration_exceeded"
            ],
            "aggregated_similarity": aggregated_similarity,
            "experience_score": 0.0,
        }


# ------------------------------------------------------
# SERVICE INSTANCE
# ------------------------------------------------------

experience_matching_service = ExperienceMatchingService()
