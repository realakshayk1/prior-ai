import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from sklearn.calibration import CalibrationDisplay
import matplotlib.pyplot as plt
import os

# Paths
DATA_DIR = "data/cms"

def load_data():
    print("Loading and resampling data from all 4 samples...")
    benes, claims_list = [], []
    for i in range(1, 5):
        b_path = os.path.join(DATA_DIR, f"DE1_0_2008_Beneficiary_Summary_File_Sample_{i}.csv")
        i_path = os.path.join(DATA_DIR, f"DE1_0_2008_to_2010_Inpatient_Claims_Sample_{i}.csv")
        o_path = os.path.join(DATA_DIR, f"DE1_0_2008_to_2010_Outpatient_Claims_Sample_{i}.csv")
        
        if os.path.exists(b_path): benes.append(pd.read_csv(b_path))
        
        def process_claims(file_path):
            if not os.path.exists(file_path): return
            df = pd.read_csv(file_path, low_memory=False)
            df['denied'] = (df['CLM_PMT_AMT'] == 0).astype(int)
            
            denied_df = df[df['denied'] == 1]
            approved_df = df[df['denied'] == 0]
            
            # Undersample the approvals to be twice the number of denials for a 1:2 ratio
            n_samples = min(len(denied_df) * 2, len(approved_df))
            if n_samples > 0:
                approved_df = approved_df.sample(n=n_samples, random_state=42)
            
            claims_list.append(pd.concat([denied_df, approved_df]))
            
        process_claims(i_path)
        process_claims(o_path)
        
    bene = pd.concat(benes, ignore_index=True)
    claims = pd.concat(claims_list, ignore_index=True)
    print(f"Resampled claims size: {len(claims)} rows.")
    return bene, claims

def preprocess(bene, claims):
    print("Preprocessing...")
    # Label is already engineered inside load_data now
    if 'denied' not in claims:
        claims['denied'] = (claims['CLM_PMT_AMT'] == 0).astype(int)
    
    # Comorbidity count (count of non-primary diagnosis codes)
    diag_cols = [c for c in claims.columns if 'ICD9_DGNS_CD_' in c and c != 'ICD9_DGNS_CD_1']
    claims['comorbidity_count'] = claims[diag_cols].notna().sum(axis=1)
    
    # Procedure code (harmonized between Inpatient and Outpatient)
    # Inpatient has ICD9_PRCDR_CD_1, Outpatient has HCPCS_CD_1
    claims['proc_code'] = claims.get('ICD9_PRCDR_CD_1', pd.Series(np.nan, index=claims.index)).fillna(
        claims.get('HCPCS_CD_1', pd.Series(np.nan, index=claims.index))
    ).fillna('None')
    
    # Number of prior claims
    claims = claims.sort_values(['DESYNPUF_ID', 'CLM_FROM_DT'])
    claims['num_prior_claims'] = claims.groupby('DESYNPUF_ID').cumcount()
    
    # Merge with beneficiary data for age/sex
    df = claims.merge(bene[['DESYNPUF_ID', 'BENE_BIRTH_DT', 'BENE_SEX_IDENT_CD']], on='DESYNPUF_ID', how='left')
    
    # Calculate Age
    df['BENE_BIRTH_DT'] = pd.to_datetime(df['BENE_BIRTH_DT'], format='%Y%m%d', errors='coerce')
    df['age'] = 2010 - df['BENE_BIRTH_DT'].dt.year
    
    # Features as per PRD R3.6
    features = ['age', 'BENE_SEX_IDENT_CD', 'ICD9_DGNS_CD_1', 'proc_code', 'comorbidity_count', 'num_prior_claims']
    cat_features = ['BENE_SEX_IDENT_CD', 'ICD9_DGNS_CD_1', 'proc_code']
    
    # Handle NaNs
    for col in cat_features:
        df[col] = df[col].astype(str).fillna('missing')
    
    df['age'] = df['age'].fillna(df['age'].median())
    df['comorbidity_count'] = df['comorbidity_count'].fillna(0)
    
    return df[features], df['denied'], cat_features

if __name__ == "__main__":
    bene, claims = load_data()
    X, y, cat_features = preprocess(bene, claims)
    
    print(f"Training on {len(X)} rows with {y.sum()} denials...")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = CatBoostClassifier(
        iterations=500,
        learning_rate=0.1,
        depth=6,
        eval_metric='AUC',
        early_stopping_rounds=50,
        random_seed=42,
        verbose=50
    )
    
    model.fit(X_train, y_train, cat_features=cat_features, eval_set=(X_test, y_test), plot=False)
    
    preds_proba = model.predict_proba(X_test)[:, 1]
    preds = (preds_proba >= 0.5).astype(int)
    
    auc = roc_auc_score(y_test, preds_proba)
    prec = precision_score(y_test, preds)
    rec = recall_score(y_test, preds)
    
    print(f"\nFinal Test AUC: {auc:.4f}")
    print(f"Precision @ 0.5: {prec:.4f}")
    print(f"Recall @ 0.5: {rec:.4f}")
    
    disp = CalibrationDisplay.from_predictions(y_test, preds_proba, n_bins=10, strategy='quantile')
    
    # Zoom in to the relevant probability range to make it visually clear
    max_prob = max(preds_proba.max() + 0.05, 0.2)
    disp.ax_.set_xlim(0, max_prob)
    disp.ax_.set_ylim(0, max_prob)
    
    # Also add a diagonal perfectly calibrated line that matches the scaled axes
    disp.ax_.plot([0, max_prob], [0, max_prob], "k:", label="Perfectly calibrated")
    
    plt.title('Calibration Curve (Scaled to Density)')
    plt.savefig('calibration_plot.png')
    print("Saved calibration plot to calibration_plot.png")
    
    model.save_model("model.cbm")
    print("Model saved as model.cbm")
