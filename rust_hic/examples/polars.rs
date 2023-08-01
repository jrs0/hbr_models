use connectorx::prelude::*;
use std::convert::TryFrom;
use std::time::{Duration, Instant};

fn main() {
    let query = r#"select top 1000000 AIMTC_Pseudo_NHS as nhs_number,AIMTC_Age as age_at_episode,PBRspellID as spell_id,
    StartDate_ConsultantEpisode as episode_start,EndDate_ConsultantEpisode as episode_end,
    AIMTC_ProviderSpell_Start_Date as spell_start,AIMTC_ProviderSpell_End_Date as spell_end,
    diagnosisprimary_icd as primary_diagnosis,
    primaryprocedure_opcs as primary_procedure
    ,diagnosis1stsecondary_icd as secondary_diagnosis_0
    ,diagnosis2ndsecondary_icd as secondary_diagnosis_1
    ,diagnosis3rdsecondary_icd as secondary_diagnosis_2
    ,diagnosis4thsecondary_icd as secondary_diagnosis_3
    ,diagnosis5thsecondary_icd as secondary_diagnosis_4
    ,diagnosis6thsecondary_icd as secondary_diagnosis_5
    ,diagnosis7thsecondary_icd as secondary_diagnosis_6
    ,diagnosis8thsecondary_icd as secondary_diagnosis_7
    ,diagnosis9thsecondary_icd as secondary_diagnosis_8
    ,diagnosis10thsecondary_icd as secondary_diagnosis_9
    ,diagnosis11thsecondary_icd as secondary_diagnosis_10
    ,diagnosis12thsecondary_icd as secondary_diagnosis_11
    ,diagnosis13thsecondary_icd as secondary_diagnosis_12
    ,diagnosis14thsecondary_icd as secondary_diagnosis_13
    ,diagnosis15thsecondary_icd as secondary_diagnosis_14
    ,diagnosis16thsecondary_icd as secondary_diagnosis_15
    ,diagnosis17thsecondary_icd as secondary_diagnosis_16
    ,diagnosis18thsecondary_icd as secondary_diagnosis_17
    ,diagnosis19thsecondary_icd as secondary_diagnosis_18
    ,diagnosis20thsecondary_icd as secondary_diagnosis_19
    ,diagnosis21stsecondary_icd as secondary_diagnosis_20
    ,diagnosis22ndsecondary_icd as secondary_diagnosis_21
    ,diagnosis23rdsecondary_icd as secondary_diagnosis_22
    ,procedure2nd_opcs as secondary_procedure_0
    ,procedure3rd_opcs as secondary_procedure_1
    ,procedure4th_opcs as secondary_procedure_2
    ,procedure5th_opcs as secondary_procedure_3
    ,procedure6th_opcs as secondary_procedure_4
    ,procedure7th_opcs as secondary_procedure_5
    ,procedure8th_opcs as secondary_procedure_6
    ,procedure9th_opcs as secondary_procedure_7
    ,procedure10th_opcs as secondary_procedure_8
    ,procedure11th_opcs as secondary_procedure_9
    ,procedure12th_opcs as secondary_procedure_10
    ,procedure13th_opcs as secondary_procedure_11
    ,procedure14th_opcs as secondary_procedure_12
    ,procedure15th_opcs as secondary_procedure_13
    ,procedure16th_opcs as secondary_procedure_14
    ,procedure17th_opcs as secondary_procedure_15
    ,procedure18th_opcs as secondary_procedure_16
    ,procedure19th_opcs as secondary_procedure_17
    ,procedure20th_opcs as secondary_procedure_18
    ,procedure21st_opcs as secondary_procedure_19
    ,procedure22nd_opcs as secondary_procedure_20
    ,procedure23rd_opcs as secondary_procedure_21
    ,procedure24th_opcs as secondary_procedure_22
    from abi.dbo.vw_apc_sem_001 where datalength(AIMTC_Pseudo_NHS) > 0 and datalength(pbrspellid) > 0
    order by nhs_number, spell_id"#;

    let start = Instant::now();
    let mut source_conn = SourceConn::try_from("mssql://XSW-000-SP09/ABI?trusted_connection=true")
        .expect("parse conn str failed");
    println!("Connected to source");
    let queries = &[CXQuery::from(query)];
    let destination = get_arrow2(&source_conn, None, queries).expect("run failed");
    let duration = start.elapsed();
    println!("Time taken to fetch HES data is: {:?}", duration);

    let df = destination.polars().expect("Should have worked");
    mssql://XSW-000-SP09/ABI?trusted_connection=true    println!("{df}");
}
