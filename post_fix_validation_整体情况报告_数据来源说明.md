# 《post_fix_validation_整体情况报告》数据来源全量说明

## 1. 说明范围（相对路径）

- 被说明报告：`outputs/post_fix_validation_整体情况报告.md`
- 主数据源：`../新数据20260511/im-10086-新工单数据汇总_比赛信息已验证_省份数据更新龄_营销活动打标(1).xlsx`
- 赛事日数据源：`../data/2026怡宝中国足球超级联赛赛程_0409_更新.xlsx`
- 主数据源工作表：`Sheet1`
- 赛事日工作表：`联赛赛程` 
- 本次报告数据行范围（主数据表）：第 `2 行到第 `2194` 行，共 `2193` 行

## 2. 报告用到的中文表头

### 2.1 主数据表（Sheet1）表头

| 中文表头 | 在报告中的用途 |
| --- | --- |
| 工单编号 | 样本定位、抽样证据定位 |
| 省份名称 | 省份分布类统计（本版正文未展开） |
| 服务时间 | 数据周期、每日趋势、异动、赛程按日匹配 |
| 工单内容 / 工单投诉内容 | 典型用户原话、赛事日样例摘要 |
| 处理意见（客服回复） | 客服应对总结 |
| 一级标签集合 | 一级问题分布、已标注/未标注划分 |
| 二级标签集合 | 二级问题分布、异动节点二级问题 |
| 三级标签集合 | 三级问题分布、一级下诉求分布、趋势主问题 |
| 触发场景-情绪 | 情绪分布、负向占比 |
| 触发场景-服务类型 | 趋势“服务类型”热点 |
| 客户关键诉求 | 未标注分析、三级证据聚合 |
| 客户诉求关键词 | 三级总结补充 |
| 客服关键处理动作 | 三级证据聚合、客服应对总结 |
| 客服处理关键词 | 三级总结补充 |
| 是否有退费诉求 | 退费专题统计（本版正文未展开） |
| 是否有升级投诉倾向 | 升级倾向统计（本版正文未展开） |
| 涉及业务/会员类型_聚类 | 异动节点“涉及业务/会员类型” |
| 触发场景-赛事/事件 | 赛事补充线索 |

### 2.2 赛事日表（联赛赛程）表头

| 中文表头 | 在报告中的用途 |
| --- | --- |
| 轮次 | 赛事摘要（如“第1轮”） |
| 日期 | 判断某天是否赛事日 |
| 主队 | 赛事摘要（主队名称） |
| 客队 | 赛事摘要（客队名称） |
| 城市 | 赛事背景信息（摘要构造可用） |
| 时间 | 赛事摘要（开赛时间） |

## 3. 统一统计口径（每条数据都按这个口径取）

- 全量数据行集：主数据表 `Sheet1` 第 `2~2194` 行，且“服务时间”在 `2026-03-01` 到 `2026-03-31`。
- 已标注数据行集：全量数据中“一级标签集合”有值的行。
- 未标注数据行集：全量数据中“一级标签集合”为空的行。
- 每日数据行集：已标注数据中，“服务时间”的日期等于该日的行。
- 一级/二级/三级提及量：分别统计“一级标签集合/二级标签集合/三级标签集合”包含该标签的行数。
- 负向占比：`当日负向情绪行数 / 当日总行数`。  
  负向情绪按程序固定集合：`愤怒、失望、焦虑、不满、烦躁`（来自“触发场景-情绪”）。
- 异动日判定：`日环比增长 >= 50%` 且 `当日问题量 >= 5`。

## 4. 报告逐段来源说明（对应报告文本，含对应 ES 聚合语句）

### 4.0 公共 ES 过滤条件（以下语句默认都带这个时间范围）

```json
{
  "query": {
    "bool": {
      "filter": [
        {
          "range": {
            "service_time": {
              "gte": "2026-03-01",
              "lt": "2026-04-01"
            }
          }
        }
      ]
    }
  }
}
```

### 4.1 报告抬头与核心摘要

- `数据周期：2026-03-01 至 2026-03-31`：来自“服务时间”最小/最大日期。  
  对应 ES 聚合语句：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } }
      ]
    }
  },
  "aggs": {
    "period_min": { "min": { "field": "service_time" } },
    "period_max": { "max": { "field": "service_time" } }
  }
}
```

- `总服务数据量：2,193`：来自全量数据行集计数。  
  对应 ES 语句：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } }
      ]
    }
  }
}
```

- “核心摘要与发现”中的三大问题数字（539、377、228 及对应占比）：来自“三级标签集合”在已标注数据中的提及量，再除以总服务数据量。  
  对应 ES 语句（一次返回三项）：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "top3_tertiary": {
      "terms": {
        "field": "tertiary_labels",
        "size": 3,
        "include": [
          "退订困难/自动续费争议",
          "权益无法兑换/使用（如不知如何兑换、兑换失败）",
          "多端体验有差异（操作一致性）"
        ]
      }
    }
  }
}
```

- “核心摘要与发现”中的行动建议：由模型生成；其输入统计值来自下列 ES 语句（一级、二级、三级、情绪、服务类型一次拉全）：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "primary": { "terms": { "field": "primary_labels", "size": 20 } },
    "secondary": { "terms": { "field": "secondary_labels", "size": 30 } },
    "tertiary": { "terms": { "field": "tertiary_labels", "size": 30 } },
    "emotion": { "terms": { "field": "scene_emotion", "size": 20 } },
    "service_type": { "terms": { "field": "scene_service_type", "size": 10 } }
  }
}
```

### 4.2 1.1 问题分布概览

- “分析结论”段全部数字来源字段：  
  一级（一级标签集合）、二级（二级标签集合）、三级（三级标签集合）、情绪（触发场景-情绪），分母为总服务数据量。  
  对应 ES 语句（同一条语句产出这一段所有数值）：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "primary": { "terms": { "field": "primary_labels", "size": 20 } },
    "secondary": { "terms": { "field": "secondary_labels", "size": 30 } },
    "tertiary": { "terms": { "field": "tertiary_labels", "size": 30 } },
    "emotion": { "terms": { "field": "scene_emotion", "size": 20 } }
  }
}
```

- “未标注一二三级标签服务数据分析”来源：  
  `580（26.4%）`、未标注情绪、未标注诉求、未标注渠道线索。  
  对应 ES 语句：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        {
          "bool": {
            "must_not": [
              { "exists": { "field": "primary_labels" } }
            ]
          }
        }
      ]
    }
  },
  "aggs": {
    "emotion": { "terms": { "field": "scene_emotion", "size": 10 } },
    "customer_key_appeal": { "terms": { "field": "customer_key_appeal.keyword", "size": 10 } },
    "csp_name": { "terms": { "field": "csp_name", "size": 10 } }
  }
}
```

- “一级问题概览”表（业务体验/使用体验/内容体验/营销活动）来源：  
  对应 ES 语句：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "primary_top4": {
      "terms": {
        "field": "primary_labels",
        "size": 4,
        "include": ["业务体验", "使用体验", "内容体验", "营销活动"]
      }
    }
  }
}
```

### 4.3 四个一级模块中的数据来源

#### A. 一级标题数字

- `业务体验（1144，52.2%）`
- `使用体验（442，20.2%）`
- `内容体验（128，5.8%）`
- `营销活动（118，5.4%）`

对应 ES 语句（一次返回四项）：

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "primary_exact": {
      "terms": {
        "field": "primary_labels",
        "size": 10,
        "include": ["业务体验", "使用体验", "内容体验", "营销活动"]
      }
    }
  }
}
```

#### B. “用户核心诉求分布”表

- 每个一级下“诉求类型、频次占比”都来自“三级标签集合”在该一级内的分布。  
  对应 ES 模板语句（把 `{{一级标签}}` 替换为业务体验/使用体验/内容体验/营销活动）：

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } },
        { "term": { "primary_labels": "{{一级标签}}" } }
      ]
    }
  },
  "aggs": {
    "tertiary_by_primary": {
      "terms": { "field": "tertiary_labels", "size": 20 }
    }
  }
}
```

- “典型用户原话”来源样本抽样。  
  对应 ES 语句（按三级标签抽样）：

```json
{
  "size": 24,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } },
        { "term": { "tertiary_labels": "{{三级标签}}" } }
      ]
    }
  },
  "_source": [
    "content",
    "cs_reply",
    "customer_key_appeal",
    "customer_keywords",
    "cs_key_action",
    "cs_keywords",
    "service_time",
    "scene_emotion"
  ],
  "aggs": {
    "appeal_agg": { "terms": { "field": "customer_key_appeal.keyword", "size": 5 } },
    "cs_action_agg": { "terms": { "field": "cs_key_action.keyword", "size": 5 } }
  }
}
```

#### C. 每个三级小节标题（“共X条，占该一级问题Y%”）

- `共X条`：三级标签计数；`占该一级问题Y%`：`三级标签计数 / 一级总计数`。  
  对应 ES 语句（同条语句同时取分子分母）：

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "primary_total": {
      "filter": { "term": { "primary_labels": "{{一级标签}}" }
      }
    },
    "tertiary_count": {
      "filter": {
        "bool": {
          "must": [
            { "term": { "primary_labels": "{{一级标签}}" } },
            { "term": { "tertiary_labels": "{{三级标签}}" } }
          ]
        }
      }
    }
  }
}
```

#### D. 每个三级下“分析小结”

- “服务内容/客服应对/根因判断”都来自该三级标签样本抽样（见 B 中抽样语句），再由模型总结。  
- 对应 ES 语句：同 B 的 `term tertiary_labels={{三级标签}}` 抽样语句。

#### E. 每个一级末尾“分析小结：XXX类问题共...；Top3为...”

- 这句话前半部分数字来源（一级总量+一级下Top3三级）对应 ES 语句：

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } },
        { "term": { "primary_labels": "{{一级标签}}" } }
      ]
    }
  },
  "aggs": {
    "top3_tertiary_in_primary": {
      "terms": { "field": "tertiary_labels", "size": 3 }
    }
  }
}
```

### 4.4 一级标签综合评价（两段）

- 两段综合评价文字由模型生成，但输入数字来自一级分布与一级小结。  
- 一级分布的 ES 语句：

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "primary": { "terms": { "field": "primary_labels", "size": 20 } }
  }
}
```

### 4.5 1.2 投诉趋势与异动表现

#### A. “分析结论”段

- 峰值日、负向峰值日、赛事日日均、非赛事日日均、峰值附近主问题，均来自按日聚合。  
- 对应 ES 语句：

```json
{
  "size": 0,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "daily": {
      "date_histogram": {
        "field": "service_time",
        "calendar_interval": "day",
        "format": "yyyy-MM-dd",
        "min_doc_count": 0
      },
      "aggs": {
        "negative": {
          "filter": {
            "terms": {
              "scene_emotion": ["愤怒", "失望", "焦虑", "不满", "烦躁"]
            }
          }
        },
        "top_primary": { "terms": { "field": "primary_labels", "size": 3 } },
        "top_secondary": { "terms": { "field": "secondary_labels", "size": 3 } },
        "top_tertiary": { "terms": { "field": "tertiary_labels", "size": 3 } },
        "top_service_type": { "terms": { "field": "scene_service_type", "size": 3 } },
        "top_member_cluster": { "terms": { "field": "biz_member_cluster", "size": 3 } }
      }
    }
  }
}
```

#### B. “每日问题提及量与负向情绪占比”描述段

- 峰值、负向峰值、赛事日合计、异动最高增幅均由 A 的同一条日聚合语句产出。  
- 赛事日判定另外来自赛程表按“日期”映射（非 ES）。

#### C. “每日明细数据”表（31行）

- 表中每一行（日期、问题量、负向占比、主要三级问题）都来自 A 的 `daily.buckets`。  
- `⚡异动`由程序规则计算，不新增 ES 查询：  
  `growth=(当日count-前一日count)/前一日count`，满足 `growth>=50% 且 count>=5`。

#### D. “赛事日样例原声”3个样例块

- 样例选择来自 `daily` 聚合 + 当日样本。  
- 对应 ES 语句（在 A 基础上增加 `sample_hits`）：

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "daily": {
      "date_histogram": {
        "field": "service_time",
        "calendar_interval": "day",
        "format": "yyyy-MM-dd",
        "min_doc_count": 0
      },
      "aggs": {
        "top_tertiary": { "terms": { "field": "tertiary_labels", "size": 3 } },
        "sample_hits": {
          "top_hits": {
            "size": 3,
            "_source": [
              "service_time",
              "content",
              "customer_key_appeal",
              "scene_emotion",
              "primary_labels",
              "secondary_labels",
              "tertiary_labels",
              "operation_action",
              "biz_member_cluster",
              "match_label"
            ]
          }
        }
      }
    }
  }
}
```

#### E. “异动节点”表（前三名）

- 当日一级/二级/三级问题 + 服务类型 + 业务/会员类型均来自 A 的同一条日聚合语句。  
- 排序方式：按 `day_over_day_growth` 降序、再按当日 `count` 降序。

## 5. 报告中全部三级标签数据（逐项可复算，逐项附 ES 语句）

以下数量全部来自：  
`已标注数据行集` 中“三级标签集合”包含该标签的行数；  
占比来自 `该标签行数 / 所属一级问题总量`。  
每一行都附了对应 ES 语句（该行位置即该行数据来源）。

| 一级模块 | 三级标签 | 报告数量 | 占该一级问题比例 | 来源中文表头 | 对应 ES 聚合语句 |
| --- | --- | --- | --- | --- | --- |
| 业务体验 | 退订困难/自动续费争议 | 539 | 47.1% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=退订困难/自动续费争议` + `filter primary_labels=业务体验` |
| 业务体验 | 权益无法兑换/使用（如不知如何兑换、兑换失败） | 377 | 33.0% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=权益无法兑换/使用（如不知如何兑换、兑换失败）` + `filter primary_labels=业务体验` |
| 业务体验 | 权益价值感低（如VIP权益可看内容少） | 217 | 19.0% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=权益价值感低（如VIP权益可看内容少）` + `filter primary_labels=业务体验` |
| 业务体验 | 不知情订购 | 144 | 12.6% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=不知情订购` + `filter primary_labels=业务体验` |
| 业务体验 | 订购入口难找 | 109 | 9.5% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=订购入口难找` + `filter primary_labels=业务体验` |
| 使用体验 | 多端体验有差异（操作一致性） | 228 | 51.6% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=多端体验有差异（操作一致性）` + `filter primary_labels=使用体验` |
| 使用体验 | 直播无法回看 | 90 | 20.4% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=直播无法回看` + `filter primary_labels=使用体验` |
| 使用体验 | 功能、活动等入口难找 | 87 | 19.7% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=功能、活动等入口难找` + `filter primary_labels=使用体验` |
| 使用体验 | 播放卡顿（含缓冲慢） | 56 | 12.7% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=播放卡顿（含缓冲慢）` + `filter primary_labels=使用体验` |
| 使用体验 | 音画不同步 | 9 | 2.0% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=音画不同步` + `filter primary_labels=使用体验` |
| 内容体验 | 赛事覆盖率低 | 56 | 43.8% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=赛事覆盖率低` + `filter primary_labels=内容体验` |
| 内容体验 | 内容陈旧/更新慢 | 31 | 24.2% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=内容陈旧/更新慢` + `filter primary_labels=内容体验` |
| 内容体验 | 画质效果差 | 27 | 21.1% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=画质效果差` + `filter primary_labels=内容体验` |
| 内容体验 | 视频、资讯资源不足 | 19 | 14.8% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=视频、资讯资源不足` + `filter primary_labels=内容体验` |
| 营销活动 | 奖励/优惠未到账，包括省侧流量、省侧话费、电影券未到账 | 45 | 38.1% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=奖励/优惠未到账，包括省侧流量、省侧话费、电影券未到账` + `filter primary_labels=营销活动` |
| 营销活动 | 活动规则不清晰，找不到 | 43 | 36.4% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=活动规则不清晰，找不到` + `filter primary_labels=营销活动` |
| 营销活动 | 活动奖品发放周期过长，咨询实物奖品发放情况 | 19 | 16.1% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=活动奖品发放周期过长，咨询实物奖品发放情况` + `filter primary_labels=营销活动` |
| 营销活动 | 咨询快递单号，中奖奖品快递单号无法在活动页面查看 | 12 | 10.2% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=咨询快递单号，中奖奖品快递单号无法在活动页面查看` + `filter primary_labels=营销活动` |
| 营销活动 | 询问赛事门票发放时间 | 8 | 6.8% | 一级标签集合、三级标签集合 | `terms tertiary_labels include=询问赛事门票发放时间` + `filter primary_labels=营销活动` |

逐条完整 ES DSL（每条数据都写在对应位置，不单独拆章节）：

- 业务体验 / 退订困难/自动续费争议（539，47.1%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "业务体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "业务体验" } },
      { "term": { "tertiary_labels": "退订困难/自动续费争议" } }
    ] } } }
  }
}
```

- 业务体验 / 权益无法兑换/使用（如不知如何兑换、兑换失败）（377，33.0%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "业务体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "业务体验" } },
      { "term": { "tertiary_labels": "权益无法兑换/使用（如不知如何兑换、兑换失败）" } }
    ] } } }
  }
}
```

- 业务体验 / 权益价值感低（如VIP权益可看内容少）（217，19.0%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "业务体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "业务体验" } },
      { "term": { "tertiary_labels": "权益价值感低（如VIP权益可看内容少）" } }
    ] } } }
  }
}
```

- 业务体验 / 不知情订购（144，12.6%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "业务体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "业务体验" } },
      { "term": { "tertiary_labels": "不知情订购" } }
    ] } } }
  }
}
```

- 业务体验 / 订购入口难找（109，9.5%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "业务体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "业务体验" } },
      { "term": { "tertiary_labels": "订购入口难找" } }
    ] } } }
  }
}
```

- 使用体验 / 多端体验有差异（操作一致性）（228，51.6%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "使用体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "使用体验" } },
      { "term": { "tertiary_labels": "多端体验有差异（操作一致性）" } }
    ] } } }
  }
}
```

- 使用体验 / 直播无法回看（90，20.4%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "使用体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "使用体验" } },
      { "term": { "tertiary_labels": "直播无法回看" } }
    ] } } }
  }
}
```

- 使用体验 / 功能、活动等入口难找（87，19.7%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "使用体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "使用体验" } },
      { "term": { "tertiary_labels": "功能、活动等入口难找" } }
    ] } } }
  }
}
```

- 使用体验 / 播放卡顿（含缓冲慢）（56，12.7%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "使用体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "使用体验" } },
      { "term": { "tertiary_labels": "播放卡顿（含缓冲慢）" } }
    ] } } }
  }
}
```

- 使用体验 / 音画不同步（9，2.0%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "使用体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "使用体验" } },
      { "term": { "tertiary_labels": "音画不同步" } }
    ] } } }
  }
}
```

- 内容体验 / 赛事覆盖率低（56，43.8%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "内容体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "内容体验" } },
      { "term": { "tertiary_labels": "赛事覆盖率低" } }
    ] } } }
  }
}
```

- 内容体验 / 内容陈旧/更新慢（31，24.2%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "内容体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "内容体验" } },
      { "term": { "tertiary_labels": "内容陈旧/更新慢" } }
    ] } } }
  }
}
```

- 内容体验 / 画质效果差（27，21.1%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "内容体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "内容体验" } },
      { "term": { "tertiary_labels": "画质效果差" } }
    ] } } }
  }
}
```

- 内容体验 / 视频、资讯资源不足（19，14.8%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "内容体验" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "内容体验" } },
      { "term": { "tertiary_labels": "视频、资讯资源不足" } }
    ] } } }
  }
}
```

- 营销活动 / 奖励/优惠未到账，包括省侧流量、省侧话费、电影券未到账（45，38.1%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "营销活动" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "营销活动" } },
      { "term": { "tertiary_labels": "奖励/优惠未到账，包括省侧流量、省侧话费、电影券未到账" } }
    ] } } }
  }
}
```

- 营销活动 / 活动规则不清晰，找不到（43，36.4%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "营销活动" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "营销活动" } },
      { "term": { "tertiary_labels": "活动规则不清晰，找不到" } }
    ] } } }
  }
}
```

- 营销活动 / 活动奖品发放周期过长，咨询实物奖品发放情况（19，16.1%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "营销活动" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "营销活动" } },
      { "term": { "tertiary_labels": "活动奖品发放周期过长，咨询实物奖品发放情况" } }
    ] } } }
  }
}
```

- 营销活动 / 咨询快递单号，中奖奖品快递单号无法在活动页面查看（12，10.2%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "营销活动" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "营销活动" } },
      { "term": { "tertiary_labels": "咨询快递单号，中奖奖品快递单号无法在活动页面查看" } }
    ] } } }
  }
}
```

- 营销活动 / 询问赛事门票发放时间（8，6.8%）

```json
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
    { "exists": { "field": "primary_labels" } }
  ] } },
  "aggs": {
    "primary_total": { "filter": { "term": { "primary_labels": "营销活动" } } },
    "tertiary_exact": { "filter": { "bool": { "must": [
      { "term": { "primary_labels": "营销活动" } },
      { "term": { "tertiary_labels": "询问赛事门票发放时间" } }
    ] } } }
  }
}
```

## 6. 赛事日数据来源（逐项）

- 赛事日日期列表：来自赛事日表“日期”列与主数据“服务时间”按日匹配。  
  主数据 ES 日聚合语句：

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "service_time": { "gte": "2026-03-01", "lt": "2026-04-01" } } },
        { "exists": { "field": "primary_labels" } }
      ]
    }
  },
  "aggs": {
    "daily": {
      "date_histogram": {
        "field": "service_time",
        "calendar_interval": "day",
        "format": "yyyy-MM-dd",
        "min_doc_count": 0
      }
    }
  }
}
```

- 本报告匹配到的 8 个赛事日：  
  `2026-03-06、2026-03-07、2026-03-08、2026-03-13、2026-03-14、2026-03-15、2026-03-20、2026-03-21`  
  匹配规则：`daily.buckets[].key_as_string` 与赛程表“日期”列做等值匹配。

- 赛事摘要文字来源：赛程表“轮次、时间、主队、客队”拼接（该部分不是 ES 计算）。

## 7. 总结类文本来源（含其底层 ES 语句）

| 报告里的总结文字 | 生成方式 | 依赖的中文表头 | 直接来源 ES 语句 |
| --- | --- | --- | --- |
| 核心摘要与发现 | 模型生成（基于聚合） | 服务时间、一级标签集合、二级标签集合、三级标签集合、触发场景-情绪、触发场景-服务类型、客户关键诉求、客服关键处理动作 | 4.1 中“一级/二级/三级/情绪/服务类型聚合语句” |
| 1.1 分析结论 | 程序固定数字 + 业务段模型生成 | 一级标签集合、二级标签集合、三级标签集合、触发场景-情绪、客户关键诉求、客服关键处理动作 | 4.2 中“分析结论”聚合语句 |
| 未标注分析 | 程序规则生成 | 一级标签集合、触发场景-情绪、客户关键诉求、服务提供商名称 | 4.2 中“未标注”聚合语句 |
| 各三级“分析小结” | 模型基于样本生成 | 工单内容/工单投诉内容、处理意见（客服回复）、客户关键诉求、客户诉求关键词、客服关键处理动作、客服处理关键词 | 4.3-B 中“三级标签抽样语句” |
| 各一级末尾“分析小结” | 程序固定前缀 + 模型续写 | 一级标签集合、三级标签集合（前缀数字）+ 上述样本字段（续写） | 4.3-E 中“一级内Top3三级语句” + 4.3-B 抽样语句 |
| 一级标签综合评价 | 模型生成 | 一级标签集合 + 各一级小结 | 4.4 中“primary terms语句” |
| 1.2 分析结论/趋势摘要/异动说明 | 程序规则生成 | 服务时间、触发场景-情绪、三级标签集合、触发场景-服务类型、涉及业务/会员类型_聚类、赛事日表日期/轮次/主队/客队/时间 | 4.5-A 的日聚合语句 |
| 赛事日样例摘要 | 程序规则摘要 | 工单内容/工单投诉内容 + 当日三级标签集合 | 4.5-D 的 `sample_hits` 语句 |

## 8. 最终结论

- 报告中的每个数字都可通过“主数据表中文表头 + 对应 ES 聚合语句 + 行条件”复算得到。
- 报告中的每段总结都可追溯其输入来源（中文表头、对应 ES 语句、样本字段）。

## 9. 中文表头 + 英文字段键值对（完整映射）

> 说明：本节保留源码键名，便于技术复核；上一节中文说明可直接给领导阅读。

| 中文表头 | Canonical Key（源码字段） | 备注 |
| --- | --- | --- |
| 工单编号 | `gd_identity` | 唯一标识、抽样定位 |
| 省份编码 | `province` | 省份编码 |
| 省份名称 | `province_name` | 省份聚合 |
| 服务时间 | `service_time` | 时间过滤、按日聚合 |
| 截止时间 | `end_time` | 未在本报告正文使用 |
| 服务时间到截止时间的耗时（分钟为单位） | `duration_minutes` | 未在本报告正文使用 |
| 开始时间的月份 | `month` | 未在本报告正文使用 |
| 日期 | `day` | 未在本报告正文使用（报告日期来自 `service_time`） |
| 时段 | `time_period` | 本版正文未使用 |
| 具体时间（时:分） | `hour` | 本版正文未使用 |
| 工单内容 | `content` | 原声与样本摘要 |
| 处理意见（客服回复） | `cs_reply` | 客服应对摘要 |
| 反馈思路 | `feedback_thought` | 本版正文未使用 |
| 工单投诉内容 | `complaint_content` | 导入后优先并入 `content` |
| CSP_ID（服务提供商ID） | `csp_id` | 本版正文未使用 |
| CSP_NAME（服务提供商名称） | `csp_name` | 未标注渠道/终端线索 |
| CSP_PROV_ID（服务提供商省份ID） | `csp_prov_id` | 本版正文未使用 |
| CSP_PROV_NAME（服务提供商省份名称） | `csp_prov_name` | 本版正文未使用 |
| 标签组 | `label_group` | 本版正文未使用 |
| 一级标签集合 | `primary_labels` | 一级分布、已标注判定 |
| 二级标签集合 | `secondary_labels` | 二级分布 |
| 三级标签集合 | `tertiary_labels` | 三级分布、Top痛点 |
| 触发场景-赛事/事件 | `scene_event` | 赛事补充线索 |
| 触发场景-情绪 | `scene_emotion` | 情绪分布、负向占比 |
| 触发场景-服务类型 | `scene_service_type` | 服务类型热点 |
| 洞察维度 | `insight_dimension` | 本版正文未使用 |
| 客户关键诉求 | `customer_key_appeal` | 未标注诉求、证据聚合 |
| 客户诉求关键词 | `customer_keywords` | 三级总结补充 |
| 客服关键处理动作 | `cs_key_action` | 证据聚合、客服总结 |
| 客服处理关键词 | `cs_keywords` | 三级总结补充 |
| 是否有退费诉求 | `has_refund_demand` | 本版正文未展开 |
| 是否有升级投诉倾向 | `has_escalation` | 本版正文未展开 |
| 模型推理说明 | `model_reasoning` | 本版正文未使用 |
| 比赛信息 | `match_info` | 可派生 `match_label` |
| 运营举措 | `operation_action` | 本版正文未展开 |
| 隐性需求描述 | `latent_need` | 本版正文未展开 |
| 隐性需求理由 | `latent_need_reason` | 本版正文未展开 |
| 涉及业务/会员类型_聚类 | `biz_member_cluster` | 异动节点业务热点 |
| 年龄 | `age` | 本版正文未展开 |
| 性别 | `gender` | 本版正文未展开 |
| 营销活动页面名称 | `marketing_activity_page` | 本版正文未展开 |
| 营销活动匹配状态 | `marketing_activity_match_status` | 本版正文未展开 |
| 营销活动匹配关键词 | `marketing_activity_match_keywords` | 本版正文未展开 |
| 营销活动匹配说明 | `营销活动匹配说明` | 无别名映射，未入本版聚合 |

## 10. 赛事日表中文表头 + 解析字段

| 赛事表中文表头 | 解析后字段 | 用途 |
| --- | --- | --- |
| 轮次 | `rounds[]` | 赛事摘要前缀（第X轮） |
| 日期 | `day_key` | 作为 `daily.date` 匹配键 |
| 主队 | `matches[].home` | 赛事摘要 |
| 客队 | `matches[].away` | 赛事摘要 |
| 城市 | `matches[].city` | 赛事背景 |
| 时间 | `matches[].time` | 赛事摘要 |

## 11. 报告关键数据的源码键路径（Key Path）

| 报告数据 | Key Path | 计算说明 |
| --- | --- | --- |
| 总服务数据量 2193 | `result.total_with_unlabeled` | `service_time` 过滤后的总命中 |
| 已标注总量 1613（内含于统计） | `result.total` | `exists primary_labels` 后总命中 |
| 一级分布表 | `result.primary[]` | terms(`primary_labels`) |
| 二级分布 | `result.secondary[]` | terms(`secondary_labels`) |
| 三级分布 | `result.tertiary[]` | terms(`tertiary_labels`) |
| 情绪分布 | `result.emotion[]` | terms(`scene_emotion`) |
| 每日问题量/负向占比 | `result.daily[]` | date_histogram(`service_time`) + filter(负向情绪) |
| 每日Top三级 | `result.daily[i].top_tertiary[]` | terms(`tertiary_labels`) |
| 异动节点 | `result.anomalies[]` | `growth>=0.5 && count>=5` |
| 赛事日标记 | `result.daily[i].is_matchday` | 赛程“日期”与 `daily.date` 匹配 |
| 赛事摘要 | `result.daily[i].matchday.match_summary` | 轮次+时间+主客队拼接 |
| 一级下诉求分布 | `primary_top_tertiary_items(...)` | canonical 三级映射 + `result.tertiary` |
| 三级分析小结 | `narratives.tertiary_cause_detail[]` | 对应三级标签证据样本经 LLM 总结 |
| 一级末尾分析小结 | `narratives.primary_summaries[]` | 前缀固定数字 + LLM续写 |
| 一级综合评价两段 | `narratives.primary_overall_evaluation[]` | LLM 总结 |
| 趋势分析结论 | `narratives.trend_conclusion[]` | fallback 规则生成 |
| 异动总结 | `narratives.anomaly_summary[]` | fallback 规则生成 |

## 12. 源码函数级溯源（Function Trace）

| 章节/模块 | 主函数 | 依赖函数 |
| --- | --- | --- |
| 数据导入与字段映射 | `excel_loader._row_to_document` | `FIELD_ALIASES`、多值拆分 |
| 汇总聚合 | `aggregations.run_overall_aggregations` | `normalize_aggregations` |
| 未标注分析 | `run_unlabeled_analysis` / `run_unlabeled_trend_analysis` | `normalize_unlabeled_*` |
| 赛事日注入 | `schedule_loader.enrich_result_with_schedule` | `load_schedule_context` |
| 证据抽样 | `evidence.fetch_tertiary_evidence_for_labels` | `_sample_body_for_label` |
| 文案生成 | `narrative_builder.build_report_narratives` | `_build_executive_summary`、`_build_primary_level_summaries`、`_build_tertiary_cause_detail_llm` |
| Markdown渲染 | `markdown_renderer.render_markdown_report` | `_primary_detail_breakdown_md`、`_daily_detail_table`、`_trend_voice_markdown`、`_anomaly_table` |

## 13. 复杂口径补充（中英双轨）

- 中文口径：  
  “当日问题量”=当日已标注工单数（按“服务时间”聚合）；“负向占比”=当日负向情绪工单数/当日问题量。
- English Key 口径：  
  `day.count` = doc_count of `date_histogram(service_time)` under labeled query;  
  `day.negative_ratio` = `day.negative.doc_count / day.count`.
- 中文口径：  
  “主要问题占比（赛事日样例）”=该日某三级问题提及量/该日问题量。
- English Key 口径：  
  `_tag_counts(day.top_tertiary, total=day.count)` in `markdown_renderer._trend_voice_markdown()`.
- 中文口径：  
  “异动节点占比”全部以该日问题量为分母，且多标签可重复，合计可超过100%。
- English Key 口径：  
  `_anomaly_table(...): _tag_counts(..., total=day_total)` where `day_total=day.count`.
