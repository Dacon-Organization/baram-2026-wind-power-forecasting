# 시장 조사와 제도 맥락

## 핵심 배경

DACON 공식 설명은 풍력발전량 예측 정확도가 전력계통 운영 안정성과 재생에너지 발전량 예측제도 정산금 확보에 연결된다고 설명합니다. 즉 이 대회는 단순 MAE 경쟁이 아니라, 실제 운영에서 쓸 수 있는 발전량 예측 능력을 평가하는 구조입니다.

## 재생에너지 발전량 예측제도

산업부와 전력거래소는 재생에너지 확대에 따른 출력 변동성 대응을 위해 발전량 예측제도를 도입했습니다. 제도의 핵심은 20MW 이상 태양광·풍력 발전사업자 등이 하루 전에 발전량을 예측해 제출하고, 당일 실제 발전량과 일정 오차율 이내이면 정산금을 받는 구조입니다.

BARAM의 FICR은 이 현실 제도의 문제의식을 대회용 평가 함수로 가져온 것입니다. 다만 실제 KPX 제도와 대회 산식은 완전히 같다고 가정하지 않고, 최종 모델 최적화는 DACON 평가 코드 기준으로 수행합니다.

## 풍력 예측이 어려운 이유

| 요인 | 설명 | 모델링 대응 |
|------|------|-------------|
| 풍속 비선형성 | 발전량은 특정 구간에서 풍속 세제곱에 가깝게 반응 | `wind_speed^2`, `wind_speed^3`, power density |
| 풍향과 지형 | 산악 지형에서는 방향별 난류와 가속이 달라짐 | direction sin/cos, grid gradient, 고도 proxy |
| 예보 오차 | LDAPS/GFS의 공간해상도와 예보 lead에 따라 오차가 달라짐 | source별 feature, lead hour, forecast spread |
| 터빈 상태 | 정지, curtailment, 유지보수, cut-out이 발전량을 왜곡 | SCADA power curve, zero-run 분석 |
| 정산 임계값 | 평균 오차 외에 6%/8% 구간 진입 여부가 중요 | OOF calibration, 그룹별 bias 보정 |

## 발표용 주장

1. 풍력 예측은 기상예보 후처리와 발전량 변환을 동시에 풀어야 한다.
2. BARAM은 1-NMAE와 FICR을 결합하므로 평균 오차와 정산 구간을 함께 관리해야 한다.
3. 실제 운영 가능성은 예측 기준시점 이후 정보를 쓰지 않는 point-in-time 설계에서 나온다.
4. 평가 기간 SCADA가 없으므로 SCADA는 train 분석과 power curve 학습 보조로 제한해야 한다.
5. 제출 파일 버전과 hash 관리는 점수 복구와 2차 재현성의 일부다.

## 사용한 공개 출처

- DACON 대회 개요: https://dacon.io/competitions/official/236727/overview/description
- DACON 평가 안내: https://dacon.io/competitions/official/236727/overview/evaluation
- DACON 규칙 안내: https://dacon.io/competitions/official/236727/overview/rules
- 산업부/KPX 예측제도 도입 자료: https://eiec.kdi.re.kr/policy/materialView.do?num=205187
- 풍력 예측 연구 리뷰 후보: https://www.mdpi.com/1996-1073/18/2/350

## 남은 조사 질문

- 최신 KPX 예측제도에서 풍력은 태양광과 같은 오차율 기준을 적용받는가.
- BARAM 대회 FICR 단가가 현행 제도와 다른 경우 발표에서는 어떻게 분리 설명할 것인가.
- 복잡 지형 풍력 예측에서 LDAPS/GFS grid pooling의 실증적으로 강한 방식은 무엇인가.
- 2025년 평가 기간에 계절별 Public/Private 표본이 어떻게 숨겨져 있을 가능성이 높은가.
