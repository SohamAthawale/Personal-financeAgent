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

  /* =======================
     Render
     ======================= */

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Please log in.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8 max-w-7xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold">Financial Dashboard</h1>

      {/* Upload Card */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 bg-white'
        }`}
      >
        <input
          type="file"
          accept=".pdf"
          id="file"
          className="hidden"
          onChange={(e) => e.target.files && handleFile(e.target.files[0])}
        />
        <Upload className="w-10 h-10 mx-auto text-gray-400 mb-3" />
        <label htmlFor="file" className="cursor-pointer text-blue-600">
          Upload bank statement (PDF)
        </label>

        {uploadStatus.status === 'uploading' && (
          <div className="mt-4 text-sm text-gray-600">
            <Loader className="animate-spin mx-auto mb-2" />
            {uploadStatus.message}
          </div>
        )}

        {uploadStatus.status === 'success' && (
          <CheckCircle className="mx-auto text-green-500 mt-4" />
        )}

        {uploadStatus.status === 'error' && (
          <AlertCircle className="mx-auto text-red-500 mt-4" />
        )}
      </div>

      {lastParse?.status === 'success' && (
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold mb-4">Latest Parse Trace</h2>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm text-gray-700">
            <div>
              <div className="text-xs text-gray-500">Statement ID</div>
              <div className="font-medium">{lastParse.statement_id ?? 'n/a'}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Transactions</div>
              <div className="font-medium">
                {lastParse.transaction_count ??
                  lastParse.transactions_count ??
                  'n/a'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Schema Confidence</div>
              <div className="font-medium">
                {formatPercent(lastParse.schema_confidence)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Variant</div>
              <div className="font-medium">{lastParse.schema_variant ?? 'n/a'}</div>
            </div>
          </div>

          {lastParse.trace && (
            <div className="mt-4 text-xs text-gray-700 space-y-2">
              <div>
                <span className="text-gray-500">Initial:</span>{' '}
                {formatPercent(lastParse.trace.initial?.confidence)}{' '}
                {lastParse.trace.initial?.schema_type
                  ? `(${lastParse.trace.initial?.schema_type})`
                  : ''}
              </div>

              {lastParse.trace.retry && (
                <div>
                  <span className="text-gray-500">Retry:</span>{' '}
                  {lastParse.trace.retry.decision ?? 'n/a'}
                </div>
              )}

              {lastParse.trace.retry?.candidates &&
                lastParse.trace.retry.candidates.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {lastParse.trace.retry.candidates.map((c, idx) => (
                      <span
                        key={`${c.variant}-${idx}`}
                        className="bg-gray-100 text-gray-700 px-2 py-1 rounded"
                      >
                        {c.variant ?? 'variant'} · {formatPercent(c.confidence)}
                        {c.schema_type ? ` · ${c.schema_type}` : ''}
                      </span>
                    ))}
                  </div>
                )}

              {lastParse.trace.arbitration?.used && (
                <div>
                  <span className="text-gray-500">Arbitration:</span>{' '}
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

      {/* Transactions */}
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="font-semibold mb-4">Transactions</h2>

        {loadingTx && <p>Loading transactions...</p>}

        {!loadingTx && transactions.length === 0 && (
          <p className="text-sm text-gray-500 text-center">
            No transactions yet. Upload a statement to begin.
          </p>
        )}

        {transactions.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th className="text-right">Amount</th>
                <th>Confidence</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr
                  key={tx.id}
                  className={`border-b ${
                    tx.needs_review ? 'bg-yellow-50' : ''
                  }`}
                >
                  <td>{tx.date.slice(0, 10)}</td>
                  <td>{tx.description}</td>
                  <td>{tx.category}</td>
                  <td className="text-right">{tx.amount.toFixed(2)}</td>
                  <td>
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        tx.confidence > 0.9
                          ? 'bg-green-100 text-green-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      {(tx.confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="text-right space-x-2">
                    <button
                      onClick={() => openExplain(tx.id)}
                      className="text-blue-600 text-xs inline-flex items-center gap-1"
                    >
                      <Info size={12} /> Explain
                    </button>
                    <button
                      onClick={() => openEdit(tx)}
                      className="text-gray-600 text-xs inline-flex items-center gap-1"
                    >
                      <Pencil size={12} /> Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals */}
      {explainTx && (
        <Modal onClose={() => setExplainTx(null)}>
          <pre className="text-xs bg-gray-100 p-4 rounded">
            {JSON.stringify(explainTx, null, 2)}
          </pre>
        </Modal>
      )}

      {editTx && (
        <Modal onClose={() => setEditTx(null)}>
          <h3 className="font-semibold mb-3">Edit Transaction</h3>
          <input
            className="border p-2 w-full mb-2"
            value={editMerchant}
            onChange={(e) => setEditMerchant(e.target.value)}
          />
          <input
            className="border p-2 w-full mb-2"
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
          <button
            onClick={saveEdit}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded"
          >
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
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-lg w-full">
        {children}
        <div className="text-right mt-4">
          <button onClick={onClose} className="text-blue-600 text-sm">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
