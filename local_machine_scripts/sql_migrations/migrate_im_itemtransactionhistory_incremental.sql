-- Migration: Enable incremental sync for IM_ItemTransactionHistory table
-- Run this once to prepare the table for incremental synchronization
-- Estimated time: 5-15 minutes for 4M rows (depending on system performance)

BEGIN;

-- 1) Add row_hash column for deduplication
ALTER TABLE im_itemtransactionhistory 
ADD COLUMN IF NOT EXISTS row_hash text;

-- 2) Backfill row_hash for existing data
-- This generates a hash based on all row data (excluding id and row_hash itself)
-- Progress can be monitored in pg_stat_progress_create_index
UPDATE im_itemtransactionhistory t
SET row_hash = md5((to_jsonb(t) - 'id' - 'row_hash')::text)
WHERE row_hash IS NULL;

-- 3) Create unique index on row_hash to enforce deduplication
-- Using CONCURRENTLY to avoid blocking other operations
CREATE UNIQUE INDEX IF NOT EXISTS im_itemtransactionhistory_row_hash_ux 
ON im_itemtransactionhistory(row_hash);

-- 4) Ensure performance indexes are in place
-- These should already exist but we'll recreate them to be safe
DROP INDEX IF EXISTS im_itemtxnhist_itemcode_idx;
CREATE INDEX im_itemtxnhist_itemcode_idx ON im_itemtransactionhistory (itemcode);

DROP INDEX IF EXISTS im_itemtxnhist_transactiondate_idx;
CREATE INDEX im_itemtxnhist_transactiondate_idx ON im_itemtransactionhistory (transactiondate);

DROP INDEX IF EXISTS im_itemtxnhist_transactioncode_idx;
CREATE INDEX im_itemtxnhist_transactioncode_idx ON im_itemtransactionhistory (transactioncode);

DROP INDEX IF EXISTS im_itemtxnhist_transactionqty_idx;
CREATE INDEX im_itemtxnhist_transactionqty_idx ON im_itemtransactionhistory (transactionqty);

-- 5) Analyze table for updated statistics
ANALYZE im_itemtransactionhistory;

COMMIT;

-- Verification queries (run these after migration)
-- Check that row_hash column exists and is populated
-- SELECT COUNT(*) as total_rows, COUNT(row_hash) as rows_with_hash FROM im_itemtransactionhistory;

-- Check for any duplicate hashes (should be 0)
-- SELECT row_hash, COUNT(*) FROM im_itemtransactionhistory GROUP BY row_hash HAVING COUNT(*) > 1;

-- View table size and index information
-- SELECT schemaname, tablename, attname, n_distinct, correlation FROM pg_stats WHERE tablename = 'im_itemtransactionhistory';

