import React, { useEffect, useState } from 'react';
import {
  Upload,
  AlertCircle,
  CheckCircle,
  Loader,
  Info,
  Pencil,
} from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import type { ParseResponse } from '../types';

/* =======================
   Types
   ======================= */

interface UploadStatus {
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
  stage?: 'upload' | 'parse' | 'classify';
  message: string;
}

interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  merchant: string;
  category: string;
  confidence: number;
  needs_review: boolean;
  corrected: boolean;
}

interface ExplainResponse {
  reasoning: string;
  rules_fired: string[];
  model_confidence: number;
}

/* =======================
   Component
   ======================= */

export function Dashboard() {
  const { auth } = useAuth();

  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: 'idle',
    progress: 0,
    message: '',
  });

  const [dragActive, setDragActive] = useState(false);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loadingTx, setLoadingTx] = useState(false);
  const [lastParse, setLastParse] = useState<ParseResponse | null>(null);

  const [explainTx, setExplainTx] = useState<ExplainResponse | null>(null);
  const [editTx, setEditTx] = useState<Transaction | null>(null);
  const [editCategory, setEditCategory] = useState('');
  const [editMerchant, setEditMerchant] = useState('');
  const [remember, setRemember] = useState(true);

  /* =======================
     Fetch Transactions
     ======================= */

  const fetchTransactions = async () => {
    if (!auth?.token) return;
    setLoadingTx(true);
    try {
      const res = await api.getTransactions(auth.token);
      setTransactions(res.transactions || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingTx(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [auth?.token]);

  /* =======================
     Upload Handler
     ======================= */

  const handleFile = async (file: File) => {
    if (!file.type.includes('pdf')) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: 'Only PDF files are supported',
      });
      return;
    }

    if (!auth?.token) return;

    try {
      setUploadStatus({
        status: 'uploading',
        progress: 10,
        stage: 'upload',
        message: 'Uploading statement...',
      });

      const result = await api.uploadStatement(
        file,
        auth.token,
        (progress) =>
          setUploadStatus((p) => ({
            ...p,
            progress: Math.min(30, Math.round(progress)),
          }))
      );
      setLastParse(result);

      setUploadStatus({
        status: 'uploading',
        progress: 60,
        stage: 'parse',
        message: 'Parsing transactions...',
      });

      await new Promise((r) => setTimeout(r, 600));

      setUploadStatus({
        status: 'uploading',
        progress: 85,
        stage: 'classify',
        message: 'Running AI classification...',
      });

      await new Promise((r) => setTimeout(r, 600));

      if (result.status === 'success') {
        const count =
          result.transaction_count ??
          result.transactions_count ??
          0;
        setUploadStatus({
          status: 'success',
          progress: 100,
          message: `Parsed ${count} transactions`,
        });
        await fetchTransactions();
        setTimeout(
          () => setUploadStatus({ status: 'idle', progress: 0, message: '' }),
          2500
        );
      } else {
        throw new Error(result.message);
      }
    } catch (err: any) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: err.message || 'Upload failed',
      });
    }
  };

  /* =======================
     Drag & Drop
     ======================= */

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter') setDragActive(true);
    if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  };

  /* =======================
     Explain / Edit
     ======================= */

  const openExplain = async (id: number) => {
    if (!auth?.token) return;
    try {
      const res = await api.explainTransaction(id, auth.token);
      setExplainTx(res);
    } catch {
      alert('Failed to fetch explanation');
    }
  };

  const openEdit = (tx: Transaction) => {
    setEditTx(tx);
    setEditCategory(tx.category);
    setEditMerchant(tx.merchant);
    setRemember(true);
  };

  const saveEdit = async () => {
    if (!auth?.token || !editTx) return;

    await api.correctTransaction(auth.token, {
      transaction_id: editTx.id,
      merchant_normalized: editMerchant,
      category: editCategory,
      remember,
    });

    setTransactions((prev) =>
      prev.map((t) =>
        t.id === editTx.id
          ? {
              ...t,
              merchant: editMerchant,
              category: editCategory,
              confidence: 1,
              corrected: true,
              needs_review: false,
            }
          : t
      )
    );

    setEditTx(null);
  };

  const formatPercent = (value?: number) => {
    if (typeof value !== 'number') return 'n/a';
    return `${(value * 100).toFixed(0)}%`;
  };

  const needsReviewCount = transactions.filter((tx) => tx.needs_review).length;
  const correctedCount = transactions.filter((tx) => tx.corrected).length;

  /* =======================
     Render
     ======================= */

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted">
        Please log in.
      </div>
    );
  }

  return (
    <div className="app-container space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <p className="eyebrow">Dashboard</p>
          <h1 className="text-4xl font-semibold text-ink">
            Financial command center
          </h1>
          <p className="text-muted">
            Upload statements, review AI categories, and keep your ledger clean.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="card-muted px-4 py-3 text-sm">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">
              Transactions
            </p>
            <p className="text-lg font-semibold text-ink">
              {transactions.length}
            </p>
          </div>
          <div className="card-muted px-4 py-3 text-sm">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">
              Needs review
            </p>
            <p className="text-lg font-semibold text-ink">
              {needsReviewCount}
            </p>
          </div>
          <div className="card-muted px-4 py-3 text-sm">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">
              Corrected
            </p>
            <p className="text-lg font-semibold text-ink">
              {correctedCount}
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr),minmax(0,1fr)]">
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`upload-drop ${dragActive ? 'upload-drop-active' : ''}`}
        >
          <input
            type="file"
            accept=".pdf"
            id="file"
            className="hidden"
            onChange={(e) => e.target.files && handleFile(e.target.files[0])}
          />
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-muted text-primary">
            <Upload className="w-6 h-6" />
          </div>
          <h2 className="mt-4 text-xl font-semibold text-ink">
            Upload a statement
          </h2>
          <p className="text-sm text-muted">
            Drag and drop a PDF, or select a file to begin parsing.
          </p>
          <label htmlFor="file" className="btn-primary mt-6 inline-flex">
            Choose PDF
          </label>

          {uploadStatus.status !== 'idle' && (
            <div className="mt-6 space-y-3 text-left">
              <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-muted">
                <span>{uploadStatus.stage ?? 'Processing'}</span>
                <span>{uploadStatus.progress}%</span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${uploadStatus.progress}%` }}
                />
              </div>
              <div className="flex items-center gap-2 text-sm text-muted">
                {uploadStatus.status === 'uploading' && (
                  <Loader className="w-4 h-4 animate-spin text-primary" />
                )}
                {uploadStatus.status === 'success' && (
                  <CheckCircle className="w-4 h-4 text-success" />
                )}
                {uploadStatus.status === 'error' && (
                  <AlertCircle className="w-4 h-4 text-danger" />
                )}
                <span>{uploadStatus.message}</span>
              </div>
            </div>
          )}
        </div>

        <div className="card p-6 space-y-4">
          <div className="space-y-1">
            <p className="eyebrow">Status</p>
            <h3 className="section-title">Parsing summary</h3>
          </div>
          <div className="divider" />
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted">Last statement ID</span>
              <span className="font-semibold text-ink">
                {lastParse?.statement_id ?? 'n/a'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Transactions parsed</span>
              <span className="font-semibold text-ink">
                {lastParse?.transaction_count ??
                  lastParse?.transactions_count ??
                  'n/a'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Schema confidence</span>
              <span className="font-semibold text-ink">
                {formatPercent(lastParse?.schema_confidence)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Variant</span>
              <span className="font-semibold text-ink">
                {lastParse?.schema_variant ?? 'n/a'}
              </span>
            </div>
          </div>
          <div className="divider" />
          <p className="text-sm text-muted">
            Review flagged transactions to keep future classifications sharp.
          </p>
        </div>
      </div>

      {lastParse?.status === 'success' && (
        <div className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="section-title">Latest parse trace</h2>
            <span className="badge badge-success">Success</span>
          </div>

          {lastParse.trace && (
            <div className="space-y-3 text-sm text-muted">
              <div>
                <span className="font-semibold text-ink">Initial:</span>{' '}
                {formatPercent(lastParse.trace.initial?.confidence)}{' '}
                {lastParse.trace.initial?.schema_type
                  ? `(${lastParse.trace.initial?.schema_type})`
                  : ''}
              </div>

              {lastParse.trace.retry && (
                <div>
                  <span className="font-semibold text-ink">Retry:</span>{' '}
                  {lastParse.trace.retry.decision ?? 'n/a'}
                </div>
              )}

              {lastParse.trace.retry?.candidates &&
                lastParse.trace.retry.candidates.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {lastParse.trace.retry.candidates.map((c, idx) => (
                      <span
                        key={`${c.variant}-${idx}`}
                        className="badge"
                      >
                        {c.variant ?? 'variant'} · {formatPercent(c.confidence)}
                        {c.schema_type ? ` · ${c.schema_type}` : ''}
                      </span>
                    ))}
                  </div>
                )}

              {lastParse.trace.arbitration?.used && (
                <div>
                  <span className="font-semibold text-ink">Arbitration:</span>{' '}
                  {lastParse.trace.arbitration.status ?? 'used'}
                  {lastParse.trace.arbitration.winner_variant
                    ? ` · ${lastParse.trace.arbitration.winner_variant}`
                    : ''}
                  {typeof lastParse.trace.arbitration.winner_confidence === 'number'
                    ? ` · ${formatPercent(
                        lastParse.trace.arbitration.winner_confidence
                      )}`
                    : ''}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="section-title">Transactions</h2>
          <span className="badge">
            {transactions.length} total
          </span>
        </div>

        {loadingTx && <p className="mt-4">Loading transactions...</p>}

        {!loadingTx && transactions.length === 0 && (
          <p className="text-sm text-muted text-center mt-6">
            No transactions yet. Upload a statement to begin.
          </p>
        )}

        {transactions.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th className="table-head pb-3">Date</th>
                  <th className="table-head pb-3">Description</th>
                  <th className="table-head pb-3">Category</th>
                  <th className="table-head pb-3 text-right">Amount</th>
                  <th className="table-head pb-3">Confidence</th>
                  <th className="table-head pb-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className={`table-row ${
                      tx.needs_review ? 'bg-warning/10' : ''
                    }`}
                  >
                    <td className="py-3 pr-4">{tx.date.slice(0, 10)}</td>
                    <td className="py-3 pr-4 text-ink">{tx.description}</td>
                    <td className="py-3 pr-4">
                      <span className="badge">{tx.category}</span>
                    </td>
                    <td className="py-3 pr-4 text-right font-semibold text-ink">
                      {tx.amount.toFixed(2)}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={`badge ${
                          tx.confidence > 0.9
                            ? 'badge-success'
                            : 'badge-warning'
                        }`}
                      >
                        {(tx.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 text-right space-x-2">
                      <button
                        onClick={() => openExplain(tx.id)}
                        className="btn-ghost text-xs"
                      >
                        <Info size={12} /> Explain
                      </button>
                      <button
                        onClick={() => openEdit(tx)}
                        className="btn-ghost text-xs"
                      >
                        <Pencil size={12} /> Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {explainTx && (
        <Modal onClose={() => setExplainTx(null)}>
          <pre className="text-xs bg-surface-muted p-4 rounded-2xl">
            {JSON.stringify(explainTx, null, 2)}
          </pre>
        </Modal>
      )}

      {editTx && (
        <Modal onClose={() => setEditTx(null)}>
          <h3 className="section-title mb-3">Edit Transaction</h3>
          <input
            className="input mb-2"
            value={editMerchant}
            onChange={(e) => setEditMerchant(e.target.value)}
          />
          <input
            className="input mb-2"
            value={editCategory}
            onChange={(e) => setEditCategory(e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            Remember this correction
          </label>
          <button onClick={saveEdit} className="btn-primary mt-4">
            Save
          </button>
        </Modal>
      )}
    </div>
  );
}

/* =======================
   Modal
   ======================= */

function Modal({
  children,
  onClose,
}: {
  children: React.ReactNode;
  onClose: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        {children}
        <div className="text-right mt-4">
          <button onClick={onClose} className="btn-ghost text-sm">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
