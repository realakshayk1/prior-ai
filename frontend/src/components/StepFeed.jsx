import { useState, useEffect, useRef } from 'react';

export default function StepFeed({ runId, isMock, runStatus, onComplete, onError }) {
  const [steps, setSteps] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const retriesRef = useRef(0);

  useEffect(() => {
    if (runStatus !== 'running') return;

    if (isMock) {
      const mockEvents = [
         { step: 1, tool: 'fetch_patient_context', status: 'running', timestamp: Date.now() },
         { step: 1, tool: 'fetch_patient_context', status: 'done', timestamp: Date.now(), result: { msg: 'Patient context loaded', id: 'pat_1' } },
         { step: 2, tool: 'check_auth_criteria', status: 'running', timestamp: Date.now() },
         { step: 2, tool: 'check_auth_criteria', status: 'done', timestamp: Date.now(), result: { criteria_met: true } },
         { step: 3, tool: 'score_clinical_risk', status: 'running', timestamp: Date.now() },
         { step: 3, tool: 'score_clinical_risk', status: 'done', timestamp: Date.now(), result: { denial_probability: 0.12, tier: 'low' } },
         { step: 4, tool: 'reasoning_agent', status: 'running', timestamp: Date.now() },
         { step: 4, tool: 'reasoning_agent', status: 'done', timestamp: Date.now(), result: { final: 'Output generated' } },
         { type: 'final', event: 'complete' }
      ];
      
      let idx = 0;
      const interval = setInterval(() => {
        if (idx >= mockEvents.length) {
          clearInterval(interval);
          return;
        }
        
        const ev = mockEvents[idx];
        if (ev.event === 'complete') {
           onComplete();
        } else {
           setSteps(prev => {
             const existing = prev.findIndex(s => s.step === ev.step);
             if (existing >= 0) {
               const next = [...prev];
               next[existing] = ev;
               return next;
             }
             return [...prev, ev];
           });
        }
        idx++;
      }, 1200);
      
      return () => clearInterval(interval);
    } else {
      const source = new EventSource(`http://localhost:8000/stream/${runId}`);

      source.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setSteps(prev => {
             const existing = prev.findIndex(s => s.step === data.step);
             if (existing >= 0) {
               const next = [...prev];
               next[existing] = data;
               return next;
             }
             return [...prev, data];
          });
        } catch (err) {
          console.error('Failed to parse SSE', err);
        }
      };

      source.addEventListener('complete', () => {
        source.close();
        onComplete();
      });

      source.onerror = () => {
        retriesRef.current += 1;
        if (retriesRef.current >= 3) {
          setErrorMsg("Could not connect to agent (Retries exceeded).");
          source.close();
          onError();
        }
      };

      return () => {
        source.close();
      };
    }
  }, [runId, isMock, runStatus, onComplete, onError]);

  if (runStatus === 'idle') return null;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800 tracking-tight">Agent Execution Trace</h2>
      
      {errorMsg ? (
        <div className="p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
          {errorMsg}
        </div>
      ) : (
        <div className="space-y-3">
          {steps.map((s, i) => (
            <StepCard key={s.step || i} stepData={s} />
          ))}
          {runStatus === 'running' && steps.length > 0 && steps[steps.length - 1]?.status === 'done' && (
             <div className="flex justify-center p-4">
               <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-400 border-t-transparent"></div>
             </div>
          )}
        </div>
      )}

      {runStatus === 'complete' && (
        <div className="p-4 bg-green-50 text-green-800 rounded-md border border-green-200 font-medium">
          Analysis complete. Ready for review.
        </div>
      )}
    </div>
  );
}

function StepCard({ stepData }) {
  const [expanded, setExpanded] = useState(false);
  const { step, tool, status, result } = stepData;

  const getStatusIcon = () => {
    if (status === 'error') return <span className="text-red-500">❌</span>;
    if (status === 'done') return <span className="text-green-500">✅</span>;
    return <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />;
  };

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm transition-all duration-300 animate-in fade-in slide-in-from-bottom-2">
      <div 
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-slate-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Step {step}</span>
            <span className="ml-2 text-sm font-medium text-slate-800 bg-slate-100 px-2 py-0.5 rounded-md">`{tool}`</span>
          </div>
        </div>
        <div className="text-xs text-slate-400">
          {status} {result && (expanded ? '▲' : '▼')}
        </div>
      </div>
      
      {expanded && result && (
        <div className="border-t border-slate-100 p-4 bg-slate-50 text-xs text-slate-700 overflow-x-auto">
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
