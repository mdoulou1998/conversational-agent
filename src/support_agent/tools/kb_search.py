from support_agent.tools.fixtures import KB_CHUNKS


def kb_search(query: str, top_k: int = 3) -> list[str]:
    """
    This is going to search top k chunks from the product knowledge base and return
    the top k chunks to the model for context.
    """
    query_words = query.lower().split()
    matches = [
        chunk.text for chunk in KB_CHUNKS if any(word in chunk.topic for word in query_words)
    ]
    return matches[:top_k]
