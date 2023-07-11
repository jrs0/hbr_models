# Academic Research Consortium High Bleeding Risk (ARC HBR)

A primary purpose of this repository is attempting to calculate (or approximate) the ARC HBR risk score, defined in [2019 Urban et al.](https://pubmed.ncbi.nlm.nih.gov/31116395/). It is likely not possible to exactly calculate the exact score due to deficiencies in the data. However, having the approximate score may be useful because:
* An automated calculation of the score (accompanied by a concise expression of the underlying data, in order to allow for additional clinical judgement) may be a clinically useful decision-support tool in its own right while prescribing blood-thinning medication following acute coronary syndromes.
* The approximate calculation of the ARC-HBR score may be useful as a prognostic model for predicting bleeding risk, provided that it can be validated using appropriate bleeding data
* The approximate calculation of the ARC-HBR score could serve as a baseline in the search for prognostic models that work better with the data available.

This file outlines the ARC HBR criteria, and how it will be calculated from the data available.

## Overview of Datasets

The following datasets are available for the calculation of the ARC-HBR score:
* Health Information Collaborative (HIC) Cardiovascular Dataset (Bristol Heart Institute, BRI)
    * Spans the Covid-19 period
    * Contains finished consultant episodes for secondary care, including diagnoses and procedures
    * Contains laboratory tests results, including blood count and urea and electrolytes
    * Contains secondary-care prescription information 
* System-wide Dataset (BNSSG ICB)
    * Spans the time-period of the HIC
    * Includes primary care patient attributes and activity
    * Is of secondary importance, due to the more fine-grained information contained in the HIC, but may fill in gaps relating to some demographic information or comorbidities.

## ARC HBR Score Definition

The ARC HBR score is a numerical consensus-based score (rather than being a statistically-driven score), where the presence of a major criterion contributes a 1 to the total score, and a minor criterion contributes 0.5 to the total. A patient is considered at HBR if their score is at least 1 (e.g. due to one major criterion, or two minor criteria).

The sections below describe what constitutes major and minor criteria, and how these will be approximated by information in the datasets.

