# Golden Queries

These questions and SQL patterns are the Phase 3 evaluation loop for the Netflix BI agent.

## 1. Movie vs TV Show Counts

Question: How many Netflix titles are Movies vs TV Shows?

```sql
select
    ct.type_name,
    sum(f.title_count) as title_count
from public.fact_title_catalog f
join public.dim_content_type ct on ct.content_type_key = f.content_type_key
group by ct.type_name
order by title_count desc;
```

## 2. Top Countries by Title Count

Question: Which countries have the most titles?

```sql
select
    c.country_name,
    count(distinct f.title_catalog_key) as title_count
from public.fact_title_catalog f
join public.bridge_catalog_country bcc on bcc.title_catalog_key = f.title_catalog_key
join public.dim_country c on c.country_key = bcc.country_key
group by c.country_name
order by title_count desc
limit 10;
```

## 3. Titles Added by Year and Month

Question: How many titles were added each month?

```sql
select
    d.year,
    d.month,
    d.month_name,
    sum(f.title_count) as title_count
from public.fact_title_catalog f
join public.dim_date_added d on d.date_added_key = f.date_added_key
group by d.year, d.month, d.month_name
order by d.year, d.month;
```

## 4. Top Genres by Content Type

Question: What are the top genres for Movies and TV Shows?

```sql
select
    ct.type_name,
    g.genre_name,
    count(distinct f.title_catalog_key) as title_count
from public.fact_title_catalog f
join public.dim_content_type ct on ct.content_type_key = f.content_type_key
join public.bridge_catalog_genre bcg on bcg.title_catalog_key = f.title_catalog_key
join public.dim_genre g on g.genre_key = bcg.genre_key
group by ct.type_name, g.genre_name
order by ct.type_name, title_count desc;
```

## 5. Average Movie Duration by Rating

Question: What is the average movie duration by maturity rating?

```sql
select
    r.rating,
    round(avg(f.duration_minutes)::numeric, 1) as avg_duration_minutes,
    count(*) as movie_count
from public.fact_title_catalog f
join public.dim_content_type ct on ct.content_type_key = f.content_type_key
join public.dim_rating r on r.rating_key = f.rating_key
where ct.type_name = 'Movie'
  and f.duration_minutes is not null
group by r.rating
order by movie_count desc;
```

## 6. TV Shows by Seasons and Rating

Question: Which ratings have the longest TV shows by average seasons?

```sql
select
    r.rating,
    round(avg(f.seasons_count)::numeric, 1) as avg_seasons,
    count(*) as tv_show_count
from public.fact_title_catalog f
join public.dim_content_type ct on ct.content_type_key = f.content_type_key
join public.dim_rating r on r.rating_key = f.rating_key
where ct.type_name = 'TV Show'
  and f.seasons_count is not null
group by r.rating
order by avg_seasons desc, tv_show_count desc;
```

## 7. Directors With the Most Movies

Question: Which directors have the most Netflix movies?

```sql
select
    p.person_name as director,
    count(distinct f.title_catalog_key) as movie_count
from public.fact_title_catalog f
join public.dim_content_type ct on ct.content_type_key = f.content_type_key
join public.bridge_catalog_person bcp on bcp.title_catalog_key = f.title_catalog_key
join public.dim_person p on p.person_key = bcp.person_key
where ct.type_name = 'Movie'
  and bcp.role = 'director'
group by p.person_name
order by movie_count desc
limit 10;
```

## 8. Recent Additions by Genre

Question: Which genres were added most often in 2021?

```sql
select
    g.genre_name,
    count(distinct f.title_catalog_key) as title_count
from public.fact_title_catalog f
join public.dim_date_added d on d.date_added_key = f.date_added_key
join public.bridge_catalog_genre bcg on bcg.title_catalog_key = f.title_catalog_key
join public.dim_genre g on g.genre_key = bcg.genre_key
where d.year = 2021
group by g.genre_name
order by title_count desc
limit 10;
```
