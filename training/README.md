# CatBoost Denial Risk Model

## Dataset Choice
The model is trained on the CMS DE-SynPUF dataset. This dataset was selected because it is free and immediately available, preventing delays while awaiting MIMIC-IV access approval.

## Label Engineering Logic
The target label (`denied`) was engineered directly from the `CLM_PMT_AMT` field in the claims data. A claim is defined as **denied (1)** if the claim payment amount is $0, and **approved (0)** otherwise.

## Class Imbalance Handling
The dataset exhibits a significant class imbalance, with denials being extremely rare compared to approvals. To combat this bias and ensure the model produces a calibrated spectrum of predicted denial probabilities (rather than clustering all predictions near 0), the `CatBoostClassifier` was configured with `auto_class_weights='Balanced'`. 

This step improved the calibration curve distribution significantly by correctly penalizing errors on the minority class during training.
