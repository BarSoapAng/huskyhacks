create extension if not exists "pgcrypto";

begin;

do $$
declare
  demo_user_id constant uuid := '11111111-1111-4111-8111-111111111111';
  demo_identity_id constant uuid := '11111111-1111-4111-8111-111111111112';
  demo_email constant text := 'browser-history@huskyhacks.local';
begin
  insert into auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    last_sign_in_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    is_super_admin,
    is_sso_user,
    is_anonymous
  )
  values (
    '00000000-0000-0000-0000-000000000000',
    demo_user_id,
    'authenticated',
    'authenticated',
    demo_email,
    crypt('demo-password', gen_salt('bf')),
    now(),
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"name":"Browser History Seed","seeded":true}'::jsonb,
    now() - interval '1 day',
    now(),
    false,
    false,
    false
  )
  on conflict (id) do update set
    aud = excluded.aud,
    role = excluded.role,
    email = excluded.email,
    encrypted_password = excluded.encrypted_password,
    email_confirmed_at = excluded.email_confirmed_at,
    last_sign_in_at = excluded.last_sign_in_at,
    raw_app_meta_data = excluded.raw_app_meta_data,
    raw_user_meta_data = excluded.raw_user_meta_data,
    updated_at = excluded.updated_at,
    is_sso_user = excluded.is_sso_user,
    is_anonymous = excluded.is_anonymous;

  insert into auth.identities (
    id,
    provider_id,
    user_id,
    identity_data,
    provider,
    last_sign_in_at,
    created_at,
    updated_at
  )
  values (
    demo_identity_id,
    demo_user_id::text,
    demo_user_id,
    jsonb_build_object(
      'sub', demo_user_id::text,
      'email', demo_email,
      'email_verified', true,
      'phone_verified', false
    ),
    'email',
    now(),
    now() - interval '1 day',
    now()
  )
  on conflict (provider_id, provider) do update set
    user_id = excluded.user_id,
    identity_data = excluded.identity_data,
    last_sign_in_at = excluded.last_sign_in_at,
    updated_at = excluded.updated_at;

  delete from public.allowed_sessions;
  delete from public.procrastination_session;
  delete from public.productive_session;

  insert into public.allowed_sessions (
    id,
    user_id,
    "timestamp",
    active,
    duration,
    visits
  )
  values
    (
      '44444444-4444-4444-8444-444444444401',
      demo_user_id,
      '2026-05-02 15:00:00-04'::timestamptz,
      false,
      900,
      '{}'::uuid[]
    ),
    (
      '44444444-4444-4444-8444-444444444402',
      demo_user_id,
      '2026-05-02 16:39:00-04'::timestamptz,
      false,
      720,
      '{}'::uuid[]
    );

  insert into public.procrastination_session (
    id,
    user_id,
    "timestamp",
    active,
    duration,
    visits
  )
  values
    (
      '55555555-5555-4555-8555-555555555501',
      demo_user_id,
      '2026-05-02 15:19:00-04'::timestamptz,
      false,
      1080,
      '{}'::uuid[]
    ),
    (
      '55555555-5555-4555-8555-555555555502',
      demo_user_id,
      '2026-05-02 15:43:00-04'::timestamptz,
      false,
      660,
      '{}'::uuid[]
    );

  insert into public.productive_session (
    id,
    user_id,
    "timestamp",
    active,
    duration,
    visits
  )
  values
    (
      '66666666-6666-4666-8666-666666666601',
      demo_user_id,
      '2026-05-02 16:01:00-04'::timestamptz,
      false,
      1500,
      '{}'::uuid[]
    ),
    (
      '66666666-6666-4666-8666-666666666602',
      demo_user_id,
      '2026-05-02 16:26:00-04'::timestamptz,
      false,
      840,
      '{}'::uuid[]
    ),
    (
      '66666666-6666-4666-8666-666666666603',
      demo_user_id,
      '2026-05-02 17:17:00-04'::timestamptz,
      true,
      1320,
      '{}'::uuid[]
    );
end $$;

commit;
