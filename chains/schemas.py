from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Label(str, Enum):
    buying = "구매절차"
    payment = "결제조합"
    aftermarket = "애프터마켓"
    tax_benefit = "세제혜택"
    test_driving = "시승"
    model = "상품 탐색 _ 엔진 / 바디타입"
    trim_option = "상품 탐색 _ 트림 / 옵션 / 옵션조합"
    design = "상품 탐색 _ 디자인"
    comparison = "상품 탐색_차종비교"
    lifestyle = "상품탐색_라이프스타일"
    etc = "기타"


class PurchasePhase(Enum):
    before = "캐스퍼 또는 새 자동차 계약을 고민하고 있는 고객"
    in_or_after = "캐스퍼 또는 다른 자동차를 샀거나 계약을 한 후에 질문하는, 또는 차 구매와 전혀 상관없는 질문을 하는 고객"


class ConsiderPurchaseIntent(BaseModel):
    buying: Optional[str] = Field(
        default="",
        description="Inquiries related to the price (including installment options), purchase process, contracts, and payment methods for Casper. Keep in mind that '기획전' is an event where you can buy a Casper.",
        examples=[
            "심사 대기에서 출고까지 얼마나 걸릴까요?",
            "기획전에서만 구매할 수 있는 건가요?",
            "캐스퍼 구매는 어떻게 하는 건가요?",
            "카마스터 추천해 주세요.",
        ],
    )
    benefit: Optional[str] = Field(
        default="",
        description="Questions regarding non-tax benefits and promotional offers for purchasing a Casper, including '브랜드kit', '썬팅 시공', '블루멤버스', '카마스터 혜택', '구매 시 캐시백', and other card-related discounts.",
        examples=[
            "캐스퍼 EV 구입시 전면 썬팅과 블랙박스도 지원해 주나요?",
            "차 구매시 현대카드 만들고 30만원 어치 포인트 지급 받는게 낫나요?",
            "현금이나 주유권 주는 카마스터가 있을까요?",
        ],
    )
    tax_beneift: Optional[str] = Field(
        default="",
        description="Inquiries about tax-related benefits for Casper purchases, including '(경차) 유류세 환급' or other tax deductions and refunds.",
        examples=[
            "경차 환급은 어떻게 받을 수 있는 건가요?",
            "일렉트릭 취득세 계산은 보조금 받은 금액으로 계산하는 건가요?",
            "캐스퍼 전기차는 경차 혜택을 보지 못한다고 하는데, 경차 혜택 기준이 뭔가요?",
        ],
    )
    membership: Optional[str] = Field(
        default="",
        description="Questions related to membership programs and associated benefits, such as '블루멤버스', 'EV 안심케어', '럭키패스H', and '바디케어'.",
        examples=[
            "현대 캐스퍼 경차카드로 구매했는데 할부로 해도 블루멤버스 포인트를 받을 수 있나요?"
        ],
    )
    test_driving: Optional[str] = Field(
        default="",
        description="Inquiries about booking or events related to exhibition and/or test driving of Casper models.",
        examples=[
            "캐스퍼 EV는 어디에 전시되어 있나요?",
            "시승하러 가는데 모바일 면허증을 지참해도 돼죠?",
        ],
    )
    info: Optional[str] = Field(
        default="",
        description="Requests for factual information about the specifications, features, or trims of Casper models, including '트림', '옵션', engine types (EV or gas), facelifts ('페리'), colors, and other objective details.",
        examples=[
            "캐스퍼 페이스 리프트 출시는 언제 되나요?",
            "전방 충돌방지 보조 기능이 주차 후 30km 미만 정도 속도로 출차할 때 전방의 측면을 긁는 사고 발생 전에도 차가 멈춰 주나요?",
            "후방 카메라가 있나요?",
            "캐스퍼 전기차는 실내 1열 폭이 넓나요?",
            "페리 어떻게 나올까요?",
            "운전 스타일 변경하는 기능은 터보에만 있는 건가요?",
        ],
    )
    opinions_models: Optional[str] = Field(
        default="",
        description="Questions asking for subjective opinions or experiences about Casper models from owners or general sentiment regarding Casper ownership (whether to buy a Casper on given conditions or not, etc).",
        examples=[
            "특별 기획전에서 캐스퍼를 결제했는데, 페리가 10월중에 나온다면 페리를 사는게 좋을까요?",
            "캐스퍼 장점이 앞, 뒷자리 폴딩이 가능한 것이라고 생각하는데 실제로도 괜찮은가요?",
            "캐스퍼 시트 불편하지 않나요?",
        ],
    )
    opinions_trims: Optional[str] = Field(
        default="",
        description="Inquiries seeking subjective feedback on Casper trims, including opinions on specific trims (e.g., '스마트', '디 에센셜 라이트', '인스퍼레이션'), color choices, and design elements.",
        examples=[
            "출퇴근만 하는데 액티브 추가하는 게 좋을까요?",
            "익스테리어 디자인 옵션 추가하는 게 나을까요?",
            "가성비 트림 및 필수 옵션 추천해 주세요.",
            "캐스퍼 썬팅 반사/비반사 뭐가 좋을까요?",
        ],
    )
    casper_alternative: Optional[str] = Field(
        default="",
        description="Comparisons between different Casper models or trims (inner-Casper comparisons).",
        examples=["캐스퍼 일렉트릭(전기차)이 나을까요, 캐스퍼 터보가 나을까요?"],
    )
    non_capser_alternative: Optional[str] = Field(
        default="",
        description="Comparisons between a Casper and non-Casper alternatives, such as '레이', '모닝', '아반떼', '아이오닉', '스파크', or '니로'.",
        examples=[
            "캐스퍼 터보 말고 모닝 신형도 괜찮을까요?",
        ],
    )
    unclassified: Optional[str] = Field(
        default="",
        description="unclassified inquiries that do not fall under any specific category above. This can include miscellaneous questions (e.g. about 3rd party items) or off-topic queries.",
        examples=[
            "캐스퍼 EV 몇 년 타고 팔면 감가가 얼마나 될까요?",
            "가로바와 루프박스를 장착하신 분 있나요?",
            "캐스퍼 종이 카탈로그는 어디서 받을 수 있나요?",
        ],
    )
