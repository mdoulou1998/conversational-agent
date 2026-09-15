def kb_search(query: str, top_k: int = 3) -> list[str]:
    """
    This is going to search top k chunks from the product knowledge base and return
    the top k chunks to the model for context.
    """
    kb_search_data = {}
    lookup_results = kb_search_data.get(query, [])
    return lookup_results[:top_k]


