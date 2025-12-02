import axios from 'axios';
import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View
} from 'react-native';

import { useFocusEffect } from '@react-navigation/native';

const BACKEND_URL = 'https://govbrief-production.up.railway.app';

interface Document {
  document_id: string;
  filename: string;
  created_at: string;
  status: string;
  file_size?: number;
  page_count?: number;
}

export default function DocumentListScreen() {
  const [searchText, setSearchText] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('전체');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // 백엔드에서 문서 목록 가져오기
  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/v1/documents/`, {
        timeout: 10000
      });
      
      const docs = response.data.documents || response.data || [];
      setDocuments(docs);
    } catch (error: any) {
      console.error('문서 목록 조회 실패:', error);
      // 조용히 실패 (기존 데이터 유지) 또는 빈 배열
      // setDocuments([]); 
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // 문서 분석 요청
  const analyzeDocument = async (documentId: string, filename: string) => {
    try {
      Alert.alert(
        '분석 시작',
        `${filename}을 분석하시겠습니까?`,
        [
          { text: '취소', style: 'cancel' },
          { 
            text: '분석하기', 
            onPress: async () => {
              try {
                const response = await axios.post(`${BACKEND_URL}/api/v1/analyze`, {
                  document_id: documentId
                }, {
                  timeout: 30000
                });
                
                Alert.alert('분석 완료!', `분석이 완료되었습니다:\n${response.data.summary || '분석 결과를 확인하세요.'}`, [
                  { text: '확인', onPress: () => fetchDocuments() }
                ]);
              } catch (error: any) {
                Alert.alert('분석 실패', `분석 중 오류가 발생했습니다: ${error.message}`);
              }
            }
          }
        ]
      );
    } catch (error) {
      console.error('분석 요청 실패:', error);
    }
  };

  // 새로고침
  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDocuments();
  }, []);

  // 화면이 포커스될 때마다 데이터 로드 (useEffect 중복 제거)
  useFocusEffect(
    useCallback(() => {
      fetchDocuments();
    }, [])
  );

  const filterCategories = ['전체', '업로드 완료', '분석 중', '분석 완료'];

  // ⭐ [수정됨] 띄어쓰기 통일 ('업로드완료' -> '업로드 완료')
  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
      case 'analyzed':
      case '분석완료':
        return '분석 완료';
      case 'analyzing':
      case 'reanalyzing':
        return '분석 중';
      case 'uploaded':
        return '업로드 완료'; // 띄어쓰기 추가됨
      default:
        return '업로드 완료'; // 띄어쓰기 추가됨
    }
  };

  const getFilteredDocuments = () => {
    return documents.filter((doc) => {
      const matchesSearch = doc.filename?.toLowerCase().includes(searchText.toLowerCase()) ?? false;
      
      let matchesFilter = true;
      if (selectedFilter !== '전체') {
        const statusText = getStatusText(doc.status);
        matchesFilter = statusText === selectedFilter;
      }
      
      return matchesSearch && matchesFilter;
    });
  };

  const filteredDocs = getFilteredDocuments();

  // ⭐ [수정됨] 색상 매칭 함수도 띄어쓰기 통일
  const getStatusColor = (status: string) => {
    switch (status) {
      case '분석완료':
      case '분석 완료': // 추가
      case 'completed':
      case 'analyzed': 
        return '#4CAF50';
      case '분석중':
      case '분석 중': // 추가
      case 'analyzing': 
      case 'reanalyzing':
        return '#FF9800';
      case '업로드완료':
      case '업로드 완료': // 추가
      case 'uploaded': 
        return '#2196F3';
      default: 
        return '#666';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case '분석완료':
      case 'completed':
      case 'analyzed': 
        return '✅';
      case '분석중':
      case 'analyzing': 
      case 'reanalyzing':
        return '🔄';
      default: 
        return '📄';
    }
  };

  const formatDate = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleDateString('ko-KR');
    } catch {
      return timestamp;
    }
  };

  if (loading && !refreshing && documents.length === 0) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={{ marginTop: 10, color: '#666' }}>문서 목록을 불러오는 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* 헤더 영역 */}
      <View style={styles.headerContainer}>
        <Text style={styles.title}>📋 내 문서들</Text>
        <Text style={styles.subtitle}>
          업로드한 문서들을 확인하고{'\n'}분석 결과를 볼 수 있어요
        </Text>

        {/* 검색창 */}
        <View style={styles.searchContainer}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput 
            style={styles.searchInput}
            placeholder="문서 이름을 검색하세요"
            value={searchText}
            onChangeText={setSearchText}
          />
          {searchText.length > 0 && (
            <TouchableOpacity onPress={() => setSearchText('')}>
              <Text style={styles.clearIcon}>✕</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* 상태 필터 버튼 */}
        <View style={styles.filterContainer}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {filterCategories.map((category) => (
              <TouchableOpacity
                key={category}
                style={[
                  styles.filterChip,
                  selectedFilter === category && styles.activeFilterChip
                ]}
                onPress={() => setSelectedFilter(category)}
              >
                <Text style={[
                  styles.filterText,
                  selectedFilter === category && styles.activeFilterText
                ]}>
                  {category}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      </View>

      {/* 문서 리스트 영역 */}
      <ScrollView 
        style={styles.documentList} 
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {filteredDocs.map((doc) => (
          <View key={doc.document_id} style={styles.documentCard}>
            
            <TouchableOpacity 
              style={styles.documentHeader}
              onPress={() => {
                if (doc.status === 'uploaded' || doc.status === '업로드완료' || doc.status === '업로드 완료') {
                  analyzeDocument(doc.document_id, doc.filename);
                } else if (doc.status === 'analyzed' || doc.status === 'completed') {
                   Alert.alert('알림', '이미 분석이 완료된 문서입니다.');
                }
              }}
            >
              <Text style={styles.documentIcon}>
                {getStatusIcon(doc.status)}
              </Text>
              <View style={styles.documentInfo}>
                <Text style={styles.documentName}>{doc.filename}</Text>
                <Text style={styles.documentDate}>업로드: {formatDate(doc.created_at)}</Text>
                {doc.file_size && (
                  <Text style={styles.fileSize}>크기: {(doc.file_size / 1024).toFixed(1)}KB</Text>
                )}
              </View>
            </TouchableOpacity>

            <View style={styles.rightSection}>
              <View style={[styles.statusBadge, { backgroundColor: getStatusColor(getStatusText(doc.status)) }]}>
                <Text style={styles.statusText}>{getStatusText(doc.status)}</Text>
              </View>
  
              {/* 업로드완료 상태일 때만 분석 버튼 표시 (조건문 강화) */}
              {(doc.status === 'uploaded' || doc.status === '업로드완료' || doc.status === '업로드 완료') && (
                <TouchableOpacity 
                  style={styles.analyzeButton}
                  onPress={() => analyzeDocument(doc.document_id, doc.filename)}
                >
                  <Text style={styles.analyzeButtonText}>분석하기</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        ))}
        
        {/* 데이터가 없을 때 */}
        {filteredDocs.length === 0 && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>📭</Text>
            <Text style={styles.emptyText}>
              {documents.length === 0 ? '아직 업로드된 문서가 없어요' : '조건에 맞는 문서가 없어요'}
            </Text>
            <Text style={styles.emptySubText}>
              {searchText ? `'${searchText}' 검색 결과가 없습니다.` : '문서를 업로드해보세요!'}
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f8ff',
  },
  headerContainer: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#f0f8ff',
    zIndex: 1,
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
    marginBottom: 20,
    lineHeight: 24,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    borderRadius: 12,
    paddingHorizontal: 15,
    height: 50,
    marginBottom: 15,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  searchIcon: {
    fontSize: 18,
    marginRight: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    height: '100%',
  },
  clearIcon: {
    fontSize: 18,
    color: '#999',
    padding: 5,
  },
  filterContainer: {
    marginBottom: 5,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'white',
    borderWidth: 1,
    borderColor: '#ddd',
    marginRight: 8,
  },
  activeFilterChip: {
    backgroundColor: '#2196F3',
    borderColor: '#2196F3',
  },
  filterText: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  activeFilterText: {
    color: 'white',
    fontWeight: 'bold',
  },
  documentList: {
    flex: 1,
    paddingHorizontal: 20,
  },
  documentCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
    borderWidth: 1,
    borderColor: '#f0f0f0',
  },
  documentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  documentIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  documentInfo: {
    flex: 1,
  },
  documentName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  documentDate: {
    fontSize: 12,
    color: '#888',
  },
  fileSize: {
    fontSize: 11,
    color: '#999',
  },
  rightSection: {
    alignItems: 'flex-end',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginBottom: 8,
  },
  statusText: {
    fontSize: 11,
    color: 'white',
    fontWeight: 'bold',
  },
  analyzeButton: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  analyzeButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 60,
  },
  emptyIcon: {
    fontSize: 50,
    marginBottom: 16,
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
    textAlign: 'center',
  },
});