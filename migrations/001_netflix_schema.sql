-- Netflix Movies and TV Shows BI warehouse schema for Supabase PostgreSQL.
-- Grain: one row per Netflix title/show_id in fact_title_catalog.

create table if not exists public.dim_content_type (
    content_type_key bigserial primary key,
    type_name text not null unique
);

create table if not exists public.dim_rating (
    rating_key bigserial primary key,
    rating text not null unique
);

create table if not exists public.dim_date_added (
    date_added_key bigserial primary key,
    full_date date not null unique,
    year integer not null,
    month integer not null check (month between 1 and 12),
    month_name text not null,
    quarter integer not null check (quarter between 1 and 4),
    day integer not null check (day between 1 and 31),
    day_of_week integer not null check (day_of_week between 0 and 6),
    day_name text not null
);

create table if not exists public.dim_title (
    title_key bigserial primary key,
    show_id text not null unique,
    title text not null,
    description text,
    release_year integer,
    duration_text text,
    duration_minutes integer,
    seasons_count integer,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.dim_genre (
    genre_key bigserial primary key,
    genre_name text not null unique
);

create table if not exists public.dim_country (
    country_key bigserial primary key,
    country_name text not null unique
);

create table if not exists public.dim_person (
    person_key bigserial primary key,
    person_name text not null unique
);

create table if not exists public.fact_title_catalog (
    title_catalog_key bigserial primary key,
    title_key bigint not null unique references public.dim_title(title_key) on delete cascade,
    content_type_key bigint not null references public.dim_content_type(content_type_key) on delete restrict,
    rating_key bigint not null references public.dim_rating(rating_key) on delete restrict,
    date_added_key bigint references public.dim_date_added(date_added_key) on delete restrict,
    release_year integer,
    title_count integer not null default 1 check (title_count = 1),
    movie_flag boolean not null default false,
    tv_show_flag boolean not null default false,
    duration_minutes integer,
    seasons_count integer,
    loaded_at timestamptz not null default now()
);

create table if not exists public.bridge_catalog_genre (
    title_catalog_key bigint not null references public.fact_title_catalog(title_catalog_key) on delete cascade,
    genre_key bigint not null references public.dim_genre(genre_key) on delete restrict,
    primary key (title_catalog_key, genre_key)
);

create table if not exists public.bridge_catalog_country (
    title_catalog_key bigint not null references public.fact_title_catalog(title_catalog_key) on delete cascade,
    country_key bigint not null references public.dim_country(country_key) on delete restrict,
    primary key (title_catalog_key, country_key)
);

create table if not exists public.bridge_catalog_person (
    title_catalog_key bigint not null references public.fact_title_catalog(title_catalog_key) on delete cascade,
    person_key bigint not null references public.dim_person(person_key) on delete restrict,
    role text not null check (role in ('director', 'cast')),
    primary key (title_catalog_key, person_key, role)
);

create index if not exists idx_fact_title_catalog_content_type
    on public.fact_title_catalog(content_type_key);

create index if not exists idx_fact_title_catalog_rating
    on public.fact_title_catalog(rating_key);

create index if not exists idx_fact_title_catalog_date_added
    on public.fact_title_catalog(date_added_key);

create index if not exists idx_fact_title_catalog_release_year
    on public.fact_title_catalog(release_year);

create index if not exists idx_bridge_catalog_genre_genre
    on public.bridge_catalog_genre(genre_key);

create index if not exists idx_bridge_catalog_country_country
    on public.bridge_catalog_country(country_key);

create index if not exists idx_bridge_catalog_person_person
    on public.bridge_catalog_person(person_key);

comment on table public.fact_title_catalog is
    'One catalog fact row per Netflix title. Measures include title_count and parsed duration/seasons.';

comment on table public.bridge_catalog_genre is
    'Many-to-many bridge between catalog fact rows and genres from listed_in.';

comment on table public.bridge_catalog_country is
    'Many-to-many bridge between catalog fact rows and production countries.';

comment on table public.bridge_catalog_person is
    'Many-to-many bridge between catalog fact rows and people, with role director or cast.';
