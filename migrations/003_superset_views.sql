-- Dashboard-ready views for Apache Superset.
-- These keep chart datasets simple while preserving the normalized warehouse schema.

create or replace view public.vw_superset_catalog_titles as
select
    f.title_catalog_key,
    t.title_key,
    t.show_id,
    t.title,
    t.description,
    ct.type_name as content_type,
    r.rating,
    d.full_date as date_added,
    d.year as date_added_year,
    d.month as date_added_month,
    d.month_name as date_added_month_name,
    d.quarter as date_added_quarter,
    d.day as date_added_day,
    d.day_of_week as date_added_day_of_week,
    d.day_name as date_added_day_name,
    coalesce(f.release_year, t.release_year) as release_year,
    f.title_count,
    f.movie_flag,
    f.tv_show_flag,
    f.duration_minutes,
    f.seasons_count,
    case
        when f.movie_flag then f.duration_minutes
        when f.tv_show_flag then f.seasons_count
        else null
    end as duration_value,
    case
        when f.movie_flag then 'minutes'
        when f.tv_show_flag then 'seasons'
        else null
    end as duration_unit,
    f.loaded_at
from public.fact_title_catalog f
join public.dim_title t
  on t.title_key = f.title_key
join public.dim_content_type ct
  on ct.content_type_key = f.content_type_key
join public.dim_rating r
  on r.rating_key = f.rating_key
left join public.dim_date_added d
  on d.date_added_key = f.date_added_key;

create or replace view public.vw_superset_title_genres as
select
    base.title_catalog_key,
    base.show_id,
    base.title,
    base.content_type,
    base.rating,
    base.date_added,
    base.date_added_year,
    base.date_added_month,
    base.date_added_month_name,
    base.date_added_quarter,
    base.release_year,
    base.title_count,
    base.movie_flag,
    base.tv_show_flag,
    g.genre_key,
    g.genre_name
from public.vw_superset_catalog_titles base
join public.bridge_catalog_genre bcg
  on bcg.title_catalog_key = base.title_catalog_key
join public.dim_genre g
  on g.genre_key = bcg.genre_key;

create or replace view public.vw_superset_title_countries as
select
    base.title_catalog_key,
    base.show_id,
    base.title,
    base.content_type,
    base.rating,
    base.date_added,
    base.date_added_year,
    base.date_added_month,
    base.date_added_month_name,
    base.date_added_quarter,
    base.release_year,
    base.title_count,
    base.movie_flag,
    base.tv_show_flag,
    c.country_key,
    c.country_name
from public.vw_superset_catalog_titles base
join public.bridge_catalog_country bcc
  on bcc.title_catalog_key = base.title_catalog_key
join public.dim_country c
  on c.country_key = bcc.country_key;

create or replace view public.vw_superset_title_people as
select
    base.title_catalog_key,
    base.show_id,
    base.title,
    base.content_type,
    base.rating,
    base.date_added,
    base.date_added_year,
    base.date_added_month,
    base.date_added_month_name,
    base.date_added_quarter,
    base.release_year,
    base.title_count,
    base.movie_flag,
    base.tv_show_flag,
    p.person_key,
    p.person_name,
    bcp.role
from public.vw_superset_catalog_titles base
join public.bridge_catalog_person bcp
  on bcp.title_catalog_key = base.title_catalog_key
join public.dim_person p
  on p.person_key = bcp.person_key;

comment on view public.vw_superset_catalog_titles is
    'Superset dataset: one row per Netflix title with fact and core dimension attributes.';

comment on view public.vw_superset_title_genres is
    'Superset dataset: one row per Netflix title and genre.';

comment on view public.vw_superset_title_countries is
    'Superset dataset: one row per Netflix title and country.';

comment on view public.vw_superset_title_people is
    'Superset dataset: one row per Netflix title and person role.';

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'bi_agent_reader') then
        execute 'grant select on table public.vw_superset_catalog_titles,
            public.vw_superset_title_genres,
            public.vw_superset_title_countries,
            public.vw_superset_title_people
            to bi_agent_reader';
    end if;
end $$;
