create extension if not exists vector;

create table if not exists chunks (
    id            bigserial primary key,
    chunk_id      text unique not null,
    source_url    text not null,
    source        text,
    category      text,
    page_title    text,
    heading       text,
    heading_level int,
    heading_path  text,
    section_order int,
    chunk_order   int,
    last_scraped  timestamptz,
    text          text not null,
    embedding     vector(384)
);

alter table chunks add column if not exists page_title text;
alter table chunks add column if not exists heading text;
alter table chunks add column if not exists heading_level int;
alter table chunks add column if not exists heading_path text;
alter table chunks add column if not exists section_order int;
alter table chunks add column if not exists chunk_order int;

create index if not exists chunks_embedding_hnsw_idx on chunks using hnsw (embedding vector_l2_ops);
create index if not exists chunks_source_url_idx on chunks (source_url);
create index if not exists chunks_source_idx on chunks (source);
create index if not exists chunks_category_idx on chunks (category);

create or replace function match_chunks(
    query_embedding vector(384),
    match_count int,
    source_urls text[] default null,
    sources text[] default null,
    categories text[] default null
)
returns table (
    chunk_id text,
    source_url text,
    source text,
    category text,
    page_title text,
    heading text,
    heading_path text,
    section_order int,
    chunk_order int,
    text text,
    similarity double precision
)
language sql
stable
as $$
    select
        c.chunk_id,
        c.source_url,
        c.source,
        c.category,
        c.page_title,
        c.heading,
        c.heading_path,
        c.section_order,
        c.chunk_order,
        c.text,
        1 - (c.embedding <=> query_embedding) as similarity
    from chunks c
    where (source_urls is null or c.source_url = any(source_urls))
      and (sources is null or c.source = any(sources))
      and (categories is null or c.category = any(categories))
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
