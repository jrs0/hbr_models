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

See [here](https://www.possiblehealth.io/clinical-decision-support-tools-are-they-medical-devices-or-not/) for a readable overview. Do not treat information in this repository as authorative. How the tool is classified depends on its intended purpose amongst other things. Any tools developed in this repository will be accompanied by an intended purpose. In addition, **all tools in this repository are for prototying purposes, and not intended for direct deployment**.

## Previous Bleeding/Ischaemic Risk Prediction Work

2021 Urban et al. [^1] present a trade-off model for bleeding and thrombotic risk for patients having PCI, developed for use on patients who have already been determined to be at HBR. They use (a modified form of) the Academic Research Consortium (ARC) HBR definition [^2] to define what HBR means. Their model is based on survival analysis, and the outcome (for a given patient) is a probability of bleeding (in this case BARC 3 or 5 level [^3]) and a probability of thrombosis (MI or ST). These two probabilities constitute a trade-off, which is also adjusted by mortality (which is higher for patients with thrombotic complications than bleeding complications).


[^1] [2021 Urban et al., Assessing the Risks of Bleeding vs Thrombotic Events in Patients at High Bleeding Risk After Coronary Stent ImplantationThe ARC–High Bleeding Risk Trade-off Model](https://jamanetwork.com/journals/jamacardiology/fullarticle/2774812)

[^2] [2019 Urban et al., Defining High Bleeding Risk in Patients Undergoing Percutaneous Coronary Intervention - A Consensus Document From the Academic Research Consortium for High Bleeding Risk](https://www.ahajournals.org/doi/10.1161/CIRCULATIONAHA.119.040167)

[^3] [2011 Mehran et al., Standardized Bleeding Definitions for Cardiovascular Clinical Trials - A Consensus Report From the Bleeding Academic Research Consortium](https://www.ahajournals.org/doi/10.1161/circulationaha.110.009449)