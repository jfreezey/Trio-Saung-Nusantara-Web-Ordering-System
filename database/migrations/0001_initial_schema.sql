-- Dijalankan oleh scripts/db.py migrate, dalam satu transaksi.
-- Jangan edit file ini setelah berhasil diterapkan pada database bersama.
CREATE SCHEMA app;
REVOKE ALL ON SCHEMA app FROM PUBLIC;

CREATE TABLE app.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (btrim(name) <> ''),
    email text NOT NULL CHECK (email = lower(btrim(email)) AND position('@' IN email) > 1),
    password_hash text NOT NULL CHECK (btrim(password_hash) <> ''),
    role text NOT NULL CHECK (role IN ('admin', 'cashier')),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (email)
);
CREATE UNIQUE INDEX users_one_admin ON app.users (role) WHERE role = 'admin';

CREATE TABLE app.categories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (btrim(name) <> ''),
    sort_order integer NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX categories_name_unique ON app.categories (lower(btrim(name)));

CREATE TABLE app.menus (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id uuid NOT NULL REFERENCES app.categories(id) ON DELETE RESTRICT,
    name text NOT NULL CHECK (btrim(name) <> ''),
    description text,
    price numeric(14,2) NOT NULL CHECK (price >= 0 AND price <> 'NaN'::numeric),
    image_url text,
    is_available boolean NOT NULL DEFAULT true,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX menus_category_idx ON app.menus(category_id);

CREATE TABLE app.restaurant_tables (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    table_number text NOT NULL UNIQUE CHECK (btrim(table_number) <> ''),
    qr_token text NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,
    is_active boolean NOT NULL DEFAULT true,
    -- Naik satu ketika sesi meja ditutup; akses halaman lama menjadi usang.
    access_epoch bigint NOT NULL DEFAULT 0 CHECK (access_epoch >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.ordering_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_code text NOT NULL UNIQUE CHECK (btrim(session_code) <> ''),
    session_type text NOT NULL CHECK (session_type IN ('table', 'takeaway')),
    table_id uuid REFERENCES app.restaurant_tables(id) ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'paid', 'cancelled')),
    opened_at timestamptz NOT NULL DEFAULT now(),
    closed_at timestamptz,
    closed_by uuid REFERENCES app.users(id) ON DELETE RESTRICT,
    CHECK ((session_type = 'table' AND table_id IS NOT NULL) OR
           (session_type = 'takeaway' AND table_id IS NULL)),
    CHECK ((status = 'open' AND closed_at IS NULL AND closed_by IS NULL) OR
           (status IN ('paid', 'cancelled') AND closed_at IS NOT NULL AND closed_by IS NOT NULL)),
    CHECK (closed_at IS NULL OR closed_at >= opened_at),
    UNIQUE (id, session_type),
    UNIQUE (id, table_id)
);
CREATE UNIQUE INDEX sessions_one_open_per_table ON app.ordering_sessions(table_id)
    WHERE status = 'open' AND table_id IS NOT NULL;
CREATE INDEX sessions_opened_idx ON app.ordering_sessions(opened_at);

CREATE TABLE app.customer_accesses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash text NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    access_type text NOT NULL CHECK (access_type IN ('table', 'takeaway')),
    table_id uuid REFERENCES app.restaurant_tables(id) ON DELETE RESTRICT,
    table_epoch bigint CHECK (table_epoch >= 0),
    session_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (expires_at > created_at),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at),
    CHECK ((access_type = 'table' AND table_id IS NOT NULL AND table_epoch IS NOT NULL) OR
           (access_type = 'takeaway' AND table_id IS NULL AND table_epoch IS NULL)),
    FOREIGN KEY (session_id, access_type) REFERENCES app.ordering_sessions(id, session_type) ON DELETE RESTRICT,
    FOREIGN KEY (session_id, table_id) REFERENCES app.ordering_sessions(id, table_id) ON DELETE RESTRICT,
    UNIQUE (id, session_id)
);
CREATE INDEX accesses_session_idx ON app.customer_accesses(session_id);
CREATE INDEX accesses_table_idx ON app.customer_accesses(table_id);
CREATE UNIQUE INDEX takeaway_one_access ON app.customer_accesses(session_id)
    WHERE access_type = 'takeaway' AND session_id IS NOT NULL;

CREATE TABLE app.orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_code text NOT NULL UNIQUE CHECK (btrim(order_code) <> ''),
    session_id uuid NOT NULL REFERENCES app.ordering_sessions(id) ON DELETE RESTRICT,
    customer_access_id uuid NOT NULL,
    fulfillment_type text NOT NULL CHECK (fulfillment_type IN ('dine_in', 'takeaway')),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    checkout_key uuid NOT NULL,
    -- SHA-256 dari payload checkout yang dinormalisasi oleh backend.
    checkout_fingerprint text NOT NULL CHECK (checkout_fingerprint ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (customer_access_id, session_id) REFERENCES app.customer_accesses(id, session_id) ON DELETE RESTRICT,
    UNIQUE (customer_access_id, checkout_key)
);
CREATE INDEX orders_session_idx ON app.orders(session_id);

CREATE TABLE app.order_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES app.orders(id) ON DELETE RESTRICT,
    menu_id uuid NOT NULL REFERENCES app.menus(id) ON DELETE RESTRICT,
    menu_name_snapshot text NOT NULL CHECK (btrim(menu_name_snapshot) <> ''),
    unit_price_snapshot numeric(14,2) NOT NULL CHECK (unit_price_snapshot >= 0 AND unit_price_snapshot <> 'NaN'::numeric),
    original_quantity integer NOT NULL CHECK (original_quantity > 0),
    quantity integer NOT NULL CHECK (quantity >= 0 AND quantity <= original_quantity),
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX items_order_idx ON app.order_items(order_id);
CREATE INDEX items_menu_idx ON app.order_items(menu_id);

CREATE TABLE app.order_adjustments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_item_id uuid NOT NULL REFERENCES app.order_items(id) ON DELETE RESTRICT,
    previous_quantity integer NOT NULL CHECK (previous_quantity > 0),
    new_quantity integer NOT NULL CHECK (new_quantity >= 0 AND new_quantity < previous_quantity),
    reason text NOT NULL CHECK (btrim(reason) <> ''),
    changed_by uuid NOT NULL REFERENCES app.users(id) ON DELETE RESTRICT,
    change_group_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX adjustments_item_idx ON app.order_adjustments(order_item_id);
CREATE INDEX adjustments_group_idx ON app.order_adjustments(change_group_id);

CREATE TABLE app.payments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_number text NOT NULL UNIQUE CHECK (btrim(receipt_number) <> ''),
    session_id uuid NOT NULL UNIQUE REFERENCES app.ordering_sessions(id) ON DELETE RESTRICT,
    subtotal_amount numeric(14,2) NOT NULL CHECK (subtotal_amount >= 0 AND subtotal_amount <> 'NaN'::numeric),
    total_amount numeric(14,2) NOT NULL CHECK (total_amount = subtotal_amount),
    payment_method text NOT NULL CHECK (payment_method IN ('cash', 'qris', 'debit_card', 'credit_card')),
    cash_received numeric(14,2),
    paid_by uuid NOT NULL REFERENCES app.users(id) ON DELETE RESTRICT,
    payment_key uuid NOT NULL UNIQUE,
    payment_fingerprint text NOT NULL CHECK (payment_fingerprint ~ '^[0-9a-f]{64}$'),
    paid_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((payment_method = 'cash' AND cash_received IS NOT NULL AND cash_received >= total_amount AND cash_received <> 'NaN'::numeric) OR
           (payment_method <> 'cash' AND cash_received IS NULL))
);
CREATE INDEX payments_paid_at_idx ON app.payments(paid_at);

CREATE FUNCTION app.set_updated_at() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['users','categories','menus','restaurant_tables','orders','order_items'] LOOP
        EXECUTE format('CREATE TRIGGER set_updated_at BEFORE UPDATE ON app.%I FOR EACH ROW EXECUTE FUNCTION app.set_updated_at()', t);
    END LOOP;
    FOREACH t IN ARRAY ARRAY['users','categories','menus','restaurant_tables','ordering_sessions','customer_accesses','orders','order_items','order_adjustments','payments'] LOOP
        EXECUTE format('ALTER TABLE app.%I ENABLE ROW LEVEL SECURITY', t);
    END LOOP;
END;
$$;
REVOKE ALL ON ALL TABLES IN SCHEMA app FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA app FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
-- Tidak ada policy publik. Role backend disiapkan oleh provision-app.

