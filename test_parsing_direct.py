"""
문서 파싱 기능 직접 테스트
APP/services/document_parser.py의 파싱 기능을 직접 호출하여 테스트
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, '.')

from APP.services.document_parser import parse_document


async def test_parsing(file_path: str):
    """파싱 테스트 메인 함수"""
    print("\n" + "="*70)
    print("📄 문서 파싱 테스트")
    print("="*70)
    
    if not Path(file_path).exists():
        print(f"\n❌ 파일을 찾을 수 없습니다: {file_path}")
        print("\n현재 디렉토리의 파일 목록:")
        for ext in ['*.pdf', '*.docx', '*.hwp', '*.jpg', '*.png']:
            for file in Path('.').glob(ext):
                print(f"  📄 {file.name}")
        return None
    
    try:
        print(f"\n🔍 파싱 시작: {file_path}")
        print("⏳ 처리 중...")
        
        # 실제 파싱 실행
        result = await parse_document(file_path)
        
        print("\n" + "="*70)
        print("✅ 파싱 성공!")
        print("="*70)
        
        # 결과 출력
        print(f"\n📊 파일 정보:")
        print(f"  • 파일명: {result['file_name']}")
        print(f"  • 파일 타입: {result['file_type']}")
        print(f"  • 파일 크기: {result['file_size']:,} bytes ({result['file_size']/1024:.1f} KB)")
        
        print(f"\n📄 문서 정보:")
        print(f"  • 페이지 수: {result['page_count']}")
        print(f"  • 테이블 포함: {'예' if result['has_tables'] else '아니오'}")
        print(f"  • 파싱 신뢰도: {result['confidence']*100:.1f}%")
        print(f"  • 추출된 텍스트 길이: {len(result['text']):,} 자")
        
        # 텍스트 미리보기
        preview_length = 500
        print(f"\n📖 추출된 텍스트 미리보기 (처음 {preview_length}자):")
        print("-" * 70)
        print(result['text'][:preview_length])
        if len(result['text']) > preview_length:
            print("...")
        print("-" * 70)
        
        # 전체 텍스트 확인 여부
        print(f"\n💡 전체 텍스트를 확인하시겠습니까?")
        user_input = input("전체 텍스트 보기 (y/n): ").lower()
        
        if user_input == 'y':
            print("\n" + "="*70)
            print("📄 전체 추출 텍스트")
            print("="*70)
            print(result['text'])
            print("="*70)
        
        # 파일로 저장
        output_file = f"parsed_{Path(file_path).stem}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write(f"파싱 결과: {result['file_name']}\n")
            f.write("="*70 + "\n\n")
            f.write(f"파일 타입: {result['file_type']}\n")
            f.write(f"페이지 수: {result['page_count']}\n")
            f.write(f"신뢰도: {result['confidence']*100:.1f}%\n\n")
            f.write("="*70 + "\n")
            f.write("추출된 전체 텍스트\n")
            f.write("="*70 + "\n\n")
            f.write(result['text'])
        
        print(f"\n💾 전체 결과가 '{output_file}' 파일로 저장되었습니다.")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 파싱 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """메인 함수"""
    print("\n" + "="*70)
    print("🚀 문서 파싱 시스템 테스트")
    print("="*70)
    
    # 테스트할 파일 입력
    print("\n파싱할 파일 경로를 입력하세요:")
    print("(예: test.pdf, 4. 마음 안심 클리닉.docx)")
    
    file_path = input("\n파일 경로: ").strip()
    
    if not file_path:
        # 기본값
        file_path = "test.pdf"
        print(f"기본값 사용: {file_path}")
    
    result = await test_parsing(file_path)
    
    if result:
        print("\n" + "="*70)
        print("✅ 테스트 완료!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ 테스트 실패")
        print("="*70)


if __name__ == "__main__":
    # asyncio로 실행
    asyncio.run(main())
