SELECT filename, applied_at FROM app_meta.schema_migrations ORDER BY filename;
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'app' ORDER BY tablename;
SELECT c.name AS category, m.name, m.price, m.is_available
FROM app.menus m JOIN app.categories c ON c.id=m.category_id ORDER BY c.sort_order, m.name;
SELECT table_number, is_active, access_epoch FROM app.restaurant_tables ORDER BY table_number;
-- Jangan SELECT password_hash, token_hash, qr_token.

