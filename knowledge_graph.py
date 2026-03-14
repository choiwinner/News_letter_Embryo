"""
뉴스 아이템에서 엔티티와 관계를 추출하여 지식 그래프를 생성합니다.
Gemini API로 추출 → networkx로 그래프 구성 → matplotlib으로 시각화
"""
import json
import base64
import io
import os
import re
import matplotlib
matplotlib.use("Agg")  # GUI 없는 환경에서 렌더링
import matplotlib.pyplot as plt
import koreanize_matplotlib
from dotenv import load_dotenv

load_dotenv()

def extract_entities_and_relations(news_items: list) -> dict:
    """
    뉴스 제목 목록을 Gemini에 전달하여 엔티티(노드)와 관계(엣지)를 JSON으로 추출합니다.
    반환 형태: {"nodes": [{"id": "SK하이닉스", "type": "기업"}, ...],
                "edges": [{"source": "SK하이닉스", "target": "HBM4", "relation": "개발"}, ...]}
    """
    from google import genai
    from summarizer import generate_content_with_retry

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"nodes": [], "edges": []}

    client = genai.Client(api_key=api_key)
    model_name = "gemini-3-flash-preview"

    # 뉴스 제목만 추출하여 프롬프트 구성 (토큰 절약)
    titles = "\n".join(f"- {item['title']}" for item in news_items)

    prompt = f"""다음 뉴스 제목 목록에서 주요 엔티티(기업, 기술, 제품, 인물)와 그 관계를 추출하세요.

뉴스 제목:
{titles}

아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
노드는 최대 15개, 엣지는 최대 20개로 제한하세요.
엔티티 type은 "기업", "기술", "제품", "인물" 중 하나여야 합니다.
관계(relation)는 짧은 한글 동사/명사구로 작성하세요 (예: 개발, 투자, 공급, 협력, 경쟁).

{{
  "nodes": [
    {{"id": "엔티티명", "type": "기업"}}
  ],
  "edges": [
    {{"source": "엔티티명A", "target": "엔티티명B", "relation": "관계"}}
  ]
}}"""

    try:
        result_text = generate_content_with_retry(client, model_name, prompt)
        # JSON 블록 추출 (마크다운 코드 블록 포함 대응)
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"엔티티/관계 추출 실패: {e}")

    return {"nodes": [], "edges": []}


def build_and_render_graph(graph_data: dict) -> str | None:
    """
    추출된 노드/엣지 데이터로 networkx 그래프를 구성하고
    matplotlib으로 렌더링 후 Base64 인코딩된 PNG 문자열을 반환합니다.
    그래프 데이터가 비어 있으면 None을 반환합니다.
    """
    import networkx as nx
    import matplotlib.patches as mpatches

    # 한글 폰트 설정 (koreanize-matplotlib에 의해 NanumGothic 등이 자동 설정됨)
    # 하지만 명확성을 위해 rcParams를 다시 확인하고 설정
    plt.rcParams["axes.unicode_minus"] = False
    _selected_font = "NanumGothic"

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    if not nodes:
        return None

    G = nx.DiGraph()

    # 노드 추가
    for node in nodes:
        G.add_node(node["id"], node_type=node.get("type", "기타"))

    # 엣지 추가 (그래프에 있는 노드만)
    node_ids = {n["id"] for n in nodes}
    for edge in edges:
        if edge["source"] in node_ids and edge["target"] in node_ids:
            G.add_edge(edge["source"], edge["target"], relation=edge.get("relation", ""))

    # 엔티티 유형별 색상
    COLOR_MAP = {
        "기업": "#4C9BE8",
        "기술": "#E8834C",
        "제품": "#5CB85C",
        "인물": "#A569BD",
        "기타": "#A0A0A0",
    }

    node_colors = [
        COLOR_MAP.get(G.nodes[n].get("node_type", "기타"), "#A0A0A0")
        for n in G.nodes
    ]

    fig, ax = plt.subplots(figsize=(14, 9))
    fig.patch.set_facecolor("#1A1A2E")
    ax.set_facecolor("#1A1A2E")

    # 레이아웃 선택
    if len(G.nodes) <= 10:
        pos = nx.spring_layout(G, seed=42, k=2.5)
    else:
        try:
            pos = nx.kamada_kawai_layout(G)
        except Exception:
            pos = nx.spring_layout(G, seed=42, k=2.0)

    # 엣지 그리기
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#7F8C8D",
        arrows=True,
        arrowsize=18,
        width=1.5,
        connectionstyle="arc3,rad=0.1",
        min_source_margin=20,
        min_target_margin=20,
    )

    # 노드 그리기
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=1800,
        alpha=0.95,
    )

    # 노드 레이블
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        font_size=9,
        font_color="white",
        font_weight="bold",
        font_family=_selected_font
    )

    # 엣지 레이블
    edge_labels = nx.get_edge_attributes(G, "relation")
    nx.draw_networkx_edge_labels(
        G, pos, ax=ax,
        edge_labels=edge_labels,
        font_size=8,
        font_color="#F0E68C",
        bbox=dict(boxstyle="round,pad=0.2", fc="#2C3E50", alpha=0.7, ec="none"),
        font_family=_selected_font
    )

    # 범례
    legend_patches = [
        mpatches.Patch(color=color, label=label)
        for label, color in COLOR_MAP.items()
        if label != "기타"
    ]
    ax.legend(
        handles=legend_patches,
        loc="upper left",
        fontsize=9,
        facecolor="#2C3E50",
        edgecolor="none",
        labelcolor="white",
    )

    ax.set_title("뉴스 지식 그래프", color="white", fontsize=16, fontweight="bold", pad=15)
    ax.axis("off")
    plt.tight_layout()

    # PNG → Base64 변환
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return encoded


def generate_knowledge_graph(news_items: list) -> str | None:
    """
    뉴스 아이템 목록을 받아 지식 그래프 PNG의 Base64 문자열을 반환합니다.
    파이프라인: 엔티티 추출 → 그래프 렌더링
    """
    print("지식 그래프 생성 중...")
    graph_data = extract_entities_and_relations(news_items)
    node_count = len(graph_data.get("nodes", []))
    edge_count = len(graph_data.get("edges", []))
    print(f"  추출된 노드: {node_count}개, 엣지: {edge_count}개")

    if node_count == 0:
        print("  노드가 없어 그래프를 생성하지 않습니다.")
        return None

    encoded = build_and_render_graph(graph_data)
    if encoded:
        print("  그래프 이미지 생성 완료.")
    return encoded


# 단독 실행 시 테스트
if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 더미 뉴스 데이터 (API 없이 그래프 렌더링 테스트)
    dummy_graph_data = {
        "nodes": [
            {"id": "SK하이닉스", "type": "기업"},
            {"id": "삼성전자", "type": "기업"},
            {"id": "마이크론", "type": "기업"},
            {"id": "엔비디아", "type": "기업"},
            {"id": "HBM4", "type": "제품"},
            {"id": "HBM3E", "type": "제품"},
            {"id": "고대역폭 메모리", "type": "기술"},
            {"id": "CoWoS", "type": "기술"},
        ],
        "edges": [
            {"source": "SK하이닉스", "target": "HBM4", "relation": "개발"},
            {"source": "삼성전자", "target": "HBM3E", "relation": "개발"},
            {"source": "마이크론", "target": "HBM3E", "relation": "생산"},
            {"source": "HBM4", "target": "엔비디아", "relation": "공급"},
            {"source": "HBM3E", "target": "엔비디아", "relation": "공급"},
            {"source": "HBM4", "target": "고대역폭 메모리", "relation": "기반"},
            {"source": "CoWoS", "target": "HBM4", "relation": "패키징"},
            {"source": "SK하이닉스", "target": "삼성전자", "relation": "경쟁"},
        ],
    }

    encoded = build_and_render_graph(dummy_graph_data)
    if encoded:
        # Base64 디코딩 후 파일 저장 (확인용)
        img_bytes = base64.b64decode(encoded)
        output_path = "knowledge_graph_test.png"
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print(f"테스트 그래프 저장 완료: {output_path}")
        print(f"Base64 길이: {len(encoded)} 문자")
    else:
        print("그래프 생성 실패")
