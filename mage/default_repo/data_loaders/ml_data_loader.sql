SELECT * 
FROM PUBLIC.CHEMBL_ML_DATASET
WHERE standard_value is not null
LIMIT 10000;-- Docs: https://docs.mage.ai/guides/sql-blocks
--OFFSET {offset}
--LIMIT {limit};