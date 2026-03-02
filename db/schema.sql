create table if not exists users (
  id varchar(128) primary key,
  email varchar(255) unique,
  password_hash varchar(255),
  auth_provider varchar(32) not null default 'password',
  created_at timestamptz not null default now()
);

create table if not exists api_profiles (
  id varchar(128) primary key,
  user_id varchar(128) not null references users(id) on delete cascade,
  name varchar(120) not null,
  provider_keys jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists saved_analyses (
  id varchar(128) primary key,
  user_id varchar(128) not null references users(id) on delete cascade,
  ticker varchar(24) not null,
  title varchar(160) not null,
  assumptions jsonb not null,
  output_summary jsonb not null,
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_saved_analyses_user_id on saved_analyses(user_id);
create index if not exists idx_saved_analyses_ticker on saved_analyses(ticker);
