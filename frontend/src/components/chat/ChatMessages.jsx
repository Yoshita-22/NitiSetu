import React, { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { EligibilityInterrupt } from './EligibilityInterrupt';

export const ChatMessages = ({
  messages,
  isLoading,
  pendingInterrupt,
  onResumeSubmit,
  onSendMessage,
  language = 'en',
}) => {
  const bottomRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, pendingInterrupt]);

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto px-4 py-6"
    >
      <div className="max-w-chat mx-auto space-y-1">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} language={language} />
        ))}

        {/* Eligibility interrupt form */}
        {pendingInterrupt && (
          <EligibilityInterrupt
            questions={pendingInterrupt.questions}
            onSubmit={onResumeSubmit}
            onNaturalLanguage={onSendMessage}
            isLoading={isLoading}
          />
        )}

        {/* Typing indicator */}
        {isLoading && <TypingIndicator />}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
