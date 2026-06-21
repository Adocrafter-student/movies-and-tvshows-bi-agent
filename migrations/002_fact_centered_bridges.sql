-- Move many-to-many bridge tables from dim_title-centered keys to fact-centered keys.
-- This keeps fact_title_catalog as the central table in the dimensional model.

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

do $$
begin
    if to_regclass('public.bridge_title_genre') is not null then
        insert into public.bridge_catalog_genre (title_catalog_key, genre_key)
        select f.title_catalog_key, old_bridge.genre_key
        from public.bridge_title_genre old_bridge
        join public.fact_title_catalog f on f.title_key = old_bridge.title_key
        on conflict do nothing;
    end if;

    if to_regclass('public.bridge_title_country') is not null then
        insert into public.bridge_catalog_country (title_catalog_key, country_key)
        select f.title_catalog_key, old_bridge.country_key
        from public.bridge_title_country old_bridge
        join public.fact_title_catalog f on f.title_key = old_bridge.title_key
        on conflict do nothing;
    end if;

    if to_regclass('public.bridge_title_person') is not null then
        insert into public.bridge_catalog_person (title_catalog_key, person_key, role)
        select f.title_catalog_key, old_bridge.person_key, old_bridge.role
        from public.bridge_title_person old_bridge
        join public.fact_title_catalog f on f.title_key = old_bridge.title_key
        on conflict do nothing;
    end if;
end $$;

drop table if exists public.bridge_title_genre;
drop table if exists public.bridge_title_country;
drop table if exists public.bridge_title_person;

create index if not exists idx_bridge_catalog_genre_genre
    on public.bridge_catalog_genre(genre_key);

create index if not exists idx_bridge_catalog_country_country
    on public.bridge_catalog_country(country_key);

create index if not exists idx_bridge_catalog_person_person
    on public.bridge_catalog_person(person_key);

comment on table public.bridge_catalog_genre is
    'Many-to-many bridge between catalog fact rows and genres from listed_in.';

comment on table public.bridge_catalog_country is
    'Many-to-many bridge between catalog fact rows and production countries.';

comment on table public.bridge_catalog_person is
    'Many-to-many bridge between catalog fact rows and people, with role director or cast.';
