import { useNavigation } from '@react-navigation/native';
import axios from 'axios';
import * as DocumentPicker from 'expo-document-picker';
import React, { useState } from 'react';
import { ActivityIndicator, Alert, StyleSheet, Text, TouchableOpacity, View } from 'react-native';


const BACKEND_URL = 'https://govbrief-production.up.railway.app';

export default function DocumentUploadScreen() {
  const navigation = useNavigation();
  const [uploadStatus, setUploadStatus] = useState('파일을 선택해주세요');
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async () => {
    try {
      // 1. 파일 선택
      setUploadStatus('파일 선택 중...');
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'application/msword', 'image/*', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        copyToCacheDirectory: true,
      });

      if (result.canceled) {
        setUploadStatus('파일 선택이 취소되었습니다.');
        return;
      }

      // 2. 백엔드 업로드
      setIsUploading(true);
      setUploadStatus(`업로드 중: ${result.assets[0].name}`);

      const formData = new FormData();
      formData.append('file', {
        uri: result.assets[0].uri,
        type: result.assets[0].mimeType || 'application/pdf',
        name: result.assets[0].name,
      } as any);

      const response = await axios.post(
        `${BACKEND_URL}/api/v1/documents/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 30000, // 30초 타임아웃
        }
      );

      setUploadStatus(`✅ 업로드 성공! 파일: ${result.assets[0].name}`);
      Alert.alert('성공!', 
        '파일이 성공적으로 업로드되었습니다! 🎉\n문서 목록으로 이동할까요?',
        [
         { 
           text: '추가 업로드', 
            style: 'cancel',
            onPress: () => console.log('업로드 화면 유지')
          },
          { 
            text: '목록 보기', 
            onPress: () => navigation.navigate('Documents' as never)
          }
        ]
      );
      console.log('업로드 응답:', response.data);

    } catch (error: any) {
      setUploadStatus(`❌ 업로드 실패: ${error.message}`);
      Alert.alert('오류', `업로드에 실패했습니다: ${error.message}`);
      console.error('업로드 에러:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>📄 문서 업로드</Text>
      <Text style={styles.description}>
        PDF, 워드, 이미지 파일을 업로드하여{'\n'}
        AI가 분석할 수 있게 해주세요
      </Text>
      
      {/* 상태 표시 */}
      <View style={styles.statusBox}>
        <Text style={[
          styles.statusText,
          uploadStatus.includes('✅') ? styles.successText : 
          uploadStatus.includes('❌') ? styles.errorText : styles.normalText
        ]}>
          {uploadStatus}
        </Text>
        {isUploading && <ActivityIndicator size="small" color="#2196F3" style={{ marginTop: 5 }} />}
      </View>
      
      <TouchableOpacity 
        style={[styles.uploadButton, isUploading && styles.uploadButtonDisabled]} 
        onPress={handleUpload}
        disabled={isUploading}
      >
        <Text style={styles.uploadIcon}>📁</Text>
        <Text style={styles.uploadText}>
          {isUploading ? '업로드 중...' : '파일 선택하기'}
        </Text>
        <Text style={styles.uploadSubText}>PDF, DOCX, JPG, PNG 지원</Text>
      </TouchableOpacity>
      
      <View style={styles.infoBox}>
        <Text style={styles.infoTitle}>💡 이용 안내</Text>
        <Text style={styles.infoText}>
          • 최대 10MB까지 업로드 가능{'\n'}
          • 한글, 영어 문서 지원{'\n'}
          • 업로드 후 자동으로 텍스트 추출
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f8ff',
    alignItems: 'center',
    padding: 20,
    paddingTop: 60,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2196F3',
    marginTop: 40,
    marginBottom: 8,
  },
  description: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 24,
  },
  statusBox: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 15,
    marginBottom: 20,
    width: '100%',
    alignItems: 'center',
    minHeight: 50,
    justifyContent: 'center',
  },
  statusText: {
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  successText: {
    color: '#4CAF50',
  },
  errorText: {
    color: '#F44336',
  },
  normalText: {
    color: '#666',
  },
  uploadButton: {
    backgroundColor: 'white',
    borderWidth: 2,
    borderColor: '#2196F3',
    borderStyle: 'dashed',
    borderRadius: 15,
    padding: 40,
    alignItems: 'center',
    width: '100%',
    marginBottom: 25,
  },
  uploadButtonDisabled: {
    opacity: 0.6,
  },
  uploadIcon: {
    fontSize: 48,
    marginBottom: 10,
  },
  uploadText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2196F3',
    marginBottom: 5,
  },
  uploadSubText: {
    fontSize: 14,
    color: '#666',
  },
  infoBox: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 20,
    width: '100%',
    borderLeftWidth: 4,
    borderLeftColor: '#2196F3',
  },
  infoTitle: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});