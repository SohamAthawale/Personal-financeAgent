import React, { useState } from 'react';
import { Upload, AlertCircle, CheckCircle, FileText, Loader } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

interface UploadStatus {
  status: 'idle' | 'uploading' | 'success' | 'error';
  progress: number;
  message: string;
  transactionCount?: number;
}

export function Dashboard() {
  const { phone } = useAuth();
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: 'idle',
    progress: 0,
    message: '',
  });
  const [dragActive, setDragActive] = useState(false);

  const handleFile = async (file: File) => {
    if (!file.type.includes('pdf')) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: 'Please upload a PDF file',
      });
      return;
    }

    if (!phone) {
      setUploadStatus({
        status: 'error',
        progress: 0,
        message: 'User phone not found',
      });
      return;
    }

    try {
      setUploadStatus({
        status: 'uploading',
        progress: 0,
        message: 'Uploading and parsing statement...',
      });

      const result = await api.uploadStatement(file, phone, (progress) => {
        setUploadStatus((prev) => ({
          ...prev,
          progress: Math.round(progress),
        }));
      });

      if (result.status === 'success') {
        setUploadStatus({
          status: 'success',
          progress: 100,
          message: `Successfully parsed ${result.transactions_count || 0} transactions`,
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
          err instanceof Error ? err.message : 'An error occurred during upload',
      });
    }
  };

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Dashboard</h1>
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
                    <div className="space-y-3">
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
                    </div>
                  </>
                )}

                {uploadStatus.status === 'success' && (
                  <>
                    <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
                    <div>
                      <p className="text-lg font-semibold text-green-700">
                        Success!
                      </p>
                      <p className="text-gray-600">{uploadStatus.message}</p>
                    </div>
                  </>
                )}

                {uploadStatus.status === 'error' && (
                  <>
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
                    <div>
                      <p className="text-lg font-semibold text-red-700">
                        Upload Failed
                      </p>
                      <p className="text-gray-600">{uploadStatus.message}</p>
                    </div>
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
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Upload any bank statement PDF</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>We extract and analyze all transactions</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>View insights and spending patterns</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Get AI-powered recommendations</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-3 mb-4">
              <FileText className="w-6 h-6 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">
                Supported Formats
              </h3>
            </div>
            <p className="text-gray-600 text-sm">
              We support PDF bank statements from most major banks and financial institutions.
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Your Account
            </h3>
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-gray-600">Phone:</span>
                <span className="font-mono text-gray-900 ml-2">{phone}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
