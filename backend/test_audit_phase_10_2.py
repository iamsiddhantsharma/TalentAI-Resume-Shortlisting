"""
TalentAI Phase 10.2: Section-Routing Explainability & Evidence Integrity Audit Runner

Executes comprehensive positive, negative, and edge-case tests against:
1. backend/app/ranking/ranking_service.py (tool-mention detection, score stability, schema integrity)
2. Evidence grounding across section routing
3. Punctuation, casing, word boundary, and incidental mentions
4. Missing, malformed, and technical failure states
"""

import sys
import unittest
from app.ranking.ranking_service import RankingEngine
from app.schemas.job_description_object import JobDescriptionObject
from app.schemas.matching import (
    CandidateExperienceItem,
    ExactMatchingResult,
    ExactSkillMatchItem,
    ExperienceMatchingResult,
    ExperienceRequirementSummary,
    ResumeMatchResult,
    SemanticRetrievalRequirementResult,
    SemanticRetrievalResult,
    SemanticSectionRetrieval,
    SemanticEvidenceMatchItem,
)
from app.ranking.ranking_schemas import CategoryScoreBreakdown


class TestPhase102ExplainabilityAudit(unittest.TestCase):
    def setUp(self):
        self.engine = RankingEngine()
        self.jd = JobDescriptionObject(
            required_skills=["Python", "FastAPI"],
            responsibilities=["Build microservices", "Database optimization"],
            tools_and_technologies=["Docker", "PostgreSQL", "Kubernetes"],
            experience_requirements=[],
        )

    # --------------------------------------------------------------------------
    # CHECK 1 & 2: Active JD Relevance & Positive Detection
    # --------------------------------------------------------------------------
    def test_positive_tool_in_relevant_employment_description(self):
        """Tool mentioned in relevant employment description, absent from projects."""
        exp = [
            CandidateExperienceItem(
                experience_index=0,
                role="Senior Backend Engineer",
                company="CloudTech",
                description="Engineered containerized microservices using Docker and managed PostgreSQL clusters.",
                relevant=True,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=self.jd.tools_and_technologies,
            candidate_experiences=exp,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(qual, 0)
        self.assertEqual(note, "Tools mentioned in employment history but not in project portfolio.")

    def test_negative_tool_absent_everywhere(self):
        """Candidate has employment history, but mentions no JD tools."""
        exp = [
            CandidateExperienceItem(
                experience_index=0,
                role="UI Designer",
                company="CreativeStudio",
                description="Designed wireframes, Figma components, and user experience flows.",
                relevant=True,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=self.jd.tools_and_technologies,
            candidate_experiences=exp,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(qual, 0)
        self.assertEqual(note, "No qualifying project evidence found for defined tools and technologies.")

    def test_negative_irrelevant_tool_not_in_jd(self):
        """Candidate mentions tools in employment (e.g., Redis, MongoDB), but none match active JD."""
        exp = [
            CandidateExperienceItem(
                experience_index=0,
                role="Backend Engineer",
                company="DataCorp",
                description="Implemented caching layers with Redis and document storage in MongoDB.",
                relevant=True,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=self.jd.tools_and_technologies,
            candidate_experiences=exp,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(qual, 0)
        # Redis and MongoDB are not in JD (Docker, PostgreSQL, Kubernetes) -> Must NOT trigger callout!
        self.assertEqual(note, "No qualifying project evidence found for defined tools and technologies.")

    # --------------------------------------------------------------------------
    # CHECK 3: Project Evidence vs Experience Distinction
    # --------------------------------------------------------------------------
    def test_tool_supported_by_qualifying_project_evidence(self):
        """Tool supported by qualifying project evidence -> score > 0, note is None."""
        retrieval = {
            "tools_and_technologies_retrieval": {
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Docker",
                        "matches": [
                            {"resume_section": "projects", "similarity": 0.85, "resume_text": "Built Docker images"}
                        ],
                    }
                ]
            }
        }
        exp = [
            CandidateExperienceItem(
                experience_index=0,
                role="Backend Engineer",
                company="CloudCorp",
                description="Used Docker in production.",
                relevant=True,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data=retrieval,
            jd_tools=self.jd.tools_and_technologies,
            candidate_experiences=exp,
        )
        self.assertGreater(score, 0.0)
        self.assertGreater(qual, 0)
        self.assertIsNone(note)

    # --------------------------------------------------------------------------
    # CHECK 4: Casing, Punctuation, Word Boundaries & Edge Cases
    # --------------------------------------------------------------------------
    def test_case_variations(self):
        """Case variations (uppercase, lowercase, mixed case) must be detected."""
        for case_variant in ["DOCKER", "docker", "dOcKeR", "POSTGRESQL", "postgresql", "PoStGrEsQl"]:
            exp = [
                CandidateExperienceItem(
                    experience_index=0,
                    role="Dev",
                    company="Co",
                    description=f"Extensive use of {case_variant} in microservices architecture.",
                    relevant=True,
                )
            ]
            score, status, total, qual, evid, note = self.engine.calculate_tools_score(
                retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
                jd_tools=self.jd.tools_and_technologies,
                candidate_experiences=exp,
            )
            self.assertEqual(
                note,
                "Tools mentioned in employment history but not in project portfolio.",
                f"Failed to detect case variant: {case_variant}",
            )

    def test_punctuation_boundaries(self):
        """Punctuation variations (period, comma, parentheses, quotes, slash, hyphen)."""
        variations = [
            "Deployed services using Docker.",
            "Technologies include Docker, Linux, and Nginx.",
            "Managed clusters with Docker; ensured 99.9% SLA.",
            "Containerization platform (Docker) was utilized.",
            "Experienced with 'Docker' containers.",
            'Configured "Docker" daemon.',
            "Built CI/CD pipeline using Docker/Kubernetes.",
            "Developed Docker-based environments.",
            "Container stack:\n- Docker\n- PostgreSQL",
        ]
        for text in variations:
            exp = [CandidateExperienceItem(experience_index=0, role="Dev", company="Co", description=text, relevant=True)]
            score, status, total, qual, evid, note = self.engine.calculate_tools_score(
                retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
                jd_tools=self.jd.tools_and_technologies,
                candidate_experiences=exp,
            )
            self.assertEqual(
                note,
                "Tools mentioned in employment history but not in project portfolio.",
                f"Failed punctuation boundary test on: {text}",
            )

    def test_special_characters_cpp_csharp_dotnet(self):
        """Test special character programming languages and tools: C++, C#, .NET."""
        jd_spec = JobDescriptionObject(
            required_skills=["Coding"],
            responsibilities=["Dev"],
            tools_and_technologies=["C++", "C#", ".NET"],
            experience_requirements=[],
        )
        exp = [
            CandidateExperienceItem(
                experience_index=0,
                role="Systems Architect",
                company="HFT Corp",
                description="Engineered low-latency engines in C++ and C# targeting .NET Core.",
                relevant=True,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=jd_spec.tools_and_technologies,
            candidate_experiences=exp,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(qual, 0)
        self.assertEqual(note, "Tools mentioned in employment history but not in project portfolio.")

    def test_nodejs_c_and_r_boundary_detection(self):
        """Verify Node.js, C, and R in valid technical contexts trigger the callout."""
        jd_tech = JobDescriptionObject(
            required_skills=["Software Engineering"],
            responsibilities=["Development"],
            tools_and_technologies=["Node.js", "C", "R"],
            experience_requirements=[],
        )
        exp_valid = [
            CandidateExperienceItem(
                experience_index=0,
                role="Full Stack & Embedded Engineer",
                company="TechCorp",
                description="Built microservices in Node.js, developed embedded drivers in ANSI C, and created statistical models in R language.",
                relevant=True,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=jd_tech.tools_and_technologies,
            candidate_experiences=exp_valid,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(qual, 0)
        self.assertEqual(note, "Tools mentioned in employment history but not in project portfolio.")

    def test_nodejs_c_and_r_negative_nontechnical_mentions(self):
        """Verify unrelated uses of letter C, R, and fragments do not trigger false positives."""
        jd_tech = JobDescriptionObject(
            required_skills=["Software Engineering"],
            responsibilities=["Development"],
            tools_and_technologies=["Node.js", "C", "R"],
            experience_requirements=[],
        )
        exp_unrelated = [
            CandidateExperienceItem(
                experience_index=0,
                role="Operations Coordinator",
                company="LogisticsHub",
                description="Assigned desks in Building C, monitored R&D budget schedules, and noted js errors in third-party vendor portal.",
                relevant=False,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=jd_tech.tools_and_technologies,
            candidate_experiences=exp_unrelated,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(qual, 0)
        self.assertEqual(note, "No qualifying project evidence found for defined tools and technologies.")

    def test_incidental_english_word_mention(self):
        """Sentence uses 'go' and 'spring' as ordinary English words -> Must NOT trigger callout."""
        jd_words = JobDescriptionObject(
            required_skills=["Python"],
            responsibilities=["Dev"],
            tools_and_technologies=["Go", "Spring"],
            experience_requirements=[],
        )
        exp_incidental = [
            CandidateExperienceItem(
                experience_index=0,
                role="Marketing Specialist",
                company="RetailStore",
                description="Helped the team go to conferences in Spring 2022 to boost sales.",
                relevant=False,
            )
        ]
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=jd_words.tools_and_technologies,
            candidate_experiences=exp_incidental,
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(qual, 0)
        self.assertEqual(note, "No qualifying project evidence found for defined tools and technologies.")

    def test_ambiguous_words_positive_technical_contexts(self):
        """Technical contexts for Go, Spring, Spark, Chef, and Ant correctly trigger callout."""
        jd_tools = JobDescriptionObject(
            required_skills=["DevOps"],
            responsibilities=["Infrastructure"],
            tools_and_technologies=["Go", "Spring", "Spark", "Chef", "Ant"],
            experience_requirements=[],
        )
        test_cases = [
            ("Developed backend services in Go.", "Go"),
            ("Built enterprise web applications using Spring Boot.", "Spring"),
            ("Orchestrated big data pipelines using Apache Spark.", "Spark"),
            ("Automated infrastructure provisioning using Chef cookbooks.", "Chef"),
            ("Maintained legacy compilation workflows using Apache Ant.", "Ant"),
        ]
        for desc, tool_name in test_cases:
            exp = [
                CandidateExperienceItem(
                    experience_index=0,
                    role="Software Developer",
                    company="Tech Corp",
                    description=desc,
                    relevant=True,
                )
            ]
            score, status, total, qual, evid, note = self.engine.calculate_tools_score(
                retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
                jd_tools=[tool_name],
                candidate_experiences=exp,
            )
            self.assertEqual(
                note,
                "Tools mentioned in employment history but not in project portfolio.",
                f"Failed for technical context of {tool_name}: '{desc}'",
            )

    def test_ambiguous_words_negative_ordinary_contexts(self):
        """Ordinary English uses for Chef, Ant, and Spark do not trigger callout."""
        jd_tools = JobDescriptionObject(
            required_skills=["Hospitality"],
            responsibilities=["General"],
            tools_and_technologies=["Chef", "Ant", "Spark"],
            experience_requirements=[],
        )
        negative_cases = [
            "Worked as executive chef at a downtown bistro preparing French cuisine.",
            "Conducted entomology fieldwork studying an ant colony ecosystem.",
            "Brought a creative spark and enthusiastic energy to corporate team offsites.",
        ]
        for desc in negative_cases:
            exp = [
                CandidateExperienceItem(
                    experience_index=0,
                    role="General Associate",
                    company="Various",
                    description=desc,
                    relevant=False,
                )
            ]
            score, status, total, qual, evid, note = self.engine.calculate_tools_score(
                retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
                jd_tools=jd_tools.tools_and_technologies,
                candidate_experiences=exp,
            )
            self.assertEqual(
                note,
                "No qualifying project evidence found for defined tools and technologies.",
                f"False positive triggered for ordinary context: '{desc}'",
            )

    def test_filename_heuristic_leakage_defect(self):
        """A file named 'candidate_tools_in_exp_portfolio.pdf' with zero tools anywhere does not trigger the callout."""
        match_data = ResumeMatchResult(
            upload_id="batch_audit",
            filename="candidate_tools_in_exp_portfolio.pdf",
            jd_id="jd_audit",
            exact_matching=ExactMatchingResult(
                total_required_skills=2,
                matched_required_skills=0,
                unmatched_required_skills=2,
                matches=[],
                status="complete",
            ),
            semantic_retrieval=SemanticRetrievalResult(
                responsibilities_retrieval=SemanticSectionRetrieval(top_k=5, results=[]),
                tools_and_technologies_retrieval=SemanticSectionRetrieval(top_k=5, results=[]),
                status="complete",
            ),
            experience_matching=ExperienceMatchingResult(
                status="complete",
                relevant_duration_years=1.0,
                minimum_duration_satisfied=False,
                experiences=[
                    CandidateExperienceItem(
                        experience_index=0,
                        role="Receptionist",
                        company="FrontDesk Inc",
                        description="Answered phones and scheduled appointments.",
                        relevant=False,
                    )
                ],
            ),
        )
        ranked = self.engine.score_candidate(match_data, self.jd)
        self.assertEqual(
            ranked.breakdown["tools_and_technologies"].notes,
            "No qualifying project evidence found for defined tools and technologies.",
        )

    # --------------------------------------------------------------------------
    # CHECK 3 & 4: Incomplete, Missing, and Malformed Evidence
    # --------------------------------------------------------------------------
    def test_empty_tools_in_jd(self):
        """JD defines no tools -> status is not_applicable, score is None."""
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=[],
            candidate_experiences=[],
        )
        self.assertIsNone(score)
        self.assertEqual(status, "not_applicable")
        self.assertEqual(note, "Job Description defines no tools and technologies requirements.")

    def test_retrieval_failure_propagation(self):
        """Technical retrieval service failure -> status unavailable, candidate marked incomplete."""
        retrieval_failed = {
            "tools_and_technologies_retrieval": {
                "status": "failed",
                "error": "Qdrant connection timeout",
                "results": [],
            }
        }
        score, status, total, qual, evid, note = self.engine.calculate_tools_score(
            retrieval_data=retrieval_failed,
            jd_tools=self.jd.tools_and_technologies,
            candidate_experiences=[],
        )
        self.assertIsNone(score)
        self.assertEqual(status, "unavailable")
        self.assertIn("failed", note)
        # Callout must NOT appear when category is unavailable!
        self.assertNotEqual(note, "Tools mentioned in employment history but not in project portfolio.")

    def test_none_experiences_and_malformed_items(self):
        """Handles None experiences and experience items missing fields gracefully."""
        # candidate_experiences is None
        score1, _, _, _, _, note1 = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=self.jd.tools_and_technologies,
            candidate_experiences=None,
        )
        self.assertEqual(note1, "No qualifying project evidence found for defined tools and technologies.")

        # candidate_experiences contains malformed dicts or objects with None attributes
        exp_malformed = [
            {"role": None, "company": None, "description": None},
            CandidateExperienceItem(experience_index=0, role=None, company=None, description=None, relevant=False),
        ]
        score2, _, _, _, _, note2 = self.engine.calculate_tools_score(
            retrieval_data={"tools_and_technologies_retrieval": {"results": []}},
            jd_tools=self.jd.tools_and_technologies,
            candidate_experiences=exp_malformed,
        )
        self.assertEqual(note2, "No qualifying project evidence found for defined tools and technologies.")

    # --------------------------------------------------------------------------
    # CHECK 6 & 7: Score Invariance & Schema Integrity
    # --------------------------------------------------------------------------
    def test_score_and_weight_invariance(self):
        """Zero tools score (0.0) and final score calculation remain mathematically identical."""
        match_data = ResumeMatchResult(
            upload_id="batch_audit",
            filename="cand_audit_tools_exp.pdf",
            jd_id="jd_audit",
            exact_matching=ExactMatchingResult(
                total_required_skills=2,
                matched_required_skills=2,
                unmatched_required_skills=0,
                matches=[
                    ExactSkillMatchItem(required_skill="Python", matched=True, match_type="exact"),
                    ExactSkillMatchItem(required_skill="FastAPI", matched=True, match_type="exact"),
                ],
                status="complete",
            ),
            semantic_retrieval=SemanticRetrievalResult(
                responsibilities_retrieval=SemanticSectionRetrieval(
                    top_k=5,
                    results=[
                        SemanticRetrievalRequirementResult(
                            jd_section="responsibilities",
                            jd_item_index=0,
                            jd_text="Build microservices",
                            matches=[
                                SemanticEvidenceMatchItem(
                                    jd_section="responsibilities",
                                    jd_item_index=0,
                                    jd_text="Build microservices",
                                    resume_section="experience",
                                    resume_text="Built microservices",
                                    similarity=0.85,
                                )
                            ],
                        )
                    ],
                ),
                tools_and_technologies_retrieval=SemanticSectionRetrieval(top_k=5, results=[]),
                status="complete",
            ),
            experience_matching=ExperienceMatchingResult(
                status="complete",
                relevant_duration_years=4.0,
                minimum_duration_satisfied=True,
                experiences=[
                    CandidateExperienceItem(
                        experience_index=0,
                        role="Backend Lead",
                        company="Acme Corp",
                        description="Used Docker and PostgreSQL in production.",
                        relevant=True,
                    )
                ],
            ),
        )

        ranked = self.engine.score_candidate(match_data, self.jd)

        # 1. Candidate must be complete
        self.assertEqual(ranked.status, "complete")
        # 2. Tools component score must be strictly 0.0
        self.assertEqual(ranked.component_scores["tools_and_technologies"], 0.0)
        # 3. CategoryScoreBreakdown.score must be 0.0
        self.assertEqual(ranked.breakdown["tools_and_technologies"].score, 0.0)
        # 4. Qualifying count must be strictly 0
        self.assertEqual(ranked.breakdown["tools_and_technologies"].qualifying_criteria_count, 0)
        # 5. Notes must deliver the exact explainability message
        self.assertEqual(
            ranked.breakdown["tools_and_technologies"].notes,
            "Tools mentioned in employment history but not in project portfolio.",
        )
        # 6. Verify CategoryScoreBreakdown Pydantic schema validation (extra='forbid')
        breakdown_dump = ranked.breakdown["tools_and_technologies"].model_dump()
        reconstructed = CategoryScoreBreakdown(**breakdown_dump)
        self.assertEqual(reconstructed.notes, "Tools mentioned in employment history but not in project portfolio.")
        # 7. Final score calculation:
        # Skills: 100 * 0.25 = 25.0
        # Responsibilities: (0.85 - 0.65)/(1 - 0.65) * 100 / 2 = 57.14 / 2 = 28.57 * 0.30 = 8.57
        # Tools: 0.0 * 0.10 = 0.0
        # Experience: 0.0 (no preferred domains matched) * 0.35 = 0.0
        # Final score strictly does NOT award points for tools!
        self.assertEqual(ranked.breakdown["tools_and_technologies"].weighted_contribution, 0.0)


if __name__ == "__main__":
    unittest.main()
