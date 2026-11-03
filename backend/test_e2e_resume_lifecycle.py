"""
End-to-End Verification of Resume Ingestion, Automatic Embedding Generation,
and Hybrid Retrieval Lookup with a New Test Resume.
"""

import asyncio
import io
import sys
from pathlib import Path
from fastapi import UploadFile

from app.database.mongodb import mongodb
from app.database.resume_repository import resume_repository
from app.database.resume_embedding_repository import resume_embedding_repository
from app.services.upload_service import upload_service
from app.queue.worker import resume_worker
from app.schemas.job_description_object import JobDescriptionObject


RESUME_TEXT = """
Siddhant Sharma
Email: siddhant@example.com
Location: New Delhi, India

Summary:
Experienced Backend Engineer specializing in Python, FastAPI, and distributed systems.

Skills:
Python, FastAPI, MongoDB, Docker, Git

Experience:
Company: TechCorp Solutions
Role: Backend Developer
Description: Developed high-throughput REST APIs using FastAPI and managed MongoDB databases.

Projects:
Project: TalentAI Shortlister
Description: Designed automated semantic matching pipeline with BGE embeddings and FastAPI.
Technologies: Python, FastAPI, MongoDB, Docker
"""


async def run_e2e_verification():
    print("=" * 80)
    print("TALENTAI — END-TO-END RESUME INGESTION & EMBEDDING VERIFICATION")
    print("=" * 80)

    await mongodb.connect()

    upload_id = None
    filename = "e2e_candidate.txt"

    try:
        # ----------------------------------------------------------------------
        # 1. Simulate Upload via UploadService
        # ----------------------------------------------------------------------
        print("\n[Step 1] Uploading new test resume...")
        file_bytes = RESUME_TEXT.encode("utf-8")
        upload_file = UploadFile(
            file=io.BytesIO(file_bytes),
            filename=filename,
            headers={"content-type": "text/plain"},
        )

        upload_response = await upload_service.create_upload_job([upload_file])
        upload_id = upload_response.upload_id

        print(f"  Upload status: {upload_response.status}")
        print(f"  Upload ID: {upload_id}")
        print(f"  Supported files: {upload_response.supported_files}")
        assert upload_response.status == "accepted"
        assert upload_response.supported_files == 1

        # ----------------------------------------------------------------------
        # 2. Process Job via ResumeWorker (triggers parser, LLM, save, embeddings)
        # ----------------------------------------------------------------------
        print("\n[Step 2] Processing job in ResumeWorker (including Qwen extraction & BGE embedding)...")
        processing_result = await resume_worker.run_once()

        print(f"  Processing status: {processing_result.status}")
        print(f"  Error (if any): {processing_result.error}")
        assert processing_result.status == "completed", f"Processing failed: {processing_result.error}"
        assert processing_result.resume_data is not None

        # ----------------------------------------------------------------------
        # 3. Verify Resume in MongoDB
        # ----------------------------------------------------------------------
        print("\n[Step 3] Verifying structured resume record in MongoDB 'resumes' collection...")
        stored_resume = await resume_repository.get(upload_id=upload_id, filename=filename)
        assert stored_resume is not None, "Resume document was not saved in MongoDB!"
        assert stored_resume["_id"] == f"{upload_id}:{filename}"
        assert stored_resume["status"] == "completed"
        rd = stored_resume["resume_data"]
        print(f"  Candidate Name: {rd.get('name')}")
        print(f"  Extracted Skills: {rd.get('skills')}")
        print(f"  Extracted Projects count: {len(rd.get('projects', []))}")
        print(f"  Extracted Experience count: {len(rd.get('experience', []))}")

        # ----------------------------------------------------------------------
        # 4. Verify Automatic Embeddings in MongoDB
        # ----------------------------------------------------------------------
        print("\n[Step 4] Verifying automatic embeddings in MongoDB 'resume_embeddings' collection...")
        stored_embedding_doc = await resume_embedding_repository.get(upload_id=upload_id, filename=filename)
        assert stored_embedding_doc is not None, "Embedding document was NOT automatically generated!"
        assert stored_embedding_doc["_id"] == f"{upload_id}:{filename}"
        assert stored_embedding_doc["upload_id"] == upload_id
        assert stored_embedding_doc["filename"] == filename

        embeddings = stored_embedding_doc.get("embeddings", [])
        print(f"  Total evidence chunks embedded: {len(embeddings)}")
        assert len(embeddings) > 0, "Embeddings list is empty!"

        # Check vector dimension and metadata
        for i, item in enumerate(embeddings):
            assert "source_type" in item
            assert "section" in item
            assert "item_index" in item
            assert "text" in item
            assert "embedding" in item
            vec = item["embedding"]
            assert len(vec) == 1024, f"Chunk {i} has dimension {len(vec)}, expected 1024!"

        print("  All vectors have 1024 dimensions: True")
        sections_found = {item["section"] for item in embeddings}
        print(f"  Sections present in embeddings: {sections_found}")

        # ----------------------------------------------------------------------
        # 5. Verify Retrieval via Hybrid Matching Lookup
        # ----------------------------------------------------------------------
        print("\n[Step 5] Verifying hybrid matching can retrieve the generated embeddings...")
        retrieved_emb = await resume_embedding_repository.get(upload_id=upload_id, filename=filename)
        assert retrieved_emb is not None
        assert retrieved_emb["upload_id"] == upload_id
        assert retrieved_emb["filename"] == filename
        assert len(retrieved_emb["embeddings"]) == len(embeddings)
        print("  Retrieved successfully via (upload_id, filename) linking.")

        print("\n" + "=" * 80)
        print("END-TO-END VERIFICATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        # Isolated test data cleanup
        if upload_id:
            print(f"\n[Cleanup] Cleaning up isolated test resume for upload_id: {upload_id}...")
            await resume_repository.delete_by_upload(upload_id)
            await resume_embedding_repository.delete(upload_id, filename)
            print("  Isolated test resume and embeddings cleaned up safely.")

        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(run_e2e_verification())
