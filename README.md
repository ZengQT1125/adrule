# AdRule

把多个 GitHub 上的广告过滤规则源**拉取 → 去重 → 合并 → 精简**成一份自己用的域名规则列表，并在 GitHub Actions 中**每天自动更新**。

精简后保留**纯域名规则**（`||domain^`），总条数**不超过 30000 条**（网络广告拦截类浏览器插件 / MV3 的规则上限），同时兼容 DNS 过滤（AdGuard Home、smartdns 等），一份规则多端通用。

## 规则源（Sources）

| 源 | 说明 | 地址 |
| --- | --- | --- |
| AWAvenue | 精品源，人工精选、质量高 | [AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) |
| abpmerge | 聚合合并列表 | [damengzhu/abpmerge](https://github.com/damengzhu/abpmerge) |
| adblock_auto | 超大聚合列表 | [lingeringsound/adblock_auto](https://github.com/lingeringsound/adblock_auto) |

## 订阅地址

```
https://raw.githubusercontent.com/ZengQT1125/adrule/main/dns.txt
```

## 精简策略

1. 只保留纯域名规则 `||domain^`（一条拦整个域名，对 DNS 和浏览器插件都有效）；
2. 规范化、去重；
3. **白名单保护**：剔除 `amazon.com`、`google.com` 等知名服务的裸主域，避免误杀整站（子域如 `ads.amazon.com` 仍会保留）；
4. **共识度加权**：被越多源收录的域名越优先保留，AWAvenue 精品源额外加分；
5. 按分数排序后截断到 `TARGET_TOTAL`（默认 30000）条。

## 本地重新生成

```bash
python build_rules.py     # 或: bash build_rules.sh
```

生成 `dns.txt`。可调整脚本头部的 `TARGET_TOTAL`、`SOURCES`、`WHITELIST` 来定制。

## 定时更新

`.github/workflows/build.yml` 每天 UTC 02:00 自动执行构建，若 `dns.txt` 有变化会自动提交并推送。也可在仓库 `Actions` 页面手动触发 `workflow_dispatch`。

---
> 仅供个人学习使用。误拦截时可自行把域名加入脚本的 `WHITELIST`，或手动在过滤客户端中添加 `@@` 例外规则。
