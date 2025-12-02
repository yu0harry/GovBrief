import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import React from 'react';

// 화면들 import
import ChatScreen from '../screens/ChatScreen';
import DocumentListScreen from '../screens/DocumentListScreen';
import DocumentUploadScreen from '../screens/DocumentUploadScreen';
import HomeScreen from '../screens/HomeScreen';

// 타입 import
import type { MainTabParamList, RootStackParamList } from '../types/navigation';

const Tab = createBottomTabNavigator<MainTabParamList>();
const Stack = createStackNavigator<RootStackParamList>();

// 탭 아이콘 설정 함수
function getTabBarIcon(routeName: keyof MainTabParamList, focused: boolean, size: number) {
  let iconName: keyof typeof Ionicons.glyphMap;

  switch (routeName) {
    case 'Home':
      iconName = focused ? 'home' : 'home-outline';
      break;
    case 'Upload':
      iconName = focused ? 'cloud-upload' : 'cloud-upload-outline';
      break;
    case 'Documents':
      iconName = focused ? 'documents' : 'documents-outline';
      break;
    case 'Chat':
      iconName = focused ? 'chatbubbles' : 'chatbubbles-outline';
      break;
    default:
      iconName = 'help-outline';
  }

  return <Ionicons name={iconName} size={size} color={focused ? '#2196F3' : '#666'} />;
}

// 메인 탭 내비게이터
function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, size }) => 
          getTabBarIcon(route.name, focused, size),
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: '#666',
        // 탭바 스타일 조정
        tabBarStyle: {
          backgroundColor: 'white',
          borderTopWidth: 1,
          borderTopColor: '#e0e0e0',
          paddingBottom: 30, 
          paddingTop: 10,    
          height: 90,        
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '600',
        },
        headerShown: false,
      })}
    >
      {/* 1. 홈 */}
      <Tab.Screen 
        name="Home" 
        component={HomeScreen} 
        options={{
          tabBarLabel: '홈',
        }}
      />

      {/* 2. 문서목록 (위치 변경됨: 두 번째로 이동) */}
      <Tab.Screen 
        name="Documents" 
        component={DocumentListScreen}
        options={{
          tabBarLabel: '문서목록',
        }}
      />

      {/* 3. 업로드 (위치 변경됨: 세 번째로 이동) */}
      <Tab.Screen 
        name="Upload" 
        component={DocumentUploadScreen}
        options={{
          tabBarLabel: '업로드',
        }}
      />

      {/* 4. 챗봇 */}
      <Tab.Screen 
        name="Chat" 
        component={ChatScreen}
        options={{
          tabBarLabel: '챗봇',
        }}
      />
    </Tab.Navigator>
  );
}

// 루트 스택 내비게이터
function RootStackNavigator() {
  return (
    <Stack.Navigator 
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="Main" component={MainTabNavigator} />
      {/* 나중에 DocumentAnalysis 화면 등 추가 예정 */}
    </Stack.Navigator>
  );
}

// 메인 내비게이션 컨테이너
export default function AppNavigator() {
  return (
    <NavigationContainer>
      <RootStackNavigator />
    </NavigationContainer>
  );
}