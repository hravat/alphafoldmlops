##RUN INS IDE LIKE DBEAVER
CREATE DATABASE chembl_35;

###RUN ON CONTAINER
pg_restore --no-owner -h localhost -p 5432 -U postgres -d data/chembl_35/chembl_35_postgresql/chembl_35_postgresql.dmp


---TABLE CHECKS 
SELECT COUNT(*) FROM  PUBLIC.activities UNION ALL
SELECT COUNT(*) FROM  PUBLIC.assays UNION ALL
SELECT COUNT(*) FROM  PUBLIC.compound_properties UNION ALL
SELECT COUNT(*) FROM  PUBLIC.compound_structures UNION ALL
SELECT COUNT(*) FROM  PUBLIC.drug_indication UNION ALL
SELECT COUNT(*) FROM  PUBLIC.target_components UNION ALL
SELECT COUNT(*) FROM  PUBLIC.target_dictionary;


----DATA PREP
CREATE TABLE public.chembl_ml_dataset AS
SELECT 
	a.activity_id,
    a.assay_id,
    a.molregno,
    a.standard_type,
    a.standard_value,
    a.standard_units,
    a.pchembl_value,
    s.assay_type,
    s.confidence_score,
    s.description AS assay_description,
    c.mw_freebase,
    c.alogp,
    c.hba,
    c.hbd,
    --c.ro5_violations,
    cs.canonical_smiles,
    di.mesh_heading,
    di.efo_term,
    --di.indication_class,
    t.pref_name AS target_name,
    t.target_type,
    tc.component_id
FROM 
    public.activities a
JOIN 
    public.assays s ON a.assay_id = s.assay_id
JOIN 
    public.compound_properties c ON a.molregno = c.molregno
JOIN 
    public.compound_structures cs ON a.molregno = cs.molregno
JOIN 
    public.drug_indication di ON a.molregno = di.molregno
JOIN 
    public.target_dictionary t ON s.tid = t.tid
JOIN 
    public.target_components tc ON tc.tid = t.tid;


pg_dump -U postgres -d chembl_35 -t public.chembl_ml_dataset -Fc -f chembl_ml_dataset.dump
