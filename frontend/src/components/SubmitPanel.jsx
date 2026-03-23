import { useState, useEffect } from 'react';

export default function SubmitPanel({ isMock, runStatus, onRunStart, onError }) {
  const [patients, setPatients] = useState([]);
  const [isLoadingPatients, setIsLoadingPatients] = useState(true);
  
  const [selectedPatient, setSelectedPatient] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);

  useEffect(() => {
    async function fetchPatients() {
      if (isMock) {
        setPatients([
          { id: 'pat_1', name: 'James Wilson' },
          { id: 'pat_2', name: 'Sarah Connor' },
          { id: 'pat_3', name: 'Michael Scott' }
        ]);
        setIsLoadingPatients(false);
        return;
      }

      try {
        const res = await fetch('http://localhost:8000/patients');
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();
        setPatients(data);
      } catch (e) {
        console.error('Failed to fetch patients', e);
      } finally {
        setIsLoadingPatients(false);
      }
    }
    fetchPatients();
  }, [isMock]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return;

    if (isMock) {
      setTimeout(() => {
        onRunStart('mock_run_' + Math.floor(Math.random() * 10000));
      }, 500);
      return;
    }

    try {
      const formData = new FormData();
      formData.append('patient_id', selectedPatient);
      if (pdfFile) formData.append('pdf', pdfFile);
      if (audioFile) formData.append('audio', audioFile);

      const res = await fetch('http://localhost:8000/run', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Run failed');
      const data = await res.json();
      onRunStart(data.run_id);
    } catch (e) {
      console.error(e);
      onError();
    }
  };

  const isRunning = runStatus === 'running';

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Patient</label>
        <div className="relative">
          <select 
            value={selectedPatient}
            onChange={(e) => setSelectedPatient(e.target.value)}
            disabled={isRunning || isLoadingPatients}
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500"
          >
            <option value="" disabled>
              {isLoadingPatients ? 'Loading patients...' : 'Select a patient'}
            </option>
            {patients.map(p => (
              <option key={p.id} value={p.id}>{p.id} - {p.name || ''}</option>
            ))}
          </select>
          {isLoadingPatients && (
            <div className="absolute right-8 top-2.5">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent pt-1"></div>
            </div>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Referral PDF (Optional)</label>
        <input 
          type="file" 
          accept="application/pdf"
          disabled={isRunning}
          onChange={(e) => setPdfFile(e.target.files[0])}
          className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 disabled:opacity-50"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Voice Note (Optional)</label>
        <input 
          type="file" 
          accept="audio/wav,audio/mpeg,audio/mp3"
          disabled={isRunning}
          onChange={(e) => setAudioFile(e.target.files[0])}
          className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 disabled:opacity-50"
        />
      </div>

      <div className="pt-4">
        <button 
          type="submit" 
          disabled={!selectedPatient || isRunning}
          className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isRunning ? 'Running...' : 'Run Authorization'}
        </button>
      </div>

      {isMock && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 text-yellow-800 text-xs rounded-md">
          <strong>Mock Mode Active:</strong> Submissions will simulate local API behavior.
        </div>
      )}
    </form>
  );
}
