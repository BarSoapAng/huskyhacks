create extension if not exists "pgcrypto";

begin;

do $$
declare
  history_user_id constant uuid := '11111111-1111-4111-8111-111111111111';
  history_identity_id constant uuid := '11111111-1111-4111-8111-111111111112';
  history_email constant text := 'browser-history@huskyhacks.local';
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
    history_user_id,
    'authenticated',
    'authenticated',
    history_email,
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
    history_identity_id,
    history_user_id::text,
    history_user_id,
    jsonb_build_object(
      'sub', history_user_id::text,
      'email', history_email,
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
  delete from public.productive_session;
  delete from public.procrastination_session;
  delete from public.visits;

  insert into public.visits (
    id,
    user_id,
    "timestamp",
    duration,
    url,
    normalized_url,
    domain,
    page_title,
    last_seen_at
  )
  values
    (
      '22222222-2222-4222-8222-222222222201',
      history_user_id,
      now() - interval '4 minutes',
      240,
      'http://127.0.0.1:5173/',
      '127.0.0.1/',
      '127.0.0.1',
      'HuskyHacks Dashboard',
      now()
    ),
    (
      '22222222-2222-4222-8222-222222222202',
      history_user_id,
      now() - interval '10 minutes',
      360,
      'https://chatgpt.com/codex',
      'chatgpt.com/codex',
      'chatgpt.com',
      'Codex',
      now() - interval '4 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222203',
      history_user_id,
      now() - interval '15 minutes',
      120,
      'http://127.0.0.1:54324/',
      '127.0.0.1/',
      '127.0.0.1',
      'Mailpit - 127.0.0.1',
      now() - interval '13 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222204',
      history_user_id,
      now() - interval '21 minutes',
      300,
      'http://127.0.0.1:54323/project/default/editor',
      '127.0.0.1/project/default/editor',
      '127.0.0.1',
      'Table Editor | Default Project | Default Organization | Supabase',
      now() - interval '16 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222205',
      history_user_id,
      now() - interval '27 minutes',
      240,
      'http://127.0.0.1:54323/project/default',
      '127.0.0.1/project/default',
      '127.0.0.1',
      'Default Project | Default Organization | Supabase',
      now() - interval '23 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222206',
      history_user_id,
      now() - interval '34 minutes',
      60,
      'http://127.0.0.1:8000/api/check-url',
      '127.0.0.1/api/check-url',
      '127.0.0.1',
      'http://127.0.0.1:8000/api/check-url',
      now() - interval '33 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222207',
      history_user_id,
      now() - interval '40 minutes',
      180,
      'https://vercel.com/',
      'vercel.com/',
      'vercel.com',
      'Vercel',
      now() - interval '37 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222208',
      history_user_id,
      now() - interval '47 minutes',
      300,
      'https://github.com/BarSoapAng/huskyhacks',
      'github.com/BarSoapAng/huskyhacks',
      'github.com',
      'BarSoapAng/huskyhacks',
      now() - interval '42 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222209',
      history_user_id,
      now() - interval '58 minutes',
      420,
      'https://docs.activitywatch.net/en/latest/examples/working-with-data.html',
      'docs.activitywatch.net/en/latest/examples/working-with-data.html',
      'docs.activitywatch.net',
      'Working with ActivityWatch Data',
      now() - interval '51 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222210',
      history_user_id,
      now() - interval '1 hour 9 minutes',
      480,
      'https://docs.activitywatch.net/en/latest/examples/working-with-data.html',
      'docs.activitywatch.net/en/latest/examples/working-with-data.html',
      'docs.activitywatch.net',
      'Working with ActivityWatch Data',
      now() - interval '1 hour 1 minute'
    ),
    (
      '22222222-2222-4222-8222-222222222211',
      history_user_id,
      now() - interval '1 hour 20 minutes',
      240,
      'http://localhost:5600/',
      'localhost/',
      'localhost',
      'ActivityWatch',
      now() - interval '1 hour 16 minutes'
    ),
    (
      '22222222-2222-4222-8222-222222222212',
      history_user_id,
      now() - interval '1 hour 28 minutes',
      300,
      'http://localhost:5600/',
      'localhost/',
      'localhost',
      'ActivityWatch',
      now() - interval '1 hour 23 minutes'
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
      '33333333-3333-4333-8333-333333333301',
      history_user_id,
      now() - interval '1 hour 28 minutes',
      false,
      1440,
      array[
        '22222222-2222-4222-8222-222222222212',
        '22222222-2222-4222-8222-222222222211',
        '22222222-2222-4222-8222-222222222210',
        '22222222-2222-4222-8222-222222222209'
      ]::uuid[]
    ),
    (
      '33333333-3333-4333-8333-333333333302',
      history_user_id,
      now() - interval '47 minutes',
      false,
      540,
      array[
        '22222222-2222-4222-8222-222222222208',
        '22222222-2222-4222-8222-222222222207',
        '22222222-2222-4222-8222-222222222206'
      ]::uuid[]
    ),
    (
      '33333333-3333-4333-8333-333333333303',
      history_user_id,
      now() - interval '27 minutes',
      true,
      1260,
      array[
        '22222222-2222-4222-8222-222222222205',
        '22222222-2222-4222-8222-222222222204',
        '22222222-2222-4222-8222-222222222203',
        '22222222-2222-4222-8222-222222222202',
        '22222222-2222-4222-8222-222222222201'
      ]::uuid[]
    );
end $$;

commit;
