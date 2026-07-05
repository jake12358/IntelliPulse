import type { KnowledgeResponse, ReportResponse } from '../types';

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/upload', { method: 'POST', body: formData });
  if (!response.ok) throw new Error('上传失败');
  return response.json();
}

export async function getReport(sessionId: string, documentIds: string[] = [], query = '对比本次提交的竞品资料'): Promise<ReportResponse> {
  const params = new URLSearchParams({ query, document_ids: documentIds.join(',') });
  const response = await fetch(`/api/report/${sessionId}?${params.toString()}`);
  if (!response.ok) throw new Error('报告获取失败');
  return response.json();
}

export async function getKnowledge(): Promise<KnowledgeResponse> {
  const response = await fetch('/api/knowledge/documents');
  if (!response.ok) throw new Error('知识库读取失败');
  return response.json();
}
