#!/usr/bin/env python3
"""zh-lint.py — 中文受控语言结构检查器(zh-plain skill)。

只查结构模式。它不比对原文与改写,不验证语义保持,也不判断改写是否更好。
零违规只意味着一件事:本次配置的结构检查没有发现问题。零违规 ≠ 合规。

永不报情态(可能/大概率/约/仅/疑似/需确认/未实测):情态是内容,不是文风。
见 --selftest 的断言。

用法:
    python zh-lint.py [文件...]              # 无参数读 stdin
    python zh-lint.py --mode voice 文档.md    # 文风模式(关句长/流水句)
    python zh-lint.py --baseline 5 存量.md    # 容忍 5 处 hard 违规,便于存量文档采用
    python zh-lint.py --disable semicolon,hype-word 文档.md
    python zh-lint.py --json 文档.md
    python zh-lint.py --selftest

退出码:hard 违规数 > baseline 时为 1,否则 0。advisory 从不导致失败。
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ponytail: 正则启发式,不是解析器。天花板在此,要升级再升级——
#   同义词表手写 8 组,不求全;的-链靠数「的」的间隔,不做词性分析;
#   无分词依赖,所以查不了「名词堆叠」以外的搭配问题。
# 句长按句末标点与换行切分:中文不断行排版,换行即结构边界,不是句子的延续。

CJK = "一-鿿"
FINALS = "。！？!?"                    # 句末标点。分号不算边界——分号连接的正是要拆开的一句。
NO_FINAL = f"[^{FINALS};；\n]"

# --- 规则定义 ------------------------------------------------------------
# (名称, 检测, 说明)。检测为 str 时按正则;为 callable 时吃整段文本返回命中列表。
SYNONYM_GROUPS = [
    ("可用", "空闲", "剩余", "余量"),
    ("实测", "复测", "验证", "核实"),
    ("删除", "清理", "清除", "处置"),
    ("解决", "修复", "修好"),
    ("开始", "启动", "开启"),
    ("显示", "展示", "呈现"),
    ("修改", "调整", "变更"),
    ("执行", "运行", "跑"),
]

HYPE = ("赋能|抓手|闭环|对齐|拉齐|颗粒度|一站式|全方位|无缝|海量|极致|打造|助力"
        "|强大|高效|全面|深入")

RULES = [
    ("semicolon", r"[;；]",
     "分号。拆成独立句子——分号连接的两个分句容易被读成一个命题。"),
    ("sentence-len", None,
     "句子过长。按句末标点与换行切分后数汉字。"),
    ("comma-run", None,
     "流水句:一句内逗号连出多个命题,读者要自己切分。拆句或用列表。"),
    ("long-enum", None,
     "并列项过长(一段里 3 个以上长顿号项)。同一结构的并列数据改用列表或表格。"),
    ("empty-verb", rf"(?:进行|作出|予以|加以|实施|开展)(?:了|一次|进一步|全面|相应)?[{CJK}]{{2}}",
     "空动词+名词化。直接用那个动词(进行验证→验证,作出判断→判断)。"),
    ("de-chain", rf"的{NO_FINAL}{{0,12}}的{NO_FINAL}{{0,12}}的",
     "「的」链 ≥3 层定语。拆成短句,或把定语改成后置说明。"),
    ("hype-word", HYPE,
     "空泛形容词/套话。换成支撑它的事实或数字,否则删。"),
    ("passive-mark", r"(?:受到|遭到|被(?!动))",
     "被动标记。被字句本身合法,这里只提示:施事若可知,写明施事。"),
]

# 「显著X」只在附近没有数字时才报——有数字就是事实,不是套话。
VAGUE_CLAIM = re.compile(rf"显著(?:提升|改善|降低|增长|增强)(?![^。！？!?；\n]{{0,15}}\d)")

# 文风模式:句长要变化、意合合法 → 关掉句长与流水句;分号降为 advisory。
MODE_OFF = {"voice": {"sentence-len", "comma-run"}}
MODE_DOWNGRADE = {"voice": {"semicolon"}}

MAX_CJK = 60          # 接口模式分句上限(汉字数)。文风模式不设上限。
MAX_COMMAS = 4        # 一句内逗号数达到此值即流水句嫌疑。
MIN_ENUM_ITEM = 8     # 顿号项达到这么多汉字才算「长」——短枚举(西瓜、苹果)不该报。

# --- 预处理 --------------------------------------------------------------
INLINE_CODE = re.compile(r"`[^`]*`")
FENCE = re.compile(r"^\s*(?:```|~~~)")


def strip_code(text):
    """把代码块与行内代码换成等长空白,保持行号与句长计数不失真。"""
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            out.append(" " * len(line))
            continue
        out.append(" " * len(line) if in_fence else INLINE_CODE.sub(lambda m: " " * len(m.group()), line))
    return "\n".join(out)


def sections(text):
    """按 markdown 标题切段(术语一致性是段内信号);无标题则整篇为一段。"""
    parts, cur, start = [], [], 1
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r"^#{1,4}\s", line):
            if any(s.strip() for s in cur):
                parts.append((start, "\n".join(cur)))
            cur, start = [], i
        cur.append(line)
    if any(s.strip() for s in cur):
        parts.append((start, "\n".join(cur)))
    return parts


def units(section_text, lineno):
    """切成 (行号, 句子) —— 中文里换行与句末标点都是结构边界。"""
    out = []
    for offset, line in enumerate(section_text.splitlines()):
        for sent in re.split(f"[{FINALS}]", line):
            if re.search(f"[{CJK}]", sent):
                out.append((lineno + offset, sent.strip()))
    return out


def cjk_len(s):
    return len(re.findall(f"[{CJK}]", s))


# --- 逐句规则 ------------------------------------------------------------
def per_sentence_rules(sent, mode):
    hits = []
    off = MODE_OFF.get(mode, set())
    for name, pat, msg in RULES:
        if name in off:
            continue
        if name == "sentence-len":
            if mode == "interface" and cjk_len(sent) > MAX_CJK:
                hits.append((name, msg, f"{cjk_len(sent)} 汉字"))
            continue
        if name == "comma-run":
            # 只数连接分句的逗号。顿号枚举名词(工具描述、错误信息、系统提示)不是流水句。
            n = len(re.findall(r"[,，]", sent))
            if n >= MAX_COMMAS:
                hits.append((name, msg, f"{n} 个逗号"))
            continue
        if name == "long-enum":
            items = [s for s in re.split("、", sent) if cjk_len(s) >= MIN_ENUM_ITEM]
            if len(items) >= 3:
                hits.append((name, msg, f"{len(items)} 个长并列项"))
            continue
        if pat:
            m = re.search(pat, sent)
            if m:
                hits.append((name, msg, m.group(0)))
    m = VAGUE_CLAIM.search(sent)
    if m:
        hits.append(("hype-word", "「显著X」没有数字支撑。给出具体数值,否则删。", m.group()))
    return hits


# --- 文件级规则 ----------------------------------------------------------
def synonym_rotation(section_text):
    """一个动作在段内被换上几个名字,读者无法判断是不是同一件事。"""
    hits = []
    for group in SYNONYM_GROUPS:
        found = sorted({w for w in group if w in section_text})
        if len(found) > 1:
            hits.append(("synonym-rotation",
                         "同一动作在段内换名。全文统一用一个词。", "/".join(found)))
    return hits


def punct_mix(text):
    mixed = [f"{a} 与 {b}" for a, b in
             (("，", ","), ("；", ";"), ("：", ":"), ("（", "("), ("）", ")"), ("？", "?"))
             if a in text and b in text]
    if not mixed:
        return []
    return [("punct-mix", "全角与半角标点混用。同一文档统一一种体系。", "、".join(mixed))]


# 中文正文里本该全角却写了半角的标点。
# 与 punct-mix 分工:一行内全角半角并存的归 punct-mix;整篇半角、一个全角都没写的归这里——
# 否则那样的文档零告警通过(实测过:一段中文 18 个半角标点、0 个全角,原先全静默)。
# ponytail: 只查逗号和分号。冒号在路径、URL、key: value、时间 3:00 里都合法,
#   误报面太大,真需要再按「冒号后不跟 / 或 \」加进来。括号同理(markdown 链接)。
ASCII_PROSE = ((",", "，", r"(?<!\d),(?!\d)"), (";", "；", r";"))


def ascii_punct(text):
    """逐行查。千分位(1,234)不算标点。"""
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not re.search(f"[{CJK}]", line):
            continue
        found = [f"{half}(应为 {full})" for half, full, pat in ASCII_PROSE
                 if full not in line and re.search(pat, line)]
        if found:
            hits.append((lineno, "、".join(found)))
    return hits


# --- 主流程 --------------------------------------------------------------
def lint(text, filename, mode, disabled):
    text = strip_code(text)
    findings = []

    def add(lineno, name, msg, detail, level):
        if name in disabled:
            return
        if mode == "voice" and name in MODE_DOWNGRADE.get("voice", set()):
            level = "advisory"
        findings.append({"file": filename, "line": lineno, "rule": name,
                         "level": level, "message": msg, "detail": detail})

    for lineno, sec in sections(text):
        for slineno, sent in units(sec, lineno):
            seen = set()
            for name, msg, detail in per_sentence_rules(sent, mode):
                if name in seen and name != "hype-word":
                    continue          # 同一句同一规则只报一次;逐句去重,跨句不可去重
                seen.add(name)
                add(slineno, name, msg, detail, "advisory" if name == "passive-mark" else "hard")
        for name, msg, detail in synonym_rotation(sec):
            add(lineno, name, msg, detail, "hard")
    for name, msg, detail in punct_mix(text):
        add(1, name, msg, detail, "advisory")
    for lineno, detail in ascii_punct(text):
        add(lineno, "ascii-punct",
            "中文正文里的半角逗号/分号。统一用全角——顿号全角、逗号半角是常见混法。",
            detail, "advisory")
    return findings


def report(findings, as_json, baseline):
    hard = [f for f in findings if f["level"] == "hard"]
    if as_json:
        print(json.dumps({"findings": findings, "hard": len(hard),
                          "advisory": len(findings) - len(hard)}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            mark = "!" if f["level"] == "hard" else "-"
            print(f"{mark} {f['file']}:{f['line']}: [{f['rule']}] {f['message']} ({f['detail']})")
        print(f"\nhard {len(hard)} 处,advisory {len(findings) - len(hard)} 处"
              f"{'(容忍上限 %d)' % baseline if baseline else ''}。"
              f"\n结构检查不验证语义保持。零违规 ≠ 合规。")
    return 1 if len(hard) > baseline else 0


SELFTEST_CASES = [
    # (文本, 期望命中的规则, 模式)
    ("扫描器删除了 3 个文件;回收站未清空。", {"semicolon"}, "interface"),
    ("工具读取配置,校验字段,写入数据库,通知下游服务,再等待确认。", {"comma-run"}, "interface"),
    ("数据分四类:应用的运行时状态、用户的个人配置文件、系统的日志与本地缓存。", {"long-enum"}, "interface"),
    ("" + "配" * 61 + "。", {"sentence-len"}, "interface"),
    ("对结果进行验证。", {"empty-verb"}, "interface"),
    ("建立在用户配置基础上的、按部门划分的、按时间排序的权限表。", {"de-chain"}, "interface"),
    ("本方案赋能企业,打造一站式闭环。", {"hype-word"}, "interface"),
    ("性能显著提升。", {"hype-word"}, "interface"),
]


def selftest():
    ok = True
    for text, expect, mode in SELFTEST_CASES:
        got = {f["rule"] for f in lint(text, "<selftest>", mode, set())}
        if not expect <= got:
            print(f"FAIL 期望 {expect},实得 {got}  ← {text[:30]}")
            ok = False
    # 情态永不报:这是内容,不是文风。改了它等于改了断言。
    # 夹具必须写成规范全角——半角逗号会招来 ascii-punct,让这条断言假红(踩过一次)。
    for text in ("请求可能已失败。", "大概率是残留文件。", "该值约 3.5GB，仅作估算。",
                 "此行为未实测，需确认。"):
        got = lint(text, "<selftest>", "interface", set())
        if got:
            print(f"FAIL 情态被误报: {text}  ← {[f['rule'] for f in got]}")
            ok = False
    # 文风模式:句长与流水句关闭,分号降级
    long_sent = "先读取配置" + "再处理数据" * 14 + "。"
    got = {f["rule"]: f["level"] for f in lint(long_sent, "<selftest>", "voice", set())}
    if "sentence-len" in got:
        print("FAIL 文风模式未关闭 sentence-len")
        ok = False
    comma_sent = "一,二,三,四,五,收尾。"
    if "comma-run" in {f["rule"] for f in lint(comma_sent, "<selftest>", "voice", set())}:
        print("FAIL 文风模式未关闭 comma-run")
        ok = False
    if got.get("semicolon") == "hard":
        print("FAIL 文风模式未把 semicolon 降为 advisory")
        ok = False
    # --disable 生效
    if lint("进行验证。", "<selftest>", "interface", {"empty-verb"}):
        print("FAIL --disable 未生效")
        ok = False
    # 整篇半角的中文正文也要报:punct-mix 只在全角半角并存时才开口
    if "ascii-punct" not in {f["rule"] for f in lint("扫描器删除了 3 个文件,回收站未清空。",
                                                    "<selftest>", "interface", set())}:
        print("FAIL 整篇半角的中文正文未报 ascii-punct")
        ok = False
    # 全角正文不该报;千分位逗号也不是标点
    for clean in ("扫描器删除了 3 个文件，回收站未清空。", "共 1,234 个文件。"):
        if "ascii-punct" in {f["rule"] for f in lint(clean, "<selftest>", "interface", set())}:
            print(f"FAIL 误报 ascii-punct: {clean}")
            ok = False
    print("selftest 全绿" if ok else "selftest 有失败项")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="中文受控语言结构检查器。零违规 ≠ 合规。")
    ap.add_argument("files", nargs="*", help="待检查文件;省略则读 stdin")
    ap.add_argument("--mode", choices=("interface", "voice"), default="interface",
                    help="interface=消歧义(默认);voice=文风(关句长/流水句)")
    ap.add_argument("--baseline", type=int, default=0, help="容忍的 hard 违规数")
    ap.add_argument("--disable", default="", help="逗号分隔的规则名,静默")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台默认 GBK 会乱码

    if args.selftest:
        return selftest()

    disabled = {s.strip() for s in args.disable.split(",") if s.strip()}
    texts = []
    if args.files:
        for p in args.files:
            texts.append((Path(p).name, Path(p).read_text(encoding="utf-8", errors="replace")))
    else:
        texts.append(("<stdin>", sys.stdin.read()))

    allf = []
    for name, text in texts:
        allf += lint(text, name, args.mode, disabled)
    return report(allf, args.json, args.baseline)


if __name__ == "__main__":
    sys.exit(main())