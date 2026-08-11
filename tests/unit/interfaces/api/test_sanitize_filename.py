"""sanitize_filename 单元测试 — P2-14 uploads 乱码清理

审查 E4/CONFIRMED: uploads/ 含历史编码 bug 残留乱码文件名
`1£¨¸ß·Ö£©.mp3` (GBK 字节被误按 Latin-1 解码 → 往返可恢复)。

本组测试驱动三项修复:
1. NFC 规范化 — 分解形式 (e + combining acute) 统一为预组合 é,
   消除 macOS(NFD) 与 Windows(NFC) 落盘字节不一致导致的同名不同字节
2. GBK 乱码往返恢复 — latin-1 → gbk, 仅当恢复结果含 CJK 才接受
   (防止误伤合法 latin-1 文件名如 café)
3. 既有行为保持 — 非法字符剥离 / 空名回退 / 中文保留
"""

import pytest

from backend.interfaces.api.routes.assessment import sanitize_filename


class TestNfcNormalization:
    """P2-14: Unicode 规范化 — 分解/预组合形式统一"""

    def test_decomposed_latin_combining_normalized_to_nfc(self):
        """macOS NFD 分解形式 café → NFC 预组合 café"""
        assert sanitize_filename("café.mp3") == "café.mp3"

    def test_fully_precomposed_unchanged(self):
        """已是 NFC 的名字原样返回 (幂等)"""
        assert sanitize_filename("café.mp3") == "café.mp3"


class TestMojibakeRecovery:
    """P2-14: GBK 乱码往返恢复 — 历史残留可迁移"""

    def test_gbk_mojibake_recovered(self):
        """1£¨¸ß·Ö£© (GBK 误按 Latin-1) → 1（高分）"""
        assert sanitize_filename("1£¨¸ß·Ö£©.mp3") == "1（高分）.mp3"

    def test_long_mojibake_recovered(self):
        """³ÂÞÈÑ¸ÄÑÌýÖ®Éù£¨µÍ·Ö£© → 陈奕迅难听之声（低分）"""
        assert (
            sanitize_filename("³ÂÞÈÑ¸ÄÑÌýÖ®Éù£¨µÍ·Ö£©.mp3")
            == "陈奕迅难听之声（低分）.mp3"
        )

    def test_normal_latin1_name_untouched(self):
        """合法 latin-1 文件名不误伤 — café 无 CJK 恢复结果, 原样保留"""
        assert sanitize_filename("café.mp3") == "café.mp3"

    def test_proper_chinese_name_untouched(self):
        """正确 UTF-8 中文名不受影响 (latin-1 编码即失败 → 原样)"""
        assert sanitize_filename("1（高分）.mp3") == "1（高分）.mp3"


class TestExistingBehaviorPreserved:
    """P2-14 重构不得破坏既有行为"""

    def test_strips_windows_illegal_chars(self):
        """<>:\"|?* 非法字符 → _; / \\ 是路径分隔符, 保留 basename 属既有设计
        (Path.stem 语义: 上传 ../x 只取最后段, 防路径穿越纵深防御)
        """
        assert sanitize_filename('a<b>:c"d|g?h*i.mp3') == "a_b__c_d_g_h_i.mp3"

    def test_path_separators_keep_basename(self):
        """/ 和 \\ 按路径分隔符处理, 只保留最后一段 (防路径穿越)"""
        assert sanitize_filename("../../secret.mp3") == "secret.mp3"

    def test_empty_name_falls_back(self):
        """纯空白名 → audio_<ts> 回退 (P2-14: 尾随空格文件名在 Windows
        落盘会被静默去尾空格, 造成显示名与落盘名不一致)"""
        name = sanitize_filename("   .mp3")
        assert name.startswith("audio_") and name.endswith(".mp3")

    def test_chinese_retained(self):
        assert sanitize_filename("中文歌曲测试.mp3") == "中文歌曲测试.mp3"

    def test_extension_preserved(self):
        assert sanitize_filename("voice.wav").endswith(".wav")

    def test_dot_only_stem_falls_back(self):
        """`..`/`...` 裸点 stem 若拼接会解析为父目录 → 回退 audio_<ts>
        (审查 MEDIUM: regex 不匹配 `.`, strip('.') 纵深防御)"""
        assert sanitize_filename("..").startswith("audio_")
        name = sanitize_filename("....mp3")
        assert name.startswith("audio_") and name.endswith(".mp3")

    def test_leading_dots_leading_to_path_stripped(self):
        """`..secret.mp3` stem 去前导点 → secret.mp3 (防御 resolve 上溯)"""
        assert sanitize_filename("..secret.mp3") == "secret.mp3"

    def test_legit_inner_dots_preserved(self):
        """合法内部点号不受影响 — 仅剥离首尾点"""
        assert sanitize_filename("v1.2.mp3") == "v1.2.mp3"
