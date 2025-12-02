import axios from 'axios';
import React, { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

const BACKEND_URL = 'https://gudrun-unscientific-foully.ngrok-free.dev';

export default function BackendTest() {
  const [status, setStatus] = useState('연결 테스트 대기 중...');

  const testConnection = async () => {
    try {
      setStatus('연결 테스트 중...');
      
      // 문서 목록 API 호출 테스트
      const response = await axios.get(`${BACKEND_URL}/`, {
        timeout: 5000  
      });
      
      setStatus(`✅ 연결 성공! 응답: ${JSON.stringify(response.data)}`);
    } catch (error) {
        setStatus(`❌ 연결 실패: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>백엔드 연결 테스트</Text>
      <Text style={styles.status}>{status}</Text>
      
      <TouchableOpacity style={styles.button} onPress={testConnection}>
        <Text style={styles.buttonText}>연결 테스트</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#f5f5f5',
    margin: 20,
    borderRadius: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  status: {
    marginVertical: 15,
    fontSize: 14,
    color: '#333',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
  },
});