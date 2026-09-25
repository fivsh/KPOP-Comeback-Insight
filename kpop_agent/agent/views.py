from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import QueryRecord, Post

import json
import requests
import time
import urllib.parse
import re


# ============================================================
# 首页
# ============================================================

def index(request):
    return render(request, 'index.html')

def illit_page(request):
    return render(request, 'illit.html')
# ============================================================
# AI 查询接口
# ============================================================

@csrf_exempt
def query(request):
    """
    前端 AI 查询接口

    接收：
    {
        "question": "...",
        "type": "heat / persona / strategy / overview / lifecycle"
    }
    """

    if request.method != 'POST':
        return JsonResponse(
            {'error': '仅支持POST'},
            status=405
        )

    # --------------------------------------------------------
    # 1. 解析 JSON
    # --------------------------------------------------------

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': '请求数据格式错误'},
            status=400
        )

    question = data.get('question', '').strip()
    analysis_type = data.get('type', 'general').strip()

    if not question:
        return JsonResponse(
            {'error': '问题不能为空'},
            status=400
        )

    print("=" * 60)
    print("📥 收到 AI 查询请求")
    print("问题：", question)
    print("分析类型：", analysis_type)
    print("=" * 60)

    # --------------------------------------------------------
    # 2. 调用智能体
    # --------------------------------------------------------

    try:
        answer = generate_agent_response(
            question,
            analysis_type
        )
    except Exception as e:
        import traceback

        print("=" * 60)
        print("❌ generate_agent_response() 出现未处理异常")
        print("错误类型：", type(e).__name__)
        print("错误内容：", str(e))
        traceback.print_exc()
        print("=" * 60)

        answer = None

    # --------------------------------------------------------
    # 3. 数据库保存前最后一道保险
    # --------------------------------------------------------

    if not answer:
        print("⚠️ AI 没有返回有效 answer")
        print("⚠️ 使用最终数据库兜底文本")

        answer = (
            "⚠️ 当前智能体暂时未生成有效分析结果。\n\n"
            "系统已经完成请求接收，但 AI 分析服务当前没有返回有效内容。"
            "请稍后重新尝试。"
        )

    # 强制转换成字符串，避免数据库出现 NULL
    answer = str(answer)

    print("=" * 60)
    print("💾 准备保存 QueryRecord")
    print("answer 是否为空：", not bool(answer))
    print("answer 长度：", len(answer))
    print("=" * 60)

    # --------------------------------------------------------
    # 4. 保存历史记录
    # --------------------------------------------------------

    record = QueryRecord.objects.create(
        question=question,
        answer=answer,
        source='AI-Agent'
    )

    # --------------------------------------------------------
    # 5. 返回前端
    # --------------------------------------------------------

    return JsonResponse({
        'id': record.id,
        'question': question,
        'answer': answer,
        'created_at': record.created_at.strftime(
            '%Y-%m-%d %H:%M:%S'
        )
    })


# ============================================================
# Bilibili 数据采集
# ============================================================

@csrf_exempt
def crawl(request):
    """
    Django 直连 B 站采集
    第一梯队：Bilibili 搜索 API
    第二梯队：Bilibili 搜索网页解析
    """

    if request.method != 'POST':
        return JsonResponse(
            {'error': '仅支持POST'},
            status=405
        )

    # --------------------------------------------------------
    # 1. 解析请求
    # --------------------------------------------------------

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': '请求数据格式错误'},
            status=400
        )

    keyword = data.get('keyword', 'Kpop').strip()

    if not keyword:
        return JsonResponse(
            {'error': '关键词不能为空'},
            status=400
        )

    print("=" * 60)
    print("🕷️ 开始采集 Bilibili 数据")
    print("关键词：", keyword)
    print("=" * 60)

    # --------------------------------------------------------
    # 2. 清空旧数据
    # --------------------------------------------------------

    Post.objects.all().delete()

    videos = []

    # --------------------------------------------------------
    # 3. 第一梯队：Bilibili 搜索 API
    # --------------------------------------------------------

    try:

        api_url = (
            'https://api.bilibili.com/x/web-interface/search/type'
            f'?keyword={urllib.parse.quote(keyword)}'
            '&search_type=video'
            '&page=1'
        )

        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 '
                '(KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://search.bilibili.com/',
            'Accept': 'application/json, text/plain, */*',
        }

        resp = requests.get(
            api_url,
            headers=headers,
            timeout=15
        )

        result = resp.json()

        if result.get('code') == 0:

            videos = (
                result
                .get('data', {})
                .get('result', [])
            )

            print(
                f"[API] 获取到 {len(videos)} 条"
            )

        else:

            print(
                "[API] 返回异常：",
                result.get('message', '未知错误')
            )

    except Exception as e:

        print(
            f"[API失败] {type(e).__name__}: {e}"
        )

    # --------------------------------------------------------
    # 4. 第二梯队：HTML 网页解析
    # --------------------------------------------------------

    if not videos:

        try:

            search_url = (
                'https://search.bilibili.com/all'
                f'?keyword={urllib.parse.quote(keyword)}'
            )

            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 '
                    '(KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Referer': 'https://search.bilibili.com/',
            }

            resp = requests.get(
                search_url,
                headers=headers,
                timeout=15
            )

            html = resp.text

            match = re.search(
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});</script>',
                html,
                re.DOTALL
            )

            if match:

                state = json.loads(
                    match.group(1)
                )

                videos = (
                    state
                    .get('flow', {})
                    .get('list', [])
                    or
                    state
                    .get('videoData', {})
                    .get('list', [])
                )

                print(
                    f"[HTML] 获取到 {len(videos)} 条"
                )

        except Exception as e:

            print(
                f"[HTML失败] {type(e).__name__}: {e}"
            )

    # --------------------------------------------------------
    # 5. 写入数据库
    # --------------------------------------------------------

    count = 0

    for v in videos[:50]:

        if not isinstance(v, dict):
            continue

        title = str(
            v.get('title', '')
        )

        title = (
            title
            .replace(
                '<em class="keyword">',
                ''
            )
            .replace(
                '</em>',
                ''
            )
        )

        author = (
            v.get('author', '')
            or v.get('up_name', '')
            or '未知UP'
        )

        play = (
            v.get('play', 0)
            or v.get('view', 0)
        )

        likes = (
            v.get('like', 0)
            or v.get('likes', 0)
        )

        if not title:
            continue

        # 播放量
        try:
            view_count = (
                int(play)
                if str(play).isdigit()
                else 0
            )
        except Exception:
            view_count = 0

        # 点赞 / 投币字段
        try:
            like_count = (
                int(likes)
                if str(likes).isdigit()
                else 0
            )
        except Exception:
            like_count = 0

        Post.objects.create(
            platform='bilibili',
            title=title,
            author=str(author).strip(),
            view_count=view_count,
            likes=like_count,
            phase='P0',
            publish_time=str(
                v.get('pubdate', '')
            )
        )

        count += 1

    print("=" * 60)
    print("✅ Bilibili 数据采集完成")
    print("实际写入数据库：", count)
    print("=" * 60)

    return JsonResponse({
        'success': True,
        'message': (
            f'✅ 成功采集 {count} 条'
            f'「{keyword}」相关视频，请刷新页面查看'
        ),
        'count': count
    })


# ============================================================
# 历史记录
# ============================================================

def history(request):

    records = QueryRecord.objects.all()[:50]

    data = [

        {
            'id': r.id,
            'question': r.question,
            'answer': r.answer,
            'source': r.source,
            'created_at': r.created_at.strftime(
                '%m-%d %H:%M'
            )
        }

        for r in records

    ]

    return JsonResponse({
        'data': data
    })


# ============================================================
# 删除历史记录
# ============================================================

@csrf_exempt
def delete_record(request, record_id):
    """删除单条历史记录"""

    if request.method != 'DELETE':

        return JsonResponse(
            {'error': '仅支持DELETE'},
            status=405
        )

    try:

        QueryRecord.objects.get(
            id=record_id
        ).delete()

        return JsonResponse({
            'success': True,
            'message': '删除成功'
        })

    except QueryRecord.DoesNotExist:

        return JsonResponse(
            {'error': '记录不存在'},
            status=404
        )


# ============================================================
# Bilibili 数据列表
# ============================================================

def post_list(request):
    """返回爬虫采集的 B 站数据"""

    posts = (
        Post.objects
        .all()
        .order_by('-view_count')[:50]
    )

    data = list(
        posts.values()
    )

    return JsonResponse({
        'data': data
    })


# ============================================================
# 核心智能体
# ============================================================

def generate_agent_response(
        question: str,
        analysis_type: str = 'general'
) -> str:
    """
    智谱 GLM 智能体核心函数

    五类分析：
    heat
    persona
    strategy
    overview
    lifecycle

    调用失败后自动进入本地 fallback。
    """

    # ========================================================
    # 1. 智谱 API Key
    # ========================================================

    # ========================================================
    # !!! 这里保留你当前实际使用的 49 位 Key !!!
    # !!! 不要把真实 Key 发到聊天里 !!!
    # ========================================================

    ZHIPU_KEY = "xxxxxxxxxxxxxxxxxxxxxx".strip()

    print("=" * 60)
    print(
        "🔑 ZHIPU_KEY 是否读取到：",
        bool(ZHIPU_KEY)
    )
    print(
        "🔑 ZHIPU_KEY 长度：",
        len(ZHIPU_KEY)
    )
    print(
        "🔑 是否仍然是默认 key：",
        ZHIPU_KEY in (
            '',
            'KEY',
            'key',
            'YOUR_REAL_ZHIPU_KEY'
        )
    )
    print("=" * 60)

    # ========================================================
    # 2. 获取数据库真实数据
    # ========================================================

    posts = (
        Post.objects
        .all()
        .order_by('-view_count')[:20]
    )

    if posts.exists():

        total_views = sum(
            p.view_count or 0
            for p in posts
        )

        total_likes = sum(
            p.likes or 0
            for p in posts
        )

        top5 = [

            f"{p.title}"
            f"（{p.view_count or 0:,}播放）"

            for p in posts[:5]

        ]

        artist_guess = (
            posts[0].title[:20]
            if posts
            else "该艺人"
        )

        data_context = (

            f"当前分析对象："
            f"{artist_guess}...\n"

            f"数据库共有 "
            f"{posts.count()} 条相关视频，"
            f"总播放量 "
            f"{total_views:,}，"
            f"总投币/互动数 "
            f"{total_likes:,}。\n"

            f"热度Top5："
            f"{', '.join(top5)}。"

        )

    else:

        total_views = 0
        total_likes = 0

        data_context = (
            "当前数据库暂无数据，"
            "建议先点击下方「开始采集」"
            "获取视频数据。"
        )

    # ========================================================
    # 3. 不同 Agent 的角色 Prompt
    # ========================================================

    type_prompts = {

        # ----------------------------------------------------
        # Heat
        # ----------------------------------------------------

        'heat': (

            "你是K-pop数据分析师。"
            "请基于下方真实B站视频数据，"
            "生成【回归热度分析报告】。\n"

            "必须包含："
            "1.热度趋势（播放量分布、峰值判断）；"
            "2.核心关键词；"
            "3.情感倾向；"
            "4.当前阶段判断（P0-P7）。\n"

            "使用emoji，"
            "数据要具体，"
            "禁止编造。"

        ),

        # ----------------------------------------------------
        # Persona
        # ----------------------------------------------------

        'persona': (

            "你是K-pop舆情分析师。"
            "请基于下方真实B站视频数据，"
            "生成【大众画像与舆论分析报告】。\n"

            "必须包含："
            "1.受众特征（年龄/性别/地域推测）；"
            "2.舆论焦点（正面/中性/负面）；"
            "3.传播路径；"
            "4.粉丝活跃度判断。\n"

            "明确说明哪些属于数据推测，"
            "不要把推测当成事实。\n"

            "使用emoji，"
            "数据要具体，"
            "禁止编造。"

        ),

        # ----------------------------------------------------
        # Strategy
        # ----------------------------------------------------

        'strategy': (

            "你是K-pop营销顾问。"
            "请基于下方真实B站视频数据，"
            "生成【营销策略建议报告】。\n"

            "必须包含："
            "1.当前数据亮点；"
            "2.可优化的传播节点；"
            "3.具体 actionable 建议"
            "（如二创激励、舞台曝光、"
            "中文粉丝互动等）。\n"

            "建议必须结合真实数据，"
            "具体可落地，"
            "禁止泛泛而谈。"

        ),

        # ----------------------------------------------------
        # Overview
        # ----------------------------------------------------

        'overview': (

            "你是K-pop数据总结助手。"
            "请基于下方真实B站视频数据，"
            "生成【数据概览】。\n"

            "用3-4句话概括："
            "视频数量、"
            "总播放量、"
            "头部内容特征、"
            "整体趋势判断。\n"

            "简洁有力，"
            "使用emoji。"

        ),

        # ----------------------------------------------------
        # Lifecycle
        # ----------------------------------------------------

        'lifecycle': (

            "你是Agent-Lifecycle"
            "（K-pop回归生命周期诊断师）。"

            "你是本平台独有的核心智能体，"
            "专门负责根据B站视频数据的"
            "标题、播放量、发布时间分布，"
            "判定该艺人当前处于回归生命周期"
            "的哪个阶段（P0-P7）。\n"

            "阶段定义："
            "P0=未识别, "
            "P1=概念照期, "
            "P2=曲目列表期, "
            "P3=预告期, "
            "P4=专辑发布期, "
            "P5=MV发布期, "
            "P6=打歌期, "
            "P7=后续活动期。\n"

            "你必须基于提供的真实视频标题、"
            "播放量结构和发布时间信息进行判断，"
            "不能凭空猜测。\n"

            "必须包含："
            "1.当前阶段判定及依据；"
            "2.该阶段的典型特征；"
            "3.下一阶段预测；"
            "4.当前阶段应该做什么"
            "（actionable建议）。\n"

            "使用emoji，"
            "诊断必须有数据支撑，"
            "禁止空泛描述。"

        ),

    }

    # ========================================================
    # 4. 构造最终 System Prompt
    # ========================================================

    system_prompt = (

        type_prompts.get(
            analysis_type,
            type_prompts['overview']
        )

        +

        f"\n\n【真实数据上下文】\n"
        f"{data_context}"

    )

    # ========================================================
    # 5. 调用智谱 GLM
    # ========================================================

    print("=" * 60)
    print("🚀 开始调用智谱 GLM")
    print(
        "🔑 API Key 是否存在：",
        bool(ZHIPU_KEY)
    )
    print(
        "🔑 API Key 长度：",
        len(ZHIPU_KEY)
    )
    print(
        "🔑 是否还是默认 key：",
        ZHIPU_KEY in (
            '',
            'KEY',
            'key',
            'YOUR_REAL_ZHIPU_KEY'
        )
    )
    print("🤖 模型：glm-4-flash")
    print(
        "📌 analysis_type：",
        analysis_type
    )
    print("=" * 60)

    # --------------------------------------------------------
    # 注意：
    # 这里统一使用 KEY / key 判断，避免大小写错误
    # --------------------------------------------------------

    if (
        ZHIPU_KEY
        and ZHIPU_KEY not in (
            'KEY',
            'key',
            'YOUR_REAL_ZHIPU_KEY'
        )
    ):

        for attempt in range(3):

            try:

                print(
                    f"🔄 第 {attempt + 1}/3 次调用 GLM..."
                )

                # ------------------------------------------------
                # 导入智谱 SDK
                # ------------------------------------------------

                from zhipuai import ZhipuAI

                # ------------------------------------------------
                # 创建客户端
                # ------------------------------------------------

                client = ZhipuAI(
                    api_key=ZHIPU_KEY
                )

                # ------------------------------------------------
                # 调用模型
                # ------------------------------------------------

                resp = client.chat.completions.create(

                    model="glm-4-flash",

                    messages=[

                        {
                            "role": "system",
                            "content": system_prompt
                        },

                        {
                            "role": "user",
                            "content": question
                        }

                    ],

                    temperature=0.7,

                    max_tokens=1024

                )

                print(
                    "✅ GLM API 调用成功！"
                )

                # ------------------------------------------------
                # 获取回答
                # ------------------------------------------------

                answer = (
                    resp
                    .choices[0]
                    .message
                    .content
                )

                # ------------------------------------------------
                # 防止 GLM 返回 None
                # ------------------------------------------------

                if answer is None:

                    print(
                        "⚠️ GLM 返回 content = None"
                    )

                    answer = ""

                answer = str(answer).strip()

                print(
                    "🧠 GLM 返回内容长度：",
                    len(answer)
                )

                print(
                    "🧠 GLM 返回前100字：",
                    answer[:100]
                )

                print("=" * 60)

                # ------------------------------------------------
                # 只有真正有内容才 return
                # ------------------------------------------------

                if answer:

                    print(
                        "🎉 正式使用 GLM 智能分析结果"
                    )

                    return answer

                else:

                    print(
                        "⚠️ GLM 返回空内容，"
                        "准备重试..."
                    )

            except Exception as e:

                import traceback

                print("=" * 60)
                print("❌ Zhipu API 调用失败")
                print(
                    "错误类型：",
                    type(e).__name__
                )
                print(
                    "错误内容：",
                    str(e)
                )
                print("完整错误堆栈：")

                traceback.print_exc()

                print("=" * 60)

                # ------------------------------------------------
                # 只有前两次失败后等待
                # 第三次失败后直接 fallback
                # ------------------------------------------------

                if attempt < 2:

                    wait_time = 2 ** attempt

                    print(
                        f"⏳ {wait_time} 秒后重试..."
                    )

                    time.sleep(wait_time)

    else:

        print("=" * 60)
        print(
            "⚠️ 没有进入 GLM API 调用"
        )
        print(
            "原因：ZHIPU_KEY 为空，"
            "或者仍然是默认占位值"
        )
        print("=" * 60)

    # ========================================================
    # 6. 最终本地 fallback
    #
    # 非常重要：
    # 这个 return 必须在 if 外面。
    # 无论 GLM 成功、失败、Key异常，
    # 都不能让函数返回 None。
    # ========================================================

    print("=" * 60)
    print(
        "⚠️ GLM 未返回有效结果"
    )
    print(
        "🔧 最终进入本地 fallback_analysis()"
    )
    print("=" * 60)

    fallback_result = fallback_analysis(
        question,
        posts,
        analysis_type
    )

    # 最后一层保护
    if not fallback_result:

        fallback_result = (
            "⚠️ 本地智能体兜底分析也未生成有效结果。"
        )

    return str(fallback_result)


# ============================================================
# 本地规则兜底
# ============================================================

def fallback_analysis(
        question: str,
        posts=None,
        analysis_type: str = 'general'
) -> str:
    """
    本地兜底分析。

    当 GLM API 不可用时，
    根据数据库真实数据生成基础分析结果。
    """

    # --------------------------------------------------------
    # 1. 获取数据
    # --------------------------------------------------------

    if posts is None:

        posts = (
            Post.objects
            .all()
            .order_by('-view_count')[:20]
        )

    count = (
        posts.count()
        if posts.exists()
        else 0
    )

    total_views = (

        sum(
            p.view_count or 0
            for p in posts
        )

        if posts.exists()

        else 0

    )

    if count:

        data_line = (
            f"基于{count}条真实B站视频"
            f"（总播放{total_views:,}）"
        )

    else:

        data_line = "当前数据库暂无有效视频数据"

    # ========================================================
    # 2. 热度分析
    # ========================================================

    if analysis_type == 'heat':

        top3 = (

            [
                p.title[:25]
                for p in posts[:3]
            ]

            if posts.exists()

            else []

        )

        top_text = (

            "".join(
                f"   • {title}\n"
                for title in top3
            )

            if top3

            else

            "   • 暂无数据\n"

        )

        return (

            "【智能体 · 回归热度分析报告】\n\n"

            f"{data_line}：\n\n"

            f"📈 热度趋势："
            f"相关视频总播放量达"
            f"{total_views:,}，"
            f"头部内容包括：\n"

            f"{top_text}\n"

            "🔑 核心关键词："
            "「视觉」「编舞」「旋律」「概念」\n"

            "😊 情感倾向："
            "当前仅根据内容结构进行基础判断，"
            "缺少评论文本时无法进行严格情感比例统计。\n"

            "📍 当前阶段判断："
            "建议结合视频标题和发布时间进一步确认"
            "P0-P7 生命周期阶段。"

        )

    # ========================================================
    # 3. 大众画像与舆论
    # ========================================================

    elif analysis_type == 'persona':

        return (

            "【智能体 · 大众画像与舆论分析】\n\n"

            f"{data_line}：\n\n"

            "👥 受众特征："
            "由于当前数据主要来自B站视频标题、"
            "播放量和互动数据，"
            "年龄、性别、地域只能作为推测，"
            "不能视为严格统计结果。\n\n"

            "💬 舆论焦点：\n"

            "   • 正面："
            "概念、舞台、编舞等内容容易形成讨论\n"

            "   • 中性："
            "回归预告、歌曲、舞台信息等\n"

            "   • 负面："
            "造型、part分配、舞台表现等可能形成讨论\n\n"

            "📊 传播路径："
            "官方内容 → 粉丝二创 → Reaction → "
            "社区讨论 → 二次传播\n\n"

            "🎯 粉丝活跃度："
            "可以结合播放量、点赞/投币等指标进行判断。"

        )

    # ========================================================
    # 4. 营销策略
    # ========================================================

    elif analysis_type == 'strategy':

        return (

            "【智能体 · 营销策略建议】\n\n"

            f"{data_line}：\n\n"

            f"✨ 数据亮点："
            f"当前样本总播放量为"
            f"{total_views:,}。\n\n"

            "🎯 具体建议：\n"

            "   1. 【二创激励】"
            "围绕播放量Top视频发起翻跳、"
            "翻唱和Reaction二创活动，"
            "扩大内容生命周期。\n"

            "   2. 【舞台曝光】"
            "针对高播放舞台类内容提高更新频率，"
            "进一步放大头部内容传播。\n"

            "   3. 【中文粉丝互动】"
            "针对高热度视频加强中文评论区互动，"
            "提高粉丝参与度。\n"

            "   4. 【概念延续】"
            "根据当前热门内容持续释出幕后、"
            "花絮及相关衍生内容，"
            "延长回归热度。"

        )

    # ========================================================
    # 5. 生命周期诊断
    # ========================================================

    elif analysis_type == 'lifecycle':

        # ----------------------------------------------------
        # 生命周期关键词
        # ----------------------------------------------------

        phase_keywords = {

            'P1': [
                '概念照',
                'concept photo',
                'concept image',
                'concept photo',
                '概念图'
            ],

            'P2': [
                '曲目',
                'tracklist',
                'track list',
                'track listing',
                '歌曲列表'
            ],

            'P3': [
                '预告',
                'teaser',
                'highlight medley',
                '预告片',
                '概念视频',
                'concept video'
            ],

            'P4': [
                '专辑发布',
                'album release',
                'album',
                '专辑上线',
                '发行'
            ],

            'P5': [
                'mv',
                'music video',
                'official mv',
                '官方mv',
                '音乐视频'
            ],

            'P6': [
                '打歌',
                'music bank',
                'm countdown',
                'inkigayo',
                'show champion',
                '舞台',
                '直拍',
                'live stage'
            ],

            'P7': [
                '幕后',
                'behind',
                'behind the scenes',
                '花絮',
                'reaction',
                'fan meeting',
                '回顾',
                '采访'
            ]

        }

        # ----------------------------------------------------
        # 阶段名称
        # ----------------------------------------------------

        phase_names = {

            'P0': '未识别',
            'P1': '概念照期',
            'P2': '曲目列表期',
            'P3': '预告期',
            'P4': '专辑发布期',
            'P5': 'MV发布期',
            'P6': '打歌期',
            'P7': '后续活动期'

        }

        # ----------------------------------------------------
        # 统计关键词
        # ----------------------------------------------------

        phase_scores = {

            phase: 0

            for phase in phase_keywords

        }

        evidence = []

        for post in posts:

            title = (
                post.title or ''
            ).lower()

            matched = False

            for phase, keywords in phase_keywords.items():

                for keyword in keywords:

                    if keyword.lower() in title:

                        phase_scores[phase] += 1

                        matched = True

                        break

            if matched:

                evidence.append(
                    post.title
                )

        # ----------------------------------------------------
        # 找到最高得分阶段
        # ----------------------------------------------------

        detected_phase = max(
            phase_scores,
            key=phase_scores.get
        )

        # ----------------------------------------------------
        # 无命中 → P0
        # ----------------------------------------------------

        if (
            phase_scores[detected_phase]
            == 0
        ):

            detected_phase = 'P0'

        current_name = (
            phase_names[detected_phase]
        )

        # ----------------------------------------------------
        # 下一阶段
        # ----------------------------------------------------

        phase_order = [

            'P0',
            'P1',
            'P2',
            'P3',
            'P4',
            'P5',
            'P6',
            'P7'

        ]

        current_index = (
            phase_order.index(
                detected_phase
            )
        )

        if (
            current_index
            < len(phase_order) - 1
        ):

            next_phase = (
                phase_order[
                    current_index + 1
                ]
            )

            next_name = (
                phase_names[next_phase]
            )

        else:

            next_phase = 'P7'

            next_name = (
                phase_names['P7']
            )

        # ----------------------------------------------------
        # 真实标题证据
        # ----------------------------------------------------

        evidence_text = '\n'.join(

            f"• {title}"

            for title in evidence[:3]

        )

        if not evidence_text:

            evidence_text = (
                "• 当前抓取的视频标题中"
                "没有发现明确的生命周期关键词"
            )

        # ----------------------------------------------------
        # 各阶段统计
        # ----------------------------------------------------

        score_text = '\n'.join(

            f"• {phase}｜"
            f"{phase_names[phase]}："
            f"{score} 条"

            for phase, score
            in phase_scores.items()

        )

        # ----------------------------------------------------
        # 返回报告
        # ----------------------------------------------------

        return f"""
🔄 Agent-Lifecycle 回归生命周期诊断

### 1. 当前阶段

**{detected_phase}｜{current_name}**

根据当前数据库中抓取到的
{len(posts)} 条视频数据进行关键词分析，
当前最明显的生命周期信号为
**{detected_phase}｜{current_name}**。

### 2. 数据依据

当前检测到的相关视频标题：

{evidence_text}

各阶段关键词命中情况：

{score_text}

### 3. 阶段特征

{current_name} 通常意味着艺人正在围绕
该阶段进行集中传播。

当前平台上的视频标题结构，
可以作为判断回归进度的重要信号。

### 4. 下一阶段预测

**{next_phase}｜{next_name}**

如果后续抓取数据中出现更多与下一阶段
相关的视频标题，则可以进一步验证
回归生命周期是否正在推进。

### 5. 当前运营建议

📌 持续抓取最新视频数据，
观察标题结构和播放量变化。

📌 如果进入下一阶段，
应及时调整内容分析重点。

📌 将生命周期阶段与播放量、
发布时间结合，可以进一步判断
当前回归热度处于上升、峰值还是回落状态。

⚠️ 当前结果属于 LLM 调用失败后的
本地规则兜底诊断。
正常情况下优先使用 Agent-Lifecycle
的 GLM 智能分析结果。
"""

    # ========================================================
    # 6. 数据概览
    # ========================================================

    else:

        return (

            "【智能体 · 数据概览】\n\n"

            f"{data_line}。\n\n"

            f"📦 视频总量："
            f"{count}条相关视频\n"

            f"▶️ 总播放量："
            f"{total_views:,}\n"

            "🔥 内容特征："
            "以MV、舞台直拍、Reaction等内容为主\n"

            "📈 整体趋势："
            "头部视频对整体热度具有明显带动作用，"
            "建议持续关注高播放内容及其二创传播。"

        )