"""Generate embeddings for seed data chunks that lack them."""

import asyncio
import asyncpg
from sentence_transformers import SentenceTransformer

DATABASE_URL = "postgresql://admin:supersecretpassword@vector_db:5432/nexus_knowledge"


async def main():
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    conn = await asyncpg.connect(DATABASE_URL)

    rows = await conn.fetch(
        "SELECT id, content FROM document_chunks WHERE embedding IS NULL"
    )
    print(f"Found {len(rows)} chunks without embeddings")

    for row in rows:
        embedding = model.encode(row["content"])
        await conn.execute(
            "UPDATE document_chunks SET embedding = $1 WHERE id = $2",
            str(embedding.tolist()),
            row["id"],
        )
        print(f"  Updated chunk {row['id']}")

    await conn.close()
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
