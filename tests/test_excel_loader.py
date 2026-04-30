from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from overall_situation_agent.excel_loader import load_tagged_feedback


class ExcelLoaderTests(unittest.TestCase):
    def test_chinese_only_new_headers_map_to_standard_fields(self) -> None:
        headers = [
            "工单编号",
            "省份编码",
            "省份名称",
            "服务时间",
            "服务截至时间",
            "服务时间到截止时间的耗时（分钟为单位）",
            "开始时间的月份",
            "日期",
            "时段",
            "具体时间（时:分）",
            "工单内容",
            "工单投诉内容",
            "标签组",
            "一级标签集合",
            "二级标签集合",
            "三级标签集合",
            "触发场景-服务类型",
            "洞察维度",
            "客户关键诉求",
            "客服关键处理动作",
            "比赛信息",
            "运营举措",
            "隐性需求描述",
            "涉及业务/会员类型_聚类",
            "营销活动页面名称",
            "营销活动匹配状态",
            "营销活动匹配关键词",
            "年龄",
            "性别",
        ]
        values = [
            "GD001",
            "240",
            "辽宁",
            "2026-03-01 10:00:00",
            "2026-03-01 10:30:00",
            30,
            "2026-03",
            1,
            "上午",
            "10:15",
            "普通工单内容",
            "投诉内容优先",
            '[{"一级标签":"营销活动","二级标签":"奖品发放","三级标签":["快递单号查询"]}]',
            "业务体验",
            "权益使用",
            "权益无法兑换/使用",
            "投诉",
            "用得亏",
            "要求退费",
            "解释规则并拒绝退费",
            '{"日期":"2026-03-01","主队":"A队","客队":"B队"}',
            "足球通首月5折活动",
            "希望权益更清楚",
            "中超赛季包",
            "活动页A",
            "已匹配",
            "足球通、首月5折",
            "35",
            "男",
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "打标结果"
            sheet.append(headers)
            sheet.append(values)
            workbook.save(path)

            records = load_tagged_feedback(path)

        self.assertEqual(len(records), 1)
        doc = records[0]
        self.assertEqual(doc["gd_identity"], "GD001")
        self.assertEqual(doc["content"], "投诉内容优先")
        self.assertEqual(doc["end_time"], "2026-03-01 10:30:00")
        self.assertEqual(doc["duration_minutes"], 30.0)
        self.assertEqual(doc["duration_hours"], 0.5)
        self.assertEqual(doc["hour"], 10)
        self.assertEqual(doc["label_group"], ["营销活动 / 奖品发放 / 快递单号查询"])
        self.assertEqual(doc["primary_labels"], ["业务体验"])
        self.assertEqual(doc["marketing_activity_match_keywords"], ["足球通", "首月5折"])
        self.assertEqual(doc["age"], 35)
        self.assertEqual(doc["gender"], "男")
        self.assertEqual(doc["marketing_activity_page"], "活动页A")
        self.assertEqual(doc["marketing_activity_match_status"], "已匹配")
        self.assertEqual(doc["biz_member_cluster"], ["中超赛季包"])
        self.assertEqual(doc["match_label"], ["2026-03-01 A队 vs B队"])


if __name__ == "__main__":
    unittest.main()
