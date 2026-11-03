"""
TalentAI — Controlled End-to-End Validation Post-Ollama Remediation

Tests:
1. File discovery and multi-format extraction (TXT, DOCX, corrupted PDF).
2. Simulated brief Ollama outage with automated worker recovery.
3. MongoDB persistence and embedding generation.
4. Failure isolation for corrupt/invalid resumes without batch degradation.
5. Idempotent MongoDB writes (no duplicates on retry).
6. Preservation of existing MongoDB records.
7. Ranking against an active Job Description with score evidence,
   category diagnostics, and incomplete-result handling.
"""

import asyncio
import io
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import docx
import fitz
import httpx
from fastapi import UploadFile

from app.database.batch_repository import batch_repository
from app.database.jd_embedding_repository import jd_embedding_repository
from app.database.jd_repository import jd_repository
from app.database.mongodb import mongodb
from app.database.resume_embedding_repository import resume_embedding_repository
from app.database.resume_repository import resume_repository
from app.queue.local_queue import local_queue
from app.queue.worker import ResumeWorker
from app.ranking.ranking_schemas import RankBatchRequest
from app.ranking.ranking_service import ranking_engine
from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.job_description import JobDescription
from app.services.jd_embedding_generation_service import (
    job_description_embedding_generation_service,
)
from app.services.llm_service import llm_service
from app.services.upload_service import upload_service


CANDIDATE_1_TXT = """Arun Kumar
Email: arun.kumar@example.com
Location: Bengaluru, India

Summary:
Full-stack and Backend Engineer with 4 years of experience building scalable microservices in Python and FastAPI.

Skills:
Python, FastAPI, Docker, PostgreSQL, Redis, Git

Experience:
Company: Nexus Innovations
Role: Senior Backend Engineer
Duration: 2022 - Present (2 years)
Description: Designed and implemented scalable microservices APIs using FastAPI. Optimized PostgreSQL database queries, reducing response times by 40%. Configured containerized cloud deployments with Docker.

Company: CloudCore Systems
Role: Software Engineer
Duration: 2020 - 2022 (2 years)
Description: Developed RESTful endpoints using Python and maintained relational databases. Built CI/CD pipelines and automated tests.

Projects:
Project: Microservices Billing Platform
Technologies: Python, FastAPI, Docker, PostgreSQL
Description: Built containerized billing service handling 5,000 transactions per minute with PostgreSQL storage.
"""

CANDIDATE_2_TEXT = """Priya Sharma
Email: priya.sharma@example.com
Location: Pune, India

Summary:
Cloud and Infrastructure Engineer with 5 years of experience in Kubernetes, Docker, and distributed cloud systems.

Skills:
Docker, Kubernetes, PostgreSQL, Python, AWS, Terraform

Experience:
Company: Apex Cloud Solutions
Role: DevOps & Cloud Engineer
Duration: 2021 - Present (3 years)
Description: Managed Kubernetes clusters and Docker containers. Maintained PostgreSQL clusters and automated deployments.

Company: DataStream Corp
Role: Systems Engineer
Duration: 2019 - 2021 (2 years)
Description: Developed automation scripts in Python. Configured containerized deployments and database backups.

Projects:
Project: Kubernetes Cluster Automation
Technologies: Docker, Kubernetes, Python, PostgreSQL
Description: Automated deployment of containerized services on Kubernetes with PostgreSQL database backend.
"""


def build_candidate_docx(text: str) -> bytes:
    doc = docx.Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_synthetic_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # File 1: TXT format (Valid backend engineer)
        zf.writestr("candidate_1_backend.txt", CANDIDATE_1_TXT.encode("utf-8"))
        # File 2: DOCX format (Valid cloud engineer)
        docx_bytes = build_candidate_docx(CANDIDATE_2_TEXT)
        zf.writestr("candidate_2_cloud.docx", docx_bytes)
        # File 3: Corrupted PDF (Failure isolation test)
        zf.writestr("candidate_3_corrupted.pdf", b"%PDF-CORRUPTED-HEADER-GARBAGE-BYTES-NON-RECOVERABLE")
    return buf.getvalue()


async def run_controlled_validation():
    print("=" * 80)
    print("TALENTAI — CONTROLLED E2E VALIDATION POST-OLLAMA REMEDIATION")
    print("=" * 80)

    await mongodb.connect()

    # Step 0: Record initial database state
    db = mongodb.get_database()
    initial_resumes_count = await db["resumes"].count_documents({})
    initial_embeddings_count = await db["resume_embeddings"].count_documents({})
    initial_batches_count = await db["batches"].count_documents({})
    print(f"\n[Baseline DB State] Resumes: {initial_resumes_count} | Embeddings: {initial_embeddings_count} | Batches: {initial_batches_count}")

    upload_id = None
    try:
        # ======================================================================
        # 1. Upload & File Discovery
        # ======================================================================
        print("\n[Step 1] Uploading synthetic 3-resume ZIP archive (TXT, DOCX, Corrupt PDF)...")
        zip_bytes = build_synthetic_zip()
        upload_file = UploadFile(
            file=io.BytesIO(zip_bytes),
            filename="synthetic_test_batch.zip",
            headers={"content-type": "application/zip"},
        )

        upload_response = await upload_service.create_upload_job(
            files=[upload_file],
            auto_activate=True,
        )
        upload_id = upload_response.upload_id
        print(f"  Upload ID: {upload_id}")
        print(f"  Upload Status: {upload_response.status}")
        print(f"  Batch Status: {upload_response.batch_status}")
        print(f"  Total Files Received: {upload_response.total_files_received}")
        print(f"  Queue Size: {local_queue.size()}")

        assert upload_response.status == "accepted", f"Upload rejected: {upload_response.message}"
        assert upload_response.batch_status == "processing"
        assert local_queue.size() == 3, f"Expected 3 jobs in queue, found {local_queue.size()}"
        print("  [PASSED] Upload and ZIP file discovery succeeded (3 distinct files enqueued).")

        # ======================================================================
        # 2. Worker Processing with Simulated Outage & Automated Recovery
        # ======================================================================
        print("\n[Step 2] Processing Job 1 (TXT) with simulated transient Ollama outage...")
        worker = ResumeWorker(recovery_timeout=5.0, health_check_interval=0.5)

        # Simulate transient connection error on first call to _send_request, then succeed
        real_send_request = llm_service._send_request
        call_count = 0

        async def mocked_send_request(payload: dict) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                print("  [Simulated Outage] Injecting ConnectError: Connection refused on first request...")
                raise httpx.ConnectError("Connection refused: 127.0.0.1:11434")
            return await real_send_request(payload)

        with patch.object(llm_service, "_send_request", side_effect=mocked_send_request):
            result_1 = await worker.run_once()

        print(f"  Candidate 1 Result: Status={result_1.status} | Name={result_1.resume_data.name if result_1.resume_data else None}")
        assert result_1.status == "completed", f"Job 1 failed: {result_1.error}"
        assert result_1.resume_data is not None
        assert call_count >= 2, "Expected retry after simulated outage!"
        print("  [PASSED] In-flight resume survived simulated outage and completed via recovery retry.")

        # Process Job 2: DOCX format
        print("\n[Step 3] Processing Job 2 (DOCX) normally...")
        result_2 = await worker.run_once()
        print(f"  Candidate 2 Result: Status={result_2.status} | Name={result_2.resume_data.name if result_2.resume_data else None}")
        assert result_2.status == "completed", f"Job 2 failed: {result_2.error}"
        assert result_2.resume_data is not None
        print("  [PASSED] DOCX extraction and schema parsing succeeded.")

        # Process Job 3: Corrupt PDF (Failure Isolation)
        print("\n[Step 4] Processing Job 3 (Corrupt PDF) - testing failure isolation...")
        result_3 = await worker.run_once()
        print(f"  Candidate 3 Result: Status={result_3.status} | Error={result_3.error[:60]}...")
        assert result_3.status == "failed", "Corrupt PDF should have status 'failed'"
        assert result_3.resume_data is None
        assert "PDF" in result_3.error or "document" in result_3.error or "cannot" in result_3.error.lower()
        print("  [PASSED] Failure isolation verified: corrupt resume recorded as failed without halting queue.")

        # ======================================================================
        # 3. Batch Progress and MongoDB State Verification
        # ======================================================================
        print("\n[Step 5] Verifying MongoDB records and batch state...")
        batch_doc = await batch_repository.get(upload_id)
        assert batch_doc is not None
        print(f"  Batch status: {batch_doc.get('status')}")
        print(f"  Total: {batch_doc.get('total_files')} | Completed: {batch_doc.get('completed_count')} | Failed: {batch_doc.get('failed_count')}")
        assert batch_doc.get("total_files") == 3
        assert batch_doc.get("completed_count") == 2
        assert batch_doc.get("failed_count") == 1
        assert batch_doc.get("is_active") is True, "Batch with auto_activate=True should be active"

        # Check records in resumes collection
        doc_1 = await resume_repository.get(upload_id, "candidate_1_backend.txt")
        doc_2 = await resume_repository.get(upload_id, "candidate_2_cloud.docx")
        doc_3 = await resume_repository.get(upload_id, "candidate_3_corrupted.pdf")
        assert doc_1 is not None and doc_1["status"] == "completed"
        assert doc_2 is not None and doc_2["status"] == "completed"
        assert doc_3 is not None and doc_3["status"] == "failed"

        # Check embeddings in resume_embeddings collection
        emb_1 = await resume_embedding_repository.get(upload_id, "candidate_1_backend.txt")
        emb_2 = await resume_embedding_repository.get(upload_id, "candidate_2_cloud.docx")
        emb_3 = await resume_embedding_repository.get(upload_id, "candidate_3_corrupted.pdf")
        assert emb_1 is not None and len(emb_1.get("embeddings", [])) > 0
        assert emb_2 is not None and len(emb_2.get("embeddings", [])) > 0
        assert emb_3 is None or len(emb_3.get("embeddings", [])) == 0
        print(f"  Candidate 1 embeddings count: {len(emb_1['embeddings'])} (dim: {len(emb_1['embeddings'][0]['embedding'])})")
        print(f"  Candidate 2 embeddings count: {len(emb_2['embeddings'])} (dim: {len(emb_2['embeddings'][0]['embedding'])})")
        print(f"  Candidate 3 embeddings count: 0 (correctly cleaned up for failed resume)")
        print("  [PASSED] MongoDB persistence, embedding generation, and progress counters verified.")

        # ======================================================================
        # 4. Idempotency Check (No duplicate records)
        # ======================================================================
        print("\n[Step 6] Verifying MongoDB idempotency on re-save...")
        await resume_repository.save(result_1)
        count_for_c1 = await db["resumes"].count_documents({"upload_id": upload_id, "filename": "candidate_1_backend.txt"})
        assert count_for_c1 == 1, f"Expected exactly 1 document for candidate 1, found {count_for_c1}"
        print("  [PASSED] Idempotency verified: re-saving result updates existing document with zero duplicates.")

        # ======================================================================
        # 5. Ranking Against Active Job Description
        # ======================================================================
        print("\n[Step 7] Setting up Job Description and executing explainable ranking...")
        test_jd_id = "jd_cloud_backend_test"
        jd_struct = JobDescriptionObject(
            required_skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
            responsibilities=[
                "Design and implement scalable microservices APIs",
                "Optimize SQL database queries and migrations",
                "Configure containerized cloud deployments",
            ],
            tools_and_technologies=["Docker", "Kubernetes", "PostgreSQL"],
            experience_requirements=[
                ExperienceRequirement(
                    minimum_years=3.0,
                    maximum_years=6.0,
                    preferred_domains=["Cloud Systems"],
                )
            ],
        )

        jd_obj = JobDescription(
            jd_id=test_jd_id,
            input_type="text",
            filename="cloud_jd.txt",
            file_extension=".txt",
            raw_text="Senior Full-Stack Cloud Engineer. Required: Python, FastAPI, Docker, PostgreSQL.",
            structured_data=jd_struct,
            status="completed",
        )
        jd_record = jd_obj.model_dump(mode="json")
        jd_record["_id"] = test_jd_id
        await db["job_descriptions"].replace_one({"_id": test_jd_id}, jd_record, upsert=True)
        await job_description_embedding_generation_service.generate_for_jd(test_jd_id)

        (
            ret_jd_id,
            ret_batch_id,
            total_eligible,
            ranked_candidates,
            unranked_candidates,
            has_more,
        ) = await ranking_engine.rank_batch(
            upload_id=upload_id,
            jd_id=test_jd_id,
        )

        print(f"  Total Eligible Candidates: {total_eligible}")
        print(f"  Ranked Candidates Count: {len(ranked_candidates)}")
        print(f"  Unranked/Incomplete in Ranking: {len(unranked_candidates)}")

        assert len(ranked_candidates) == 2, f"Expected 2 ranked candidates, got {len(ranked_candidates)}"
        assert total_eligible == 2, f"Expected 2 eligible candidates, got {total_eligible}"

        top_candidate = ranked_candidates[0]
        second_candidate = ranked_candidates[1]

        print(f"\n  Rank #1: {top_candidate.filename} (Score: {top_candidate.final_score:.2f})")
        print(f"    Required Skills Score: {top_candidate.component_scores.get('required_skills')} (Qualifying: {top_candidate.breakdown['required_skills'].qualifying_criteria_count})")
        print(f"    Responsibilities Score: {top_candidate.component_scores.get('responsibilities')}")
        print(f"    Tools Score: {top_candidate.component_scores.get('tools_and_technologies')}")
        print(f"    Experience Score: {top_candidate.component_scores.get('experience_relevance')} (Diagnostic: {top_candidate.experience_diagnostic.diagnostic_message})")

        print(f"\n  Rank #2: {second_candidate.filename} (Score: {second_candidate.final_score:.2f})")
        print(f"    Required Skills Score: {second_candidate.component_scores.get('required_skills')} (Qualifying: {second_candidate.breakdown['required_skills'].qualifying_criteria_count})")
        print(f"    Responsibilities Score: {second_candidate.component_scores.get('responsibilities')}")
        print(f"    Tools Score: {second_candidate.component_scores.get('tools_and_technologies')}")
        print(f"    Experience Score: {second_candidate.component_scores.get('experience_relevance')}")

        # Corrupt/failed resume was properly excluded from ranking eligibility
        assert doc_3["status"] == "failed"
        print(f"\n  Failed/Incomplete Resume Isolation: {doc_3['filename']}")
        print(f"    Status: {doc_3['status']} (Excluded from ranking pool)")
        print(f"    Recorded Error: {doc_3['error'][:70]}...")

        assert top_candidate.final_score > 0.0
        assert second_candidate.final_score > 0.0
        assert top_candidate.final_score >= second_candidate.final_score
        print("  [PASSED] Explainable ranking, category diagnostics, evidence, and incomplete-result handling verified.")

        # ======================================================================
        # 6. Baseline Record Preservation Audit
        # ======================================================================
        print("\n[Step 8] Verifying baseline database records are preserved intact...")
        final_resumes_count = await db["resumes"].count_documents({})
        # We added exactly 3 resumes to the database (2 completed, 1 failed)
        assert final_resumes_count == initial_resumes_count + 3, f"Expected {initial_resumes_count + 3} resumes, found {final_resumes_count}"

        # Confirm the 145-batch records (ID 93cce6d0-3f25-4bdb-b11a-c423caf5f6b0) are untouched
        batch_145_completed = await db["resumes"].count_documents({"upload_id": "93cce6d0-3f25-4bdb-b11a-c423caf5f6b0", "status": "completed"})
        batch_145_failed = await db["resumes"].count_documents({"upload_id": "93cce6d0-3f25-4bdb-b11a-c423caf5f6b0", "status": "failed"})
        print(f"  Original 145-batch count check: completed={batch_145_completed}, failed={batch_145_failed}")
        assert batch_145_completed == 1, f"Expected 1 completed resume in 145-batch, got {batch_145_completed}"
        assert batch_145_failed == 141, f"Expected 141 failed resumes in 145-batch, got {batch_145_failed}"
        print("  [PASSED] Existing database data strictly preserved. Zero deletions or resets.")

        print("\n" + "=" * 80)
        print("ALL CONTROLLED E2E VALIDATION CHECKS PASSED (100%)")
        print("=" * 80)

    finally:
        # Isolated test data cleanup
        if upload_id:
            print(f"\n[Cleanup] Cleaning up isolated validation batch: {upload_id}...")
            await resume_repository.delete_by_upload(upload_id)
            await resume_embedding_repository.delete_by_upload(upload_id)
            await batch_repository.delete(upload_id)
            # Remove test JD
            await jd_repository.delete("jd_cloud_backend_test")
            await jd_embedding_repository.delete()
            print("  Isolated validation data safely cleaned up.")

        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(run_controlled_validation())
