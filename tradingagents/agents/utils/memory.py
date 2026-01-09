import logging
import os
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class FinancialSituationMemory:
    """Memory system for storing and retrieving financial situations.

    Supports multiple embedding providers:
    - same_as_llm: Use the same provider as the LLM
    - openai: Use Official OpenAI embeddings
    - gemini: Use Google Gemini embeddings (gemini-embedding-001)
    - local: Use HuggingFace sentence-transformers (all-MiniLM-L6-v2)
    - disabled: Skip embeddings entirely
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.config = config
        self.name = name
        self.local_model = None
        self.client = None

        # Determine embedding provider
        self.embedding_provider = config.get("embedding_provider", "same_as_llm")

        # Check if embeddings should be disabled
        if config.get("disable_embeddings", False) or self.embedding_provider == "disabled":
            self._init_disabled()
            return

        # Initialize based on provider
        if self.embedding_provider == "local":
            self._init_local()
        elif self.embedding_provider == "gemini":
            self._init_gemini()
        else:
            self._init_api_based()

    def _init_disabled(self):
        """Initialize with embeddings disabled."""
        self.embeddings_disabled = True
        self.client = None
        self.local_model = None
        self.chroma_client = None
        self.situation_collection = None
        logger.info("Embeddings disabled - memory lookups will return empty results")

    def _init_local(self):
        """Initialize with local sentence-transformers model."""
        self.embeddings_disabled = False
        self.client = None

        # Get model name from config
        model_name = self.config.get("embedding_model", "all-MiniLM-L6-v2")

        try:
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer(model_name)
        except ImportError:
            logger.error("sentence-transformers required for local embeddings. Install with: pip install sentence-transformers")
            logger.warning("Falling back to disabled embeddings")
            self._init_disabled()
            return

        # Initialize ChromaDB
        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.get_or_create_collection(name=self.name)
        logger.info(f"Using local embeddings with model: {model_name}")

    def _init_gemini(self):
        """Initialize with Google Gemini embeddings."""
        self.embeddings_disabled = False
        self.client = None
        self.local_model = None

        try:
            from google import genai
            self.gemini_client = genai.Client()
        except ImportError:
            logger.error("google-genai required for Gemini embeddings. Install with: pip install google-genai")
            logger.warning("Falling back to disabled embeddings")
            self._init_disabled()
            return

        # Check for API key
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set - disabling Gemini embeddings")
            self._init_disabled()
            return

        # Get embedding model
        self.embedding_model = self.config.get("embedding_model") or "gemini-embedding-001"

        # Initialize ChromaDB
        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.get_or_create_collection(name=self.name)
        logger.info(f"Using Gemini embeddings with model: {self.embedding_model}")

    def _init_api_based(self):
        """Initialize with API-based embeddings (OpenAI-compatible)."""
        from openai import OpenAI

        self.embeddings_disabled = False
        self.local_model = None

        # Determine backend URL based on provider
        if self.embedding_provider == "openai":
            backend_url = "https://api.openai.com/v1"
        else:
            # same_as_llm - use LLM backend URL or embedding-specific URL
            backend_url = self.config.get("embedding_backend_url") or self.config.get("backend_url", "")

        # Auto-disable for incompatible endpoints (e.g., ZhipuAI coding endpoints)
        if "/coding/" in backend_url:
            logger.info("Coding endpoints don't support embeddings - auto-disabling")
            self._init_disabled()
            return

        # Get embedding model
        self.embedding = self._get_embedding_model(backend_url)

        # Get API key
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("API key not found for embeddings - disabling")
            self._init_disabled()
            return

        self.client = OpenAI(base_url=backend_url, api_key=api_key)
        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        self.situation_collection = self.chroma_client.get_or_create_collection(name=self.name)
        logger.info(f"Using API embeddings - model: {self.embedding}, endpoint: {backend_url}")

    def _get_embedding_model(self, backend_url: str) -> str:
        """Determine embedding model based on config and provider."""
        if self.config.get("embedding_model"):
            return self.config["embedding_model"]
        elif backend_url == "http://localhost:11434/v1":
            return "nomic-embed-text"
        elif "z.ai" in backend_url:
            return "embedding-3"
        else:
            return "text-embedding-3-small"

    def _get_api_key(self) -> Optional[str]:
        """Get API key from config."""
        if self.embedding_provider == "openai":
            # For official OpenAI, use embedding-specific key first, then fallback
            api_key_env = self.config.get("embedding_api_key_env_var", "OPENAI_API_KEY")
        else:
            # For same_as_llm, use embedding key if set, otherwise LLM key
            api_key_env = self.config.get("embedding_api_key_env_var") or \
                         self.config.get("api_key_env_var", "OPENAI_API_KEY")

        if not api_key_env:
            return None

        # Handle direct key (prefixed with __DIRECT_KEY__:)
        if api_key_env.startswith("__DIRECT_KEY__:"):
            return api_key_env.replace("__DIRECT_KEY__:", "")

        return os.environ.get(api_key_env)

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text.

        Returns:
            List of floats representing the embedding vector.
            Returns dummy vector if embeddings are disabled.
        """
        if self.embeddings_disabled:
            return [0.0] * 384  # Match all-MiniLM-L6-v2 dimension

        if self.local_model is not None:
            # Local embedding using sentence-transformers
            return self.local_model.encode(text).tolist()

        if hasattr(self, "gemini_client") and self.gemini_client is not None:
            # Gemini embedding
            result = self.gemini_client.models.embed_content(
                model=self.embedding_model,
                contents=text,
            )
            return list(result.embeddings[0].values)

        # API-based embedding (OpenAI-compatible)
        response = self.client.embeddings.create(
            model=self.embedding, input=text
        )
        return response.data[0].embedding

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice.

        Args:
            situations_and_advice: List of tuples (situation, recommendation)
        """
        if self.embeddings_disabled:
            logger.debug("Skipping add_situations (embeddings disabled)")
            return

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation: str, n_matches: int = 1) -> List[Dict]:
        """Find matching recommendations based on current situation.

        Args:
            current_situation: Description of the current market situation
            n_matches: Number of similar situations to retrieve

        Returns:
            List of dictionaries with matched_situation, recommendation, and similarity_score
        """
        if self.embeddings_disabled:
            logger.debug("Skipping memory lookup (embeddings disabled)")
            return []

        query_embedding = self.get_embedding(current_situation)

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append({
                "matched_situation": results["documents"][0][i],
                "recommendation": results["metadatas"][0][i]["recommendation"],
                "similarity_score": 1 - results["distances"][0][i],
            })

        return matched_results


def get_situation_memories(
    memory: FinancialSituationMemory,
    market_report: str,
    sentiment_report: str,
    news_report: str,
    fundamentals_report: str,
    n_matches: int = 2,
) -> str:
    """Build situation context and retrieve relevant past memories.

    Args:
        memory: FinancialSituationMemory instance
        market_report: Market analysis report
        sentiment_report: Social media sentiment report
        news_report: News report
        fundamentals_report: Company fundamentals report
        n_matches: Number of memory matches to retrieve

    Returns:
        Formatted string of past recommendations
    """
    situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
    memories = memory.get_memories(situation, n_matches=n_matches)
    return "\n\n".join(rec["recommendation"] for rec in memories)


if __name__ == "__main__":
    # Example usage
    config = {
        "embedding_provider": "disabled",  # or "local", "openai", "same_as_llm"
        "embedding_model": "all-MiniLM-L6-v2",
    }
    matcher = FinancialSituationMemory("test_memory", config)

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
