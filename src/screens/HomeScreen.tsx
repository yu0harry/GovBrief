import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import axios from 'axios';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View
} from 'react-native';

const BACKEND_URL = 'https://govbrief-production.up.railway.app';

interface NotificationItem {
  id: string;
  type: 'complete' | 'analyzing' | 'info';
  title: string;
  message: string;
  date: string;
  read: boolean; 
}

interface Document {
  document_id: string;
  filename: string;
  created_at: string;
  status: string;
  file_size?: number;
  page_count?: number;
}

export default function HomeScreen() {
  const navigation = useNavigation();

  // 문서 관련 state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // 알림 관련 state (환영 메시지만)
  const [notifications, setNotifications] = useState<NotificationItem[]>([
    { 
      id: 'welcome', 
      type: 'info', 
      title: '👋 환영합니다', 
      message: 'AI LIFE에 오신 것을 환영합니다! 문서를 업로드하고 AI 분석을 받아보세요.', 
      date: '지금', 
      read: false 
    },
  ]);

  const [isNotiModalVisible, setNotiModalVisible] = useState(false);
  const [showMainNotification, setShowMainNotification] = useState(true);

  const hasUnread = notifications.some(n => !n.read);

  // 백엔드에서 문서 목록 가져오기
  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/v1/documents/`, {
        timeout: 10000
      });
      
      const docs = response.data.documents || [];
      setDocuments(docs);

      // 새로운 분석 완료 문서가 있으면 알림 추가
      if (docs.length > 0) {
        const completedDocs = docs.filter((doc: Document) => 
          doc.status === 'completed' || doc.status === '분석완료'
        );

        if (completedDocs.length > 0) {
          const newNotifications = completedDocs.slice(0, 3).map((doc: Document, index: number) => ({
            id: `complete_${doc.document_id}`,
            type: 'complete' as const,
            title: '✅ 분석 완료',
            message: `${doc.filename} 분석이 끝났습니다.`,
            date: formatDate(doc.created_at),
            read: false
          }));

          setNotifications(prev => [
            ...newNotifications,
            ...prev.filter(n => n.type === 'info')
          ]);
        }
      }
    } catch (error) {
      console.error('문서 목록 조회 실패:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // 새로고침
  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDocuments();
  }, []);

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    fetchDocuments();
  }, []);

  // 최근 문서 3개
  const recentDocs = documents.slice(0, 3);
  // 가장 최신 문서
  const latestDoc = documents.length > 0 ? documents[0] : null;

  const handleNotificationItemPress = (id: string, type: string) => {
    setNotifications(prev => prev.map(item => 
      item.id === id ? { ...item, read: true } : item
    ));

    setNotiModalVisible(false);

    if (type === 'complete') {
      navigation.navigate('Documents' as never);
    }
  };

  const handleMainCardPress = () => {
    if (latestDoc && (latestDoc.status === '분석완료' || latestDoc.status === 'completed')) {
      setShowMainNotification(false);
      navigation.navigate('Documents' as never);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case '분석완료':
      case 'completed':
      case 'analyzed':
        return '#4CAF50';
      case '분석중':
      case 'analyzing':
        return '#FF9800';
      case '업로드완료':
      case 'uploaded':
        return '#2196F3';
      default: 
        return '#999';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return '분석완료';
      case 'analyzing':
        return '분석중';
      case 'uploaded':
        return '업로드완료';
      default:
        return status;
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return '방금 전';
      if (diffMins < 60) return `${diffMins}분 전`;
      if (diffHours < 24) return `${diffHours}시간 전`;
      if (diffDays < 7) return `${diffDays}일 전`;
      
      return date.toLocaleDateString('ko-KR', { 
        month: '2-digit', 
        day: '2-digit' 
      });
    } catch {
      return dateString;
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#f0f8ff' }}>
      <ScrollView 
        style={styles.container} 
        contentContainerStyle={{ paddingBottom: 20 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>🤖 AI LIFE</Text>
            <Text style={styles.subtitle}>공공문서 AI 서비스</Text>
          </View>
          
          <TouchableOpacity onPress={() => setNotiModalVisible(true)} style={styles.bellButton}>
            <Ionicons name="notifications" size={28} color="#333" />
            {hasUnread && <View style={styles.redDot} />}
          </TouchableOpacity>
        </View>


        {/* 메인 알림 카드 - 최신 문서가 있을 때만 표시 */}
        {showMainNotification && latestDoc && (
          <View style={styles.notificationWrapper}>
            <TouchableOpacity 
              style={styles.notificationCard}
              onPress={handleMainCardPress}
              activeOpacity={
                latestDoc.status === '분석완료' || latestDoc.status === 'completed' 
                  ? 0.7 
                  : 1
              }
            >
              <View style={styles.notiContent}>
                <Text style={[
                  styles.notiTitle, 
                  { 
                    color: (latestDoc.status === '분석중' || latestDoc.status === 'analyzing') 
                      ? '#FF9800' 
                      : '#4CAF50' 
                  }
                ]}>
                  {(latestDoc.status === '분석중' || latestDoc.status === 'analyzing') 
                    ? '⏳ 분석 진행 중' 
                    : '✅ 분석 완료'}
                </Text>
                <Text style={styles.notiText}>
                  <Text style={{ fontWeight: 'bold' }}>{latestDoc.filename}</Text>
                  {(latestDoc.status === '분석중' || latestDoc.status === 'analyzing')
                    ? ' 문서를 열심히 분석하고 있어요.' 
                    : ' 분석이 끝났습니다. 확인해보세요!'}
                </Text>
              </View>
              <TouchableOpacity 
                style={styles.closeButton} 
                onPress={(e) => {
                  e.stopPropagation();
                  setShowMainNotification(false);
                }}
              >
                <Text style={styles.closeButtonText}>✕</Text>
              </TouchableOpacity>
            </TouchableOpacity>
          </View>
        )}

        {/* 최근 문서 섹션 */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>📋 최근 문서</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Documents' as never)}>
            <Text style={styles.moreLink}>더보기 ➜</Text>
          </TouchableOpacity>
        </View>

        {/* 로딩 중 */}
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color="#2196F3" />
            <Text style={styles.loadingText}>문서 목록을 불러오는 중...</Text>
          </View>
        ) : recentDocs.length > 0 ? (
          /* 문서 목록 */
          <View style={styles.listContainer}>
            {recentDocs.map((doc) => (
              <TouchableOpacity 
                key={doc.document_id} 
                style={styles.docItem}
                onPress={() => navigation.navigate('Documents' as never)}
              >
                <View style={styles.docIconWrapper}>
                  <Text style={styles.docIcon}>📄</Text>
                </View>
                <View style={styles.docInfo}>
                  <Text style={styles.docName}>{doc.filename}</Text>
                  <Text style={styles.docDate}>{formatDate(doc.created_at)}</Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(doc.status) }]}>
                  <Text style={styles.statusText}>{getStatusText(doc.status)}</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        ) : (
          /* 문서 없을 때 */
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>📭</Text>
            <Text style={styles.emptyText}>아직 업로드된 문서가 없어요</Text>
            <Text style={styles.emptySubText}>업로드 탭에서 문서를 추가해보세요!</Text>
            <TouchableOpacity 
              style={styles.uploadButton}
              onPress={() => navigation.navigate('Upload' as never)}
            >
              <Text style={styles.uploadButtonText}>📤 문서 업로드하기</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* AI 챗봇 배너 */}
        <TouchableOpacity 
          style={styles.banner}
          onPress={() => navigation.navigate('Chat' as never)}
        >
          <Text style={styles.bannerIcon}>💬</Text>
          <View>
            <Text style={styles.bannerTitle}>AI에게 질문하기</Text>
            <Text style={styles.bannerSubtitle}>문서 내용이 어렵다면 물어보세요</Text>
          </View>
        </TouchableOpacity>

      </ScrollView>

      {/* 알림 모달 */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={isNotiModalVisible}
        onRequestClose={() => setNotiModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>🔔 알림 센터</Text>
              <TouchableOpacity onPress={() => setNotiModalVisible(false)}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>

            <FlatList
              data={notifications}
              keyExtractor={item => item.id}
              contentContainerStyle={{ paddingBottom: 20 }}
              renderItem={({ item }) => (
                <TouchableOpacity 
                  style={[
                    styles.historyItem,
                    item.read && styles.readItem
                  ]}
                  onPress={() => handleNotificationItemPress(item.id, item.type)}
                >
                  <View style={styles.historyIconBox}>
                    <Text>{item.type === 'complete' ? '✅' : item.type === 'analyzing' ? '⏳' : 'ℹ️'}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <View style={{flexDirection:'row', justifyContent:'space-between', marginBottom: 2}}>
                      <Text style={[styles.historyTitle, item.read && {color: '#888'}]}>
                        {item.title}
                      </Text>
                      <Text style={styles.historyDate}>{item.date}</Text>
                    </View>
                    <Text style={[styles.historyMessage, item.read && {color: '#aaa'}]}>
                      {item.message}
                    </Text>
                  </View>
                </TouchableOpacity>
              )}
              ListEmptyComponent={
                <View style={{ alignItems: 'center', marginTop: 50 }}>
                  <Text style={{ color: '#999' }}>새로운 알림이 없습니다.</Text>
                </View>
              }
            />
          </View>
        </View>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#f0f8ff',
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center',
  },
  bellButton: {
    position: 'relative',
    padding: 5,
  },
  redDot: {
    position: 'absolute',
    top: 5,
    right: 5,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'red',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2196F3',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  notificationWrapper: {
    paddingHorizontal: 20,
    marginTop: 10,
  },
  notificationCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 }, 
    shadowOpacity: 0.1,
    shadowRadius: 5,
    elevation: 4,
  },
  notiContent: {
    paddingRight: 20,
  },
  notiTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  notiText: {
    fontSize: 15,
    color: '#333',
    lineHeight: 22,
  },
  closeButton: {
    position: 'absolute',
    top: 10,
    right: 10,
    padding: 5,
    zIndex: 1, 
  },
  closeButtonText: {
    fontSize: 16,
    color: '#999',
    fontWeight: 'bold',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 10,
    marginTop: 20, 
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  moreLink: {
    fontSize: 14,
    color: '#2196F3',
    fontWeight: '600',
  },
  loadingContainer: {
    paddingHorizontal: 20,
    paddingVertical: 40,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 14,
    color: '#666',
  },
  listContainer: {
    paddingHorizontal: 20,
  },
  docItem: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 12,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 2,
    elevation: 1,
  },
  docIconWrapper: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#f5f5f5',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 15,
  },
  docIcon: {
    fontSize: 20,
  },
  docInfo: {
    flex: 1,
  },
  docName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 2,
  },
  docDate: {
    fontSize: 12,
    color: '#999',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  statusText: {
    color: 'white',
    fontSize: 10,
    fontWeight: 'bold',
  },
  emptyContainer: {
    paddingHorizontal: 20,
    paddingVertical: 40,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 50,
    marginBottom: 15,
    opacity: 0.5,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#888',
    marginBottom: 8,
  },
  emptySubText: {
    fontSize: 14,
    color: '#999',
    marginBottom: 20,
  },
  uploadButton: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 25,
  },
  uploadButtonText: {
    color: 'white',
    fontSize: 15,
    fontWeight: 'bold',
  },
  banner: {
    backgroundColor: '#E3F2FD',
    margin: 20,
    padding: 20,
    borderRadius: 15,
    flexDirection: 'row',
    alignItems: 'center',
  },
  bannerIcon: {
    fontSize: 30,
    marginRight: 15,
  },
  bannerTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1565C0',
    marginBottom: 2,
  },
  bannerSubtitle: {
    fontSize: 13,
    color: '#5c86ac',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)', 
    justifyContent: 'flex-end', 
  },
  modalContent: {
    backgroundColor: 'white',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    height: '80%', 
    padding: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  historyItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    borderRadius: 12,
    backgroundColor: 'white',
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#eee',
  },
  readItem: {
    opacity: 0.6,
    backgroundColor: '#f9f9f9',
    borderColor: '#f0f0f0',
  },
  historyIconBox: {
    marginRight: 15,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f5f5f5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  historyTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#333',
  },
  historyMessage: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },
  historyDate: {
    fontSize: 11,
    color: '#999',
  },
});