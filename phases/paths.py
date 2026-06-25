"""Project-wide path constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = PROJECT_ROOT / "corpus"
PROCESSED_DIR = CORPUS_DIR / "processed"
FACTS_FILE = PROCESSED_DIR / "facts.json"
CHUNKS_FILE = PROCESSED_DIR / "chunks.json"
EMBEDDED_CHUNKS_FILE = PROCESSED_DIR / "embedded_chunks.json"
URLS_FILE = CORPUS_DIR / "urls.json"
METADATA_DIR = CORPUS_DIR / "metadata"
SCHEME_REGISTRY_FILE = METADATA_DIR / "scheme_registry.json"
SOURCE_REGISTRY_FILE = METADATA_DIR / "source_registry.json"
RAW_DIR = CORPUS_DIR / "raw"
DATA_DIR = PROJECT_ROOT / "data"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
INDEX_REGISTRY_FILE = METADATA_DIR / "index_registry.json"

DEFAULT_COLLECTION_NAME = "mf_facts"
MIN_INDEX_CHUNK_COUNT = 50
