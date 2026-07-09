import React, { useState } from 'react';
import AudioRecorder from './components/AudioRecorder';
import DataForm from './components/DataForm';

function App() {
  const [formData, setFormData] = useState({
    age: '',
    gender: 'male',
    tbContactHistory: false,
    wheezingHistory: false,
    phlegmCough: false,
    familyAsthmaHistory: false,
    feverHistory: false,
    coldPresent: false,
    packYears: ''
  });
  const [modelId, setModelId] = useState('exp4-encoder-free-unified');
  const [audioBlob, setAudioBlob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);

  // In production, this should be the Render URL
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleAudioReady = (blob) => {
    setAudioBlob(blob);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!audioBlob) {
      setError('Please record an audio sample first.');
      return;
    }
    if (formData.age === '') {
      setError('Please fill out the patient age.');
      return;
    }

    setError(null);
    setIsLoading(true);
    setMetrics(null);
    const startTime = performance.now();

    try {
      const submitData = new FormData();
      submitData.append('audio', audioBlob, 'recording.wav');
      submitData.append('model_id', modelId);
      
      // Append all 9 features precisely
      Object.keys(formData).forEach(key => {
        submitData.append(key, formData[key]);
      });

      const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        body: submitData,
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Network response was not ok');
      }

      if (data.error) {
        throw new Error(data.error);
      }

      setResult(data.prediction);
      
      const endTime = performance.now();
      setMetrics({
        latencyMs: Math.round(endTime - startTime)
      });
    } catch (err) {
      console.error(err);
      setError(err.message || 'Failed to connect to the server. Is the API running?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header>
        <h1>AIRS Diagnostic</h1>
        <h2>Respiratory Disease Classifier</h2>
      </header>

      <main>
        {error && (
          <div className="card" style={{ borderLeft: '4px solid var(--danger)' }}>
            <p style={{ color: 'var(--danger)', fontWeight: '500' }}>{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="card">
            <h3 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>1. Model Selection</h3>
            <div className="form-group">
              <label htmlFor="model_id">Select Active Model Configuration</label>
              <select
                id="model_id"
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
              >
                <option value="exp4-encoder-free-unified">Exp 4: Encoder-Free Unified (Best Performance)</option>
                <option value="exp1-tabular-attention">Exp 1: Tabular Attention (Clinical Only)</option>
                <option value="exp2-acoustic-both">Exp 2: Acoustic Dual-Stream</option>
              </select>
            </div>
          </div>

          <div className="card">
            <DataForm formData={formData} setFormData={setFormData} />
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>3. Respiratory Audio</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Please record up to 5 seconds of the patient coughing.
            </p>
            <AudioRecorder onAudioReady={handleAudioReady} />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={isLoading || !audioBlob}
            style={{ marginBottom: '2rem' }}
          >
            {isLoading ? 'Analyzing Patient Data...' : 'Run Diagnostics'}
          </button>
        </form>

        {result && (
          <div className="card results-container">
            <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              Diagnostic Results
            </h3>
            <div className="result-row">
              <span className="result-label">Diagnosis</span>
              <span className={`result-value ${result.diagnosis === 'Positive' ? 'positive' : 'negative'}`}>
                {result.diagnosis}
              </span>
            </div>
            <div className="result-row">
              <span className="result-label">Disease Probability</span>
              <span className="result-value">{(result.disease_probability * 100).toFixed(1)}%</span>
            </div>
            <div className="result-row">
              <span className="result-label">Confidence</span>
              <span className="result-value">{result.confidence}</span>
            </div>
            <div className="result-row">
              <span className="result-label">Model Architecture</span>
              <span className="result-value" style={{ fontSize: '0.85rem' }}>{result.model_version}</span>
            </div>
            <div className="result-row">
              <span className="result-label">Active Weights</span>
              <span className="result-value" style={{ fontSize: '0.85rem' }}>{result.model_id}</span>
            </div>
            {metrics && (
              <div className="result-row">
                <span className="result-label">API Latency</span>
                <span className="result-value" style={{ fontSize: '0.85rem', color: 'var(--primary)' }}>
                  {(metrics.latencyMs / 1000).toFixed(2)}s
                </span>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
