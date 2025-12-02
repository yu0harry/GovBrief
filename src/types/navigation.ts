// 내비게이션 타입 정의
export type RootStackParamList = {
    Main: undefined;
    DocumentAnalysis: { documentId: string };
  };
  
  export type MainTabParamList = {
    Home: undefined;
    Upload: undefined;
    Documents: undefined;
    Chat: undefined;
  };