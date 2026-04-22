# CatBoost Denial Risk Model

## Dataset Choice
The model is trained on the CMS DE-SynPUF dataset. This dataset was selected because it is free and immediately available, preventing delays while awaiting MIMIC-IV access approval.

## Label Engineering Logic
The target label (`denied`) was engineered directly from the `CLM_PMT_AMT` field in the claims data. A claim is defined as **denied (1)** if the claim payment amount is $0, and **approved (0)** otherwise.

## Class Imbalance Handling
The dataset exhibits a significant class imbalance, with denials being extremely rare compared to approvals. To combat this, approved claims are undersampled at a 1:2 ratio relative to denials during data loading (2 approved rows kept per 1 denied row). This ensures the model trains on a balanced representation and produces a calibrated spectrum of predicted denial probabilities rather than clustering near 0.
