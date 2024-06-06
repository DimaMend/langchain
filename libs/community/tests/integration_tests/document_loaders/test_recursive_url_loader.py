from datetime import datetime

from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader


async def test_async_recursive_url_loader() -> None:
    url = "https://docs.python.org/3.9/"
    loader = RecursiveUrlLoader(
        url,
        extractor=lambda _: "placeholder",
        use_async=True,
        max_depth=3,
        timeout=None,
        check_response_status=True,
    )
    docs = [document async for document in loader.alazy_load()]
    assert len(docs) == 512
    assert docs[0].page_content == "placeholder"


def test_async_recursive_url_loader_deterministic() -> None:
    url = "https://docs.python.org/3.9/"
    loader = RecursiveUrlLoader(
        url,
        use_async=True,
        max_depth=3,
        timeout=None,
    )
    docs = sorted(loader.load(), key=lambda d: d.metadata["source"])
    docs_2 = sorted(loader.load(), key=lambda d: d.metadata["source"])
    assert docs == docs_2


def test_sync_recursive_url_loader() -> None:
    url = "https://python.langchain.com/"
    loader = RecursiveUrlLoader(
        url,
        extractor=lambda _: "placeholder",
        use_async=False,
        max_depth=3,
        timeout=None,
        check_response_status=True,
    )
    docs = [document for document in loader.lazy_load()]
    with open(f"/Users/bagatur/Desktop/docs_{datetime.now()}.txt", "w") as f:
        f.write("\n".join(doc.metadata["source"] for doc in docs))
    assert docs[0].page_content == "placeholder"
    # no duplicates
    deduped = [doc for i, doc in enumerate(docs) if doc not in docs[:i]]
    assert len(docs) == len(deduped)
    assert len(docs) == 512


def test_sync_async_equivalent() -> None:
    url = "https://docs.python.org/3.9/"
    loader = RecursiveUrlLoader(url, use_async=False, max_depth=2)
    async_loader = RecursiveUrlLoader(url, use_async=False, max_depth=2)
    docs = sorted(loader.load(), key=lambda d: d.metadata["source"])
    async_docs = sorted(async_loader.load(), key=lambda d: d.metadata["source"])
    assert docs == async_docs


def test_loading_invalid_url() -> None:
    url = "https://this.url.is.invalid/this/is/a/test"
    loader = RecursiveUrlLoader(
        url, max_depth=1, extractor=lambda _: "placeholder", use_async=False
    )
    docs = loader.load()
    assert len(docs) == 0


def test_sync_async_metadata_necessary_properties() -> None:
    url = "https://docs.python.org/3.9/"
    loader = RecursiveUrlLoader(url, use_async=False, max_depth=2)
    async_loader = RecursiveUrlLoader(url, use_async=False, max_depth=2)
    docs = loader.load()
    async_docs = async_loader.load()
    for doc in docs:
        assert "source" in doc.metadata
        assert "content_type" in doc.metadata
    for doc in async_docs:
        assert "source" in doc.metadata
        assert "content_type" in doc.metadata
