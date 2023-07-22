# Academic Research Consortium High Bleeding Risk (ARC HBR)

A primary purpose of this repository is attempting to calculate (or approximate) the ARC-HBR risk score [^1]. It is likely not possible to exactly calculate the exact score due to deficiencies in the data. However, having the approximate score may be useful because:
* An automated calculation of the score (accompanied by a concise expression of the underlying data, in order to allow for clinical judgement) may be a clinically useful decision-support tool in its own right while prescribing blood-thinning medication following acute coronary syndromes.
* The approximate calculation of the ARC-HBR score may be useful as a prognostic model for predicting bleeding risk, provided that it can be validated using appropriate bleeding data
* The approximate calculation of the ARC-HBR score could serve as a baseline in the search for prognostic models that work better with the data available.

Application of the ARC-HBR score sometimes modifies the score for data availability; for example in [^2]. The modifications used in this study will be described below.

This file outlines the ARC-HBR criteria, and how it will be calculated from the data available.

## Overview of Datasets

The following datasets are available for the calculation of the ARC-HBR score:
* **HIC** Health Information Collaborative Cardiovascular Dataset (Bristol Heart Institute, BRI)
    * Spans the Covid-19 period
    * Contains finished consultant episodes for secondary care, including diagnoses and procedures
    * Contains laboratory tests results, including blood count and urea and electrolytes
    * Contains secondary-care prescription information 
* **SWD** System-wide Dataset (BNSSG ICB)
    * Spans the time-period of the HIC
    * Includes primary-care patient attributes and activity
    * Is of secondary importance, due to the more fine-grained information contained in the HIC, but may fill in gaps relating to some demographic information or comorbidities.

The restriction to the Covid period may have implications for the use of the score in modelling bleeding risk. However, it does not have any bearing on prototyping a tool for directly calculating the score, because the form of data (the definitions of the data fields) does not depend on the presence or absence of Covid.

## ARC HBR Score Definition

The ARC HBR score is a numerical consensus-based score (rather than being a statistically-driven score), where the presence of a major criterion contributes a 1 to the total score, and a minor criterion contributes 0.5 to the total. A patient is considered at HBR if their score is at least 1 (e.g. due to one major criterion, or two minor criteria).

The sections below describe what constitutes major and minor criteria, and how these will be approximated by information in the datasets.

Many of the criteria have the property that the presence of a condition in the data implies the criterion is present, but the absence of the condition in the data does not imply the criterion is absent. For example, lack of information about intracranial haemorrhage (ICH) (in the Covid-19 period) does not imply lack of ICH *at any time* (required for the prior ICH criterion). As a result, the estimated ARC HBR score is a lower bound: a low score does not necessarily imply the patient is not at high bleeding risk. Any presentation of the calculated result should make this fact clear.

### Anaemia (Low Haemoglobin, Major/Minor)

Haemoglobin level < 11.0 g/dL is a major criterion (for men and women).

Haemoglobin `hb` greater than 11.0 g/dL is divided into two categories:
* Women: 11.0 g/dL <= hb < 11.9 g/dL is a minor criterion
* Men: 11.0 g/dL <= hb < 12.9 g/dL is a minor criterion

Any other haemoglobin level is not an ARC HBR criterion.

Haemoglobin level varies with time, and is captured in the data as either laboratory measurements from the full blood count, or potentially as anaemia codes from ICD-10 data in hospital episode statistics.

A blood test including an Hb measurement is often performed in the intervention episode, so this should be used to calculate the risk. If Hb from the index is not available, then a previous low Hb could be taken as a proxy to calculate the risk (the program should indicate that this has been done). 

In addition to the calculation using the same-episode Hb value, prior Hb measurement could be used to improve the performance of the score. This is not part of the ARC HBR calculation, but is discussed in connection with other HBR models **TODO link to where**. Test results should not be averaged over time; instead, what is relevant is whether the measurement dips below a threshold at any time.

### Thrombocytopenia (Low Platelet Count, Major)

Moderate or severe baseline thrombocytopenia (low platelet count) i, meaning count < 100e9/L, is a major criterion.

Baseline means before intervention. The platelet count can be obtained from measurements from the full blood count. This information is routinely collected in the index presentation.

### Chronic Kidney Disease (Major/Minor)

Severe or end-stage chronic kidney disease (CKD) is a major criterion; moderate CKD is a minor criterion.

The stages of chronic kidney disease map to both ICD-10 codes and estimated glomerular filtration rate measurements (eGFR, from urea and electrolytes laboratory results), as follows (see [here](https://www.nhs.uk/conditions/kidney-disease/diagnosis/)):

| Stage | ICD-10 | eGFR | ARC-HBR |
|-------|--------|------|---------|
| Stage 5, end-stage | N18.5 | eGFR < 15 ml/min | Major |
| Stage 4, severe | N18.4 | 15 ml/min <= eGFR < 30 ml/min | Major |
| Stage 3b, moderate | N18.3 | 30 ml/min <= eGFR < 45 ml/min | Minor |
| Stage 3a, moderate | N18.3 | 45 ml/min <= eGFR < 60 ml/min | Minor |
| Stage 2, mild | N18.2 | 60 ml/min <= eGFR < 90 ml/min | None |
| Stage 1, normal eGFR | N18.1 | eGFR > 90 ml/min | None |

The eGFR value obtained during the index episode should be used for the risk calculation. This value is also routinely collected, similarly to platelets and haemoglobin.

### Age (Minor)

Patient age at least 75 at the time of risk score calculation is considered a minor criterion. Age is obtained from the demographic information of both HIC and SWD.

The relevant time point for the calculation is the time of intervention (the PCI procedure, or shortly afterwords when therapy is being prescribed). Afterwords, the risk level theoretically changes (if the patient crosses the 75 boundary), although this is likely an arbitrary distinction (for example, for the duration of DAPT, the patient is likely either at risk due to age for the full period, or not at risk due to age).





### Oral Anticoagulant Use (Major)

Anticipated use of long-term OAC is considered a major criterion. There are two types of oral anticoagulants:
* Vitamin K antagonists: warfarin
* Direct oral anticoagulants: apixaban, dabigatran, edoxaban, rivaroxaban






[^1] [2019 Urban et al., Defining High Bleeding Risk in Patients Undergoing Percutaneous Coronary Intervention - A Consensus Document From the Academic Research Consortium for High Bleeding Risk](https://www.ahajournals.org/doi/10.1161/CIRCULATIONAHA.119.040167)

[^2] [2021 Urban et al., Assessing the Risks of Bleeding vs Thrombotic Events in Patients at High Bleeding Risk After Coronary Stent ImplantationThe ARC–High Bleeding Risk Trade-off Model](https://jamanetwork.com/journals/jamacardiology/fullarticle/2774812)