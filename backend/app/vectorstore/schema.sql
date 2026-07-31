-- Run once against the target Postgres (local dev, or Supabase's Postgres in prod).
-- Supabase: run via the SQL editor or `psql "$DATABASE_URL" -f schema.sql`.

create extension if not exists vector;

create table if not exists papers (
    canonical_id text primary key,
    title text not null,
    abstract text,
    year int,
    authors text[] not null default '{}',
    pmid text,
    doi text,
    semantic_scholar_id text,
    sources text[] not null default '{}',
    is_open_access boolean not null default false,
    citation_count int,
    link text,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now()
);

create index if not exists idx_papers_pmid on papers (pmid) where pmid is not null;
create index if not exists idx_papers_doi on papers (doi) where doi is not null;

-- 384-dim to match the default embedding model (BAAI/bge-small-en-v1.5).
create table if not exists chunks (
    id bigserial primary key,
    paper_canonical_id text not null references papers (canonical_id) on delete cascade,
    chunk_index int not null,
    section text not null default 'abstract',
    text text not null,
    embedding vector(384) not null,
    created_at timestamptz not null default now(),
    unique (paper_canonical_id, chunk_index)
);

-- HNSW is a reasonable default at this scale (thousands-to-low-millions of rows);
-- cosine distance matches fastembed's normalized bge embeddings.
create index if not exists idx_chunks_embedding on chunks
    using hnsw (embedding vector_cosine_ops);

create index if not exists idx_chunks_paper on chunks (paper_canonical_id);
