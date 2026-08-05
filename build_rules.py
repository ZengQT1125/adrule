#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AdRule builder: 拉取 -> 去重 -> 合并 -> 精简(<=TARGET_TOTAL) -> 输出 dns.txt
跨平台(Python3)，可用于本地 Windows / Linux 服务器 / GitHub Actions 定时任务。
"""
import io, os, re, sys, time, collections, urllib.request

TARGET_TOTAL = 30000      # MV3 插件规则上限
OUT = "dns.txt"
UA = {"User-Agent": "Mozilla/5.0 (adrule-builder; +https://github.com/ZengQT1125/adrule)"}

SOURCES = {
    "awavenue":    "https://github.boki.moe/https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/AWAvenue-Ads-Rule.txt",
    "abpmerge":    "https://raw.githubusercontent.com/damengzhu/abpmerge/refs/heads/main/abpmerge.txt",
    "adblock_auto":"https://lingeringsound.github.io/adblock_auto/Rules/adblock_auto.txt",
}
PREMIUM = {"awavenue"}   # 精品源：体积小、人工精选，评分加成

# 知名服务主域白名单：裸主域绝不拦截（子域不受影响，如 ads.amazon.com 仍保留）
WHITELIST = {d.strip().lower() for d in """
amazon.com amazon.co.uk amazon.cn amazonaws.com
google.com googleapis.com gstatic.com googlesyndication.com doubleclick.net googleusercontent.com
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

DOM_RE = re.compile(r"^([a-z0-9_\-]+(?:\.[a-z0-9_\-]+)+)", re.I)

def norm_rule(r):
    """只接受纯域名规则。返回 ('dom', '||d^') / ('wild','||*.d^') / None"""
    r = r.strip()
    if not r.startswith("||"):
        return None
    body = r[2:]
    wild = False
    if body.startswith("*."):
        body = body[2:]
        wild = True
    m = DOM_RE.match(body)
    if not m:
        return None
    dom = m.group(1).lower().rstrip(".")
    if not dom or "." not in dom:
        return None
    if wild:
        return ("wild", "||*." + dom + "^")
    return ("dom", "||" + dom + "^")

def main():
    per_src_dom = {}   # name -> set(domain)
    per_src_wild = {}  # name -> set('||*.d^')
    ok = []
    for name, url in SOURCES.items():
        try:
            lines = fetch(url)
        except Exception as e:
            print("[WARN] %s 下载失败: %s" % (name, e))
            continue
        ok.append(name)
        doms, wilds = set(), set()
        for x in lines:
            s = x.strip()
            if not s or s.startswith("!"):
                continue
            nd = norm_rule(s)
            if nd is None:
                continue
            if nd[0] == "dom":
                doms.add(nd[1][2:-1])
            else:
                wilds.add(nd[1])
        per_src_dom[name] = doms
        per_src_wild[name] = wilds
        print("[OK] %s: 下载行数=%d 域名规则去重=%d 通配规则=%d" % (name, len(lines), len(doms), len(wilds)))

    if not ok:
        sys.exit("所有源下载失败，退出")

    freq = collections.Counter()
    for s in per_src_dom.values():
        freq.update(s)
    all_dom = set(freq)
    print()
    print("唯一域名(去重前): %d" % len(all_dom))

    dropped = sorted(d for d in all_dom if d in WHITELIST)
    kept = [d for d in all_dom if d not in WHITELIST]
    if dropped:
        print("白名单剔除 %d 个知名主域: %s" % (len(dropped), dropped[:20]))

    def score(d):
        s = freq[d] * 1000
        for p in PREMIUM:
            if d in per_src_dom.get(p, ()):
                s += 300
        if d.count(".") >= 2:
            s += 50
        return s

    ranked = sorted(kept, key=lambda d: (-score(d), len(d), d))

    wild_all = set()
    for s in per_src_wild.values():
        wild_all |= s

    dom_quota = TARGET_TOTAL - len(wild_all)
    selected = ranked[:dom_quota]
    print("通配规则保留: %d  域名配额: %d" % (len(wild_all), dom_quota))
    print("入选域名: %d  最低共识度: %s" % (len(selected), freq[selected[-1]] if selected else "-"))
    dist = collections.Counter(freq[d] for d in selected)
    print("入选域名共识度分布: %s" % dict(sorted(dist.items(), reverse=True)))

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    body_count = len(selected) + len(wild_all)
    out = []
    out.append("! Title: AdRule (merged & deduped by ZengQT1125)")
    out.append("! Version: " + now)
    out.append("! Total count: %d" % body_count)
    out.append("! Homepage: https://github.com/ZengQT1125/adrule")
    out.append("! Sources:")
    for name in ok:
        out.append("!   %s: %s" % (name, SOURCES[name]))
    out.append("! Strategy: keep ||domain rules only, weighted by cross-source consensus + premium source, whitelist protected, cap %d" % TARGET_TOTAL)
    for w in sorted(wild_all):
        out.append(w)
    for d in selected:
        out.append("||" + d + "^")

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    print()
    print("写入 %s: 有效规则 %d 条 (上限 %d)" % (OUT, body_count, TARGET_TOTAL))
    print("文件大小: %d bytes" % os.path.getsize(OUT))

if __name__ == "__main__":
    main()
