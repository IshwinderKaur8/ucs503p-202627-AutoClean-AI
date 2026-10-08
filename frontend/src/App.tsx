import { useState } from "react";
import { motion } from "framer-motion";
import "./App.css";
import AnimatedBackground from "./components/AnimatedBackground";
import FileUpload from "./components/FileUpload";
import DatasetList from "./components/DatasetList";
import ColumnProfileTable from "./components/ColumnProfileTable";
import PreviewTable from "./components/PreviewTable";
import PipelineConfigPanel from "./components/PipelineConfigPanel";
import AuditTrailView from "./components/AuditTrailView";
import DownloadResult from "./components/DownloadResult";
import ToolsPanel from "./components/ToolsPanel";
import RecommendationPanel from "./components/RecommendationPanel";
import ChatAssistant from "./components/ChatAssistant";
import {
  uploadDatasets,
  listDatasets,
  getProfile,
  getPreview,
  runPipeline,
  combineDatasets,
  generateSynthetic,
} from "./api/client";
import type { AuditTrail, ColumnProfile, DatasetSummary, PipelineConfigIn, PreviewResult } from "./types";
import { DEFAULT_PIPELINE_CONFIG } from "./types";

const panelMotion = (index: number) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay: index * 0.06 },
});

function App() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [profile, setProfile] = useState<ColumnProfile[] | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [config, setConfig] = useState<PipelineConfigIn>(DEFAULT_PIPELINE_CONFIG);
  const [auditTrail, setAuditTrail] = useState<AuditTrail | null>(null);
  const [explanations, setExplanations] = useState<{ step_name: string; explanation: string }[]>([]);
  const [resultDatasetId, setResultDatasetId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedDataset = datasets.find((d) => d.dataset_id === selectedId) ?? null;

  const refreshDatasets = async () => {
    setDatasets(await listDatasets());
  };

  const handleUpload = async (files: File[]) => {
    setError(null);
    try {
      const uploaded = await uploadDatasets(files);
      await refreshDatasets();
      if (uploaded.length > 0) await handleSelect(uploaded[0].dataset_id);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSelect = async (id: string) => {
    setSelectedId(id);
    setAuditTrail(null);
    setResultDatasetId(null);
    setError(null);
    try {
      const [p, pv] = await Promise.all([getProfile(id), getPreview(id)]);
      setProfile(p);
      setPreview(pv);
    } catch (e) {
      setError(String(e));
    }
  };

  const toggleChecked = (id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleRunPipeline = async () => {
    if (!selectedId) return;
    setRunning(true);
    setError(null);
    try {
      const result = await runPipeline(selectedId, config);
      setAuditTrail(result.audit_trail);
      setExplanations(result.step_explanations);
      setResultDatasetId(result.dataset_id);
      await refreshDatasets();
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  const handleCombine = async (mode: "concat" | "merge", on: string | null) => {
    setError(null);
    try {
      const ids = Array.from(checkedIds);
      const result = await combineDatasets(ids, mode, on ? [on] : null, "outer");
      await refreshDatasets();
      await handleSelect(result.dataset_id);
      setCheckedIds(new Set());
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSynthetic = async (nRows: number, augment: boolean) => {
    if (!selectedId) return;
    setError(null);
    try {
      const result = await generateSynthetic(selectedId, nRows, null, augment);
      await refreshDatasets();
      await handleSelect(result.dataset_id);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <>
      <AnimatedBackground />
      <div className="app-shell">
        <header>
          <h1>AutoClean AI</h1>
          <p className="tagline">Upload messy data → automated cleaning, feature engineering, and normalization → trainable output.</p>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <motion.section className="panel" {...panelMotion(0)}>
          <h2>1. Upload data</h2>
          <FileUpload onUpload={handleUpload} />
          <DatasetList
            datasets={datasets}
            selectedId={selectedId}
            onSelect={(id) => void handleSelect(id)}
            checkedIds={checkedIds}
            onToggleChecked={toggleChecked}
          />
        </motion.section>

        <motion.section className="panel" {...panelMotion(1)}>
          <h2>2. Combine &amp; augment</h2>
          <ToolsPanel
            checkedCount={checkedIds.size}
            onCombine={handleCombine}
            selectedId={selectedId}
            onSynthetic={handleSynthetic}
            busy={running}
          />
        </motion.section>

        {selectedId && profile && preview && (
          <motion.section className="panel" {...panelMotion(2)}>
            <h2>3. Inspect selected dataset</h2>
            <ColumnProfileTable profile={profile} />
            <PreviewTable preview={preview} />
          </motion.section>
        )}

        {selectedId && (
          <motion.section className="panel" {...panelMotion(3)}>
            <h2>4. Configure &amp; run cleaning pipeline</h2>
            <PipelineConfigPanel config={config} onChange={setConfig} onRun={handleRunPipeline} running={running} />
          </motion.section>
        )}

        {auditTrail && resultDatasetId && (
          <motion.section className="panel" {...panelMotion(4)}>
            <h2>5. Audit trail</h2>
            <AuditTrailView trail={auditTrail} explanations={explanations} />
            <DownloadResult datasetId={resultDatasetId} />
          </motion.section>
        )}

        {selectedId && profile && (
          <motion.section className="panel" {...panelMotion(5)}>
            <h2>6. Recommended algorithms</h2>
            <RecommendationPanel datasetId={selectedId} columnNames={profile.map((p) => p.name)} />
          </motion.section>
        )}
      </div>

      <ChatAssistant selectedId={selectedId} selectedName={selectedDataset?.name ?? null} />
    </>
  );
}

export default App;
