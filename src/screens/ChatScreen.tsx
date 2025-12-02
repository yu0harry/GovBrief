import axios from 'axios';
import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  LayoutChangeEvent,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View
} from 'react-native';

const BACKEND_URL = 'https://govbrief-production.up.railway.app';

const SUGGESTED_QUESTIONS = [
  "📋 문서 요약해줘",
  "💡 중요 내용 알려줘", 
  "❓ 이 문서의 주의사항은?",
  "📅 마감 날짜 알려줘",
  "📍 제출처가 어디야?"
];

interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: number;
}

export default function ChatScreen() {
  // --- 🔍 검색 기능 관련 State ---
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [foundIds, setFoundIds] = useState<string[]>([]);
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);
  const messageYPositions = useRef<{ [key: string]: number }>({});

  // --- 💬 채팅 관련 State ---
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      text: '안녕하세요! 업로드한 문서에 대해 궁금한 점을 물어보세요 😊\n\n📄 분석된 문서가 있다면 해당 문서의 내용을 바탕으로 답변드릴게요!',
      isUser: false,
      timestamp: Date.now(),
    }
  ]);

  // --- ⏳ 로딩 관련 State ---
  const [isTyping, setIsTyping] = useState(false);
  const [currentDocumentId, setCurrentDocumentId] = useState<string | null>(null);

  const scrollViewRef = useRef<ScrollView>(null);

  // 메시지 추가 시 자동 스크롤
  useEffect(() => {
    if (!isSearchMode) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages, isSearchMode]);

  useEffect(() => {
  const fetchLatestDocument = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/v1/documents/`);
      const docs = response.data.documents || [];
      
      if (docs.length > 0) {
        const latestDoc = docs[0];
        setCurrentDocumentId(latestDoc.document_id);
        
        const systemMessage: ChatMessage = {
          id: Date.now().toString() + '_system',
          text: `📄 "${latestDoc.filename}" 문서가 자동으로 선택되었습니다. 이제 이 문서에 대해 질문할 수 있어요!`,
          isUser: false,
          timestamp: Date.now(),
        };
        setMessages(prev => [...prev, systemMessage]);
      }
    } catch (error) {
      console.error('문서 조회 실패:', error);
    }
  };
  
  fetchLatestDocument();
}, []);

  // --- 🔍 검색 로직 ---
  useEffect(() => {
    if (searchText.trim() === '') {
      setFoundIds([]);
      return;
    }
    const ids = messages
      .filter(msg => msg.text.includes(searchText))
      .map(msg => msg.id);
    
    setFoundIds(ids);
    setCurrentMatchIndex(0);
  }, [searchText, messages]);

  useEffect(() => {
    if (foundIds.length > 0) {
      const targetId = foundIds[currentMatchIndex];
      const yPos = messageYPositions.current[targetId];

      if (yPos !== undefined) {
        scrollViewRef.current?.scrollTo({ y: yPos, animated: true });
      }
    }
  }, [currentMatchIndex, foundIds]);

  // 검색 관련 함수들
  const handlePrevMatch = () => {
    if (foundIds.length === 0) return;
    setCurrentMatchIndex(prev => (prev - 1 + foundIds.length) % foundIds.length);
  };

  const handleNextMatch = () => {
    if (foundIds.length === 0) return;
    setCurrentMatchIndex(prev => (prev + 1) % foundIds.length);
  };

  const closeSearch = () => {
    setIsSearchMode(false);
    setSearchText('');
    setFoundIds([]);
  };

  // --- 💬 실제 백엔드 채팅 함수 ---
  const sendMessageToBackend = async (userMessage: string): Promise<string> => {
    try {
      const response = await axios.post(`${BACKEND_URL}/api/v1/chat`, {
        question: userMessage,
        document_id: currentDocumentId, // 현재 선택된 문서 ID (없으면 null)
        max_tokens: 1000
      }, {
        timeout: 30000, // 30초 타임아웃
        headers: {
          'Content-Type': 'application/json'
        }
      });

      return response.data.answer || response.data.response || 'AI 응답을 받지 못했습니다.';
    } catch (error: any) {
      console.error('백엔드 채팅 오류:', error);
      
      if (error.code === 'ECONNABORTED') {
        return '⏰ 응답 시간이 초과되었습니다. 다시 시도해주세요.';
      } else if (error.response?.status === 404) {
        return '📄 먼저 문서를 업로드하고 분석해주세요. 그래야 해당 문서에 대해 질문할 수 있어요!';
      } else if (error.response?.status === 500) {
        return '🔧 서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
      } else {
        return `❌ 연결 오류: ${error.message}`;
      }
    }
  };

  // 메시지 전송 함수
  const sendMessage = async (textToSend: string) => {
    if (!textToSend.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      text: textToSend.trim(),
      isUser: true,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setMessage(''); 
    setIsTyping(true);

    try {
      // 실제 백엔드 API 호출
      const aiResponse = await sendMessageToBackend(textToSend.trim());
      
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: aiResponse,
        isUser: false,
        timestamp: Date.now(),
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      // 예외적인 에러 처리
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: '죄송해요, 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요. 🤖',
        isUser: false,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSendButtonPress = () => {
    sendMessage(message);
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  // 문서 선택 함수 (향후 문서 목록에서 호출될 수 있도록)
  const selectDocument = (documentId: string, filename: string) => {
    setCurrentDocumentId(documentId);
    const systemMessage: ChatMessage = {
      id: Date.now().toString(),
      text: `📄 "${filename}" 문서가 선택되었습니다. 이제 이 문서에 대해 질문할 수 있어요!`,
      isUser: false,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, systemMessage]);
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined} 
      keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0} 
    >
      {/* 헤더 영역 */}
      <View style={styles.header}>
        {!isSearchMode ? (
          <View style={styles.headerContent}>
            <View>
              <Text style={styles.title}>💬 AI 챗봇</Text>
              <Text style={styles.subtitle}>
                {currentDocumentId 
                  ? '선택된 문서에 대해 질문해보세요' 
                  : '문서에 대해 질문해보세요'
                }
              </Text>
            </View>
            <TouchableOpacity onPress={() => setIsSearchMode(true)} style={styles.searchIconBtn}>
              <Text style={{fontSize: 24}}>🔍</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.searchHeaderContent}>
            <TextInput 
              style={styles.searchInput}
              placeholder="대화 내용 검색..."
              value={searchText}
              onChangeText={setSearchText}
              autoFocus
            />
            <View style={styles.searchControls}>
              <Text style={styles.matchCount}>
                {foundIds.length > 0 ? `${currentMatchIndex + 1}/${foundIds.length}` : '0/0'}
              </Text>
              <TouchableOpacity onPress={handlePrevMatch} style={styles.controlBtn}>
                <Text style={styles.controlBtnText}>▲</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={handleNextMatch} style={styles.controlBtn}>
                <Text style={styles.controlBtnText}>▼</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={closeSearch} style={styles.controlBtn}>
                <Text style={styles.controlBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>
      
      {/* 메시지 영역 */}
      <ScrollView 
        ref={scrollViewRef}
        style={styles.messageContainer} 
        contentContainerStyle={{ paddingBottom: 20 }}
        showsVerticalScrollIndicator={false}
      >
        {messages.map((msg) => {
          const isMatch = foundIds.includes(msg.id);
          const isCurrentMatch = foundIds[currentMatchIndex] === msg.id;

          return (
            <View 
              key={msg.id} 
              onLayout={(event: LayoutChangeEvent) => {
                const layout = event.nativeEvent.layout;
                messageYPositions.current[msg.id] = layout.y;
              }}
              style={[
                styles.messageWrapper,
                msg.isUser ? styles.userMessageWrapper : styles.aiMessageWrapper
              ]}
            >
              <View 
                style={[
                  styles.messageBubble,
                  msg.isUser ? styles.userMessage : styles.aiMessage,
                  isMatch && { borderWidth: 2, borderColor: '#FFD700' }, 
                  isCurrentMatch && { backgroundColor: '#FFF9C4' } 
                ]}
              >
                <Text style={[
                  styles.messageText,
                  msg.isUser ? styles.userMessageText : styles.aiMessageText,
                  isCurrentMatch && { color: 'black' } 
                ]}>
                  {msg.text}
                </Text>
              </View>
              <Text style={styles.messageTime}>
                {formatTime(msg.timestamp)}
              </Text>
            </View>
          );
        })}

        {/* AI 타이핑 중 표시 */}
        {isTyping && (
          <View style={[styles.messageWrapper, styles.aiMessageWrapper]}>
            <View style={[styles.messageBubble, styles.aiMessage]}>
              <View style={styles.typingIndicator}>
                <ActivityIndicator size="small" color="#666" />
                <Text style={[styles.messageText, styles.aiMessageText, { marginLeft: 10 }]}>
                  AI가 답변을 생각하고 있어요...
                </Text>
              </View>
            </View>
          </View>
        )}
      </ScrollView>

      {/* 추천 질문 (메시지가 1개이거나 적을 때) */}
      {!isSearchMode && (
        <View style={styles.suggestionWrapper}>
          <Text style={styles.suggestionTitle}>추천 질문</Text>
          <ScrollView 
            horizontal 
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.suggestionScrollContent}
          >
            {SUGGESTED_QUESTIONS.map((question, index) => (
              <TouchableOpacity 
                key={index} 
                style={styles.suggestionChip}
                onPress={() => sendMessage(question)}
              >
                <Text style={styles.suggestionText}>{question}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}
      
      {/* 입력창 영역 */}
      {!isSearchMode && (
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            value={message}
            onChangeText={setMessage}
            placeholder="질문을 입력하세요..."
            multiline
            maxLength={500}
            editable={!isTyping}
          />
          <TouchableOpacity 
            style={[
              styles.sendButton, 
              (!message.trim() || isTyping) && styles.sendButtonDisabled
            ]} 
            onPress={handleSendButtonPress}
            disabled={!message.trim() || isTyping}
          >
            <Text style={styles.sendButtonText}>
              {isTyping ? '⏳' : '전송'}
            </Text>
          </TouchableOpacity>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f8ff',
  },
  header: {
    paddingTop: 60,
    paddingBottom: 15,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: 'white',
    zIndex: 10,
    justifyContent: 'center',
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  searchIconBtn: {
    padding: 5,
  },
  searchHeaderContent: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 50, 
  },
  searchInput: {
    flex: 1,
    height: 40,
    backgroundColor: '#f1f1f1',
    borderRadius: 20,
    paddingHorizontal: 15,
    marginRight: 10,
  },
  searchControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  matchCount: {
    marginRight: 10,
    color: '#666',
    fontSize: 12,
    fontWeight: '600',
  },
  controlBtn: {
    padding: 8,
    marginLeft: 2,
  },
  controlBtnText: {
    fontSize: 18,
    color: '#333',
    fontWeight: 'bold',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2196F3',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
  },
  messageContainer: {
    flex: 1,
    padding: 15,
  },
  messageWrapper: {
    marginBottom: 15,
  },
  userMessageWrapper: {
    alignItems: 'flex-end',
  },
  aiMessageWrapper: {
    alignItems: 'flex-start',
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 18,
    marginBottom: 4,
  },
  userMessage: {
    backgroundColor: '#2196F3',
    borderBottomRightRadius: 4,
  },
  aiMessage: {
    backgroundColor: 'white',
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageText: {
    color: 'white',
  },
  aiMessageText: {
    color: '#333',
  },
  messageTime: {
    fontSize: 12,
    color: '#666',
    marginHorizontal: 5,
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  suggestionWrapper: {
    paddingVertical: 10,
    backgroundColor: '#f0f8ff', 
  },
  suggestionTitle: {
    fontSize: 12,
    color: '#888',
    marginLeft: 20,
    marginBottom: 8,
    fontWeight: '600',
  },
  suggestionScrollContent: {
    paddingHorizontal: 15,
  },
  suggestionChip: {
    backgroundColor: 'white',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#2196F3',
    marginRight: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 1,
    elevation: 1,
  },
  suggestionText: {
    color: '#2196F3',
    fontSize: 14,
    fontWeight: '600',
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 10,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    alignItems: 'flex-end',
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 10,
    marginRight: 10,
    maxHeight: 100,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  sendButton: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#ccc',
  },
  sendButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
});