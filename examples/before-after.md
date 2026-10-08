# 中文改写实例

标注格式:`违反规则` 用 SKILL.md 里的规则名。例 1、2、6 取自本机真实语料(存储分析记忆文件),
其余是构造例。同文件里既有好例子也有坏例子,所以本文件自检必然报错——那是预期。

---

## 例 1 · 接口模式:流水句 + 分号 + 施事不明

命中的规则:`sentence-len`(71 汉字)、`semicolon`、流水句

**原文**

> **已补丁 server.py(两处,Windows 适配)**:① do_POST 二级护栏 roots 原来只有 `(HOME, "/Applications")`,
> Windows 上红灯 app_paths(Program Files)和回收站(C:\$Recycle.Bin)的 open 按钮会被自家护栏 403 拒绝——
> 现在 win 分支追加 ProgramFiles/ProgramFiles(x86)/$Recycle.Bin 三个 root(仅影响 open,rm/trash 白名单从不含这些路径);
> ② open_in_file_manager win 分支对 $Recycle.Bin 特判改用 `explorer shell:RecycleBinFolder`。

**改写**

> server.py 改了两处,适配 Windows:
>
> 1. do_POST 的二级护栏 roots 原先是 `(HOME, "/Applications")`。Windows 上,红灯项里的 app_paths
>    (Program Files)和回收站(C:\$Recycle.Bin)的 open 按钮会被自家护栏 403 拒绝。
>    现在 win 分支追加 ProgramFiles、ProgramFiles(x86)、$Recycle.Bin 三个 root。
>    这个改动只影响 open,rm/trash 白名单从没包含这些路径。
> 2. open_in_file_manager 的 win 分支对 $Recycle.Bin 特判,改用 `explorer shell:RecycleBinFolder`。
>    直接传裸路径会打开 SID 目录视图。

改动:一句拆成编号列表;分号拆句;补上「server.py 改了两处」把施事和范围说清。

---

## 例 2 · 接口模式:零主语 + 意义被动

命中的规则:零主语、意义被动

**原文**

> **中文路径 mojibake 已解决**(2026-09-29 复测):之前中文目录名 GBK 解码错误(「金山文档」变乱码),
> 根因是 Windows 控制台/重定向默认编码。

**改写**

> 加 `PYTHONUTF8=1 python -X utf8` 之后,scan.py 能正确解码中文目录名。
> 在此之前,中文目录名按 GBK 解码(「金山文档」变成乱码),根因是 Windows 控制台与重定向的默认编码。

改动:谁解决了、怎么解决的写出来;「已解决」这种意义被动换成动作;顺带把「之前」的分界说清。

---

## 例 3 · 接口模式:空动词 + 名词化

命中的规则:`empty-verb`

| 原文 | 改写 |
|---|---|
| 对结果进行验证 | 验证结果 |
| 作出判断后再执行 | 判断后再执行 |
| 予以确认 | 确认 |
| 对配置加以修改 | 修改配置 |

名词化的动作把施事藏起来了。「进行验证」看不出谁验证,「验证结果」也没有——但至少主语必须写出来。

---

## 例 4 · 文风模式:套话 → 具体数字

命中的规则:套话与空泛形容词、没有数字的「显著提升」

**原文**

> 该方案赋能企业实现全方位降本增效,打造一站式智能运营闭环,效率显著提升。

**改写**

> 该方案把对账耗时从 6 小时压到 20 分钟,财务团队每天少加 2 小时班。

改动:一个数字顶掉四个形容词。原文的信息量是零——每句话都在宣称,没有一句在陈述。
没有数字可填时,正确做法是删掉整句,不是换个说法。

---

## 例 5 · 接口模式:情态必须保住(错例示范)

这是最容易犯的错,单独列出来。情态是作者给出的置信度,**是内容**。

| 原文 | 错误改写 | 为什么错 | 正确改写 |
|---|---|---|---|
| 请求可能已失败 | 请求已失败 | 把不确定升格成断言 | 请求可能已失败 |
| 大概率是残留文件 | 是残留文件 | 丢掉了 90% 这个判断 | 大概率是残留文件 |
| 该值约 3.5GB | 该值为 3.5GB | 把估算说成实测 | 该值约 3.5GB(估算) |
| 此行为未实测 | 此行为正常 | 把未知说成已知 | 此行为未实测,需确认 |

改写让句子变短变顺,顺手就升级了断言——这是「更短」压过「更准」的时候。
读起来别扭的原文可能只是丑,改完变成假话就是废。

---

## 例 6 · 接口模式:数据流水句 → 表格

命中的规则:`comma-run`(单句 11 个逗号)

**原文**

> 其他大户:Roaming\TRAE SOLO CN 3.5GB(已从上次的 vm\tools 变成 ai-agent\vm,仍是在用运行时非残留)、
> Roaming\Tencent 3.5GB(新版 xwechat 1.98GB + WeMeet 673MB + 旧版 WeChat 621MB,新旧微信并存)、
> Orca 4.0GB(四处分摊)、.codex 1.8GB、.rustup 2.9GB(MSVC 1.3GB + GNU 1.5GB 两套并存)。

**改写**

| 路径 | 占用 | 备注 |
|---|---|---|
| Roaming\TRAE SOLO CN | 3.5GB | 在用运行时,非残留;已从 vm\tools 变成 ai-agent\vm |
| Roaming\Tencent | 3.5GB | 新版 xwechat 1.98GB + WeMeet 673MB + 旧版 WeChat 621MB |
| Orca | 4.0GB | 四处分摊 |
| .codex | 1.8GB | |
| .rustup | 2.9GB | MSVC 1.3GB + GNU 1.5GB 两套并存 |

改动:同一结构的并列数据一律进表格。逗号串联的并列项,读者要自己数到第几个才找到目标。