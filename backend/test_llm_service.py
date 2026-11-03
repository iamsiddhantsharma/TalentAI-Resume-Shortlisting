import asyncio

from app.services.llm_service import llm_service


async def main():
    print("=" * 50)
    print("PHASE 5.3 - LLM SERVICE TEST")
    print("=" * 50)

    prompt = """
Extract the candidate name and skills from this text.

Return a simple JSON object.

Text:
Siddhant Sharma is a B.Tech student skilled in
Python, C++, FastAPI and MongoDB.
"""

    print("\nSending request to Qwen3-8B...")

    result = await llm_service.generate_json(
        prompt
    )

    print("\n---------- QWEN RESPONSE ----------")
    print(result)

    print("\n---------- VALIDATION ----------")

    assert isinstance(result, dict)

    assert result

    print("✓ Ollama connection successful")
    print("✓ Qwen3-8B responded")
    print("✓ Response is valid JSON")
    print("✓ LLMService is working")

    print("\nPHASE 5.3 TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
