# REFLECTION.md — 反思报告

> 本报告由学生本人撰写，基于 AI4SE 期末项目 Coding Agent Harness 的完整开发过程。

---

## 一、Superpowers 技能：哪些发挥了最大作用，哪些"形式大于实质"

### 最大作用的技能

**Brainstorming** 是整个过程最有价值的技能。它强制追问模糊点，把"做一个安全的编码 agent"这种模糊想法转化为有 11 个章节的完整 SPEC。在六个关键决策点（语言、供应商、重点维度、分发、WebUI、任务范围），它每次都要求我做出明确选择并提供理由。没有这个技能，我大概率会跳过"为什么选治理而不是记忆"这种深度思考，直接进入实现。

**Subagent-Driven Development** 是效率放大器。14 个 task 通过两批并行分发（Task 3-7 和 Task 9-14），将线性 14 步压缩到约 4 步。每个 subagent 带着精确的 task brief 和独立上下文开始工作，不会受到之前 task 的上下文污染。Review 环节在 Task 3 中发现了 `config.api_key` 不存在的 Critical 问题——如果跳过 review，这个 bug 会在后续 task 中引发连锁错误。

**Writing-Plans** 的"完整代码示例"策略出人意料地有效。PLAN 中每个 task 都包含完整的测试代码和实现代码，subagent 的工作从"设计 + 实现"变成了"转录 + 验证 + 修正"。这极大地降低了 subagent 偏离主题的概率。

### 形式大于实质的技能

**TDD 强制**在某些场景下感觉形式化。对于纯脚手架任务（Task 1），没有测试可写，但流程仍然要求"先写测试、确认失败、再写实现"——这变成了走过场。对于 plan 已经提供了完整代码的 task，TDD 的"红-绿-重构"循环中，"红"这一步是人为制造的：你已经知道代码会通过测试，但还是得先跑一次失败。

**Test-Driven Development** 技能本身的设计假设是"你有一个模糊的需求，通过测试来澄清"，但在 subagent-driven 流程中，需求已经通过 SPEC 和 PLAN 澄清了，测试只是验证手段而非设计工具。

---

## 二、TDD 在 AI 协作下：阻碍还是放大器？

**总体是放大器，但有前提条件。**

当 PLAN 提供了完整代码时，TDD 的"红-绿"循环主要是形式验证——确保 subagent 没有在转录代码时出错。在 Task 3（LLM 抽象）中，TDD 的价值体现在 MockLLM 的测试上：`test_mock_cycles_through_responses` 和 `test_mock_call_history` 这些测试确实驱动了 MockLLM 的设计——你需要决定"响应序列用完后是重复最后一个还是抛出异常"。

当 PLAN 的代码示例有缺陷时，TDD 变成了真正的设计工具。Task 6（治理）的测试 `test_guardrail_allows_safe_commands` 暴露了命令分类器对"安全命令"的定义不够精确——`echo hello` 是安全的，但 `echo "rm -rf /"` 呢？这迫使我们在分类器的设计中加入"只检查命令本身，不检查参数中的字符串"的明确规则。

但 TDD 的"重构"步骤在 AI 协作中几乎完全缺失。Subagent 写完通过测试的代码后就停止了，没有人会主动说"这段代码虽然通过了测试，但可以重构得更简洁"。这是因为 PLAN 中的代码已经是"最终版本"——但这不是 TDD 的本意。

---

## 三、Subagent-Driven 工作流的自主运行能力

Subagent 在收到清晰的 task brief 后，能自主运行约 5-10 分钟而不偏离主题。Task 8（Agent 主循环）是最复杂的 task，subagent 自主完成了 12 个测试的实现，期间自行修正了 3 处测试问题（blocked action 索引、retry 响应格式、HITL 路径触发），没有请求人工干预。

但 subagent 的自主性有明确的边界：
1. **接口不一致时无法自行判断**：Task 3 的 `config.api_key` 问题，subagent 选择按 PLAN 代码实现，而不是质疑接口设计
2. **跨 task 影响无法感知**：Task 4 移除了 `llm.py` 中的 `Message` 类，但 Task 3 的 subagent 不知道这个变更，可能导致后续冲突
3. **对"偏离"的容忍度不一致**：Task 5 的 subagent 在测试字符串与 brief 不一致时选择了修正代码而非修正测试，而 Task 8 的 subagent 做了相反的选择

**最优 task 颗粒度**：一个 task 应该恰好覆盖一个文件的创建或修改，包含 3-8 个测试。如果 task 涉及 2 个以上文件（如 Task 8 需要集成所有模块），subagent 的偏离概率会显著增加。如果 task 只有 1-2 个测试（如 Task 11 的 WebUI），subagent 会觉得"太简单"而倾向于添加额外功能（YAGNI 违规）。

---

## 四、SPEC/PLAN 质量如何影响实现质量

**具体案例：`config.api_key` 接口不一致**

PLAN 的 Task 3（LLM 模块）中，`DeepSeekAdapter.__init__` 的代码示例写成：
```python
self.client = OpenAI(api_key=config.api_key, ...)
```

但 PLAN 的 Task 9（CLI 模块）中，调用方式写成：
```python
llm=DeepSeekAdapter(api_key=api_key, config=config)
```

这两个 task 由不同的 subagent 实现，Task 3 的 subagent 严格按 task brief 的代码实现，使用了 `config.api_key`。但 Config 数据类中根本没有 `api_key` 字段——这是 PLAN 中的设计缺陷：API key 不应该存在 Config 中（这是安全需求），但 PLAN 的 Task 3 代码示例没有反映这一点。

这个不一致在 batch review 中被发现并修复（commit `2494ab3`），但它完美地展示了"规约不清导致 subagent 偏离"的因果链：SPEC 说"凭据不存储于配置"，PLAN 的 Task 3 代码却引用了 `config.api_key`，subagent 选择信任代码而非 SPEC。

**教训**：PLAN 中的代码示例是 SPEC 的"编译产物"。如果 SPEC 和 PLAN 代码冲突，subagent 会优先信任代码。因此，PLAN 的代码示例必须在全 task 范围内保持接口一致性，不能有"这个 task 先这样写，后面再修正"的侥幸心理。

---

## 五、最有效的 Prompt/Context 策略

**策略 1：完整代码示例优于自然语言描述**

当 PLAN 中包含完整的测试代码和实现代码时，subagent 的产出质量最高。Task 6（治理）的 brief 包含 370 行完整代码，subagent 的产出与预期几乎完全一致，只有 2 处微小修正。相比之下，Task 8（Agent 主循环）的 brief 有 342 行但代码中包含了需要跨模块理解的接口调用，subagent 需要自行修正 3 处测试问题。

**策略 2：独立上下文优于共享上下文**

每个 subagent 只接收 task brief 和必要的接口信息，不接收其他 task 的实现细节。这避免了上下文污染——subagent 不会因为"看到"了其他模块的实现而产生不正确的假设。

**策略 3：显式标注接口依赖**

在 dispatch prompt 中显式标注"DeepSeekAdapter 现在接受 `api_key` 作为独立参数"，比让 subagent 自己从代码中推断更可靠。Task 8 的 dispatch 中包含了这个标注，subagent 正确使用了新接口签名。

---

## 六、凭据与分发：迫使我想清楚的问题

**凭据安全**迫使我想清楚了一个关键问题：**API key 的生命周期是什么？** 它不只是"不硬编码"——它涉及到：
- 录入：首次运行时如何安全获取（隐藏输入）
- 存储：在哪里存储（keyring vs .env vs 环境变量）
- 查看：如何显示状态而不泄露明文（只显示前 4 后 4 位）
- 更新：如何安全替换
- 清除：如何彻底删除
- 分发：在 Docker 容器中，keyring 不可用怎么办（.env 回退 + 明文风险说明）

这些细节在 SPEC 的"凭据威胁模型"一节中被系统化地梳理了。如果没有这个要求，我大概率会偷懒用环境变量然后说"README 里写了要设置"。

**Docker 分发**迫使我想清楚了"别人如何运行我的项目"。这不是 `pip install` 就完事——它需要：
- 宿主机依赖（ripgrep）
- 工作目录挂载
- API key 在容器中的安全传递（不能用 `-e`，因为会进入 shell history）
- 端口映射

这些工程细节在"只有我自己用"的项目中永远不会被认真对待。

---

## 七、如果重做，我会改变什么

1. **先做冷启动验证再做实现**：我的冷启动验证是在实现完成后做的，失去了它作为"规约质量检查"的本来价值。如果重做，我会在 PLAN 完成后立即用不同 agent 验证 1-2 个 task，根据发现修订 SPEC/PLAN，然后再开始实现。

2. **PLAN 的代码示例应该经过"跨 task 接口一致性检查"**：`config.api_key` 问题如果有一个自动化的接口一致性检查（类似编译器的类型检查），可以在 PLAN 阶段就被发现。

3. **治理维度可以更深入**：当前的三级护栏 + HITL 状态机是"基础深入"，但如果重做，我会加入沙箱执行的实际实现（`chroot` 或 Windows Job Object），以及护栏规则的动态学习（从历史拦截中提取新模式）。

4. **给 subagent 更多"质疑权"**：当前的 dispatch 流程中，subagent 被要求"严格按 PLAN 实现"，这压制了它们发现 PLAN 问题时的主动反馈。应该在 dispatch 中增加"如果发现 PLAN 与 SPEC 不一致，暂停并报告"的指令。

---

## 八、对 Superpowers 方法论的批判

### 它假设了什么

Superpowers 假设了以下前提：
1. **SPEC 和 PLAN 是"真理的源头"**：所有 subagent 的工作都基于 SPEC 和 PLAN，如果这两者有缺陷，所有下游产出都会受污染
2. **Task 可以独立执行**：每个 task 由独立 subagent 完成，不需要理解其他 task 的实现细节
3. **Review 可以捕获所有缺陷**：两阶段 review（spec 合规 + 代码质量）足以发现所有问题
4. **人类 reviewer 有足够的技术判断力**：review 结果需要人类裁决"哪些是真正的缺陷，哪些是 PLAN 本身的问题"

### 这些假设在我的项目里成立吗

**假设 1 部分成立**。SPEC 和 PLAN 确实定义了项目边界，但 SPEC 与 PLAN 之间的一致性没有自动检查机制。`config.api_key` 问题就是 SPEC 说"API key 不存于 Config"而 PLAN 代码却引用了 `config.api_key`——这种不一致在当前的 workflow 中没有被系统性地检测。

**假设 2 基本成立**。Task 3-7 和 Task 9-14 的并行分发验证了"独立 task 可以并行执行"的假设。但 Task 4 和 Task 3 的 Message 类去重操作表明，即使是"独立"的 task 之间也存在隐式依赖（共享的数据类型）。

**假设 3 不成立**。Review 发现了 `config.api_key` 问题，但 review 本身也有限制：reviewer 只看到 diff，看不到跨 task 的一致性。如果两个 task 的 diff 分别正确但组合起来不一致（如 Task 3 使用 `config.api_key` 而 Task 9 使用 `api_key` 参数），单 task review 无法发现。

**假设 4 部分成立**。我作为 reviewer 需要判断 review 发现是否是真正的缺陷。Task 2 的 review 发现 `load_config` 静默忽略未知 YAML key，但这是因为 PLAN 代码就是这样写的，不是实现错误。这种判断需要技术判断力，而这些判断力恰恰是 Superpowers 试图"自动化"的部分。

### 最根本的批判

Superpowers 的价值主张是"用流程纪律替代人的判断力"。但在这个项目中，最关键的几个决策——选哪个维度深入、如何定义危险命令、HITL 的超时设为多少——都不是流程能替你做决定的。流程能保证"你不会跳过 review"，但不能保证"review 的判断是正确的"。当一个工程师的真正价值在于"做什么"和"做对了吗"这两个问题时，流程脚手架守住了纪律，但没有——也不可能——替代判断力本身。

这正是这门课最想教给我的东西。

---

*本报告由学生本人撰写，AI 辅助润色。*