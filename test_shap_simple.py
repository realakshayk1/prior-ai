import sys
import os
import json
from catboost import CatBoostClassifier

def test_shap_logic():
    RISK_MODEL_PATH = "model.cbm"
    if not os.path.exists(RISK_MODEL_PATH):
        print(f"Error: {RISK_MODEL_PATH} not found.")
        return

    model = CatBoostClassifier()
    model.load_model(RISK_MODEL_PATH)
    
    # Mock features: [age, gender, primary_dx, proc_code, comorbidity_count, num_prior_claims]
    features = [50, '1', 'I10', 'None', 2, 0]
    feature_names = ['Age', 'Gender', 'Primary Diagnosis', 'Procedure Code', 'Comorbidity Count', 'Prior Claims']
    
    print(f"Testing SHAP calculation for features: {dict(zip(feature_names, features))}")
    
    # Predict probability
    probs = model.predict_proba([features])[0]
    denial_prob = float(probs[1])
    print(f"Denial Probability: {denial_prob:.4f}")
    
    from catboost import Pool
    # Indices of categorical features: Gender(1), Primary DX(2), Procedure(3)
    cat_feature_indices = [1, 2, 3]
    
    # Calculate SHAP values
    shap_values = model.get_feature_importance(
        data=Pool([features], cat_features=cat_feature_indices), 
        type='ShapValues'
    )[0]
    
    # Map values to names and sort by absolute magnitude
    shap_map = []
    for i in range(len(feature_names)):
        shap_map.append({
            "factor": feature_names[i],
            "value": float(shap_values[i])
        })
    
    # Sort by absolute SHAP value
    shap_map.sort(key=lambda x: abs(x["value"]), reverse=True)
    top_factors = [item["factor"] for item in shap_map[:3] if abs(item["value"]) > 0.01]
    
    if not top_factors:
        top_factors = ["Baseline Risk"]
        
    print(f"Top SHAP Factors: {top_factors}")
    
    if len(top_factors) > 0:
        print("\nSUCCESS: SHAP factors calculated successfully.")
    else:
        print("\nFAILURE: No SHAP factors calculated.")

if __name__ == "__main__":
    test_shap_logic()
