import { useState, useEffect } from 'react';

export default function OutputPanel({ runId, isMock }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' or 'json'

  useEffect(() => {
    async function fetchResult() {
      if (isMock) {
        // Return a fully formed mock result matching the backend spec.
        setTimeout(() => {
          setResult({
            patient_id: "pat_1",
            patient_name: "James Wilson",
            procedure_requested: "MRI Lumbar Spine",
            procedure_description: "Magnetic resonance imaging of lumbar spine without contrast",
            primary_diagnosis: "M54.50 (Low back pain)",
            supporting_diagnoses: ["M51.26 (Other intervertebral disc displacement)"],
            recommendation: "APPROVE",
            confidence: 0.94,
            denial_risk_score: 0.12,
            clinical_rationale: "Patient presents with persistent severe low back pain radiating to the left leg, unresponsive to 6 weeks of conservative therapy (NSAIDs, physical therapy). Signs of radiculopathy are present. Given the duration and failure of conservative management, MRI is medically necessary to assess for disc herniation or nerve root compression.\n\nCriteria met: 6 weeks conservative therapy failed, evidence of radiculopathy.",
            criteria_met: ["6 weeks conservative therapy failed", "Nerve root compression symptoms"],
            criteria_not_met: [],
            recommended_actions: ["Proceed with MRI", "Schedule follow-up to discuss results"],
            audit_flags: []
          });
          setLoading(false);
        }, 800);
        return;
      }

      try {
        const res = await fetch(`http://localhost:8000/result/${runId}`);
        if (!res.ok) throw new Error('Result fetch failed');
        const data = await res.json();
        setResult(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchResult();
  }, [runId, isMock]);

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-500 animate-pulse bg-white rounded-lg shadow-sm border border-slate-200">
        Compiling final authorization package...
      </div>
    );
  }

  if (error) {
    return <div className="text-red-600">Error loading result: {error}</div>;
  }

  if (!result || result.status === 'pending') {
    return <div className="text-slate-500">Result is pending...</div>;
  }

  const handleDownloadJSON = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `auth_result_${runId}.json`;
    a.click();
  };

  const handleDownloadLetter = () => {
    // Generate letter from clinical rationale, explicitly formatting newlines to preserve paragraph structure.
    const letterContent = `Prior Authorization Request Form\n\nPatient: ${result.patient_name} (${result.patient_id})\nRequested Procedure: ${result.procedure_requested}\nPrimary Diagnosis: ${result.primary_diagnosis}\n\nClinical Rationale:\n${result.clinical_rationale}\n\nRecommendation: ${result.recommendation} (Confidence: ${(result.confidence * 100).toFixed(1)}%)`;
    
    const blob = new Blob([letterContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `auth_letter_${runId}.txt`;
    a.click();
  };

  const getBadgeColor = (rec) => {
    if (rec === 'APPROVE') return 'bg-green-100 text-green-800 border-green-200';
    if (rec === 'DENY') return 'bg-red-100 text-red-800 border-red-200';
    return 'bg-amber-100 text-amber-800 border-amber-200';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
      {/* Tabs Layout */}
      <div className="border-b border-slate-200 bg-slate-50 flex px-2 text-sm font-medium text-slate-600">
        <button 
          className={`py-3 px-4 focus:outline-none border-b-2 transition-colors ${activeTab === 'summary' ? 'border-indigo-500 text-indigo-700 bg-white' : 'border-transparent hover:text-slate-800'}`}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
        <button 
          className={`py-3 px-4 focus:outline-none border-b-2 transition-colors ${activeTab === 'json' ? 'border-indigo-500 text-indigo-700 bg-white' : 'border-transparent hover:text-slate-800'}`}
          onClick={() => setActiveTab('json')}
        >
          Raw JSON
        </button>
      </div>

      <div className="p-6">
        {activeTab === 'summary' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold text-slate-800">{result.patient_name}</h3>
                <p className="text-slate-500 text-sm">{result.procedure_requested}</p>
              </div>
              <div className={`px-4 py-1.5 rounded-full border font-bold tracking-wide ${getBadgeColor(result.recommendation)}`}>
                {result.recommendation}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
               <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                 <div className="text-xs text-slate-500 mb-1 font-semibold uppercase">Confidence Score</div>
                 <div className="text-2xl font-bold text-slate-800">{(result.confidence * 100).toFixed(1)}%</div>
               </div>
               <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                 <div className="text-xs text-slate-500 mb-1 font-semibold uppercase">Denial Risk</div>
                 <div className="w-full bg-slate-200 rounded-full h-2.5 mt-2 mb-1">
                   <div className="bg-amber-500 h-2.5 rounded-full" style={{ width: `${result.denial_risk_score * 100}%` }}></div>
                 </div>
                 <div className="text-right text-xs text-slate-500">{(result.denial_risk_score * 100).toFixed(1)}%</div>
               </div>
            </div>

            <div>
              <h4 className="font-semibold text-slate-800 mb-2">Clinical Rationale</h4>
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {result.clinical_rationale}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold text-slate-800 text-sm mb-2">Criteria Met</h4>
                <ul className="list-disc pl-5 text-sm text-slate-600 space-y-1">
                  {result.criteria_met?.map((c, i) => <li key={i}>{c}</li>)}
                  {result.criteria_met?.length === 0 && <li className="text-slate-400 list-none -ml-5">None</li>}
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-slate-800 text-sm mb-2">Criteria Not Met</h4>
                <ul className="list-disc pl-5 text-sm text-slate-600 space-y-1">
                  {result.criteria_not_met?.map((c, i) => <li key={i}>{c}</li>)}
                  {result.criteria_not_met?.length === 0 && <li className="text-slate-400 list-none -ml-5">None</li>}
                </ul>
              </div>
            </div>
            
            {result.recommended_actions?.length > 0 && (
              <div>
                <h4 className="font-semibold text-slate-800 text-sm mb-2">Recommended Actions</h4>
                <ol className="list-decimal pl-5 text-sm text-slate-600 space-y-1">
                  {result.recommended_actions.map((c, i) => <li key={i}>{c}</li>)}
                </ol>
              </div>
            )}
          </div>
        )}

        {activeTab === 'json' && (
          <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto text-sm text-green-400">
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}

        {/* Download Buttons */}
        <div className="mt-8 pt-6 border-t border-slate-200 flex space-x-4">
          <button 
            onClick={handleDownloadLetter}
            className="flex-1 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 font-medium py-2 rounded-md shadow-sm transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            &#8595; Download Letter
          </button>
          <button 
            onClick={handleDownloadJSON}
            className="flex-1 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 font-medium py-2 rounded-md shadow-sm transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            &#8595; Download JSON
          </button>
        </div>
      </div>
    </div>
  );
}
