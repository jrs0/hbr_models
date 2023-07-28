# Bleeding and Ischaemic Risk Modelling

The purpose of the code in this repository is to develop tools to help clinicians assess bleeding and ischaemic risk in patients prescribed blood-thinning medication (such as dual antiplatelet therapy) following percutaneous coronary intervention (PCI) (e.g. stent implantation).

This file contains the plan for what models will be tried, the rationale, what data will be used, and the deployability of the results.

## Problem Overview

Patients who present at hospital with an acute coronary syndrome (ACS) (for example, a heart attack) may require a PCI procedure such as a stent implantation to re-open the affected coronary artery. Following procedures like this, blood-thinning medication is prescribed to reduce the risk of further clotting events (thrombotic events) -- either around the implanted stent, which is called stent thrombosis (ST), or due to the same underlying reasons causing the original ACS. Clotting can block arteries, leading to ischaemia (reduced blood flow to a region). This can lead to tissue death (infarction), such as myocardial infarction (MI) (tissue death in the myocardium, heart attack). Ischaemia can also occur in the brain, where it is referred to as stroke.

On the other hand, blood thinning medication can cause increased bleeding (due to the lack of clotting), which can be a serious complication in itself. Some patients are more prone to bleeding than others (those at high bleeding risk).

The clinician is required to balance the risk of thrombotic complications when prescribing medication. Both types of complications can be fatal, and the mortality rate may vary depending on the type of complication which occurs. 

For a model to be useful, it should be deployed in a manner that is useful to clinicians. This means:
* The risk prediction is suitably easy for clinicians to obtain, and integrates well with their current working practice. In particular, the use of the tools should not place a significant additional burden on the clinician to manually source information for use in the risk score calculation
* The risk prediction should be reliable, fast, and easy to use. Hospitals contain myriad slow, incompatible, and demoralising-to-use computer systems, which take up clinician time and provide questionable benefit (often because they are not used). Any risk prediction tool should not slip into this category, otherwise it may be better not to deploy it.
* The risk prediction tool should be possible to deploy. This means it should use data sources that are actually available in the deployment setting.
* The deployment tool should be verifieid. Software for clinical decision support can fall into two cateogries; roughly;
    * Not a medical device, if the tool simply presents information to the clinician that they could find elsewhere by themself, and the clinician still relies on their own expertise to make decisions
    * Medical device, if the tool makes calculations and/or draws conclusions and presents them, where the clinician is not able to view the underlying data or process by which the calculation was made.

See [here](https://www.possiblehealth.io/clinical-decision-support-tools-are-they-medical-devices-or-not/) for a readable overview. Do not treat information in this repository as authoritative. How the tool is classified depends on its intended purpose amongst other things. Any tools developed in this repository will be accompanied by an intended purpose. In addition, **all tools in this repository are for prototyping purposes, and not intended for direct deployment**.

## Previous Bleeding/Ischaemic Risk Prediction Work

2021 Urban et al.[^1] present a trade-off model for bleeding and thrombotic risk for patients having PCI, developed for use on patients who have already been determined to be at HBR. They use (a modified form of) the Academic Research Consortium (ARC) HBR definition[^2] to define what HBR means. Their model is based on survival analysis, and the outcome (for a given patient) is a probability of bleeding (in this case BARC 3 or 5 level[^3]) and a probability of thrombosis (MI or ST). These two probabilities constitute a trade-off, which is also adjusted by mortality (which is higher for patients with thrombotic complications than bleeding complications, meaning clinicians should bias slightly towards the bleeding complication side).

## High Bleeding Risk

Identifying patients at high bleeding risk is fundamentally important, both for highlighting patients who require care in prescribing therapy, and for defining a cohort of interest for modelling purposes.

There are two ways to obtain the bleeding risk: use a statistical model to calculate probability of bleeding; or use a consensus-based score thought (or subsequently verified) to correspond to bleeding risk.

Creating a statistical model requires a carefully prepared dataset with available patient data to use as input variables and a bleeding outcome that is clinically relevant (e.g. major bleeding, BARC 3 or 5). On the other hand, a consensus-based score can be directly calculated without needing the actual bleeding outcome information in the dataset. It cannot be verified, but it may have been verified elsewhere. In addition, by its nature as a consensus score, there is more direct clinical involvement in drawing the HBR conclusion, especially if the underlying patient characteristics are presented as part of the score; the clinician could potentially take more "ownership" of the decision.

This repository will focus on the ARC-HBR[^2] consensus-based definition of bleeding. This is a pragmatic result of the lack of BARC 3 and 5 major bleeding in available datasets (although it may be possible to use ICD-10 codes to approximate the major bleeding outcome). The ARC-HBR score has been validated in multiple studies, and found to correspond to major bleeding risk with moderate performance[^4].

The ARC-HBR score for the purpose of this work is described [here](arc_hbr.md).

## Bleeding Outcome Definition

The clinically relevant bleeding definition is BARC 3 or 5, as used in the ARC HBR definition. However, this definition is not readily available in the datasets used here, because it requires expert judgement (which is often performed manually in studies). However, it is possible to find proxies for major bleeding. For example, in hospital episode statistics, ICD-10 codes have been found to approximate major bleeding events. Here, two groups of ICD-10 codes will be used as a stand-in for major bleeding, for model development purposes:

* **Al-Ani Group** `bleeding_al_ani`: 
    This group has the advantage that it comes with positive predicted value (PPV) of 88%[^5] for identifying major bleeding; this means that if a code arises, then there is 88% chance it corresponds to a major bleeding event. Disadvantages include the location (Canada) and the difference in coding scheme (ICD-10CM), which means the coding practices may differ enough to modify the PPV. In addition, the major bleeding definition used in the paper is not BARC 3 or 5 (although aligns quite closely with it). In addition, the high PPV is at the expense of including potentially important codes, as noted elsewhere[^6].

    | Description | ICD-10CM Codes |
    |-------------|--------|
    | Subarachnoid hemorrhage |I60 |
    | Intracranial hemorrhage |I61 |
    | Subdural hemorrhage | I62 |
    | Upper gastrointestinal bleeding |  I85.0, K22.1, K22.6, K25.0, K25.2, K25.4, K25.6,K26.0, K26.2, K26.4, K26.6, K27.0, K27.2, K27.4,K27.6, K28.0, K28.2, K28.4, K28.6, K29.0, K31.80,K63.80, K92.0, K92.1, K92.2 |
    | Lower gastrointestinal bleeding |  K55.2, K51, K57, K62.5, K92.0, K92.1, K92.2 |

    This groups has been interpreted as the following set of (UK) ICD-10 codes:
    | Description | ICD-10 |
    |-------------|--------|
    | I60 | Subarachnoid haemorrhage |
    | I61 | Intracerebral haemorrhage |
    | I62 | Other nontraumatic intracranial haemorrhage |
    | I85.0 | Oesophageal varices with bleeding |
    | K22.1 | Ulcer of oesophagus |
    | K22.6 | Gastro-oesophageal laceration-haemorrhage syndrome |
    | K25.0 | Gastric ulcer : acute with haemorrhage |
    | K25.2 | Gastric ulcer : acute with both haemorrhage and perforation |
    | K25.4 | Gastric ulcer : chronic or unspecified with haemorrhage |
    | K25.6 | Gastric ulcer : chronic or unspecified with both haemorrhage and perforation |
    | K26.0 | Duodenal ulcer : acute with haemorrhage |
    | K26.2 | Duodenal ulcer : acute with both haemorrhage and perforation |
    | K26.4 | Duodenal ulcer : chronic or unspecified with haemorrhage |
    | K26.6 | Duodenal ulcer : chronic or unspecified with both haemorrhage and perforation |
    | K27.0 | Peptic ulcer, site unspecified : acute with haemorrhage |
    | K27.2 | Peptic ulcer, site unspecified : acute with both haemorrhage and perforation |
    | K27.4 | Peptic ulcer, site unspecified : chronic or unspecified with haemorrhage |
    | K27.6 | Peptic ulcer, site unspecified : chronic or unspecified with both haemorrhage and perforation |
    | K28.0 | Gastrojejunal ulcer : acute with haemorrhage |
    | K28.2 | Gastrojejunal ulcer : acute with both haemorrhage and perforation |
    | K28.4 | Gastrojejunal ulcer : chronic or unspecified with haemorrhage |
    | K28.6 | Gastrojejunal ulcer : chronic or unspecified with both haemorrhage and perforation |
    | K29.0 | Acute haemorrhagic gastritis |
    | K92.0 | Haematemesis |
    | K92.1 | Melaena |
    | K92.2 | Gastrointestinal haemorrhage, unspecified |
    | K55.2 | Angiodysplasia of colon |
    | K51 | Ulcerative colitis |
    | K57 | Diverticular disease of intestine |
    | K62.5 | Haemorrhage of anus and rectum |
    | 

    Inclusion/exclusion notes (to check):
    * The codes K31.80, K63.80,  were excluded because its description in ICD-10 did not appear to correspond exclusively to a definite bleeding event, and may reduce positive predictive value of the codes.
    * Keeping ulcerative colitis (K51), even though it is not directly a bleeding condition, as it was presumably determined to often occur with bleeding
    * Keeping diverticular disease of intestine (K57), even though it is not directly a bleeding condition, as it was presumably determined to often occur with bleeding
    * Note: K92.0, K92.1 and K92.2 occurred twice in the original list (applicable to both lower and upper gastrointestinal bleeding). Included only once in the derived list.

* **CADTH Group**
    This set of codes was used to calculate costs associated with major bleeding in connection with estimating costs resulting from DAPT duration. The group is as follows:
    | Descriptions | ICD-10 |
    |--------------|--------|
    | Gastrointestinal |I850 Esophageal varices with bleeding|
    || K250 Gastric ulcer, acute with hemorrhage| 
    ||K252 Gastric ulcer, acute with both hemorrhage and perforation|
    ||K254 Gastric ulcer, chronic or unspecified with hemorrhage|
    ||K256 Gastric ulcer, chronic or unspecified with both hemorrhage and perforation|
    ||K260 Duodenal ulcer, acute with hemorrhage|
    ||K262 Duodenal ulcer, acute with both hemorrhage and perforation|
    ||K264 Duodenal ulcer, chronic or unspecified with hemorrhage|
    ||K266 Duodenal ulcer, chronic or unspecified with both hemorrhage and perforation|
    ||K270 Peptic ulcer, acute with hemorrhage|
    ||K272 Peptic ulcer, acute with both hemorrhage and perforation|
    ||K274 Peptic ulcer, chronic or unspecified with hemorrhage|
    ||K276 Peptic ulcer, chronic or unspecified with both hemorrhage and perforation|
    ||K280 Gastrojejunal ulcer, acute with hemorrhage|
    ||K282 Gastrojejunal ulcer, acute with both hemorrhage and perforation|
    ||K284 Gastrojejunal ulcer, chronic or unspecified with hemorrhage|
    ||K286 Gastrojejunal ulcer, chronic or unspecified with both hemorrhage and perforation|
    ||K290 Acute hemorrhagic gastritis|
    ||K625 Hemorrhage of anus and rectum|
    ||K661 Hemoperitoneum|
    ||K920 Hematemesis|
    ||K921 Melena|
    ||K922 Gastrointestinal hemorrhage, unspecified|
    |Hematology |R58 Hemorrhage, not elsewhere classified|
    |Intracranial (other than hemorrhagic stroke) |I629 Intracranial hemorrhage (non-traumatic), unspecified|
    |Respiratory |R040 Epistaxis|
    ||R041 Hemorrhage from throat|
    ||R042 Hemoptysis|
    ||R048 Hemorrhage form other site in respiratory passages|
    ||R049 Hemorrhage from respiratory passages, unspecified|
    |Urogenital|N020-029 Recurrent and persistent hematuria R310, 311, 318 Unspecified hematuria|

* **ADAPTT Group**
    The ADAPTT trial[^7] was conducted in the UK, and uses ICD-10 codes to identify all bleeding events (i.e. BARC 2 - 5). This 


It is important to recognise that no group of ICD-10 codes corresponds exactly to major bleeding events. Any models developed using this outcome must interpret the results in light of this shortcoming.

## Modelling and Analysis

This section contains plans for different modelling approaches and descriptive analysis, along with references to the scripts that implement them.

### Bleeding/Ischaemia Survival Analysis using Hospital Episode Statistics

Survival analysis was used in the bleeding-thrombotic trade-off model[^1], in the HBR group. The aim of this analysis is to try to reproduce the results as closely as possible, using the definition of bleeding and ischaemia based on groups of ICD-10, and without restricting the cohort to the high-bleeding risk group. Variables that go into the model will also be drawn from groups of ICD-10 codes, corresponding to the risk factors identified in the paper[^1].

#### Dataset Definition

Each row of the dataset will be a patient with an index event which is either ACS or PCI (method specified in detail below), and has the following columns:
* **bleed_time** 1 if a bleeding event occurred in the follow up period (i.e. any time within the range of the raw data), 0 if no bleeding event occurred in the follow up period. This is the status column in when using `Surv` in R.
* **bleed_time**: The time between the index spell start time and the bleeding spell start time. This is the time column when using `Surv` in R.
* **pci_performed**: True if the index spell contained a PCI procedure. False if the index spell was ACS-only (conservatively or medically managed ACS)
* **age_at_index**: Patient age at the start of the index spell







[^1]: [2021 Urban et al., Assessing the Risks of Bleeding vs Thrombotic Events in Patients at High Bleeding Risk After Coronary Stent Implantation - The ARC–High Bleeding Risk Trade-off Model](https://jamanetwork.com/journals/jamacardiology/fullarticle/2774812)

[^2]: [2019 Urban et al., Defining High Bleeding Risk in Patients Undergoing Percutaneous Coronary Intervention - A Consensus Document From the Academic Research Consortium for High Bleeding Risk](https://www.ahajournals.org/doi/10.1161/CIRCULATIONAHA.119.040167)

[^3]: [2011 Mehran et al., Standardized Bleeding Definitions for Cardiovascular Clinical Trials - A Consensus Report From the Bleeding Academic Research Consortium](https://www.ahajournals.org/doi/10.1161/circulationaha.110.009449)

[^4]: [2022 Silverio et al., Validation of the academic research consortium high bleeding risk criteria in patients undergoing percutaneous coronary intervention: A systematic review and meta-analysis of 10 studies and 67,862 patients](https://www.sciencedirect.com/science/article/abs/pii/S0167527321017848)

[^5]: [2015 Al-Ani et al., Identifying venous thromboembolism and major bleeding in emergency room discharges using administrative data](https://pubmed.ncbi.nlm.nih.gov/26553020/)

[^6]: [2019 Wells et al., Dual Antiplatelet Therapy Following Percutaneous Coronary Intervention: Clinical and Economic Impact of Standard Versus Extended Duration](https://www.ncbi.nlm.nih.gov/books/NBK542937/)

[^7]: [2019 Pufulete et al., Comprehensive ascertainment of bleeding in patients prescribed different combinations of dual antiplatelet therapy (DAPT) and triple therapy (TT) in the UK: study protocol for three population-based cohort studies emulating ‘target trials’ (the ADAPTT Study)](https://bmjopen.bmj.com/content/9/6/e029388)