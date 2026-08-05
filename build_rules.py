#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AdRule builder: 拉取 -> 去重 -> 合并 -> 按质量排序 -> 输出 dns.txt
不截断：插件(MV3)会自行按条数截断，本脚本只保证【越好的规则越靠前】。
跨平台(Python3)，可用于本地 Windows / Linux 服务器 / GitHub Actions 定时任务。
"""
import io, os, re, sys, time, collections, urllib.request

OUT = "dns.txt"
UA = {"User-Agent": "Mozilla/5.0 (adrule-builder; +https://github.com/ZengQT1125/adrule)"}

SOURCES = {
    "awavenue":    "https://github.boki.moe/https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/AWAvenue-Ads-Rule.txt",
    "abpmerge":    "https://raw.githubusercontent.com/damengzhu/abpmerge/refs/heads/main/abpmerge.txt",
    "adblock_auto":"https://lingeringsound.github.io/adblock_auto/Rules/adblock_auto.txt",
}

# 防御性白名单：仅剔除"整域拦截知名服务主域"的域名级规则(如 ||google.com^ )。
# 子域/路径级规则不受影响；广告域(doubleclick.net 等)不在其中。
WHITELIST = {d.strip().lower() for d in """
amazon.com amazon.co.uk amazon.cn amazonaws.com
google.com googleapis.com gstatic.com googleusercontent.com
apple.com icloud.com
microsoft.com live.com office.com windows.com bing.com msn.com microsoftonline.com
facebook.com fbcdn.net instagram.com whatsapp.com messenger.com
youtube.com ytimg.com googlevideo.com
twitter.com x.com twimg.com
github.com githubusercontent.com gitlab.com
cloudflare.com cloudflare.net
alibaba.com taobao.com tmall.com alicdn.com aliyun.com 1688.com
baidu.com baidustatic.com bcebos.com sogou.com
tencent.com qq.com qqmail.com gtimg.com qpic.cn myqcloud.com
jd.com 360buyimg.com
bilibili.com bilibili.tv hdslb.com
zhihu.com weibo.com weibocdn.com douyin.com bytedance.com
163.com netease.com 126.com
sina.com sinaimg.cn sohu.com ifeng.com
mozilla.org mozilla.net
w3.org apache.org
""".split()}

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    for enc in ("utf-8", "gbk"):
        try:
            return data.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace").splitlines()

COSMETIC_RE = re.compile(r'#[@?$]?#')
DOMBODY_RE = re.compile(r'^([a-z0-9_\-]+(?:\.[a-z0-9_\-]+)+)', re.I)

def classify(r):
    """返回 ('allow'|'dom'|'path'|'regex'|'cosmetic'|'other', rule) 或 None(注释/空行)"""
    r = r.strip()
    if not r or r.startswith("!"):
        return None
    if r.startswith("@@"):
        return ("allow", r)
    if COSMETIC_RE.search(r):
        return ("cosmetic", r)
    if r.startswith("||"):
        body = r[2:]
        if body.startswith("*."):
            body = body[2:]
        m = DOMBODY_RE.match(body)
        if m:
            # 剩余部分是 ^ / 路径 / 修饰符
            rest = body[m.end():]
            if rest == "" or rest == "^" or rest.startswith("^") and " " not in rest and "/" not in rest and "?" not in rest and "*" not in rest:
                # 纯域名规则(允许 ^ 结尾)
                if "/" not in rest and "?" not in rest and "*" not in rest:
                    return ("dom", r)
        return ("path", r)
    if r.startswith("/") and "/" in r[1:]:
        return ("regex", r)
    return ("other", r)

def dom_of_rule(r):
    body = r[2:]
    if body.startswith("*."):
        body = body[2:]
    m = DOMBODY_RE.match(body)
    return m.group(1).lower().rstrip(".") if m else None

def main():
    per_src = {}          # name -> Counter 无需，用 set
    rule_freq = collections.Counter()
    dom_freq = collections.Counter()
    ok = []
    for name, url in SOURCES.items():
        try:
            lines = fetch(url)
        except Exception as e:
            print("[WARN] %s 下载失败: %s" % (name, e))
            continue
        ok.append(name)
        seen_rules = set()
        seen_doms = set()
        for x in lines:
            s = x.strip()
            if not s or s.startswith("!"):
                continue
            if s not in seen_rules:
                seen_rules.add(s)
                rule_freq[s] += 1
            if s.startswith("||"):
                dd = dom_of_rule(s)
                if dd and dd not in seen_doms:
                    seen_doms.add(dd)
                    dom_freq[dd] += 1
        print("[OK] %s: 下载行数=%d" % (name, len(lines)))

    if not ok:
        sys.exit("所有源下载失败，退出")

    # 收集全部去重规则
    all_rules = set(rule_freq.keys())
    print()
    print("合并去重后规则总数: %d" % len(all_rules))

    buckets = {"allow": [], "dom": [], "path": [], "regex": [], "cosmetic": [], "other": []}
    for r in all_rules:
        c = classify(r)
        if c is None:
            continue
        buckets[c[0]].append(r)

    # 防御性白名单：剔除整域拦截知名主域(||google.com^ 这种)的域名级规则
    before = len(buckets["dom"])
    kept_dom = []
    for r in buckets["dom"]:
        dd = dom_of_rule(r)
        if dd in WHITELIST:
            continue
        kept_dom.append(r)
    buckets["dom"] = kept_dom
    print("域名级规则 %d -> %d (白名单剔除 %d)" % (before, len(kept_dom), before - len(kept_dom)))

    # 排序键：质量优先
    def dom_key(r):
        dd = dom_of_rule(r)
        return (-dom_freq.get(dd, 0), -rule_freq[r], len(r), r)
    def plain_key(r):
        return (-rule_freq[r], len(r), r)

    sections = []
    # 1) @@ 例外（防误杀，必须最先被加载）
    sections.append(("@@" + " 例外规则(allow)", sorted(buckets["allow"], key=plain_key)))
    # 2) 域名级 ||d^ ：高共识在前（覆盖广、可信度高）
    sections.append(("域名级规则(domain)", sorted(buckets["dom"], key=dom_key)))
    # 3) 路径级 ||d/... ：精确、误杀小（按域名共识度）
    sections.append(("路径级规则(path)", sorted(buckets["path"], key=dom_key)))
    # 4) 其他网络规则
    sections.append(("其他网络规则(other)", sorted(buckets["other"], key=plain_key)))
    # 5) 正则
    sections.append(("正则规则(regex)", sorted(buckets["regex"], key=plain_key)))
    # 6) cosmetic 元素隐藏（量大、放最后）
    sections.append(("cosmetic 规则", sorted(buckets["cosmetic"], key=plain_key)))

    total = sum(len(b[1]) for b in sections)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    out = []
    out.append("! Title: AdRule merged & deduped (ZengQT1125)")
    out.append("! Version: " + now)
    out.append("! Total count: %d" % total)
    out.append("! Homepage: https://github.com/ZengQT1125/adrule")
    out.append("! Sources:")
    for name in ok:
        out.append("!   %s: %s" % (name, SOURCES[name]))
    out.append("! Order: allow -> domain(high-consensus) -> path -> other -> regex -> cosmetic")
    out.append("! Note: 不截断，插件自行按条数限制截断；本文件只保证越好的规则越靠前")
    for label, items in sections:
        out.append("")
        out.append("! ===== %s (%d) =====" % (label, len(items)))
        out.extend(items)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    print("写入 %s: 有效规则 %d 条, 文件 %d bytes" % (OUT, total, os.path.getsize(OUT)))
    for label, items in sections:
        print("  %-24s %6d" % (label, len(items)))

if __name__ == "__main__":
    main()
