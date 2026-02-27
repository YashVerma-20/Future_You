"""Flask extensions initialization."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
from elasticsearch import Elasticsearch
import redis

# SQLAlchemy
db = SQLAlchemy()

# Flask-Migrate
migrate = Migrate()

# Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)

# External database clients (initialized in app factory)
qdrant_client = None
neo4j_driver = None
es_client = None
redis_client = None


def init_qdrant(app):
    """Initialize Qdrant client."""
    global qdrant_client
    qdrant_client = QdrantClient(
        host=app.config['QDRANT_HOST'],
        port=app.config['QDRANT_PORT']
    )
    
    # Create collections if they don't exist
    _create_qdrant_collections()


def _create_qdrant_collections():
    """Create Qdrant collections for embeddings."""
    from qdrant_client.models import Distance, VectorParams
    
    collections = ['resume_embeddings', 'job_embeddings']
    
    for collection in collections:
        try:
            qdrant_client.get_collection(collection)
        except Exception:
            qdrant_client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )


def init_neo4j(app):
    """Initialize Neo4j driver."""
    global neo4j_driver
    neo4j_driver = GraphDatabase.driver(
        app.config['NEO4J_URI'],
        auth=(app.config['NEO4J_USER'], app.config['NEO4J_PASSWORD'])
    )


def init_elasticsearch(app):
    """Initialize Elasticsearch client."""
    global es_client
    es_client = Elasticsearch([app.config['ELASTICSEARCH_URL']])
    
    # Create indices if they don't exist
    _create_es_indices()


def _create_es_indices():
    """Create Elasticsearch indices."""
    index_name = 'jobs'
    
    if not es_client.indices.exists(index=index_name):
        es_client.indices.create(
            index=index_name,
            body={
                'mappings': {
                    'properties': {
                        'title': {'type': 'text', 'analyzer': 'standard'},
                        'description': {'type': 'text', 'analyzer': 'standard'},
                        'skills': {'type': 'keyword'},
                        'company': {'type': 'text', 'analyzer': 'standard'},
                        'location': {'type': 'text', 'analyzer': 'standard'},
                        'created_at': {'type': 'date'}
                    }
                }
            }
        )


def init_redis(app):
    """Initialize Redis client."""
    global redis_client
    redis_client = redis.from_url(app.config['REDIS_URL'])


def close_extensions():
    """Close all extension connections."""
    if neo4j_driver:
        neo4j_driver.close()
