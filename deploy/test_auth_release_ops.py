"""Rollback gates use synthetic local databases only; no Docker/server calls."""
import shutil,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import auth_release_ops as ops
class RollbackGateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.before=self.root/'before.sqlite3';self.current=self.root/'accounts.sqlite3'
  with sqlite3.connect(self.before) as db:
   db.executescript("""CREATE TABLE users(id INTEGER,email TEXT,salt TEXT,password_hash TEXT,created_at INTEGER);INSERT INTO users VALUES(1,'qa@example.org','test-salt','legacy-scrypt',1);CREATE TABLE sessions(token_hash TEXT,user_id INTEGER,expires_at INTEGER);INSERT INTO sessions VALUES('test-session',1,9999999999);CREATE TABLE workspaces(user_id INTEGER,plant TEXT,readings TEXT);INSERT INTO workspaces VALUES(1,'{}','[]');CREATE TABLE imports(id INTEGER,user_id INTEGER,raw_csv TEXT);CREATE TABLE production_readings(user_id INTEGER,device_id TEXT,reading_date TEXT,kwh REAL);INSERT INTO production_readings VALUES(1,'test-source','2026-08-01',1);CREATE TABLE import_sources(import_id INTEGER,device_id TEXT);""")
  shutil.copy2(self.before,self.current)
  with sqlite3.connect(self.current) as db:db.execute('ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1')
  self.volume=patch.object(ops,'volume',return_value=self.root);self.volume.start()
 def tearDown(self):self.volume.stop();self.tmp.cleanup()
 def test_additive_active_column_allows_unchanged_data(self):self.assertTrue(ops.same_business_data(self.before))
 def test_password_format_upgrade_refuses_old_binary(self):
  with sqlite3.connect(self.current) as db:db.execute("UPDATE users SET password_hash='pbkdf2_sha256$600000$test'")
  self.assertFalse(ops.same_business_data(self.before))
 def test_inactive_account_refuses_old_binary_that_ignores_activation(self):
  with sqlite3.connect(self.current) as db:db.execute('UPDATE users SET active=0')
  self.assertFalse(ops.same_business_data(self.before))
 def test_new_session_is_not_discarded_by_rollback(self):
  with sqlite3.connect(self.current) as db:db.execute("INSERT INTO sessions VALUES('new-session',1,9999999999)")
  self.assertFalse(ops.same_business_data(self.before))
 def test_new_production_reading_refuses_rollback(self):
  with sqlite3.connect(self.current) as db:db.execute("INSERT INTO production_readings VALUES(1,'test-source','2026-08-02',2)")
  self.assertFalse(ops.same_business_data(self.before))
 def test_legacy_password_comparison_handles_env_quotes_and_spacing(self):
  self.assertTrue(ops.same_password("'abcd efgh ijkl mnop'",'abcdefghijklmnop'));self.assertFalse(ops.same_password('old-test-password','new-test-password'))
if __name__=='__main__':unittest.main()
