import { useState, useEffect } from 'react';
import SubmitPanel from './components/SubmitPanel';
import StepFeed from './components/StepFeed';
import OutputPanel from './components/OutputPanel';

function App() {
  const [runId, setRunId] = useState(null);
  const [runStatus, setRunStatus] = useState('idle'); // idle, running, complete, error
  const [isMock, setIsMock] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('mock') === 'true') {
      setIsMock(true);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex overflow-hidden font-sans">
      {/* Left Panel: 1/3 width */}
      <div className="w-1/3 border-r border-slate-200 bg-white shadow-sm z-10 p-8 flex flex-col h-screen overflow-y-auto">
         <div className="mb-10">
           <h1 className="text-3xl font-semibold text-slate-900 tracking-tight">PriorAI</h1>
           <p className="text-sm text-slate-500 mt-2">Automated Prior Auth Assembly</p>
         </div>
         
         <div className="flex-1">
           <SubmitPanel 
             isMock={isMock} 
             runStatus={runStatus} 
             onRunStart={(id) => {
               setRunId(id);
               setRunStatus('running');
             }}
             onError={() => setRunStatus('error')}
           />
         </div>
      </div>

      {/* Right Panel: 2/3 width */}
      <div className="w-2/3 bg-slate-50 h-screen overflow-y-auto p-10">
        {runStatus === 'idle' && (
           <div className="h-full flex items-center justify-center text-slate-400 font-mono">
             <p>Select a patient and click "Run Authorization" to begin.</p>
           </div>
        )}

        {runStatus !== 'idle' && runId && (
          <div className="max-w-4xl mx-auto space-y-10">
             <StepFeed 
               runId={runId} 
               isMock={isMock} 
               runStatus={runStatus}
               onComplete={() => setRunStatus('complete')}
               onError={() => setRunStatus('error')}
             />

             {runStatus === 'complete' && (
               <OutputPanel runId={runId} isMock={isMock} />
             )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
