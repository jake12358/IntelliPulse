import { useState } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { Dashboard } from './components/Dashboard';
import { UploadZone } from './components/UploadZone';
import type { AnalysisResult } from './types';

export default function App() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [knowledgeRefreshKey, setKnowledgeRefreshKey] = useState(0);
  const [lastQuery, setLastQuery] = useState('对比飞书和钉钉');

  const addDocumentId = (documentId: string) => {
    setDocumentIds((items) => {
      const nextBase = analysis && !isAnalyzing ? [] : items;
      return nextBase.includes(documentId) ? nextBase : [...nextBase, documentId];
    });
    if (analysis && !isAnalyzing) setAnalysis(null);
    setKnowledgeRefreshKey((value) => value + 1);
  };

  const handleAnalysisStart = (query: string) => {
    setLastQuery(query);
    setAnalysis(null);
    setIsAnalyzing(true);
    setKnowledgeRefreshKey((value) => value + 1);
  };

  const handleAnalysisComplete = () => {
    setIsAnalyzing(false);
    setKnowledgeRefreshKey((value) => value + 1);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>IntelliPulse</h1>
          <p>AI 智能竞品分析平台</p>
        </div>
      </header>
      <div className="workspace">
        <div className="left-column">
          <UploadZone
            onDocumentUploaded={addDocumentId}
            currentDocumentIds={documentIds}
            isAnalyzing={isAnalyzing}
            refreshKey={knowledgeRefreshKey}
          />
          <Dashboard
            analysis={analysis}
            documentIds={documentIds}
            query={lastQuery}
            isAnalyzing={isAnalyzing}
          />
        </div>
        <ChatWindow
          onAnalysis={setAnalysis}
          documentIds={documentIds}
          onAnalysisStart={handleAnalysisStart}
          onAnalysisComplete={handleAnalysisComplete}
        />
      </div>
    </main>
  );
}
