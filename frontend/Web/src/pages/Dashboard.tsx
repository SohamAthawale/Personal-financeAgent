import React, { useState } from 'react';
import {
  Upload,
  AlertCircle,
  CheckCircle,
  Loader,
} from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

interface UploadStatus {
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
  message: string;
  transactionCount?: number;
}

export function Dashboard() {
  const { auth } = useAuth();

  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: 'idle',
    progress: 0,
    message: '',
  });
  const [dragActive, setDragActive] = useState(false);

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

    if (!auth?.token) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: 'You must be logged in to upload a statement',
      });
      return;
    }

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
          message: `Successfully parsed ${
            result.transactions_count || 0
          } transactions`,
          transactionCount: result.transactions_count,
        });

        setTimeout(() => {
          setUploadStatus({
            status: 'idle',
            progress: 0,
            message: '',
          });
        }, 3000);
      } else {
        setUploadStatus({
          status: 'error',
          progress: 0,
          message: result.message || 'Failed to parse statement',
        });
      }
    } catch (err) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message:
          err instanceof Error
            ? err.message
            : 'An error occurred during upload',
      });
    }
  };

  /* =======================
     Drag & drop handlers
     ======================= */

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  /* =======================
     Render
     ======================= */

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-slate-500">
          Please log in to upload bank statements.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Dashboard
          </h1>
          <p className="text-gray-600">
            Upload your bank statements to start analyzing your finances
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2">
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-12 text-center transition ${
                dragActive
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 bg-white'
              }`}
            >
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileInput}
                className="hidden"
                id="file-input"
                disabled={uploadStatus.status === 'uploading'}
              />

              <div className="space-y-4">
                <Upload className="w-12 h-12 text-gray-400 mx-auto" />

                {uploadStatus.status === 'idle' && (
                  <>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">
                        Drag and drop your PDF
                      </p>
                      <p className="text-gray-600">or click to browse</p>
                    </div>
                    <label
                      htmlFor="file-input"
                      className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg cursor-pointer transition"
                    >
                      Choose File
                    </label>
                  </>
                )}

                {uploadStatus.status === 'uploading' && (
                  <>
                    <Loader className="w-8 h-8 text-blue-600 mx-auto animate-spin" />
                    <p className="text-gray-700 font-semibold">
                      {uploadStatus.message}
                    </p>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadStatus.progress}%` }}
                      />
                    </div>
                    <p className="text-sm text-gray-600">
                      {uploadStatus.progress}%
                    </p>
                  </>
                )}

                {uploadStatus.status === 'success' && (
                  <>
                    <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
                    <p className="text-gray-600">
                      {uploadStatus.message}
                    </p>
                  </>
                )}

                {uploadStatus.status === 'error' && (
                  <>
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
                    <p className="text-gray-600">
                      {uploadStatus.message}
                    </p>
                    <label
                      htmlFor="file-input"
                      className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg cursor-pointer transition"
                    >
                      Try Again
                    </label>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              About This Tool
            </h3>
            <ul className="space-y-3 text-sm text-gray-600">
              <li>• Upload any bank statement PDF</li>
              <li>• We extract and analyze all transactions</li>
              <li>• View insights and spending patterns</li>
              <li>• Get AI-powered recommendations</li>
            </ul>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Your Account
          </h3>
          <p className="text-sm text-gray-600">
            Logged in as:{' '}
            <span className="font-mono text-gray-900">
              {auth.user.email}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
