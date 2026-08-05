# AdRule

把多个 GitHub 上的广告过滤规则源**拉取 → 去重 → 合并 → 按质量排序**成一份自己用的规则列表，并在 GitHub Actions 中**每天自动更新**。

**不做条数截断**：浏览器插件（MV3 / uBO / AdGuard）会按自身的条数限制自行截断，本仓库只负责把**最有价值的规则排在最前面**，插件截断时保留的就是最好的部分。

## 规则源（Sources）

| 源 | 说明 | 地址 |
| --- | --- | --- |
| AWAvenue | 精品源，人工精选、质量高 | [AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) |
| abpmerge | 聚合合并列表（规则类型全） | [damengzhu/abpmerge](https://github.com/damengzhu/abpmerge) |

## 订阅地址

```
https://raw.githubusercontent.com/ZengQT1125/adrule/main/dns.txt
```

## 排序策略（越好的越靠前）

规则按以下段落顺序输出，段落内部按"共识度"（被越多源收录越可信）降序排列：

1. `@@` 例外规则（防止误杀，必须最先加载，例如百度搜索页等场景）
2. 域名级规则 `||domain^`（覆盖广，一条拦整个域名）
3. 路径级规则 `||domain/path`（精确、误杀小）
4. 其他网络规则（`$csp=` 等高级修饰符）
5. 正则规则 `/.../`
6. cosmetic 元素隐藏规则（`##` 等，量大、放最后）

同时做**防御性白名单**：剔除 `||google.com^` 这类"整域拦截知名服务主域"的明显误写规则（子域与路径级不受影响）。

## 本地重新生成

```bash
python build_rules.py     # 或: bash build_rules.sh
```

生成 `dns.txt`。可编辑脚本头部的 `SOURCES`、`WHITELIST` 定制。

## 定时更新

`.github/workflows/build.yml` 每天 UTC 02:00 自动执行构建，若 `dns.txt` 有变化会自动提交并推送。也可在仓库 `Actions` 页面手动触发。

---
> 仅供个人学习使用。误拦截时可自行把域名加入脚本 `WHITELIST`，或手动在过滤客户端中添加 `@@` 例外规则。
