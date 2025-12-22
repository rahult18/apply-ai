-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.autofill_events (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL,
  user_id uuid NOT NULL,
  event_type text NOT NULL,
  payload jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT autofill_events_pkey PRIMARY KEY (id),
  CONSTRAINT autofill_events_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.autofill_runs(id),
  CONSTRAINT autofill_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.autofill_feedback (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  job_application_id uuid,
  run_id uuid,
  site_key text,
  question_signature text,
  correction jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT autofill_feedback_pkey PRIMARY KEY (id),
  CONSTRAINT autofill_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT autofill_feedback_job_application_id_fkey FOREIGN KEY (job_application_id) REFERENCES public.job_applications(id),
  CONSTRAINT autofill_feedback_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.autofill_runs(id)
);
CREATE TABLE public.autofill_runs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  job_application_id uuid NOT NULL,
  page_url text NOT NULL,
  dom_html text,
  dom_captured_at timestamp with time zone DEFAULT now(),
  plan_json jsonb,
  plan_summary jsonb,
  status text NOT NULL DEFAULT 'planned'::text CHECK (status = ANY (ARRAY['planned'::text, 'running'::text, 'needs_user'::text, 'failed'::text, 'submitted'::text, 'cancelled'::text])),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  dom_html_hash text,
  CONSTRAINT autofill_runs_pkey PRIMARY KEY (id),
  CONSTRAINT autofill_runs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT autofill_runs_job_application_id_fkey FOREIGN KEY (job_application_id) REFERENCES public.job_applications(id)
);
CREATE TABLE public.extension_connect_codes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  code_hash text NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  used_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT extension_connect_codes_pkey PRIMARY KEY (id),
  CONSTRAINT extension_connect_codes_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.job_applications (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  job_title text NOT NULL,
  company text NOT NULL,
  job_posted text,
  job_description text,
  url text NOT NULL,
  required_skills ARRAY DEFAULT '{}'::text[],
  preferred_skills ARRAY DEFAULT '{}'::text[],
  education_requirements ARRAY DEFAULT '{}'::text[],
  experience_requirements ARRAY DEFAULT '{}'::text[],
  keywords ARRAY DEFAULT '{}'::text[],
  job_site_type text NOT NULL CHECK (job_site_type = ANY (ARRAY['linkedin'::text, 'job-board'::text, 'y-combinator'::text, 'careers page'::text])),
  open_to_visa_sponsorship boolean DEFAULT false,
  status text DEFAULT 'saved'::text CHECK (status = ANY (ARRAY['saved'::text, 'applied'::text, 'interviewing'::text, 'rejected'::text, 'offer'::text, 'withdrawn'::text])),
  notes text,
  application_date date DEFAULT CURRENT_DATE,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  normalized_url text,
  jd_dom_html text,
  CONSTRAINT job_applications_pkey PRIMARY KEY (id),
  CONSTRAINT job_applications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.site_configs (
  site_key text NOT NULL,
  config jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT site_configs_pkey PRIMARY KEY (site_key)
);
CREATE TABLE public.site_domain_map (
  hostname text NOT NULL,
  site_key text NOT NULL,
  enabled boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT site_domain_map_pkey PRIMARY KEY (hostname),
  CONSTRAINT fk_site_key FOREIGN KEY (site_key) REFERENCES public.site_configs(site_key)
);
CREATE TABLE public.users (
  id uuid NOT NULL,
  email text NOT NULL UNIQUE,
  full_name text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  first_name text,
  last_name text,
  phone_number text,
  linkedin_url text,
  github_url text,
  portfolio_url text,
  other_url text,
  resume text,
  address text,
  city text,
  state text,
  zip_code text,
  country text,
  authorized_to_work_in_us boolean,
  visa_sponsorship boolean,
  visa_sponsorship_type text,
  desired_salary text,
  desired_location ARRAY,
  gender text,
  race text,
  veteran_status text,
  disability_status text,
  resume_text text,
  resume_profile jsonb,
  resume_parsed_at timestamp with time zone,
  resume_parse_status text,
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);