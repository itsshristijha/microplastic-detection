import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface BackendResponse {
  success: boolean;
  image_url: string;
  analysis: {
    total_particles: number;
    breakdown: Record<string, number>;
  };
  health_risk: {
    concentration_per_ml: number;
    status: string;
    risk_level: string;
    message: string;
  };
  error?: string;
}

interface AnalysisContextType {
  file: File | null;
  setFile: (file: File | null) => void;
  preview: string | null;
  setPreview: (preview: string | null) => void;
  analyzing: boolean;
  setAnalyzing: (analyzing: boolean) => void;
  result: BackendResponse | null;
  setResult: (result: BackendResponse | null) => void;
  error: string | null;
  setError: (error: string | null) => void;
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

export const AnalysisProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<BackendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <AnalysisContext.Provider value={{
      file, setFile,
      preview, setPreview,
      analyzing, setAnalyzing,
      result, setResult,
      error, setError
    }}>
      {children}
    </AnalysisContext.Provider>
  );
};

export const useAnalysis = () => {
  const context = useContext(AnalysisContext);
  if (context === undefined) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
};
