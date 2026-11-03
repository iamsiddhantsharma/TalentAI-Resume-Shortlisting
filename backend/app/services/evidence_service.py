from app.schemas.resume_object import ResumeObject
from app.schemas.job_description import JobDescriptionObject


class EvidenceService:
    """
    Converts structured Resume and Job Description objects
    into semantic evidence units.

    Each evidence unit keeps:
    - source_type
    - section
    - item_index
    - text

    The text will later be converted into a 1024-dimensional
    embedding using BGE-large-en-v1.5.
    """

    # ==========================================================
    # RESUME EVIDENCE
    # ==========================================================

    def build_resume_evidence(
        self,
        resume: ResumeObject,
    ) -> list[dict]:
        """
        Convert a structured resume into semantic evidence units.
        """

        evidence = []

        # ------------------------------------------------------
        # SKILLS
        # ------------------------------------------------------

        for index, skill in enumerate(resume.skills):

            if skill and skill.strip():
                evidence.append(
                    {
                        "source_type": "resume",
                        "section": "skills",
                        "item_index": index,
                        "text": f"Skill: {skill.strip()}",
                    }
                )

        # ------------------------------------------------------
        # PROJECTS
        # ------------------------------------------------------

        for index, project in enumerate(resume.projects):

            project_name = project.name or "Unnamed project"
            description = project.description or ""

            technologies = [
                tech.strip()
                for tech in project.technologies
                if tech and tech.strip()
            ]

            text_parts = [
                f"Project: {project_name.strip()}",
            ]

            if description.strip():
                text_parts.append(
                    f"Description: {description.strip()}"
                )

            if technologies:
                text_parts.append(
                    f"Technologies: {', '.join(technologies)}"
                )

            evidence.append(
                {
                    "source_type": "resume",
                    "section": "projects",
                    "item_index": index,
                    "text": " | ".join(text_parts),
                }
            )

        # ------------------------------------------------------
        # EXPERIENCE
        # ------------------------------------------------------

        for index, experience in enumerate(resume.experience):

            role = experience.role or ""
            company = experience.company or ""
            description = experience.description or ""

            text_parts = []

            if role.strip():
                text_parts.append(
                    f"Role: {role.strip()}"
                )

            if company.strip():
                text_parts.append(
                    f"Company: {company.strip()}"
                )

            if description.strip():
                text_parts.append(
                    f"Work: {description.strip()}"
                )

            if text_parts:
                evidence.append(
                    {
                        "source_type": "resume",
                        "section": "experience",
                        "item_index": index,
                        "text": " | ".join(text_parts),
                    }
                )

        # ------------------------------------------------------
        # EDUCATION
        # ------------------------------------------------------

        for index, education in enumerate(resume.education):

            text_parts = []

            if education.degree:
                text_parts.append(
                    f"Degree: {education.degree.strip()}"
                )

            if education.field_of_study:
                text_parts.append(
                    f"Field: {education.field_of_study.strip()}"
                )

            if education.institution:
                text_parts.append(
                    f"Institution: {education.institution.strip()}"
                )

            if text_parts:
                evidence.append(
                    {
                        "source_type": "resume",
                        "section": "education",
                        "item_index": index,
                        "text": " | ".join(text_parts),
                    }
                )

        # ------------------------------------------------------
        # CERTIFICATIONS
        # ------------------------------------------------------

        for index, certification in enumerate(
            resume.certifications
        ):

            text_parts = []

            if certification.name:
                text_parts.append(
                    f"Certification: "
                    f"{certification.name.strip()}"
                )

            if certification.issuing_organization:
                text_parts.append(
                    f"Issued by: "
                    f"{certification.issuing_organization.strip()}"
                )

            if text_parts:
                evidence.append(
                    {
                        "source_type": "resume",
                        "section": "certifications",
                        "item_index": index,
                        "text": " | ".join(text_parts),
                    }
                )

        # ------------------------------------------------------
        # ACHIEVEMENTS
        # ------------------------------------------------------

        for index, achievement in enumerate(
            resume.achievements
        ):

            if achievement and achievement.strip():
                evidence.append(
                    {
                        "source_type": "resume",
                        "section": "achievements",
                        "item_index": index,
                        "text": (
                            f"Achievement: "
                            f"{achievement.strip()}"
                        ),
                    }
                )

        return evidence

    # ==========================================================
    # JOB DESCRIPTION EVIDENCE
    # ==========================================================

    def build_jd_evidence(
        self,
        job_description: JobDescriptionObject,
    ) -> list[dict]:
        """
        Convert a structured Job Description into semantic
        evidence units.
        """

        evidence = []

        # ------------------------------------------------------
        # REQUIRED SKILLS
        # ------------------------------------------------------

        for index, skill in enumerate(
            job_description.required_skills
        ):

            if skill and skill.strip():
                evidence.append(
                    {
                        "source_type": "job_description",
                        "section": "required_skills",
                        "item_index": index,
                        "text": (
                            f"Required skill: "
                            f"{skill.strip()}"
                        ),
                    }
                )

        # ------------------------------------------------------
        # RESPONSIBILITIES
        # ------------------------------------------------------

        for index, responsibility in enumerate(
            job_description.responsibilities
        ):

            if responsibility and responsibility.strip():
                evidence.append(
                    {
                        "source_type": "job_description",
                        "section": "responsibilities",
                        "item_index": index,
                        "text": (
                            f"Responsibility: "
                            f"{responsibility.strip()}"
                        ),
                    }
                )

        # ------------------------------------------------------
        # EXPERIENCE REQUIREMENTS
        # ------------------------------------------------------

        for index, requirement in enumerate(
            job_description.experience_requirements
        ):

            text_parts = []

            if requirement.minimum_years is not None:
                text_parts.append(
                    f"Minimum experience: "
                    f"{requirement.minimum_years} years"
                )

            if requirement.maximum_years is not None:
                text_parts.append(
                    f"Maximum experience: "
                    f"{requirement.maximum_years} years"
                )

            if requirement.preferred_domains:

                domains = [
                    domain.strip()
                    for domain in requirement.preferred_domains
                    if domain and domain.strip()
                ]

                if domains:
                    text_parts.append(
                        "Preferred domains: "
                        + ", ".join(domains)
                    )

            if text_parts:
                evidence.append(
                    {
                        "source_type": "job_description",
                        "section": "experience_requirements",
                        "item_index": index,
                        "text": " | ".join(text_parts),
                    }
                )

        # ------------------------------------------------------
        # TOOLS AND TECHNOLOGIES
        # ------------------------------------------------------

        for index, tool in enumerate(
            job_description.tools_and_technologies
        ):

            if tool and tool.strip():
                evidence.append(
                    {
                        "source_type": "job_description",
                        "section": "tools_and_technologies",
                        "item_index": index,
                        "text": (
                            f"Tool or technology: "
                            f"{tool.strip()}"
                        ),
                    }
                )

        return evidence


evidence_service = EvidenceService()
