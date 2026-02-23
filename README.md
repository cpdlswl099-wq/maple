
# 메이플키우기 종결 계산기 (Streamlit)

- PC/휴대폰 모두 브라우저로 사용 가능(배포 시)
- 고대책 반영
- 균형/목표치 + 필요횟수 계산(1회당 상승량 입력)

## 로컬 실행(PC)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 배포 추천(초보자 기준): Streamlit Community Cloud
가장 쉽고 빠릅니다.

1) GitHub에 이 폴더 그대로 올리기 (레포 이름 아무거나)
2) Streamlit Community Cloud에서 레포 연결
3) Entry point: `app.py` 선택 → Deploy
4) 생성된 URL로 PC/휴대폰에서 접속

## Docker 배포(선택)
```bash
docker build -t maple-endgame .
docker run -p 8501:8501 maple-endgame
```
