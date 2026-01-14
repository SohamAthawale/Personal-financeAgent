import React, { useEffect, useState } from 'react';
import {
  Upload,
  AlertCircle,
  CheckCircle,
  Loader,
} from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

/* =======================
   Types
   ======================= */

interface UploadStatus {
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
  message: string;
  transactionCount?: number;
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

  const [explainTx, setExplainTx] = useState<any | null>(null);
  const [editTx, setEditTx] = useState<Transaction | null>(null);
  const [editCategory, setEditCategory] = useState('');
  const [editMerchant, setEditMerchant] = useState('');
  const [remember, setRemember] = useState(true);

  /* =======================
     Fetch transactions
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
     Upload handler
     ======================= */

  const handleFile = async (file: File) => {
    if (!file.type.includes('pdf')) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: 'Please upload a PDF file',
      });
      return;
    }

    if (!auth?.token) return;

    try {
      setUploadStatus({
        status: 'uploading',
        progress: 0,
        message: 'Uploading and parsing statement...',
      });

      const result = await api.uploadStatement(
        file,
        auth.token,
        (progress) => {
          setUploadStatus((prev) => ({
            ...prev,
            progress: Math.round(progress),
          }));
        }
      );

      if (result.status === 'success') {
        setUploadStatus({
          status: 'success',
          progress: 100,
          message: `Parsed ${result.transactions_count || 0} transactions`,
        });

        await fetchTransactions();

        setTimeout(() => {
          setUploadStatus({ status: 'idle', progress: 0, message: '' });
        }, 2500);
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
     Drag & drop
     ======================= */

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type !== 'dragleave');
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
    const res = await api.explainTransaction(id, auth.token);
    setExplainTx(res);
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
              confidence: 1.0,
              corrected: true,
              needs_review: false,
            }
          : t
      )
    );

    setEditTx(null);
  };

  /* =======================
     Render
     ======================= */

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Please log in.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      {/* Upload */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-10 text-center mb-8 ${
          dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-white'
        }`}
      >
        <input
          type="file"
          accept=".pdf"
          id="file"
          className="hidden"
          onChange={(e) => e.target.files && handleFile(e.target.files[0])}
        />
        <Upload className="w-10 h-10 mx-auto mb-2 text-gray-400" />
        <label htmlFor="file" className="cursor-pointer text-blue-600">
          Upload bank statement PDF
        </label>

        {uploadStatus.status === 'uploading' && (
          <div className="mt-4">
            <Loader className="animate-spin mx-auto" />
            <p>{uploadStatus.progress}%</p>
          </div>
        )}

        {uploadStatus.status === 'success' && (
          <CheckCircle className="mx-auto text-green-500 mt-4" />
        )}

        {uploadStatus.status === 'error' && (
          <AlertCircle className="mx-auto text-red-500 mt-4" />
        )}
      </div>

      {/* Transactions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-semibold mb-4">Transactions</h2>

        {loadingTx ? (
          <p>Loading...</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th>Amount</th>
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
                    {(tx.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="space-x-2 text-right">
                    <button
                      onClick={() => openExplain(tx.id)}
                      className="text-blue-600 text-xs"
                    >
                      Explain
                    </button>
                    <button
                      onClick={() => openEdit(tx)}
                      className="text-gray-600 text-xs"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Explain Modal */}
      {explainTx && (
        <Modal onClose={() => setExplainTx(null)}>
          <pre className="text-xs bg-gray-100 p-4 rounded">
            {JSON.stringify(explainTx, null, 2)}
          </pre>
        </Modal>
      )}

      {/* Edit Modal */}
      {editTx && (
        <Modal onClose={() => setEditTx(null)}>
          <h3 className="font-semibold mb-2">Edit Transaction</h3>
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
          <label className="text-sm flex items-center gap-2">
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
   Modal helper
   ======================= */

function Modal({
  children,
  onClose,
}: {
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-lg max-w-lg w-full">
        {children}
        <div className="text-right mt-4">
          <button onClick={onClose} className="text-blue-600">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
