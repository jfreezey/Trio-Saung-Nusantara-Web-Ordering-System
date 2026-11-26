DO $$
DECLARE
  a uuid; c uuid; t uuid; s uuid; ac uuid; o uuid; item uuid; other_session uuid;
BEGIN
  INSERT INTO app.users(name,email,password_hash,role) VALUES ('Test Admin','test@example.invalid','test-only-hash','admin') RETURNING id INTO a;
  BEGIN
    INSERT INTO app.users(name,email,password_hash,role) VALUES ('Other','other@example.invalid','test-only','admin');
    RAISE EXCEPTION 'FAIL: admin kedua diterima';
  EXCEPTION WHEN unique_violation THEN NULL; END;

  INSERT INTO app.users(name,email,password_hash,role) VALUES ('Kasir','cashier@example.invalid','test-only','cashier') RETURNING id INTO c;
  SELECT id INTO t FROM app.restaurant_tables WHERE table_number='1';
  INSERT INTO app.ordering_sessions(session_code,session_type,table_id) VALUES ('TEST-S','table',t) RETURNING id INTO s;
  BEGIN
    INSERT INTO app.ordering_sessions(session_code,session_type,table_id) VALUES ('TEST-S2','table',t);
    RAISE EXCEPTION 'FAIL: dua sesi terbuka diterima';
  EXCEPTION WHEN unique_violation THEN NULL; END;
  INSERT INTO app.customer_accesses(token_hash,access_type,table_id,table_epoch,session_id,expires_at)
    VALUES (repeat('a',64),'table',t,0,s,now()+interval '1 day') RETURNING id INTO ac;
  INSERT INTO app.ordering_sessions(session_code,session_type,table_id)
    VALUES ('TEST-OTHER','table','30000000-0000-4000-8000-000000000002') RETURNING id INTO other_session;
  BEGIN
    INSERT INTO app.customer_accesses(token_hash,access_type,table_id,table_epoch,session_id,expires_at)
      VALUES (repeat('d',64),'table',t,0,other_session,now()+interval '1 day');
    RAISE EXCEPTION 'FAIL: akses terikat ke sesi meja lain';
  EXCEPTION WHEN foreign_key_violation THEN NULL; END;
  BEGIN
    INSERT INTO app.orders(order_code,session_id,customer_access_id,fulfillment_type,checkout_key,checkout_fingerprint)
      VALUES ('TEST-WRONG',other_session,ac,'dine_in',gen_random_uuid(),repeat('b',64));
    RAISE EXCEPTION 'FAIL: order terikat ke sesi berbeda dari akses';
  EXCEPTION WHEN foreign_key_violation THEN NULL; END;
  INSERT INTO app.orders(order_code,session_id,customer_access_id,fulfillment_type,checkout_key,checkout_fingerprint)
    VALUES ('TEST-O',s,ac,'dine_in','40000000-0000-4000-8000-000000000001',repeat('b',64)) RETURNING id INTO o;
  BEGIN
    INSERT INTO app.orders(order_code,session_id,customer_access_id,fulfillment_type,checkout_key,checkout_fingerprint)
      VALUES ('TEST-O2',s,ac,'dine_in','40000000-0000-4000-8000-000000000001',repeat('b',64));
    RAISE EXCEPTION 'FAIL: checkout duplikat diterima';
  EXCEPTION WHEN unique_violation THEN NULL; END;
  INSERT INTO app.order_items(order_id,menu_id,menu_name_snapshot,unit_price_snapshot,original_quantity,quantity)
    VALUES (o,'20000000-0000-4000-8000-000000000001','Nasi Goreng',25000,2,2) RETURNING id INTO item;
  BEGIN
    UPDATE app.order_items SET quantity=-1 WHERE id=item;
    RAISE EXCEPTION 'FAIL: quantity negatif diterima';
  EXCEPTION WHEN check_violation THEN NULL; END;
  BEGIN
    UPDATE app.order_items SET quantity=3 WHERE id=item;
    RAISE EXCEPTION 'FAIL: quantity di atas jumlah awal diterima';
  EXCEPTION WHEN check_violation THEN NULL; END;
  BEGIN
    UPDATE app.menus SET price=-1 WHERE id='20000000-0000-4000-8000-000000000001';
    RAISE EXCEPTION 'FAIL: harga negatif diterima';
  EXCEPTION WHEN check_violation THEN NULL; END;
  BEGIN
    DELETE FROM app.menus WHERE id='20000000-0000-4000-8000-000000000001';
    RAISE EXCEPTION 'FAIL: menu yang dipakai transaksi dapat dihapus';
  EXCEPTION WHEN foreign_key_violation OR restrict_violation THEN NULL; END;
  BEGIN
    INSERT INTO app.payments(receipt_number,session_id,subtotal_amount,total_amount,payment_method,cash_received,paid_by,payment_key,payment_fingerprint)
      VALUES ('TEST-LOW',s,50000,50000,'cash',10000,c,gen_random_uuid(),repeat('c',64));
    RAISE EXCEPTION 'FAIL: tunai kurang dari tagihan diterima';
  EXCEPTION WHEN check_violation THEN NULL; END;
  INSERT INTO app.payments(receipt_number,session_id,subtotal_amount,total_amount,payment_method,cash_received,paid_by,payment_key,payment_fingerprint)
    VALUES ('TEST-R',s,50000,50000,'cash',50000,c,gen_random_uuid(),repeat('c',64));
  BEGIN
    INSERT INTO app.payments(receipt_number,session_id,subtotal_amount,total_amount,payment_method,cash_received,paid_by,payment_key,payment_fingerprint)
      VALUES ('TEST-R2',s,50000,50000,'cash',50000,c,gen_random_uuid(),repeat('c',64));
    RAISE EXCEPTION 'FAIL: pembayaran sesi yang sama diterima dua kali';
  EXCEPTION WHEN unique_violation THEN NULL; END;
END;
$$;

