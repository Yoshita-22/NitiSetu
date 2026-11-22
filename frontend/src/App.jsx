import React, { useState, useEffect, useCallback } from 'react';
import { ChatHeader } from './components/chat/ChatHeader';
import { ChatMessages } from './components/chat/ChatMessages';
import { WelcomeScreen } from './components/chat/WelcomeScreen';
import { MessageComposer } from './components/chat/MessageComposer';
import { ConversationSidebar } from './components/chat/ConversationSidebar';
import { checkBackendHealth, sendChatQuery, resumeChatQuery, uploadDocument, indexDocument } from './services/api';

export const App = () => {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [language, setLanguage] = useState('en');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Conversation state
  const [conversationId, setConversationId] = useState(() =>
    `conv-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
  );
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingInterrupt, setPendingInterrupt] = useState(null);
  const [activeDocumentId, setActiveDocumentId] = useState(null);
  const [conversationHistory, setConversationHistory] = useState([]);

  // Backend health check
  const verifyHealth = useCallback(async () => {
    setBackendStatus('checking');
    try {
      const result = await checkBackendHealth();
      setBackendStatus(result.success && result.data?.status === 'healthy' ? 'connected' : 'disconnected');
    } catch {
      setBackendStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    verifyHealth();
  }, [verifyHealth]);

  // Start new conversation
  const handleNewChat = useCallback(() => {
    // Save current conversation to history if it has messages
    if (messages.length > 0) {
      setConversationHistory(prev => {
        const existing = prev.find(c => c.id === conversationId);
        if (existing) {
          return prev.map(c => c.id === conversationId ? { ...c, messages, updatedAt: Date.now() } : c);
        }
        const firstUserMsg = messages.find(m => m.role === 'user');
        return [
          {
            id: conversationId,
            title: firstUserMsg?.content?.substring(0, 50) || 'New conversation',
            messages,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          ...prev,
        ];
      });
    }

    const newId = `conv-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    setConversationId(newId);
    setMessages([]);
    setPendingInterrupt(null);
    setActiveDocumentId(null);
    setSidebarOpen(false);
  }, [messages, conversationId]);

  // Load conversation from history
  const handleLoadConversation = useCallback((conv) => {
    setConversationId(conv.id);
    setMessages(conv.messages || []);
    setPendingInterrupt(null);
    setActiveDocumentId(null);
    setSidebarOpen(false);
  }, []);

  // Handle sending a message
  const handleSendMessage = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setPendingInterrupt(null);

    try {
      const res = await sendChatQuery(conversationId, text.trim(), activeDocumentId);
      if (!res.success) {
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: res.error || 'Something went wrong. Please try again.',
          isError: true,
          timestamp: new Date(),
        }]);
        return;
      }

      const data = res.data;

      if (data.status === 'waiting_for_user') {
        setPendingInterrupt({
          questions: data.pending_questions || [],
          prompt: data.answer,
        });

        setMessages(prev => [...prev, {
          id: `bot-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          intent: data.intent,
          isInterrupt: true,
          pendingQuestions: data.pending_questions,
          timestamp: new Date(),
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: `bot-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          intent: data.intent,
          sources: data.sources || [],
          execution: data.execution,
          results: data.results,
          timestamp: new Date(),
        }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Network error. Please check your connection and try again.',
        isError: true,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, isLoading, activeDocumentId]);

  // Handle resume (eligibility structured answers)
  const handleResumeSubmit = useCallback(async (answers) => {
    setIsLoading(true);
    try {
      const res = await resumeChatQuery(conversationId, answers);
      if (!res.success) {
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: res.error || 'Failed to resume workflow.',
          isError: true,
          timestamp: new Date(),
        }]);
        return;
      }

      const data = res.data;
      setPendingInterrupt(null);

      if (data.status === 'waiting_for_user') {
        setPendingInterrupt({
          questions: data.pending_questions || [],
          prompt: data.answer,
        });
        setMessages(prev => [...prev, {
          id: `bot-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          intent: data.intent,
          isInterrupt: true,
          pendingQuestions: data.pending_questions,
          timestamp: new Date(),
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: `bot-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          intent: data.intent,
          sources: data.sources || [],
          execution: data.execution,
          results: data.results,
          timestamp: new Date(),
        }]);
      }
    } catch {
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Failed to resume the assessment. Please try again.',
        isError: true,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId]);

  // Handle file upload (PDF)
  const handleFileUpload = useCallback(async (file) => {
    // Add a user message indicating upload
    const userMsg = {
      id: `user-upload-${Date.now()}`,
      role: 'user',
      content: `📎 Uploaded document: ${file.name}`,
      isUpload: true,
      fileName: file.name,
      fileSize: file.size,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const uploadRes = await uploadDocument(file);
      if (!uploadRes.success) {
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Failed to upload document: ${uploadRes.error}`,
          isError: true,
          timestamp: new Date(),
        }]);
        return;
      }

      const docId = uploadRes.data?.document_id;
      if (!docId) {
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'Upload succeeded but no document ID was returned.',
          isError: true,
          timestamp: new Date(),
        }]);
        return;
      }

      // Index document if not already indexed during upload
      if (uploadRes.data?.processing_status !== 'INDEXED') {
        const indexRes = await indexDocument(docId, 'anonymous_citizen');
        if (!indexRes.success) {
          setMessages(prev => [...prev, {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: `Document uploaded but indexing failed: ${indexRes.error}`,
            isError: true,
            timestamp: new Date(),
          }]);
          return;
        }
      }

      setActiveDocumentId(docId);
      setMessages(prev => [...prev, {
        id: `bot-upload-${Date.now()}`,
        role: 'assistant',
        content: `✅ Document "${file.name}" has been uploaded and indexed successfully.\n\nYou can now ask questions about this document. For example:\n- "Summarize this document"\n- "What are the key provisions?"\n- "Explain section 3 of this document"`,
        intent: 'DOCUMENT_QA',
        timestamp: new Date(),
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'An error occurred while processing the document.',
        isError: true,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-screen bg-navy-950 text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <ConversationSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversationHistory}
        currentId={conversationId}
        onNewChat={handleNewChat}
        onLoadConversation={handleLoadConversation}
      />

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <ChatHeader
          language={language}
          onLanguageChange={setLanguage}
          onNewChat={handleNewChat}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          backendStatus={backendStatus}
        />

        {/* Chat Content */}
        <div className="flex-1 overflow-hidden relative">
          {hasMessages ? (
            <ChatMessages
              messages={messages}
              isLoading={isLoading}
              pendingInterrupt={pendingInterrupt}
              onResumeSubmit={handleResumeSubmit}
              onSendMessage={handleSendMessage}
              language={language}
            />
          ) : (
            <WelcomeScreen
              onSendMessage={handleSendMessage}
              language={language}
            />
          )}
        </div>

        {/* Message Composer */}
        <MessageComposer
          onSendMessage={handleSendMessage}
          onFileUpload={handleFileUpload}
          isLoading={isLoading}
          hasActiveDocument={!!activeDocumentId}
          language={language}
        />
      </div>
    </div>
  );
};

export default App;
