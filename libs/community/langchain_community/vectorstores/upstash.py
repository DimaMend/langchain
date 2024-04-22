from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Tuple

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.utils.iter import batch_iterate
from langchain_core.vectorstores import VectorStore

from langchain_community.vectorstores.utils import (
    maximal_marginal_relevance,
)

if TYPE_CHECKING:
    from upstash_vector import AsyncIndex, Index

logger = logging.getLogger(__name__)


class UpstashVectorStore(VectorStore):
    """Upstash Vector vector store

    To use, the ``upstash-vector`` python package must be installed.

    Also an Upstash Vector index is required. First create a new Upstash Vector index
    and copy the `index_url` and `index_token` variables. Then either pass
    them through the constructor or set the environment
    variables `UPSTASH_VECTOR_REST_URL` and `UPSTASH_VECTOR_REST_TOKEN`.

    Example:
        .. code-block:: python

            from langchain_community.vectorstores.upstash import UpstashVectorStore
            from langchain_community.embeddings.openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings()
            vectorstore = UpstashVectorStore(
                embedding=embeddings,
                index_url="...",
                index_token="..."
            )

            # or

            import os

            os.environ["UPSTASH_VECTOR_REST_URL"] = "..."
            os.environ["UPSTASH_VECTOR_REST_TOKEN"] = "..."

            vectorstore = UpstashVectorStore(
                embedding=embeddings
            )
    """

    def __init__(
        self,
        text_key: str = "text",
        index: Optional[Index] = None,
        async_index: Optional[AsyncIndex] = None,
        index_url: Optional[str] = None,
        index_token: Optional[str] = None,
        embedding: Optional[Embeddings] = None,
    ):
        """
        Constructor for UpstashVectorStore.

        If index or index_url and index_token are not provided, the constructor will
        attempt to create an index using the environment variables
        `UPSTASH_VECTOR_REST_URL`and `UPSTASH_VECTOR_REST_TOKEN`.

        Args:
            text_key: Key to store the text in metadata.
            index: UpstashVector Index object.
            async_index: UpstashVector AsyncIndex object, provide only if async
            functions are needed
            index_url: URL of the UpstashVector index.
            index_token: Token of the UpstashVector index.
            embedding: Embeddings object.

        Example:
            .. code-block:: python

                from langchain_community.vectorstores.upstash import UpstashVectorStore
                from langchain_community.embeddings.openai import OpenAIEmbeddings

                embeddings = OpenAIEmbeddings()
                vectorstore = UpstashVectorStore(
                    embedding=embeddings,
                    index_url="...",
                    index_token="..."
                )

                # With an existing index
                from upstash_vector import Index

                index = Index(url="...", token="...")
                vectorstore = UpstashVectorStore(
                    embedding=embeddings,
                    index=index
                )
        """

        try:
            from upstash_vector import AsyncIndex, Index
        except ImportError:
            raise ImportError(
                "Could not import upstash_vector python package. "
                "Please install it with `pip install upstash_vector`."
            )

        if index:
            if not isinstance(index, Index):
                raise ValueError(
                    "Passed index object should be an "
                    "instance of upstash_vector.Index, "
                    f"got {type(index)}"
                )
            self._index = index
            logger.info("Using the index passed as parameter")
        if async_index:
            if not isinstance(async_index, AsyncIndex):
                raise ValueError(
                    "Passed index object should be an "
                    "instance of upstash_vector.AsyncIndex, "
                    f"got {type(async_index)}"
                )
            self._async_index = async_index
            logger.info("Using the async index passed as parameter")

        if index_url and index_token:
            self._index = Index(url=index_url, token=index_token)
            self._async_index = AsyncIndex(url=index_url, token=index_token)
            logger.info("Created index from the index_url and index_token parameters")
        elif not index and not async_index:
            self._index = Index.from_env()
            self._async_index = AsyncIndex.from_env()
            logger.info("Created index using environment variables")

        self._embeddings = embedding
        self._text_key = text_key

    @property
    def embeddings(self) -> Optional[Embeddings]:
        """Access the query embedding object if available."""
        return self._embeddings

    def _embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
        """Embed strings using the embeddings object"""
        if not self._embeddings:
            raise ValueError(
                "No embeddings object provided. "
                "Pass an embeddings object to the constructor."
            )
        return self._embeddings.embed_documents(list(texts))

    def _embed_query(self, text: str) -> List[float]:
        """Embed query text using the embeddings object."""
        if not self._embeddings:
            raise ValueError(
                "No embeddings object provided. "
                "Pass an embeddings object to the constructor."
            )
        return self._embeddings.embed_query(text)

    def add_documents(
        self,
        documents: Iterable[Document],
        ids: Optional[List[str]] = None,
        batch_size: int = 32,
        embedding_chunk_size: int = 1000,
    ) -> List[str]:
        """
        Get the embeddings for the documents and add them to the vectorstore.

        Documents are sent to the embeddings object
        in batches of size `embedding_chunk_size`.
        The embeddings are then upserted into the vectorstore
        in batches of size `batch_size`.

        Args:
            documents: Iterable of Documents to add to the vectorstore.
            batch_size: Batch size to use when upserting the embeddings.
            Upstash supports at max 1000 vectors per request.
            embedding_batch_size: Chunk size to use when embedding the texts.

        Returns:
            List of ids from adding the texts into the vectorstore.

        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        return self.add_texts(
            texts,
            metadatas=metadatas,
            batch_size=batch_size,
            ids=ids,
            embedding_chunk_size=embedding_chunk_size,
        )

    async def aadd_documents(
        self,
        documents: Iterable[Document],
        ids: Optional[List[str]] = None,
        batch_size: int = 32,
        embedding_chunk_size: int = 1000,
    ) -> List[str]:
        """
        Get the embeddings for the documents and add them to the vectorstore.

        Documents are sent to the embeddings object
        in batches of size `embedding_chunk_size`.
        The embeddings are then upserted into the vectorstore
        in batches of size `batch_size`.

        Args:
            documents: Iterable of Documents to add to the vectorstore.
            batch_size: Batch size to use when upserting the embeddings.
            Upstash supports at max 1000 vectors per request.
            embedding_batch_size: Chunk size to use when embedding the texts.

        Returns:
            List of ids from adding the texts into the vectorstore.

        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        return self.aadd_texts(
            texts,
            metadatas=metadatas,
            ids=ids,
            batch_size=batch_size,
            embedding_chunk_size=embedding_chunk_size,
        )

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        batch_size: int = 32,
        embedding_chunk_size: int = 1000,
    ) -> List[str]:
        """
        Get the embeddings for the texts and add them to the vectorstore.

        Texts are sent to the embeddings object
        in batches of size `embedding_chunk_size`.
        The embeddings are then upserted into the vectorstore
        in batches of size `batch_size`.

        Args:
            texts: Iterable of strings to add to the vectorstore.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of ids to associate with the texts.
            batch_size: Batch size to use when upserting the embeddings.
            Upstash supports at max 1000 vectors per request.
            embedding_batch_size: Chunk size to use when embedding the texts.

        Returns:
            List of ids from adding the texts into the vectorstore.

        """
        texts = list(texts)
        ids = ids or [str(uuid.uuid4()) for _ in texts]

        # Copy metadatas to avoid modifying the original documents
        if metadatas:
            metadatas = [m.copy() for m in metadatas]
        else:
            metadatas = [{} for _ in texts]

        # Add text to metadata
        for metadata, text in zip(metadatas, texts):
            metadata[self._text_key] = text

        for i in range(0, len(texts), embedding_chunk_size):
            chunk_texts = texts[i : i + embedding_chunk_size]
            chunk_ids = ids[i : i + embedding_chunk_size]
            chunk_metadatas = metadatas[i : i + embedding_chunk_size]
            embeddings = self._embed_documents(chunk_texts)

            for batch in batch_iterate(
                batch_size, zip(chunk_ids, embeddings, chunk_metadatas)
            ):
                self._index.upsert(vectors=batch)

        return ids

    async def aadd_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        batch_size: int = 32,
        embedding_chunk_size: int = 1000,
    ) -> List[str]:
        """
        Get the embeddings for the texts and add them to the vectorstore.

        Texts are sent to the embeddings object
        in batches of size `embedding_chunk_size`.
        The embeddings are then upserted into the vectorstore
        in batches of size `batch_size`.

        Args:
            texts: Iterable of strings to add to the vectorstore.
            metadatas: Optional list of metadatas associated with the texts.
            ids: Optional list of ids to associate with the texts.
            batch_size: Batch size to use when upserting the embeddings.
            Upstash supports at max 1000 vectors per request.
            embedding_batch_size: Chunk size to use when embedding the texts.

        Returns:
            List of ids from adding the texts into the vectorstore.

        """
        texts = list(texts)
        ids = ids or [str(uuid.uuid4()) for _ in texts]

        # Copy metadatas to avoid modifying the original documents
        if metadatas:
            metadatas = [m.copy() for m in metadatas]
        else:
            metadatas = [{} for _ in texts]

        # Add text to metadata
        for metadata, text in zip(metadatas, texts):
            metadata[self._text_key] = text

        for i in range(0, len(texts), embedding_chunk_size):
            chunk_texts = texts[i : i + embedding_chunk_size]
            chunk_ids = ids[i : i + embedding_chunk_size]
            chunk_metadatas = metadatas[i : i + embedding_chunk_size]
            embeddings = self._embed_documents(chunk_texts)

            for batch in batch_iterate(
                batch_size, zip(chunk_ids, embeddings, chunk_metadatas)
            ):
                await self._async_index.upsert(vectors=batch)

        return ids

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
    ) -> List[Tuple[Document, float]]:
        """Retrieve texts most similar to query and
        convert the result to `Document` objects.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query and score for each
        """
        return self.similarity_search_by_vector_with_score(
            self._embed_query(query), k=k
        )

    async def asimilarity_search_with_score(
        self,
        query: str,
        k: int = 4,
    ) -> List[Tuple[Document, float]]:
        """Retrieve texts most similar to query and
        convert the result to `Document` objects.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query and score for each
        """
        return await self.asimilarity_search_by_vector_with_score(
            self._embed_query(query), k=k
        )

    def _process_results(self, results: List) -> List[Tuple[Document, float]]:
        docs = []
        for res in results:
            metadata = res.metadata
            if metadata and self._text_key in metadata:
                text = metadata.pop(self._text_key)
                doc = Document(page_content=text, metadata=metadata)
                docs.append((doc, res.score))
            else:
                logger.warning(
                    f"Found document with no `{self._text_key}` key. Skipping."
                )
        return docs

    def similarity_search_by_vector_with_score(
        self,
        embedding: List[float],
        k: int = 4,
    ) -> List[Tuple[Document, float]]:
        """Return texts whose embedding is closest to the given embedding"""

        results = self._index.query(
            vector=embedding,
            top_k=k,
            include_metadata=True,
        )

        return self._process_results(results)

    async def asimilarity_search_by_vector_with_score(
        self,
        embedding: List[float],
        k: int = 4,
    ) -> List[Tuple[Document, float]]:
        """Return texts whose embedding is closest to the given embedding"""

        results = await self._async_index.query(
            vector=embedding,
            top_k=k,
            include_metadata=True,
        )

        return self._process_results(results)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
    ) -> List[Document]:
        """Return documents most similar to query.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query and score for each
        """
        docs_and_scores = self.similarity_search_with_score(query, k=k)
        return [doc for doc, _ in docs_and_scores]

    async def asimilarity_search(
        self,
        query: str,
        k: int = 4,
    ) -> List[Document]:
        """Return documents most similar to query.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query
        """
        docs_and_scores = await self.asimilarity_search_with_score(query, k=k)
        return [doc for doc, _ in docs_and_scores]

    def similarity_search_by_vector(
        self, embedding: List[float], k: int = 4
    ) -> List[Document]:
        """Return documents closest to the given embedding.

        Args:
            embedding: Embedding to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query
        """
        docs_and_scores = self.similarity_search_by_vector_with_score(embedding, k=k)
        return [doc for doc, _ in docs_and_scores]

    async def asimilarity_search_by_vector(
        self, embedding: List[float], k: int = 4
    ) -> List[Document]:
        """Return documents closest to the given embedding.

        Args:
            embedding: Embedding to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query
        """
        docs_and_scores = await self.asimilarity_search_by_vector_with_score(
            embedding, k=k
        )
        return [doc for doc, _ in docs_and_scores]

    def _similarity_search_with_relevance_scores(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> List[Tuple[Document, float]]:
        """
        Since Upstash always returns relevance scores, default implementation is used.
        """
        return self.similarity_search_with_score(query, k=k, **kwargs)

    async def _asimilarity_search_with_relevance_scores(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> List[Tuple[Document, float]]:
        """
        Since Upstash always returns relevance scores, default implementation is used.
        """
        return await self.asimilarity_search_with_score(query, k=k, **kwargs)

    def max_marginal_relevance_search_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """Return docs selected using the maximal marginal relevance.

        Maximal marginal relevance optimizes for similarity to query AND diversity
        among selected documents.

        Args:
            embedding: Embedding to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            fetch_k: Number of Documents to fetch to pass to MMR algorithm.
            lambda_mult: Number between 0 and 1 that determines the degree
                        of diversity among the results with 0 corresponding
                        to maximum diversity and 1 to minimum diversity.
                        Defaults to 0.5.
        Returns:
            List of Documents selected by maximal marginal relevance.
        """
        results = self._index.query(
            vector=embedding,
            top_k=fetch_k,
            include_vectors=True,
            include_metadata=True,
        )
        mmr_selected = maximal_marginal_relevance(
            np.array([embedding], dtype=np.float32),
            [item.vector for item in results],
            k=k,
            lambda_mult=lambda_mult,
        )
        selected = [results[i].metadata for i in mmr_selected]
        return [
            Document(page_content=metadata.pop((self._text_key)), metadata=metadata)  # type: ignore since include_metadata=True
            for metadata in selected
        ]

    async def amax_marginal_relevance_search_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """Return docs selected using the maximal marginal relevance.

        Maximal marginal relevance optimizes for similarity to query AND diversity
        among selected documents.

        Args:
            embedding: Embedding to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            fetch_k: Number of Documents to fetch to pass to MMR algorithm.
            lambda_mult: Number between 0 and 1 that determines the degree
                        of diversity among the results with 0 corresponding
                        to maximum diversity and 1 to minimum diversity.
                        Defaults to 0.5.
        Returns:
            List of Documents selected by maximal marginal relevance.
        """
        results = await self._async_index.query(
            vector=embedding,
            top_k=fetch_k,
            include_vectors=True,
            include_metadata=True,
        )
        mmr_selected = maximal_marginal_relevance(
            np.array([embedding], dtype=np.float32),
            [item.vector for item in results],
            k=k,
            lambda_mult=lambda_mult,
        )
        selected = [results[i].metadata for i in mmr_selected]
        return [
            Document(page_content=metadata.pop((self._text_key)), metadata=metadata)  # type: ignore since include_metadata=True
            for metadata in selected
        ]

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """Return docs selected using the maximal marginal relevance.

        Maximal marginal relevance optimizes for similarity to query AND diversity
        among selected documents.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            fetch_k: Number of Documents to fetch to pass to MMR algorithm.
            lambda_mult: Number between 0 and 1 that determines the degree
                        of diversity among the results with 0 corresponding
                        to maximum diversity and 1 to minimum diversity.
                        Defaults to 0.5.
        Returns:
            List of Documents selected by maximal marginal relevance.
        """
        embedding = self._embed_query(query)
        return self.max_marginal_relevance_search_by_vector(
            embedding=embedding, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
        )

    async def amax_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """Return docs selected using the maximal marginal relevance.

        Maximal marginal relevance optimizes for similarity to query AND diversity
        among selected documents.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.
            fetch_k: Number of Documents to fetch to pass to MMR algorithm.
            lambda_mult: Number between 0 and 1 that determines the degree
                        of diversity among the results with 0 corresponding
                        to maximum diversity and 1 to minimum diversity.
                        Defaults to 0.5.
        Returns:
            List of Documents selected by maximal marginal relevance.
        """
        embedding = self._embed_query(query)
        return await self.amax_marginal_relevance_search_by_vector(
            embedding=embedding, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
        )

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        embedding_chunk_size: int = 1000,
        batch_size: int = 32,
        text_key: str = "text",
        index: Optional[Index] = None,
        async_index: Optional[AsyncIndex] = None,
        index_url: Optional[str] = None,
        index_token: Optional[str] = None,
    ) -> UpstashVectorStore:
        """Create a new UpstashVectorStore from a list of texts.

        Example:
            .. code-block:: python
                from langchain_community.vectorstores.upstash import UpstashVectorStore
                from langchain_community.embeddings import OpenAIEmbeddings

                embeddings = OpenAIEmbeddings()
                vector_store = UpstashVectorStore.from_texts(
                    texts,
                    embeddings,
                )
        """
        vector_store = cls(
            embedding=embedding,
            text_key=text_key,
            index=index,
            async_index=async_index,
            index_url=index_url,
            index_token=index_token,
        )

        vector_store.add_texts(
            texts,
            metadatas=metadatas,
            ids=ids,
            batch_size=batch_size,
            embedding_chunk_size=embedding_chunk_size,
        )
        return vector_store

    def delete(
        self,
        ids: Optional[List[str]] = None,
        delete_all: Optional[bool] = None,
        batch_size=1000,
    ) -> None:
        """Delete by vector IDs

        Args:
            ids: List of ids to delete.
            delete_all: Delete all vectors in the index.
            batch_size: Batch size to use when deleting the embeddings.
            Upstash supports at max 1000 deletions per request.
        """

        if delete_all:
            self._index.reset()
        elif ids is not None:
            for batch in batch_iterate(batch_size, ids):
                self._index.delete(ids=batch)
        else:
            raise ValueError("Either ids or delete_all should be provided")

        return None

    async def adelete(
        self,
        ids: Optional[List[str]] = None,
        delete_all: Optional[bool] = None,
        batch_size=1000,
    ) -> None:
        """Delete by vector IDs

        Args:
            ids: List of ids to delete.
            delete_all: Delete all vectors in the index.
            batch_size: Batch size to use when deleting the embeddings.
            Upstash supports at max 1000 deletions per request.
        """

        if delete_all:
            await self._async_index.reset()
        elif ids is not None:
            for batch in batch_iterate(batch_size, ids):
                await self._async_index.delete(ids=batch)
        else:
            raise ValueError("Either ids or delete_all should be provided")

        return None

    def info(self):
        """Get statistics about the index.

        Returns:
            - total number of vectors
            - total number of vectors waiting to be indexed
            - total size of the index on disk in bytes
            - dimension count for the index
            - similarity function selected for the index
        """
        return self._index.info()

    async def ainfo(self):
        """Get statistics about the index.

        Returns:
            - total number of vectors
            - total number of vectors waiting to be indexed
            - total size of the index on disk in bytes
            - dimension count for the index
            - similarity function selected for the index
        """
        return await self._async_index.info()
