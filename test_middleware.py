"""
Phase 4 미들웨어 테스트 스크립트

서버 실행 후 이 스크립트로 미들웨어 기능을 테스트할 수 있습니다.

실행 방법:
1. 서버 실행: python APP/main.py
2. 새 터미널에서: python test_middleware.py
"""
import requests
import time


BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """섹션 구분선 출력"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def test_logging_middleware():
    """Logging 미들웨어 테스트"""
    print_section("1. Logging Middleware 테스트")
    
    print("📝 서버 로그에서 다음 정보를 확인하세요:")
    print("   - 요청 정보 (메서드, 경로, IP)")
    print("   - 처리 시간 (X-Process-Time 헤더)")
    print("   - 응답 상태 코드\n")
    
    response = requests.get(f"{BASE_URL}/health")
    
    print(f"✅ Status Code: {response.status_code}")
    print(f"✅ Process Time: {response.headers.get('X-Process-Time')}s")
    print(f"✅ Request ID: {response.headers.get('X-Request-ID')}")


def test_rate_limiting():
    """Rate Limiting 미들웨어 테스트"""
    print_section("2. Rate Limiting 테스트")
    
    print("🔄 연속 요청 5회 전송 중...\n")
    
    for i in range(5):
        response = requests.get(f"{BASE_URL}/api/v1/documents/")
        
        print(f"요청 #{i+1}")
        print(f"  - Status: {response.status_code}")
        print(f"  - Remaining: {response.headers.get('X-RateLimit-Remaining')}/{response.headers.get('X-RateLimit-Limit')}")
        print(f"  - Window: {response.headers.get('X-RateLimit-Window')}s")
        print()
        
        time.sleep(0.5)
    
    print("💡 Rate Limit 헤더 확인:")
    print(f"   - X-RateLimit-Limit: 최대 요청 수")
    print(f"   - X-RateLimit-Remaining: 남은 요청 수")
    print(f"   - X-RateLimit-Window: 시간 윈도우")


def test_error_handling():
    """Error Handler 테스트"""
    print_section("3. Error Handling 테스트")
    
    # 1. 404 Not Found
    print("1) 404 Not Found 테스트")
    response = requests.get(f"{BASE_URL}/api/v1/documents/non-existent-id")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # 2. 422 Validation Error
    print("2) 422 Validation Error 테스트")
    response = requests.post(
        f"{BASE_URL}/api/v1/analyze",
        json={"invalid_field": "test"}  # document_id 누락
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")


def test_security_headers():
    """Security Headers 테스트"""
    print_section("4. Security Headers 테스트")
    
    response = requests.get(f"{BASE_URL}/health")
    
    print("🔒 보안 헤더 확인:")
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }
    
    for header, expected in security_headers.items():
        actual = response.headers.get(header)
        status = "✅" if actual == expected else "❌"
        print(f"   {status} {header}: {actual}")


def test_request_id():
    """Request ID 테스트"""
    print_section("5. Request ID 추적 테스트")
    
    # 커스텀 Request ID 전송
    custom_id = "custom-request-12345"
    response = requests.get(
        f"{BASE_URL}/health",
        headers={"X-Request-ID": custom_id}
    )
    
    returned_id = response.headers.get("X-Request-ID")
    
    print(f"📝 전송한 Request ID: {custom_id}")
    print(f"📝 반환된 Request ID: {returned_id}")
    print(f"{'✅ 일치!' if custom_id == returned_id else '❌ 불일치'}")
    
    # 자동 생성 Request ID
    response = requests.get(f"{BASE_URL}/health")
    auto_id = response.headers.get("X-Request-ID")
    
    print(f"\n📝 자동 생성 Request ID: {auto_id}")
    print(f"{'✅ UUID 형식' if len(auto_id) == 36 else '❌ 형식 오류'}")


def main():
    """메인 테스트 실행"""
    print("\n" + "🎯" * 30)
    print("  Phase 4: 미들웨어 테스트 스크립트")
    print("🎯" * 30)
    
    try:
        # 서버 연결 확인
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 서버 응답 오류: {response.status_code}")
            return
        
        print(f"✅ 서버 연결 성공: {BASE_URL}\n")
        
        # 테스트 실행
        test_logging_middleware()
        test_rate_limiting()
        test_error_handling()
        test_security_headers()
        test_request_id()
        
        print("\n" + "=" * 60)
        print("  ✅ 모든 테스트 완료!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print(f"❌ 서버에 연결할 수 없습니다: {BASE_URL}")
        print("   서버가 실행 중인지 확인하세요:")
        print("   $ python APP/main.py")
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")


if __name__ == "__main__":
    main()