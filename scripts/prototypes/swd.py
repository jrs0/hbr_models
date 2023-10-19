import sqlalchemy as sql
import pandas as pd
import time
import numpy as np

def make_attributes_query(start_date, end_date, patient_ids):
    '''
    - **Linking columns** the columns that will be used to link a row in the attributes to a HES row are `nhs_number` and `attribute_period`
    - **Unnecessary metadata columns** the following columns are not needed and have been excluded from the dataset
        - mabatch: not sure what it is
        - process_id, process_id_pseudo: no need to know anything about the process used to fill the attribute period
        - processed_date, inserted_date: just going to use attribute period instead

    You have to add the nhs_number not
    null condition, otherwise pandas will convert the column
    to floating point (with the associated undefined equality
    comparison which comes along with it).
    '''
    patient_id_list = ','.join([f"'{x}'" for x in patient_ids.tolist()])
    return (
        "select "
        #" ProcessID_Pseudo"
        #" ProcessDate"
        " NHSNumberWasValid"
        ", nhs_number as patient_id"
        #", Process_ID"
        #", InsertedDate"
        #", MABATCH"
        ", attribute_period"
        ", homeless"
        ", practice_code"
        ", age"
        ", sex"
        ", smoking"
        ", bmi"
        ", ethnicity"
        ", veteran"
        ", lsoa"
        ", religion"
        ", prim_language"
        ", marital"
        ", sexual_orient"
        ", gender_identity"
        ", pregnancy"
        ", alcohol_cscore"
        ", alcohol_units"
        ", gppaq"
        ", health_check"
        ", mmr1"
        ", mmr2"
        ", qrisk2_3"
        ", live_birth"
        ", newborn_check"
        ", infant_feeding"
        ", newborn_weight"
        ", diabetes_gest"
        ", polypharmacy_repeat"
        ", polypharmacy_acute"
        ", hearing_impair"
        ", visual_impair"
        ", phys_disability"
        ", efi_category"
        ", eol_plan"
        ", pref_death"
        ", epaccs"
        ", dna_cpr"
        ", is_carer"
        ", has_carer"
        ", housebound"
        ", nh_rh"
        ", organ_transplant"
        ", screen_eye"
        ", screen_cervical"
        ", screen_breast"
        ", screen_bowel"
        ", screen_aaa"
        ", egfr"
        ", fev1"
        ", mrc_dyspnoea"
        ", gout"
        ", inflam_arthritic"
        ", osteoarthritis"
        ", anaemia_other"
        ", anaemia_iron"
        ", coag"
        ", sickle"
        ", osteoporosis"
        ", ricketts"
        ", cancer_lung"
        ", cancer_breast"
        ", cancer_bowel"
        ", cancer_prostate"
        ", cancer_leuklymph"
        ", cancer_cervical"
        ", cancer_ovarian"
        ", cancer_melanoma"
        ", cancer_nonmaligskin"
        ", cancer_headneck"
        ", cancer_giliver"
        ", cancer_other"
        ", cancer_metase"
        ", cancer_bladder"
        ", cancer_kidney"
        ", cancer_lung_year"
        ", cancer_breast_year"
        ", cancer_bowel_year"
        ", cancer_prostate_year"
        ", cancer_leuklymph_year"
        ", cancer_cervical_year"
        ", cancer_ovarian_year"
        ", cancer_melanoma_year"
        ", cancer_nonmaligskin_year"
        ", cancer_headneck_year"
        ", cancer_giliver_year"
        ", cancer_other_year"
        ", cancer_metase_year"
        ", cancer_bladder_year"
        ", cancer_kidney_year"
        ", ihd_nonmi"
        ", af"
        ", arrhythmia_other"
        ", stroke"
        ", ihd_mi"
        ", hf"
        ", ht"
        ", bp_date"
        ", bp_reading"
        ", vasc_dis"
        ", cardio_other"
        ", eczema"
        ", psoriasis"
        ", pre_diabetes"
        ", diabetes_1"
        ", diabetes_2"
        ", diabetes_retina"
        ", thyroid"
        ", endocrine_other"
        ", coeliac"
        ", stomach"
        ", ibd"
        ", ibs"
        ", liver_alcohol"
        ", liver_nafl"
        ", hep_b"
        ", hep_c"
        ", liver_other"
        ", endometriosis"
        ", uterine"
        ", pelvic"
        ", poly_ovary"
        ", abortion"
        ", miscarriage"
        ", contraception"
        ", incont_urinary"
        ", nose"
        ", angio_anaph"
        ", hiv"
        ", obesity"
        ", dep_alcohol"
        ", dep_opioid"
        ", dep_cocaine"
        ", dep_cannabis"
        ", dep_benzo"
        ", dep_other"
        ", adhd"
        ", sad"
        ", depression"
        ", disorder_eating"
        ", smi"
        ", disorder_pers"
        ", ptsd"
        ", self_harm"
        ", back_pain"
        ", fragility"
        ", neuro_various"
        ", autism"
        ", fatigue"
        ", neuro_pain"
        ", dementia"
        ", learning_diff"
        ", epilepsy"
        ", learning_dis"
        ", migraine"
        ", mnd"
        ", ms"
        ", parkinsons"
        ", macular_degen"
        ", cataracts"
        ", ckd"
        ", asthma"
        ", copd"
        ", cystic_fibrosis"
        ", lung_restrict"
        ", tb"
        ", amputations"
        ", measles_mumps"
        ", qof_af"
        ", qof_chd"
        ", qof_hf"
        ", qof_ht"
        ", qof_pad"
        ", qof_stroke"
        ", qof_asthma"
        ", qof_copd"
        ", qof_obesity"
        ", qof_cancer"
        ", qof_ckd"
        ", qof_diabetes"
        ", qof_pall"
        ", qof_dementia"
        ", qof_depression"
        ", qof_epilepsy"
        ", qof_learndis"
        ", qof_mental"
        ", qof_osteoporosis"
        ", qof_rheumarth"
        + " from modelling_sql_area.dbo.primary_care_attributes"
        # Consider adding parentheses around the where .. between .. and construction.,
        # Don't think it makes any difference, but would be safer probably.
        f" where attribute_period between '{start_date}' and '{end_date}'"
        f" and nhs_number in ({patient_id_list})"
        " and nhs_number is not null"
        # This specific NHS number is used to mean "NHS number 
        # is not valid".
        " and nhs_number != '9000219621'"
    )
    
def get_attributes_data(start_date, end_date, patient_ids, num_chunks = 10):

    con = sql.create_engine("mssql+pyodbc://xsw")
    start = time.time()
    
    raw_data_list = []
    count = 1
    for chunk in np.array_split(patient_ids, num_chunks):
        print(f"Fetching chunk {count} of {num_chunks}")
        df = pd.read_sql(make_attributes_query(start_date, end_date, chunk), con)
        raw_data_list.append(df)
        count += 1
    
    # Reset the index to ensure that the index runs from 0..num_rows
    raw_data = pd.concat(raw_data_list).reset_index(drop=True)
    
    stop = time.time()
    print(f"Time to fetch attributes data: {stop - start}")
    return raw_data

def get_raw_attributes_data(start_date, end_date, patient_ids, from_file):
    """
    Fetch the patient attributes data from the primary_care_attributes table
    (onecare). Only obtain data for patients in the patient_ids list, which 
    corresponds to patients with index events. The start_date and end_date can
    be used to limit the date range (based on the attribute_period column).
    
    If from_file = False, the data is fetched from SQL and saved to 
    datasets/raw_attributes.pkl. If from_file = True, then all other parameters
    are ignored and the data is read from that file
    """
    if not from_file:
        print("Fetching attributes dataset from SQL")
        raw_attributes = get_attributes_data(start_date, end_date, patient_ids, 10)
        raw_attributes.to_pickle("datasets/raw_attributes.pkl")
    else:
        raw_attributes = pd.read_pickle("datasets/raw_attributes.pkl")
        
    # Exclude any rows where NHSNumberWasValid is not equal to 1
    nhs_number_not_valid = raw_attributes["NHSNumberWasValid"] != 1
    num_not_valid = np.sum(nhs_number_not_valid)
    print(f"Removing {num_not_valid} invalid NHS numbers")
    raw_attributes = raw_attributes[~nhs_number_not_valid]
    raw_attributes.drop(columns=["NHSNumberWasValid"], inplace=True)
    
    # Many columns encode true/false as 1/NA. Replace with zero
    replace_na_with_zero(raw_attributes)

    # Convert the attribute_period column to a datetime
    raw_attributes["attribute_period"] = pd.to_datetime(raw_attributes["attribute_period"])

    # This is necessary to defragment the frame. Not sure which step makes this
    # necessary, but the next line has a problem without it.
    raw_attributes = raw_attributes.copy()

    # Add swd_ prefix to all columns except those excluded below
    exclude = ["attribute_period", "patient_id"]
    new_columns = ["swd_" + x if (x not in exclude) else x for x in raw_attributes.columns]
    raw_attributes.columns = new_columns

    # Add an ID column to use for joining later
    raw_attributes["attribute_id"] = raw_attributes.reset_index(drop=True).index    
    
    return raw_attributes
    
def replace_na_with_zero(raw_attributes):
    """
    Many column in the primary care attributes data use NA
    as a marker for 0. It is important to replace these NAs
    with zero before performing a join of the attributes onto
    a larger table, which could produce NAs that mean "row
    was not present in attributes"). The raw attributes 
    argument is modified in place
    """
    na_means_zero = [
        "abortion",
        "adhd",
        "af",
        "amputations",
        "anaemia_iron",
        "anaemia_other",
        "angio_anaph",
        "arrhythmia_other",
        "asthma",
        "autism",
        "back_pain",
        "cancer_bladder",
        "cancer_bladder_year",
        "cancer_bowel",
        "cancer_bowel_year",
        "cancer_breast",
        "cancer_breast_year",
        "cancer_cervical",
        "cancer_cervical_year",
        "cancer_giliver",
        "cancer_giliver_year",
        "cancer_headneck",
        "cancer_headneck_year",
        "cancer_kidney",
        "cancer_kidney_year",
        "cancer_leuklymph",
        "cancer_leuklymph_year",
        "cancer_lung",
        "cancer_lung_year",
        "cancer_melanoma",
        "cancer_melanoma_year",
        "cancer_metase",
        "cancer_metase_year",
        "cancer_other",
        "cancer_other_year",
        "cancer_ovarian",
        "cancer_ovarian_year",
        "cancer_prostate",
        "cancer_prostate_year",
        "cardio_other",
        "cataracts",
        "ckd",
        "coag",
        "coeliac",
        "contraception",
        "copd",
        "cystic_fibrosis",
        "dementia",
        "dep_alcohol",
        "dep_benzo",
        "dep_cannabis",
        "dep_cocaine",
        "dep_opioid",
        "dep_other",
        "depression",
        "diabetes_1",
        "diabetes_2",
        "diabetes_gest",
        "diabetes_retina",
        "disorder_eating",
        "disorder_pers",
        "dna_cpr",
        "eczema",
        "endocrine_other",
        "endometriosis",
        "eol_plan",
        "epaccs",
        "epilepsy",
        "fatigue",
        "fragility",
        "gout",
        "has_carer",
        "health_check",
        "hearing_impair",
        "hep_b",
        "hep_c",
        "hf",
        "hiv",
        "homeless",
        "housebound",
        "ht",
        "ibd",
        "ibs",
        "ihd_mi",
        "ihd_nonmi",
        "incont_urinary",
        "inflam_arthritic",
        "is_carer",
        "learning_diff",
        "learning_dis",
        "live_birth",
        "liver_alcohol",
        "liver_nafl",
        "liver_other",
        "lung_restrict",
        "macular_degen",
        "measles_mumps",
        "migraine",
        "miscarriage",
        "mmr1",
        "mmr2",
        "mnd",
        "ms",
        "neuro_pain",
        "neuro_various",
        "newborn_check",
        "nh_rh",
        "nose",
        "obesity",
        "organ_transplant",
        "osteoarthritis",
        "osteoporosis",
        "parkinsons",
        "pelvic",
        "phys_disability",
        "poly_ovary",
        "pre_diabetes",
        "pregnancy",
        "psoriasis",
        "ptsd",
        "qof_af",
        "qof_asthma",
        "qof_chd",
        "qof_ckd",
        "qof_copd",
        "qof_dementia",
        "qof_depression",
        "qof_diabetes",
        "qof_epilepsy",
        "qof_hf",
        "qof_ht",
        "qof_learndis",
        "qof_mental",
        "qof_obesity",
        "qof_osteoporosis",
        "qof_pad",
        "qof_pall",
        "qof_rheumarth",
        "qof_stroke",
        "sad",
        "screen_aaa",
        "screen_bowel",
        "screen_breast",
        "screen_cervical",
        "screen_eye",
        "self_harm",
        "sickle",
        "smi",
        "stomach",
        "stroke",
        "tb",
        "thyroid",
        "uterine",
        "vasc_dis",
        "veteran",
        "visual_impair"
    ]
    raw_attributes[na_means_zero] = raw_attributes[na_means_zero].fillna(value=0)