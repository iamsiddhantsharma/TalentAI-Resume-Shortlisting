"""
TalentAI — Regression Test Suite for Resume Embedding Consistency

Verifies:
1. Successfully processed resume triggers embedding generation.
2. Correct upload_id and filename reach the generation service.
3. The generation service loads the intended resume from MongoDB.
4. Failed resume processing does NOT trigger embedding generation.
5. Embedding-generation failures are handled and logged correctly (no false success).
6. Retries do not create duplicate or incorrectly linked records.
7. Existing embeddings remain readable and preserve metadata.
8. Hybrid matching retrieves the intended resume embeddings using (upload_id, filename).
9. Generated embedding vectors have 1024 dimensions.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.mongodb import mongodb
from app.database.resume_embedding_repository import resume_embedding_repository
from app.database.resume_repository import resume_repository
from app.queue.worker import resume_worker
from app.schemas.job_description import JobDescription
from app.schemas.job_description_object import JobDescriptionObject
from app.schemas.processing_job import ProcessingJob
from app.schemas.processing_result import ProcessingResult
from app.schemas.resume_object import ResumeObject
from app.services.hybrid_matching_service import hybrid_matching_service
from app.services.resume_embedding_generation_service import (
    resume_embedding_generation_service,
)


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


# ==============================================================================
# TEST 1 & 2: Successful resume triggers generation with correct IDs
# ==============================================================================


async def test_1_and_2_successful_processing_triggers_generation():
    print("\n" + "=" * 70)
    print("TEST 1 & 2: SUCCESSFUL PROCESSING TRIGGERS EMBEDDING GENERATION")
    print("=" * 70)

    job = ProcessingJob(
        upload_id="upload-alpha-123",
        filename="alice_resume.pdf",
        file_path="dummy/path/alice_resume.pdf",
        file_extension=".pdf",
        relative_path="alice_resume.pdf",
    )

    fake_resume_obj = ResumeObject(
        name="Alice Smith",
        skills=["Python", "FastAPI"],
    )

    with (
        patch("app.queue.worker.parser_factory.get_parser") as mock_get_parser,
        patch("app.queue.worker.text_normalizer.normalize") as mock_norm,
        patch(
            "app.queue.worker.extraction_recovery_service.extract_resume",
            new_callable=AsyncMock,
        ) as mock_extract,
        patch("app.queue.worker.result_store.save") as mock_store_save,
        patch(
            "app.queue.worker.resume_repository.save",
            new_callable=AsyncMock,
        ) as mock_repo_save,
        patch(
            "app.queue.worker.resume_embedding_generation_service.generate_for_resume",
            new_callable=AsyncMock,
        ) as mock_gen,
    ):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = "Raw Alice text"
        mock_get_parser.return_value = mock_parser
        mock_norm.return_value = "Normalized Alice text"
        mock_extract.return_value = fake_resume_obj
        mock_gen.return_value = {
            "upload_id": "upload-alpha-123",
            "filename": "alice_resume.pdf",
            "evidence_count": 2,
            "embedding_count": 2,
            "embedding_dimension": 1024,
            "status": "completed",
        }

        result = await resume_worker.process_job(job)

        # Assertions
        assert result.status == "completed", f"Expected completed, got {result.status}"
        assert mock_repo_save.await_count == 1, "Resume should be saved to MongoDB"

        # Test 1: Embedding generation was triggered
        assert mock_gen.await_count == 1, "Embedding generation was not triggered!"

        # Test 2: Correct upload_id and filename were passed
        mock_gen.assert_awaited_once_with(
            upload_id="upload-alpha-123",
            filename="alice_resume.pdf",
        )

    print_status(
        "Successfully processed resume triggers embedding generation with correct IDs",
        True,
    )


# ==============================================================================
# TEST 3: Generation service loads the intended resume from MongoDB
# ==============================================================================


async def test_3_generation_service_loads_intended_resume():
    print("\n" + "=" * 70)
    print("TEST 3: EMBEDDING SERVICE LOADS INTENDED RESUME")
    print("=" * 70)

    stored_doc = {
        "_id": "upload-beta-456:bob_resume.pdf",
        "upload_id": "upload-beta-456",
        "filename": "bob_resume.pdf",
        "file_path": "dummy/bob.pdf",
        "file_extension": ".pdf",
        "relative_path": "bob_resume.pdf",
        "status": "completed",
        "text": "Bob resume text",
        "resume_data": {
            "name": "Bob Jones",
            "skills": ["Docker", "Kubernetes"],
            "projects": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "achievements": [],
            "interests": [],
            "coding_profiles": [],
        },
        "error": None,
    }

    with (
        patch(
            "app.services.resume_embedding_generation_service.resume_repository.get",
            new_callable=AsyncMock,
        ) as mock_get_resume,
        patch(
            "app.services.resume_embedding_generation_service.evidence_embedding_service.embed_evidence"
        ) as mock_embed,
        patch(
            "app.services.resume_embedding_generation_service.resume_embedding_repository.save",
            new_callable=AsyncMock,
        ) as mock_emb_save,
    ):
        mock_get_resume.return_value = stored_doc
        mock_embed.return_value = [
            {
                "source_type": "resume",
                "section": "skills",
                "item_index": 0,
                "text": "Skill: Docker",
                "embedding": [0.05] * 1024,
            }
        ]

        res = await resume_embedding_generation_service.generate_for_resume(
            upload_id="upload-beta-456",
            filename="bob_resume.pdf",
        )

        # Assert correct resume loaded
        mock_get_resume.assert_awaited_once_with(
            upload_id="upload-beta-456",
            filename="bob_resume.pdf",
        )
        assert res["status"] == "completed"
        assert res["embedding_dimension"] == 1024

        # Verify not found raises ValueError
        mock_get_resume.return_value = None
        try:
            await resume_embedding_generation_service.generate_for_resume(
                upload_id="missing-id",
                filename="missing.pdf",
            )
            assert False, "Should have raised ValueError on missing resume"
        except ValueError as exc:
            assert "Resume not found" in str(exc)

    print_status("Embedding generation service correctly loads intended resume", True)


# ==============================================================================
# TEST 4: Failed resume processing does NOT trigger embedding generation
# ==============================================================================


async def test_4_failed_processing_skips_embedding_generation():
    print("\n" + "=" * 70)
    print("TEST 4: FAILED PROCESSING SKIPS EMBEDDING GENERATION")
    print("=" * 70)

    job = ProcessingJob(
        upload_id="upload-fail-789",
        filename="corrupt.pdf",
        file_path="dummy/path/corrupt.pdf",
        file_extension=".pdf",
        relative_path="corrupt.pdf",
    )

    with (
        patch("app.queue.worker.parser_factory.get_parser") as mock_get_parser,
        patch(
            "app.queue.worker.resume_repository.save",
            new_callable=AsyncMock,
        ) as mock_repo_save,
        patch(
            "app.queue.worker.resume_embedding_generation_service.generate_for_resume",
            new_callable=AsyncMock,
        ) as mock_gen,
    ):
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = RuntimeError("Corrupted PDF stream")
        mock_get_parser.return_value = mock_parser

        result = await resume_worker.process_job(job)

        assert result.status == "failed"
        assert "Corrupted PDF stream" in result.error
        # Crucial: embedding generation MUST NOT be called!
        assert mock_gen.await_count == 0, "Embedding generation should NOT be called on failure!"

    print_status("Failed resume processing does not trigger embedding generation", True)


# ==============================================================================
# TEST 5: Embedding-generation failures handled and logged correctly
# ==============================================================================


async def test_5_embedding_failures_handled_and_logged():
    print("\n" + "=" * 70)
    print("TEST 5: EMBEDDING GENERATION FAILURES HANDLED (NO FALSE SUCCESS)")
    print("=" * 70)

    job = ProcessingJob(
        upload_id="upload-emb-fail-101",
        filename="charlie.pdf",
        file_path="dummy/path/charlie.pdf",
        file_extension=".pdf",
        relative_path="charlie.pdf",
    )

    with (
        patch("app.queue.worker.parser_factory.get_parser") as mock_get_parser,
        patch("app.queue.worker.text_normalizer.normalize") as mock_norm,
        patch(
            "app.queue.worker.extraction_recovery_service.extract_resume",
            new_callable=AsyncMock,
        ) as mock_extract,
        patch(
            "app.queue.worker.resume_repository.save",
            new_callable=AsyncMock,
        ) as mock_repo_save,
        patch(
            "app.queue.worker.resume_embedding_generation_service.generate_for_resume",
            new_callable=AsyncMock,
        ) as mock_gen,
        patch(
            "app.queue.worker.resume_embedding_repository.delete",
            new_callable=AsyncMock,
        ) as mock_emb_del,
    ):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = "Charlie text"
        mock_get_parser.return_value = mock_parser
        mock_norm.return_value = "Charlie text"
        mock_extract.return_value = ResumeObject(name="Charlie", skills=["Python"])
        # Embedding generation raises an error (e.g. OOM or timeout)
        mock_gen.side_effect = RuntimeError("Embedding service connection timed out")

        result = await resume_worker.process_job(job)

        # Assert no false success: result is marked failed!
        assert result.status == "failed", f"Expected failed status, got {result.status}"
        assert "Embedding service connection timed out" in result.error
        # Stale embeddings cleanup was called
        mock_emb_del.assert_awaited_once_with(
            upload_id="upload-emb-fail-101",
            filename="charlie.pdf",
        )

    print_status(
        "Embedding-generation failures produce status='failed' and clean up stale embeddings",
        True,
    )


# ==============================================================================
# TEST 6: Retries do not create duplicate or incorrectly linked records
# ==============================================================================


async def test_6_retries_idempotent_no_duplicates():
    print("\n" + "=" * 70)
    print("TEST 6: RETRIES AND REPEATED PROCESSING IDEMPOTENCY")
    print("=" * 70)

    # Verify repository implementation uses replace_one with upsert=True
    # and document _id is f"{upload_id}:{filename}"
    upload_id = "upload-retry-999"
    filename = "diana.pdf"
    doc_id = f"{upload_id}:{filename}"

    collection_mock = AsyncMock()
    with patch.object(resume_embedding_repository, "_collection", return_value=collection_mock):
        embeddings = [
            {
                "source_type": "resume",
                "section": "skills",
                "item_index": 0,
                "text": "Skill: Python",
                "embedding": [0.1] * 1024,
            }
        ]

        # First save
        await resume_embedding_repository.save(
            upload_id=upload_id,
            filename=filename,
            embeddings=embeddings,
        )
        assert collection_mock.replace_one.await_count == 1
        call_args = collection_mock.replace_one.await_args
        filter_dict = call_args[0][0]
        replacement_doc = call_args[0][1]
        kwargs = call_args[1]

        assert filter_dict == {"_id": doc_id}
        assert replacement_doc["_id"] == doc_id
        assert replacement_doc["upload_id"] == upload_id
        assert replacement_doc["filename"] == filename
        assert kwargs.get("upsert") is True

        # Retry save (second save with updated embeddings)
        await resume_embedding_repository.save(
            upload_id=upload_id,
            filename=filename,
            embeddings=embeddings + [
                {
                    "source_type": "resume",
                    "section": "skills",
                    "item_index": 1,
                    "text": "Skill: Go",
                    "embedding": [0.2] * 1024,
                }
            ],
        )
        assert collection_mock.replace_one.await_count == 2
        call_args_2 = collection_mock.replace_one.await_args
        assert call_args_2[0][0] == {"_id": doc_id}
        assert call_args_2[0][1]["_id"] == doc_id
        assert len(call_args_2[0][1]["embeddings"]) == 2

    print_status(
        "Retries use replace_one(upsert=True) keyed on upload_id:filename without duplicates",
        True,
    )


# ==============================================================================
# TEST 7: Existing embeddings remain readable
# ==============================================================================


async def test_7_existing_embeddings_remain_readable():
    print("\n" + "=" * 70)
    print("TEST 7: EXISTING EMBEDDINGS READABILITY AND METADATA INTEGRITY")
    print("=" * 70)

    # Test reading existing records from MongoDB
    await mongodb.connect()
    try:
        all_embeddings = await resume_embedding_repository.get_all()
        assert len(all_embeddings) >= 1, "Expected at least 1 existing embedding document in MongoDB"

        doc = all_embeddings[0]
        assert "upload_id" in doc
        assert "filename" in doc
        assert "_id" in doc
        assert doc["_id"] == f"{doc['upload_id']}:{doc['filename']}"

        embeddings = doc.get("embeddings", [])
        assert len(embeddings) > 0, "Embeddings list must not be empty"

        for item in embeddings:
            assert "source_type" in item, "Missing source_type"
            assert "section" in item, "Missing section"
            assert "item_index" in item, "Missing item_index"
            assert "text" in item, "Missing text"
            assert "embedding" in item, "Missing embedding vector"
            assert len(item["embedding"]) == 1024, f"Vector dimension must be 1024, got {len(item['embedding'])}"
    finally:
        await mongodb.disconnect()

    print_status(
        "Existing embeddings are readable with all metadata and 1024-dim vectors",
        True,
    )


# ==============================================================================
# TEST 8: Hybrid matching retrieves intended resume embeddings
# ==============================================================================


async def test_8_hybrid_matching_retrieves_embeddings():
    print("\n" + "=" * 70)
    print("TEST 8: HYBRID MATCHING LOOKUP BY (UPLOAD_ID, FILENAME)")
    print("=" * 70)

    jd_id = "jd-test-8"
    upload_id = "upload-test-8"
    filename = "edward_resume.pdf"

    mock_jd_doc = {
        "_id": jd_id,
        "jd_id": jd_id,
        "input_type": "text",
        "raw_text": "Need Python developer with FastAPI and Git",
        "status": "completed",
        "structured_data": JobDescriptionObject(
            required_skills=["Python"],
            responsibilities=["Build FastAPI services"],
            experience_requirements=[],
            tools_and_technologies=["Git"],
        ).model_dump(mode="json"),
    }


    mock_jd_emb_doc = {
        "jd_id": jd_id,
        "embeddings": [
            {
                "source_type": "job_description",
                "section": "responsibilities",
                "item_index": 0,
                "text": "Responsibility: Build FastAPI services",
                "embedding": [0.1] * 1024,
            },
            {
                "source_type": "job_description",
                "section": "tools_and_technologies",
                "item_index": 0,
                "text": "Tool: Git",
                "embedding": [0.2] * 1024,
            },
        ],
    }

    mock_resume_doc = {
        "_id": f"{upload_id}:{filename}",
        "upload_id": upload_id,
        "filename": filename,
        "file_path": "edward.pdf",
        "file_extension": ".pdf",
        "relative_path": "edward.pdf",
        "status": "completed",
        "resume_data": ResumeObject(
            name="Edward",
            skills=["Python"],
            projects=[
                {
                    "name": "Backend Service",
                    "description": "FastAPI service with Git",
                    "technologies": ["FastAPI", "Git"],
                }
            ],
        ).model_dump(mode="json"),
    }

    mock_resume_emb_doc = {
        "_id": f"{upload_id}:{filename}",
        "upload_id": upload_id,
        "filename": filename,
        "embeddings": [
            {
                "source_type": "resume",
                "section": "projects",
                "item_index": 0,
                "text": "Project: Backend Service | Technologies: FastAPI, Git",
                "embedding": [0.1] * 1024,
            }
        ],
    }

    with (
        patch("app.services.hybrid_matching_service.jd_repository.get", new_callable=AsyncMock) as mock_get_jd,
        patch(
            "app.services.hybrid_matching_service.jd_embedding_repository.get_by_jd_id",
            new_callable=AsyncMock,
        ) as mock_get_jd_emb,
        patch(
            "app.services.hybrid_matching_service.resume_repository.get",
            new_callable=AsyncMock,
        ) as mock_get_res,
        patch(
            "app.services.hybrid_matching_service.resume_embedding_repository.get",
            new_callable=AsyncMock,
        ) as mock_get_res_emb,
    ):
        mock_get_jd.return_value = mock_jd_doc
        mock_get_jd_emb.return_value = mock_jd_emb_doc
        mock_get_res.return_value = mock_resume_doc
        mock_get_res_emb.return_value = mock_resume_emb_doc

        match_output = await hybrid_matching_service.match_resume(
            jd_id=jd_id,
            upload_id=upload_id,
            filename=filename,
        )

        # Assert hybrid matching requested resume embeddings with correct upload_id and filename
        mock_get_res_emb.assert_awaited_once_with(
            upload_id=upload_id,
            filename=filename,
        )
        assert match_output["upload_id"] == upload_id
        assert match_output["filename"] == filename
        assert "semantic_retrieval" in match_output
        assert "responsibilities_retrieval" in match_output["semantic_retrieval"]
        assert "tools_and_technologies_retrieval" in match_output["semantic_retrieval"]

    print_status(
        "Hybrid matching retrieves resume embeddings using (upload_id, filename)",
        True,
    )


# ==============================================================================
# TEST 9: Every generated embedding vector has 1024 dimensions
# ==============================================================================


def test_9_embedding_vector_dimension():
    print("\n" + "=" * 70)
    print("TEST 9: EMBEDDING VECTOR DIMENSION (1024)")
    print("=" * 70)

    from app.services.embedding_service import embedding_service
    from app.services.evidence_embedding_service import evidence_embedding_service

    test_evidence = [
        {
            "source_type": "resume",
            "section": "skills",
            "item_index": 0,
            "text": "Skill: Python programming language",
        },
        {
            "source_type": "resume",
            "section": "projects",
            "item_index": 0,
            "text": "Project: TalentAI resume parser with LLM",
        },
    ]

    embedded = evidence_embedding_service.embed_evidence(test_evidence)
    assert len(embedded) == 2, f"Expected 2 embedded units, got {len(embedded)}"

    for item in embedded:
        vec = item["embedding"]
        assert isinstance(vec, list), "Embedding must be a list of floats"
        assert len(vec) == 1024, f"Vector dimension must be 1024, got {len(vec)}"
        assert all(isinstance(v, float) for v in vec), "Vector elements must be floats"

    print_status("Every generated embedding vector has exactly 1024 dimensions", True)


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================


async def main():
    print("=" * 80)
    print("TALENTAI — RESUME EMBEDDING CONSISTENCY & WORKFLOW REGRESSION SUITE")
    print("=" * 80)

    await test_1_and_2_successful_processing_triggers_generation()
    await test_3_generation_service_loads_intended_resume()
    await test_4_failed_processing_skips_embedding_generation()
    await test_5_embedding_failures_handled_and_logged()
    await test_6_retries_idempotent_no_duplicates()
    await test_7_existing_embeddings_remain_readable()
    await test_8_hybrid_matching_retrieves_embeddings()
    test_9_embedding_vector_dimension()

    print("\n" + "=" * 80)
    print("ALL TESTS (1 through 9) PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
