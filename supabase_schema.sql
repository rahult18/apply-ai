
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

create table public.users (
  id uuid not null,
  email text not null,
  full_name text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  first_name text null,
  last_name text null,
  phone_number text null,
  linkedin_url text null,
  github_url text null,
  portfolio_url text null,
  other_url text null,
  resume text null,
  address text null,
  city text null,
  state text null,
  zip_code text null,
  country text null,
  authorized_to_work_in_us boolean null,
  visa_sponsorship boolean null,
  visa_sponsorship_type text null,
  desired_salary text null,
  desired_location text[] null,
  gender text null,
  race text null,
  veteran_status text null,
  disability_status text null,
  resume_text text null,
  resume_profile jsonb null,
  resume_parsed_at timestamp with time zone null,
  resume_parse_status text null,
  constraint users_pkey primary key (id),
  constraint users_email_key unique (email),
  constraint users_id_fkey foreign KEY (id) references auth.users (id) on delete CASCADE
) TABLESPACE pg_default;

create table public.job_applications (
  id uuid not null default extensions.uuid_generate_v4 (),
  user_id uuid not null,
  job_title text not null,
  company text not null,
  job_posted text null,
  job_description text null,
  url text not null,
  required_skills text[] null default '{}'::text[],
  preferred_skills text[] null default '{}'::text[],
  education_requirements text[] null default '{}'::text[],
  experience_requirements text[] null default '{}'::text[],
  keywords text[] null default '{}'::text[],
  job_site_type text not null,
  open_to_visa_sponsorship boolean null default false,
  status text null default 'saved'::text,
  notes text null,
  application_date date null default CURRENT_DATE,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  normalized_url text null,
  constraint job_applications_pkey primary key (id),
  constraint job_applications_user_id_normalized_url_key unique (user_id, normalized_url),
  constraint job_applications_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE,
  constraint job_applications_job_site_type_check check (
    (
      job_site_type = any (
        array[
          'linkedin'::text,
          'job-board'::text,
          'y-combinator'::text,
          'careers page'::text
        ]
      )
    )
  ),
  constraint job_applications_status_check check (
    (
      status = any (
        array[
          'saved'::text,
          'applied'::text,
          'interviewing'::text,
          'rejected'::text,
          'offer'::text,
          'withdrawn'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

create table public.extension_connect_codes (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  code_hash text not null,
  expires_at timestamp with time zone not null,
  used_at timestamp with time zone null,
  created_at timestamp with time zone not null default now(),
  constraint extension_connect_codes_pkey primary key (id),
  constraint extension_connect_codes_user_id_fkey foreign KEY (user_id) references auth.users (id) on delete CASCADE
) TABLESPACE pg_default;

create unique INDEX IF not exists idx_extension_connect_codes_code_hash on public.extension_connect_codes using btree (code_hash) TABLESPACE pg_default;

create index IF not exists idx_extension_connect_codes_user_active on public.extension_connect_codes using btree (user_id, expires_at) TABLESPACE pg_default
where
  (used_at is null);

create table public.site_domain_map (
  hostname text not null,
  site_key text not null,
  enabled boolean null default true,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint site_domain_map_pkey primary key (hostname),
  constraint fk_site_key foreign KEY (site_key) references site_configs (site_key) on delete CASCADE
) TABLESPACE pg_default;

create trigger trg_site_domain_map_updated BEFORE
update on site_domain_map for EACH row
execute FUNCTION set_updated_at ();

create table public.site_configs (
  site_key text not null,
  config jsonb not null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint site_configs_pkey primary key (site_key)
) TABLESPACE pg_default;

create trigger trg_site_configs_updated BEFORE
update on site_configs for EACH row
execute FUNCTION set_updated_at ();
